"""Render or apply a P6 candidate; never promote traffic or grant public invocation."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit

from decision_agent.ingestion.cloud_job import release_descriptor

SECRETS = {
    "DECISION_AGENT_LLM_API_KEY": "nexus-groq-key",
    "DECISION_AGENT_MILVUS_TOKEN": "nexus-vector-read-token",
    "DECISION_AGENT_DB_READONLY_PASSWORD": "nexus-db-reader-password",
    "DECISION_AGENT_PUBLIC_DEMO_SIGNING_SECRET": "nexus-demo-signing-key",
}


def gcloud_json(*args):
    return json.loads(
        subprocess.check_output(["gcloud", *args, "--format=json"], stderr=subprocess.DEVNULL)
    )


def build_plan(config: dict, promotion: dict, manifest: dict, env_path: Path) -> dict:
    expected = release_descriptor(manifest, promotion["image"])
    if any(promotion.get(key) != value for key, value in expected.items()):
        raise ValueError("promotion manifest mismatch")
    project, region, service = (config[key] for key in ("project", "region", "service"))
    if (
        not re.fullmatch(r"[a-z][a-z0-9-]{4,61}[a-z0-9]", project)
        or not re.fullmatch(r"[a-z]+-[a-z]+[0-9]", region)
        or not re.fullmatch(r"[a-z][a-z0-9-]{0,47}", service)
    ):
        raise ValueError("invalid resource name")
    origin = config["origin"]
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
        raise ValueError("exact HTTPS tagged origin required")
    versions = config["secret_versions"]
    if set(versions) != set(SECRETS.values()) or any(
        not re.fullmatch(r"[1-9][0-9]*", str(value)) for value in versions.values()
    ):
        raise ValueError("four pinned reader secrets required")
    env = {
        "DECISION_AGENT_DEPLOYMENT_MODE": "public_demo",
        "DECISION_AGENT_CONTROLLED_WORKFLOW_ENABLED": "true",
        "DECISION_AGENT_PUBLIC_DEMO_ORIGIN": origin,
        "DECISION_AGENT_AUDIT_MODE": "stdout",
        "DECISION_AGENT_MEMORY_MODE": "in_memory",
        "DECISION_AGENT_MEMORY_MAX_SESSIONS": "1000",
        "DECISION_AGENT_REQUEST_EXECUTION_TIMEOUT_SECONDS": "240",
        "DECISION_AGENT_PUBLIC_DEMO_BODY_TIMEOUT_SECONDS": "10",
        "DECISION_AGENT_PUBLIC_DEMO_MAX_ACTIVE": "2",
        "DECISION_AGENT_RELEASE_ID": promotion["image"].split("sha256:")[1][:16],
        "DECISION_AGENT_CORPUS_RELEASE_ID": manifest["corpus_release_id"],
        "DECISION_AGENT_MILVUS_COLLECTION": manifest["collection"],
        "DECISION_AGENT_MILVUS_URI": config["milvus_uri"],
        "DECISION_AGENT_MILVUS_INDEX_TYPE": "AUTOINDEX",
        "DECISION_AGENT_MILVUS_DATABASE": "default",
        "DECISION_AGENT_DB_UNIX_SOCKET": f"/cloudsql/{project}:{region}:nexus-demo-mysql",
        "DECISION_AGENT_DB_DATABASE": "enterprise_operations",
        "DECISION_AGENT_DB_READONLY_USERNAME": "decision_agent_readonly",
        "DECISION_AGENT_DB_POOL_SIZE": "2",
        "DECISION_AGENT_DB_POOL_TIMEOUT_SECONDS": "5",
        "DECISION_AGENT_LLM_BASE_URL": "https://api.groq.com/openai/v1",
        "DECISION_AGENT_LLM_MODEL_NAME": "openai/gpt-oss-20b",
    }
    vector = urlsplit(config["milvus_uri"])
    if vector.scheme != "https" or not vector.hostname or vector.username or vector.password:
        raise ValueError("TLS vector endpoint required")
    command = [
        "gcloud",
        "run",
        "deploy",
        service,
        "--project",
        project,
        "--region",
        region,
        "--image",
        promotion["image"],
        "--service-account",
        f"nexus-serving@{project}.iam.gserviceaccount.com",
        "--no-allow-unauthenticated",
        "--invoker-iam-check",
        "--no-traffic",
        "--tag",
        "p6",
        "--execution-environment",
        "gen2",
        "--cpu",
        "2",
        "--memory",
        "4Gi",
        "--concurrency",
        "2",
        "--timeout",
        "300s",
        "--min",
        "1",
        "--max",
        "1",
        "--min-instances",
        "0",
        "--max-instances",
        "1",
        "--port",
        "8080",
        "--command",
        "python",
        "--args=-m,decision_agent.cloud",
        "--no-use-http2",
        "--set-cloudsql-instances",
        f"{project}:{region}:nexus-demo-mysql",
        "--env-vars-file",
        str(env_path),
        "--set-secrets",
        ",".join(f"{key}={name}:{versions[name]}" for key, name in SECRETS.items()),
        "--startup-probe",
        "httpGet.path=/ready,httpGet.port=8080,periodSeconds=5,timeoutSeconds=2,failureThreshold=48",
        "--liveness-probe",
        "httpGet.path=/health,httpGet.port=8080,periodSeconds=10,timeoutSeconds=2,failureThreshold=3",
        "--readiness-probe",
        "httpGet.path=/ready,httpGet.port=8080,periodSeconds=10,timeoutSeconds=2,failureThreshold=3,successThreshold=1",
        "--deploy-health-check",
        "--quiet",
    ]
    return {"environment": env, "command": command}


def bootstrap_plan(plan: dict) -> dict:
    """A first service may expose health/UI only, with its executor denying all callers."""
    plan["environment"]["DECISION_AGENT_DEPLOYMENT_MODE"] = "private"
    plan["environment"].pop("DECISION_AGENT_PUBLIC_DEMO_ORIGIN")
    plan["command"].remove("--no-traffic")
    return plan


def check_restricted(policy: dict, service: dict, origin: str) -> None:
    if any(
        member in {"allUsers", "allAuthenticatedUsers"}
        for binding in policy.get("bindings", [])
        for member in binding.get("members", [])
    ):
        raise ValueError("public IAM binding exists")
    if (
        service.get("metadata", {})
        .get("annotations", {})
        .get("run.googleapis.com/invoker-iam-disabled")
        == "true"
    ):
        raise ValueError("IAM check disabled")
    if not any(
        t.get("tag") == "p6" and t.get("url") == origin
        for t in service["status"].get("traffic", [])
    ):
        raise ValueError("bootstrap tag origin differs")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--promotion", type=Path, required=True)
    parser.add_argument(
        "--manifest", type=Path, default=Path("deploy/cloud-run/corpus-release.json")
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument(
        "--bootstrap", action="store_true", help="Create a new deny-all private service only"
    )
    args = parser.parse_args()
    try:
        output = args.output.resolve()
        if not output.is_relative_to(Path.cwd().resolve()):
            raise ValueError("workspace output required")
        config = json.loads(args.config.read_text())
        promotion = json.loads(args.promotion.read_text())
        if args.bootstrap:
            config["origin"] = "https://private-bootstrap.run.app"
        plan = build_plan(
            config, promotion, json.loads(args.manifest.read_text()), output / "runtime.env.json"
        )
        if args.bootstrap:
            plan = bootstrap_plan(plan)
        output.mkdir(parents=True, exist_ok=True)
        (output / "runtime.env.json").write_text(json.dumps(plan["environment"], indent=2) + "\n")
        (output / "plan.json").write_text(json.dumps(plan, indent=2) + "\n")
        if args.apply:
            help_text = subprocess.check_output(
                ["gcloud", "run", "deploy", "--help"], stderr=subprocess.DEVNULL, text=True
            )
            if "--readiness-probe" not in help_text:
                raise ValueError("update Cloud SDK for native readiness probes")
            project, region = config["project"], config["region"]
            billing = gcloud_json("billing", "projects", "describe", project)
            if billing.get("billingEnabled") is not True:
                raise ValueError("billing unavailable")
            # Recheck real execution and receipt, never trust a locally edited descriptor.
            verified = json.loads(
                subprocess.check_output(
                    [
                        sys.executable,
                        str(Path(__file__).with_name("prepare_corpus_promotion.py")),
                        "--project",
                        project,
                        "--region",
                        region,
                        "--execution",
                        promotion["execution"],
                        "--bucket",
                        config["release_bucket"],
                        "--image",
                        promotion["image"],
                        "--manifest",
                        str(args.manifest),
                    ],
                    stderr=subprocess.DEVNULL,
                )
            )
            if verified != promotion:
                raise ValueError("promotion changed")
            common = [config["service"], "--project", project, "--region", region]
            if args.bootstrap:
                existing = gcloud_json(
                    "run",
                    "services",
                    "list",
                    "--project",
                    project,
                    "--region",
                    region,
                    "--filter",
                    f"metadata.name={config['service']}",
                )
                if existing:
                    raise ValueError("bootstrap refuses an existing service")
                previous, policy = {"service_absent": True}, {}
            else:
                previous = gcloud_json("run", "services", "describe", *common)
                policy = gcloud_json("run", "services", "get-iam-policy", *common)
                check_restricted(policy, previous, config["origin"])
                for container in previous["spec"]["template"]["spec"]["containers"]:
                    for entry in container.get("env", []):
                        if entry["name"] in SECRETS and (
                            "value" in entry
                            or not re.fullmatch(
                                r"[1-9][0-9]*",
                                entry.get("valueFrom", {}).get("secretKeyRef", {}).get("key", ""),
                            )
                        ):
                            raise ValueError("prior secrets must be pinned references")
            snapshot = output / "previous-service.json"
            if snapshot.exists():
                raise ValueError("use a new output directory to preserve rollback snapshot")
            snapshot.write_text(json.dumps(previous, indent=2) + "\n")
            snapshot.chmod(0o600)
            (output / "previous-iam.json").write_text(json.dumps(policy, indent=2) + "\n")
            subprocess.run(
                plan["command"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            current = gcloud_json("run", "services", "describe", *common)
            current_policy = gcloud_json("run", "services", "get-iam-policy", *common)
            tagged_url = next(
                t["url"] for t in current["status"]["traffic"] if t.get("tag") == "p6"
            )
            check_restricted(
                current_policy, current, tagged_url if args.bootstrap else config["origin"]
            )
            state = current["status"]
            if state.get("latestCreatedRevisionName") != state.get(
                "latestReadyRevisionName"
            ) or not any(
                c.get("type") == "Ready" and c.get("status") == "True"
                for c in state.get("conditions", [])
            ):
                raise ValueError("candidate revision is not ready")
            (output / "deployed-service.json").write_text(json.dumps(current, indent=2) + "\n")
        print(
            json.dumps(
                {"status": "deployed" if args.apply else "planned", "traffic_promoted": False}
            )
        )
        return 0
    except Exception:
        print('{"status":"failed","error_code":"restricted_deployment_failed"}')
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
