"""Restricted command planning refuses widened identity and mismatched releases."""

import copy
from pathlib import Path

import pytest
from scripts.deploy_restricted_revision import SECRETS, build_plan, check_restricted
from scripts.measure_restricted_service import percentile

from decision_agent.ingestion.cloud_job import release_descriptor


@pytest.fixture
def inputs():
    manifest = {
        "corpus_release_id": "test",
        "collection": "nexus_test",
        "parents": 1,
        "children": 2,
    }
    promotion = release_descriptor(
        manifest, "us-west1-docker.pkg.dev/project/repo/app@sha256:" + "a" * 64
    )
    config = {
        "project": "nexus-agent-510512",
        "region": "us-west1",
        "service": "nexusagent",
        "origin": "https://p6---nexusagent-test.run.app",
        "milvus_uri": "https://vectors.test",
        "secret_versions": {s: "1" for s in SECRETS.values()},
    }
    return config, promotion, manifest


def test_command_keeps_traffic_private_and_pairs_release(inputs):
    plan = build_plan(*inputs, Path(".tmp-p6/runtime.json"))
    command = plan["command"]
    assert "--no-traffic" in command and "--no-allow-unauthenticated" in command
    assert "--invoker-iam-check" in command
    assert command[command.index("--min") + 1] == "1"
    assert command[command.index("--timeout") + 1] == "300s"
    assert "nexus-vector-write-token" not in " ".join(command)
    assert plan["environment"]["DECISION_AGENT_MILVUS_COLLECTION"] == "nexus_test"


@pytest.mark.parametrize("change", ["image", "collection", "latest", "write", "origin"])
def test_bad_release_or_identity_fails(inputs, change):
    config, promotion, manifest = copy.deepcopy(inputs)
    if change == "image":
        promotion["image"] = "app:latest"
    elif change == "collection":
        promotion["collection"] = "different"
    elif change == "latest":
        config["secret_versions"]["nexus-groq-key"] = "latest"
    elif change == "write":
        config["secret_versions"]["nexus-vector-write-token"] = "1"
    else:
        config["origin"] = "https://demo.test/"
    with pytest.raises(ValueError):
        build_plan(config, promotion, manifest, Path("unused"))


def test_public_policy_and_incorrect_origin_refused():
    service = {"status": {"traffic": [{"tag": "p6", "url": "https://tag.run.app"}]}}
    check_restricted({}, service, "https://tag.run.app")
    with pytest.raises(ValueError):
        check_restricted({"bindings": [{"members": ["allUsers"]}]}, service, "https://tag.run.app")
    with pytest.raises(ValueError):
        check_restricted({}, service, "https://wrong.run.app")
    assert percentile([1.0, 3.0], 0.5) == 2.0


@pytest.mark.asyncio
async def test_measurement_projection_and_secure_cookie_checks(monkeypatch):
    import json

    import httpx
    from scripts import measure_restricted_service as measurements

    cases = [
        {
            "case_id": "synthetic",
            "question": "private marker",
            "expected_route": "knowledge",
            "expected_final_status": "completed",
            "expected_error_codes": [],
        }
    ]
    visitor_count = 0
    history = set()

    def handle(request):
        nonlocal visitor_count
        if "x-serverless-authorization" not in request.headers:
            return httpx.Response(403)
        if request.url.path.endswith("/session"):
            visitor_count += 1
            return httpx.Response(
                200,
                headers={
                    "set-cookie": f"__Host-nexus-demo=visitor-{visitor_count}; Path=/; Secure; HttpOnly; SameSite=strict"
                },
            )
        if request.url.path.endswith("/execute"):
            if request.headers["origin"] != "https://p6---test.run.app":
                return httpx.Response(403)
            body = json.loads(request.content)
            key = (request.headers.get("cookie"), body["session_id"])
            context = "projected" if key in history else "empty"
            history.add(key)
            return httpx.Response(
                200,
                json={
                    "route": "knowledge",
                    "status": "completed",
                    "citations": ["E1"],
                    "answer": "private marker",
                    "memory_context_status": context,
                    "memory_persistence_status": "persisted",
                },
            )
        return httpx.Response(200, json={"status": "ok"})

    client_class = httpx.AsyncClient
    monkeypatch.setattr(
        measurements.httpx,
        "AsyncClient",
        lambda **kw: client_class(**kw, transport=httpx.MockTransport(handle)),
    )
    result = await measurements.measure(
        "https://p6---test.run.app", lambda: "private-token", cases, 2
    )
    assert result["status"] == "passed"
    assert result["health_samples"] >= 1
    assert "private" not in json.dumps(result)
    assert result["cold_start_measured"] is False and result["peak_rss_measured"] is False


def test_bootstrap_denies_execution_and_does_not_touch_existing_traffic(inputs):
    from scripts.deploy_restricted_revision import bootstrap_plan

    plan = bootstrap_plan(build_plan(*inputs, Path("unused")))
    assert plan["environment"]["DECISION_AGENT_DEPLOYMENT_MODE"] == "private"
    assert "DECISION_AGENT_PUBLIC_DEMO_ORIGIN" not in plan["environment"]
    assert "--no-allow-unauthenticated" in plan["command"]
    assert "--no-traffic" not in plan["command"]
