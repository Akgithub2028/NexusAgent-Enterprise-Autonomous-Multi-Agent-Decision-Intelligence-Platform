"""Authenticated HTTPS checks and bounded latency sampling; emit no queries or answers."""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import time
import uuid
from collections.abc import Callable
from contextlib import suppress
from pathlib import Path
from urllib.parse import urlsplit

import httpx

from decision_agent.api.public_demo import COOKIE_NAME, EXECUTE_ENDPOINT, SESSION_ENDPOINT

CASE_IDS = (
    "m9-knowledge-fact-001",
    "m9-data-aggregate-005",
    "m9-mixed-inventory-007",
    "m9-knowledge-unanswerable-003",
)


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    rank = (len(ordered) - 1) * fraction
    low = math.floor(rank)
    return ordered[low] + (ordered[math.ceil(rank)] - ordered[low]) * (rank - low)


async def measure(
    origin: str, token: str | Callable[[], str], cases: list[dict], repeats: int
) -> dict:
    parsed = urlsplit(origin)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or not parsed.hostname.endswith(".run.app")
        or parsed.netloc != parsed.hostname
        or parsed.path
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("exact Cloud Run HTTPS origin required")
    if not 2 <= repeats <= 3:
        raise ValueError("bounded sampling requires two or three repeats")

    async def request_headers():
        value = await asyncio.to_thread(token) if callable(token) else token
        return {"X-Serverless-Authorization": "Bearer " + value, "Origin": origin}

    health_times = []
    results = []
    stopped = asyncio.Event()
    # Use a separate connection: service concurrency=2 leaves one slot for health while
    # sequential requests execute. Concurrent pairs are checked separately below.
    async with httpx.AsyncClient(base_url=origin, timeout=270, follow_redirects=False) as monitor:
        unauthenticated = await monitor.get("/health")
        if unauthenticated.status_code not in (401, 403):
            raise ValueError("service is publicly invokable")
        for path in ("/health", "/ready", "/", "/assets/app.js"):
            response = await monitor.get(path, headers=await request_headers())
            if response.status_code != 200:
                raise ValueError("runtime or UI unavailable")

        async def health_loop():
            while not stopped.is_set():
                start = time.perf_counter()
                response = await monitor.get("/health", headers=await request_headers(), timeout=10)
                if response.status_code != 200:
                    raise ValueError("health failed during inference")
                health_times.append(time.perf_counter() - start)
                with suppress(TimeoutError):
                    await asyncio.wait_for(stopped.wait(), timeout=1)

        async def bootstrap(client):
            response = await client.get(SESSION_ENDPOINT, headers=await request_headers())
            cookie = response.headers.get("set-cookie", "").lower()
            if response.status_code != 200 or not all(
                x in cookie for x in ("secure", "httponly", "samesite=strict")
            ):
                raise ValueError("secure visitor bootstrap failed")
            return client.cookies.get(COOKIE_NAME)

        async def execute(client, case, session):
            start = time.perf_counter()
            response = await client.post(
                EXECUTE_ENDPOINT,
                headers=await request_headers(),
                json={
                    "request_id": uuid.uuid4().hex,
                    "session_id": session,
                    "query": case["question"],
                },
            )
            elapsed = time.perf_counter() - start
            if response.status_code != 200:
                raise ValueError("execution transport failed")
            body = response.json()
            if (
                body.get("route") != case["expected_route"]
                or body.get("status") != case["expected_final_status"]
            ):
                raise ValueError("route/status acceptance failed")
            if case["expected_final_status"] == "completed" and not body.get("citations"):
                raise ValueError("grounding missing")
            if (
                case["expected_error_codes"]
                and body.get("error_code") not in case["expected_error_codes"]
            ):
                raise ValueError("abstention failed")
            return elapsed, body

        health_task = asyncio.create_task(health_loop())
        await asyncio.sleep(0)
        try:
            for case in cases:
                async with httpx.AsyncClient(base_url=origin, timeout=270) as visitor:
                    await bootstrap(visitor)
                    samples = []
                    session = uuid.uuid4().hex
                    for _ in range(repeats):
                        elapsed, body = await execute(visitor, case, session)
                        samples.append(elapsed)
                    if case["expected_final_status"] == "completed" and (
                        body.get("memory_context_status") != "projected"
                        or body.get("memory_persistence_status") != "persisted"
                    ):
                        # Do not infer visitor isolation from cookie signatures alone.
                        raise ValueError("multi-turn memory was not used")
                    results.append(
                        {
                            "case_id": case["case_id"],
                            "samples": len(samples),
                            "first_request_seconds": samples[0],
                            "p50_seconds": percentile(samples, 0.5),
                            "p95_seconds": percentile(samples, 0.95),
                        }
                    )
        finally:
            stopped.set()
            await health_task
        # Distinct visitors may use the same label without sharing ownership. Pair
        # checks do not poll health: Cloud Run's two transport slots are occupied.
        async with (
            httpx.AsyncClient(base_url=origin, timeout=270) as a,
            httpx.AsyncClient(base_url=origin, timeout=270) as b,
        ):
            cookie_a, cookie_b = await bootstrap(a), await bootstrap(b)
            if cookie_a == cookie_b:
                raise ValueError("visitor identities are shared")
            pair = await asyncio.gather(
                execute(a, cases[0], "same-label"), execute(b, cases[0], "same-label")
            )
            if any(body.get("memory_context_status") != "empty" for _, body in pair):
                raise ValueError("fresh visitors unexpectedly reused history")
            denial = await a.post(
                EXECUTE_ENDPOINT,
                headers={**(await request_headers()), "Origin": "https://wrong.test"},
                json={"request_id": uuid.uuid4().hex, "query": "synthetic"},
            )
            if denial.status_code != 403:
                raise ValueError("origin protection failed")
    return {
        "status": "passed",
        "cases": results,
        "health_samples": len(health_times),
        "health_p95_seconds": percentile(health_times, 0.95),
        "concurrent_request_seconds": [elapsed for elapsed, _ in pair],
        "cold_start_measured": False,
        "peak_rss_measured": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--origin", required=True)
    parser.add_argument("--token-file", type=Path, required=True)
    parser.add_argument("--repeats", type=int, default=2)
    args = parser.parse_args()
    try:
        cases = json.loads(Path("datasets/agent_tasks/m9_final_eval_v1.json").read_text())["cases"]
        cases = [next(c for c in cases if c["case_id"] == name) for name in CASE_IDS]
        result = asyncio.run(
            measure(args.origin, args.token_file.read_text().strip(), cases, args.repeats)
        )
        print(json.dumps(result, sort_keys=True))
        return 0
    except Exception:
        print('{"status":"failed","error_code":"restricted_measurement_failed"}')
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
