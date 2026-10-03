"""Serialized P7 release actions; cloud mutations require explicit workflow enablement."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from threading import Lock

from scripts.deploy_restricted_revision import SECRETS, build_plan, gcloud_json
from scripts.measure_restricted_service import CASE_IDS, measure

from decision_agent.ingestion.cloud_job import release_descriptor

ACCEPTANCE_GATES = (
    "billing_and_budget",
    "sql_socket_and_denials",
    "vector_identity_denials",
    "ingestion_repeat",
    "startup_headroom",
    "peak_memory",
    "https_and_grounding",
    "concurrency_and_health",
    "restart_and_overlap",
    "dependency_reconnect",
    "sigterm_and_audit",
    "rollback_and_pause",
)


def require_acceptance(acceptance: dict, candidate: dict) -> None:
    if (
        acceptance.get("schema_version") != 1
        or acceptance.get("status") != "approved"
        or acceptance.get("image") != candidate["image"]
        or set(acceptance.get("gates", {})) != set(ACCEPTANCE_GATES)
        or not all(value is True for value in acceptance["gates"].values())
        or not acceptance.get("evidence")
        or candidate.get("measurement", {}).get("status") != "passed"
    ):
        raise ValueError("managed acceptance incomplete")


def runtime_bindings(config: dict) -> dict:
    return {key: config[key] for key in ("project", "region", "milvus_uri", "secret_versions")}


def command(*args):
    subprocess.run(
        [str(a) for a in args], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )


def capture(*args) -> dict:
    return json.loads(subprocess.check_output([str(a) for a in args], stderr=subprocess.DEVNULL))


def upload(path: Path, uri: str) -> None:
    command("gcloud", "storage", "cp", path, uri, "--if-generation-match=0", "--quiet")


def service_config(config: dict, preview: bool) -> dict:
    return {
        **config,
        "service": config["preview_service"] if preview else config["production_service"],
        "origin": config["preview_origin"] if preview else config["production_origin"],
    }


class IdentityToken:
    """Refresh short-lived HTTPS identity tokens independently of the OAuth session."""

    def __init__(self, project: str, audience: str):
        self._project, self._audience = project, audience
        self._lock = Lock()
        self._value, self._until = "", 0.0

    def __call__(self) -> str:
        with self._lock:
            if time.monotonic() >= self._until:
                self._value = subprocess.check_output(
                    [
                        "gcloud",
                        "auth",
                        "print-identity-token",
                        f"--audiences={self._audience}",
                        f"--impersonate-service-account=nexus-release@{self._project}.iam.gserviceaccount.com",
                    ],
                    stderr=subprocess.DEVNULL,
                    text=True,
                ).strip()
                self._until = time.monotonic() + 120
            return self._value


def candidate(config, image, manifest, directory, run_id):
    project, region = config["project"], config["region"]
    writer_version = str(config["writer_secret_version"])
    if not re.fullmatch(r"[1-9][0-9]*", writer_version):
        raise ValueError("numeric writer secret required")
    env = {
        "NEXUS_RELEASE_IMAGE": image,
        "NEXUS_RELEASE_BUCKET": config["release_bucket"],
        "DECISION_AGENT_MILVUS_URI": config["milvus_uri"],
        "DECISION_AGENT_MILVUS_INDEX_TYPE": "AUTOINDEX",
    }
    env_file = directory / "ingestion.env.json"
    env_file.write_text(json.dumps(env))
    command(
        "gcloud",
        "run",
        "jobs",
        "deploy",
        "nexus-ingestion",
        "--project",
        project,
        "--region",
        region,
        "--image",
        image,
        "--service-account",
        f"nexus-ingestion@{project}.iam.gserviceaccount.com",
        "--command",
        "python",
        "--args=-m,decision_agent.ingestion.cloud_job",
        "--tasks",
        "1",
        "--parallelism",
        "1",
        "--max-retries",
        "0",
        "--task-timeout",
        "900s",
        "--cpu",
        "2",
        "--memory",
        "4Gi",
        "--env-vars-file",
        env_file,
        "--clear-cloudsql-instances",
        "--set-secrets",
        f"DECISION_AGENT_MILVUS_TOKEN=nexus-vector-write-token:{writer_version}",
        "--quiet",
    )
    execution = gcloud_json(
        "run",
        "jobs",
        "execute",
        "nexus-ingestion",
        "--project",
        project,
        "--region",
        region,
        "--wait",
    )
    promotion = capture(
        sys.executable,
        "scripts/prepare_corpus_promotion.py",
        "--project",
        project,
        "--region",
        region,
        "--execution",
        execution["metadata"]["name"],
        "--bucket",
        config["release_bucket"],
        "--image",
        image,
        "--manifest",
        "deploy/cloud-run/corpus-release.json",
    )
    config_file, promotion_file = directory / "preview.json", directory / "promotion.json"
    config_file.write_text(json.dumps(service_config(config, True)))
    promotion_file.write_text(json.dumps(promotion))
    # Preview bootstrap is an operator prerequisite; automatic release never creates
    # services or changes IAM policy. It updates only the existing restricted preview.
    try:
        command(
            sys.executable,
            "scripts/deploy_restricted_revision.py",
            "--config",
            config_file,
            "--promotion",
            promotion_file,
            "--output",
            directory / "candidate",
            "--apply",
        )
        token = IdentityToken(config["project"], config["preview_audience"])
        cases = json.loads(Path("datasets/agent_tasks/m9_final_eval_v1.json").read_text())["cases"]
        selected = [next(c for c in cases if c["case_id"] == name) for name in CASE_IDS]
        measurement = asyncio.run(measure(config["preview_origin"], token, selected, 2))
        record = {
            **promotion,
            "commit": os.environ["RELEASE_SHA"],
            "measurement": measurement,
            "runtime_bindings": runtime_bindings(config),
            "preview_revision": json.loads(
                (directory / "candidate/deployed-service.json").read_text()
            )["status"]["latestReadyRevisionName"],
        }
        path = directory / "candidate.json"
        path.write_text(json.dumps(record, indent=2))
        upload(
            path,
            f"gs://{config['release_bucket']}/candidates/{hashlib.sha256(image.encode()).hexdigest()}/{run_id}.json",
        )
    finally:
        command(
            "gcloud",
            "run",
            "services",
            "update",
            config["preview_service"],
            "--project",
            project,
            "--region",
            region,
            "--min",
            "0",
            "--quiet",
        )


def save_snapshot(service: dict, path: Path) -> None:
    for container in service["spec"]["template"]["spec"]["containers"]:
        for env in container.get("env", []):
            if env["name"] in SECRETS and (
                "value" in env
                or not re.fullmatch(
                    r"[1-9][0-9]*", env.get("valueFrom", {}).get("secretKeyRef", {}).get("key", "")
                )
            ):
                raise ValueError("rollback requires numeric secret references")
    path.write_text(json.dumps(service, indent=2))
    path.chmod(0o600)


def public_release(config, image, manifest, directory, run_id, candidate_run, acceptance):
    if not re.fullmatch(r"[0-9]+", candidate_run):
        raise ValueError("candidate run ID required")
    record = capture(
        "gcloud",
        "storage",
        "cat",
        f"gs://{config['release_bucket']}/candidates/{hashlib.sha256(image.encode()).hexdigest()}/{candidate_run}.json",
    )
    expected = release_descriptor(manifest, image)
    if any(record.get(key) != value for key, value in expected.items()):
        raise ValueError("candidate release mismatch")
    require_acceptance(acceptance, record)
    if record["runtime_bindings"] != runtime_bindings(config):
        raise ValueError("candidate configuration differs")
    # Validate the actual successful ingestion again before any production mutation.
    capture(
        sys.executable,
        "scripts/prepare_corpus_promotion.py",
        "--project",
        config["project"],
        "--region",
        config["region"],
        "--execution",
        record["execution"],
        "--bucket",
        config["release_bucket"],
        "--image",
        image,
        "--manifest",
        "deploy/cloud-run/corpus-release.json",
    )
    common = [
        config["production_service"],
        "--project",
        config["project"],
        "--region",
        config["region"],
    ]
    previous = gcloud_json("run", "services", "describe", *common)
    if previous["status"]["url"] != config["production_origin"]:
        raise ValueError("canonical production origin differs")
    previous_policy = gcloud_json("run", "services", "get-iam-policy", *common)
    snapshot = directory / "previous-production.json"
    save_snapshot(previous, snapshot)
    upload(snapshot, f"gs://{config['release_bucket']}/rollbacks/{run_id}/service.json")
    policy_path = directory / "previous-iam.json"
    policy_path.write_text(json.dumps(previous_policy))
    upload(policy_path, f"gs://{config['release_bucket']}/rollbacks/{run_id}/iam.json")
    plan = build_plan(
        service_config(config, False), record, manifest, directory / "production.env.json"
    )
    plan["command"][plan["command"].index("--tag") + 1] = "release"
    # Keep existing production IAM unchanged while validating the new revision.
    plan["command"].remove("--no-allow-unauthenticated")
    (directory / "production.env.json").write_text(json.dumps(plan["environment"]))
    command(*plan["command"])
    current = gcloud_json("run", "services", "describe", *common)
    revision = current["status"]["latestReadyRevisionName"]
    if revision != current["status"]["latestCreatedRevisionName"]:
        raise ValueError("production candidate not ready")
    tagged_url = next(t["url"] for t in current["status"]["traffic"] if t.get("tag") == "release")
    token = subprocess.check_output(
        [
            "gcloud",
            "auth",
            "print-identity-token",
            f"--audiences={config['production_origin']}",
            f"--impersonate-service-account=nexus-release@{config['project']}.iam.gserviceaccount.com",
        ],
        stderr=subprocess.DEVNULL,
        text=True,
    ).strip()
    # Production tag shares IAM with production. Test protected cookie/Origin on
    # the tagged revision without requiring unauthenticated denial on an existing public service.
    import httpx

    with httpx.Client(
        base_url=tagged_url,
        headers={
            "X-Serverless-Authorization": "Bearer " + token,
            "Origin": config["production_origin"],
        },
        timeout=270,
    ) as client:
        for endpoint in ("/ready", "/health", "/", "/api/v1/demo/session"):
            if client.get(endpoint).status_code != 200:
                raise ValueError("production tag smoke failed")
        response = client.post(
            "/api/v1/agent/execute",
            json={
                "request_id": "release-" + run_id,
                "session_id": "release-" + run_id,
                "query": "What is the standard base warranty period for Product B?",
            },
        )
        if (
            response.status_code != 200
            or response.json().get("status") != "completed"
            or not response.json().get("citations")
        ):
            raise ValueError("production execution smoke failed")
    try:
        command(
            "gcloud",
            "run",
            "services",
            "update-traffic",
            *common,
            "--to-revisions",
            f"{revision}=100",
            "--quiet",
        )
        command(
            "gcloud",
            "run",
            "services",
            "add-iam-policy-binding",
            *common,
            "--member=allUsers",
            "--role=roles/run.invoker",
            "--quiet",
        )
        with httpx.Client(timeout=15, follow_redirects=False) as client:
            if any(
                client.get(config["production_origin"] + p).status_code != 200
                for p in ("/", "/health", "/ready")
            ):
                raise ValueError("public verification failed; inspect rollback snapshot")
    except Exception:
        rollback(config, run_id)
        raise
    result = directory / "public-release.json"
    result.write_text(
        json.dumps(
            {
                "status": "verified_public",
                "url": config["production_origin"],
                "image": image,
                "revision": revision,
                "rollback_snapshot": f"rollbacks/{run_id}/service.json",
            },
            indent=2,
        )
    )
    upload(result, f"gs://{config['release_bucket']}/public/{run_id}.json")
    # Badge is added only by the verified operator process described in the runbook.


def rollback(config, run_id):
    snapshot = capture(
        "gcloud",
        "storage",
        "cat",
        f"gs://{config['release_bucket']}/rollbacks/{run_id}/service.json",
    )
    if snapshot["metadata"]["name"] != config["production_service"]:
        raise ValueError("rollback service differs")
    traffic = [
        (t["revisionName"], int(t["percent"]))
        for t in snapshot["status"]["traffic"]
        if t.get("percent", 0)
    ]
    if not traffic or sum(percent for _, percent in traffic) != 100:
        raise ValueError("invalid rollback traffic")
    command(
        "gcloud",
        "run",
        "services",
        "update-traffic",
        config["production_service"],
        "--project",
        config["project"],
        "--region",
        config["region"],
        "--to-revisions",
        ",".join(f"{r}={p}" for r, p in traffic),
        "--quiet",
    )

    previous_policy = capture(
        "gcloud", "storage", "cat", f"gs://{config['release_bucket']}/rollbacks/{run_id}/iam.json"
    )
    was_public = any(
        b.get("role") == "roles/run.invoker" and "allUsers" in b.get("members", [])
        for b in previous_policy.get("bindings", [])
    )
    current_policy = gcloud_json(
        "run",
        "services",
        "get-iam-policy",
        config["production_service"],
        "--project",
        config["project"],
        "--region",
        config["region"],
    )
    is_public = any(
        b.get("role") == "roles/run.invoker" and "allUsers" in b.get("members", [])
        for b in current_policy.get("bindings", [])
    )
    if is_public != was_public:
        command(
            "gcloud",
            "run",
            "services",
            "add-iam-policy-binding" if was_public else "remove-iam-policy-binding",
            config["production_service"],
            "--project",
            config["project"],
            "--region",
            config["region"],
            "--member=allUsers",
            "--role=roles/run.invoker",
            "--quiet",
        )


def pause(config, directory, run_id):
    # IAM removal alone cannot recall work in progress. Also route to a deny-all
    # private-mode revision, using the same immutable assets and dependency config.
    common = [
        config["production_service"],
        "--project",
        config["project"],
        "--region",
        config["region"],
    ]
    previous = gcloud_json("run", "services", "describe", *common)
    previous_policy = gcloud_json("run", "services", "get-iam-policy", *common)
    path = directory / "pause-snapshot.json"
    save_snapshot(previous, path)
    upload(path, f"gs://{config['release_bucket']}/rollbacks/{run_id}/service.json")
    policy_path = directory / "pause-iam.json"
    policy_path.write_text(json.dumps(previous_policy))
    upload(policy_path, f"gs://{config['release_bucket']}/rollbacks/{run_id}/iam.json")
    if any(
        b.get("role") == "roles/run.invoker" and "allUsers" in b.get("members", [])
        for b in previous_policy.get("bindings", [])
    ):
        command(
            "gcloud",
            "run",
            "services",
            "remove-iam-policy-binding",
            *common,
            "--member=allUsers",
            "--role=roles/run.invoker",
            "--quiet",
        )
    command(
        "gcloud",
        "run",
        "services",
        "update",
        *common,
        "--update-env-vars",
        "DECISION_AGENT_DEPLOYMENT_MODE=private",
        "--min",
        "0",
        "--no-traffic",
        "--quiet",
    )
    current = gcloud_json("run", "services", "describe", *common)
    if (
        current["status"]["latestReadyRevisionName"]
        != current["status"]["latestCreatedRevisionName"]
    ):
        raise ValueError("deny-all revision not ready")
    command(
        "gcloud",
        "run",
        "services",
        "update-traffic",
        *common,
        "--to-revisions",
        current["status"]["latestReadyRevisionName"] + "=100",
        "--clear-tags",
        "--quiet",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["candidate", "public", "rollback", "pause"])
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--image", default="")
    parser.add_argument("--candidate-run", default="")
    parser.add_argument("--rollback-run", default="")
    parser.add_argument(
        "--acceptance", type=Path, default=Path("docs/deployment/LIVE_ACCEPTANCE.json")
    )
    args = parser.parse_args()
    try:
        if os.environ.get("NEXUS_RELEASE_ENABLED") != "true":
            raise ValueError("release disabled")
        config = json.loads(args.config.read_text())
        if config["preview_service"] == config["production_service"]:
            raise ValueError("preview must remain separate from public production")
        run_id = os.environ["GITHUB_RUN_ID"]
        if not re.fullmatch(r"[0-9]+", run_id):
            raise ValueError("numeric run ID required")
        if (
            gcloud_json("billing", "projects", "describe", config["project"]).get("billingEnabled")
            is not True
        ):
            raise ValueError("billing disabled")
        directory = Path(".tmp-release") / run_id
        directory.mkdir(parents=True, exist_ok=False)
        manifest = json.loads(Path("deploy/cloud-run/corpus-release.json").read_text())
        if args.action == "candidate":
            release_descriptor(manifest, args.image)
            candidate(config, args.image, manifest, directory, run_id)
        elif args.action == "public":
            public_release(
                config,
                args.image,
                manifest,
                directory,
                run_id,
                args.candidate_run,
                json.loads(args.acceptance.read_text()),
            )
        elif args.action == "rollback":
            if not re.fullmatch(r"[0-9]+", args.rollback_run):
                raise ValueError("numeric rollback run required")
            rollback(config, args.rollback_run)
        else:
            pause(config, directory, run_id)
        print(json.dumps({"status": "passed", "action": args.action}))
        return 0
    except Exception:
        print('{"status":"failed","error_code":"cloud_release_failed"}')
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
