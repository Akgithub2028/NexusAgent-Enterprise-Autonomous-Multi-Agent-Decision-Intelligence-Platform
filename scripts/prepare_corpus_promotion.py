"""Prepare a P6 release descriptor only from a successful managed job execution."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from decision_agent.ingestion.cloud_job import release_descriptor


def check_execution(execution: dict, image: str) -> None:
    status = execution["status"]
    containers = execution["spec"]["template"]["spec"]["containers"]
    if (
        status.get("succeededCount") != 1
        or status.get("failedCount", 0) != 0
        or not any(
            c["type"] == "Completed" and c["status"] == "True" for c in status.get("conditions", [])
        )
        or len(containers) != 1
        or containers[0]["image"] != image
    ):
        raise ValueError("successful matching execution required")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True)
    parser.add_argument("--region", required=True)
    parser.add_argument("--execution", required=True)
    parser.add_argument("--bucket", required=True)
    parser.add_argument("--image", required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    try:
        expected = release_descriptor(json.loads(args.manifest.read_text()), args.image)
        execution = json.loads(
            subprocess.check_output(
                [
                    "gcloud",
                    "run",
                    "jobs",
                    "executions",
                    "describe",
                    args.execution,
                    "--project",
                    args.project,
                    "--region",
                    args.region,
                    "--format=json",
                ],
                stderr=subprocess.DEVNULL,
            )
        )
        check_execution(execution, args.image)
        receipt_uri = f"gs://{args.bucket}/validated/{expected['collection']}.json"
        receipt = json.loads(
            subprocess.check_output(
                ["gcloud", "storage", "cat", receipt_uri],
                stderr=subprocess.DEVNULL,
            )
        )
        if receipt != expected:
            raise ValueError("completion mismatch")
        print(
            json.dumps(
                {**expected, "execution": args.execution, "receipt": receipt_uri}, sort_keys=True
            )
        )
        return 0
    except Exception:
        print('{"status":"failed","error_code":"promotion_gate_failed"}')
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
