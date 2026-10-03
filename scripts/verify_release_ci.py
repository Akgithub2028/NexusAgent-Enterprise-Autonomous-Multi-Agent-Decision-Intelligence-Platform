"""Require all six original CI jobs on the exact release commit."""

import json
import os
import re
import subprocess

EXPECTED = {
    "quality",
    "unit",
    "offline-integration",
    "security-evaluation",
    "secret-scan",
    "dependency-scan",
}


def main() -> int:
    try:
        sha = os.environ["RELEASE_SHA"]
        if not re.fullmatch(r"[a-f0-9]{40}", sha):
            raise ValueError("invalid commit")
        runs = json.loads(
            subprocess.check_output(
                [
                    "gh",
                    "run",
                    "list",
                    "--workflow",
                    "ci.yml",
                    "--commit",
                    sha,
                    "--branch",
                    "main",
                    "--limit",
                    "20",
                    "--json",
                    "databaseId,headSha,conclusion,event",
                ],
                stderr=subprocess.DEVNULL,
            )
        )
        run = next(
            r
            for r in runs
            if r["headSha"] == sha and r["conclusion"] == "success" and r["event"] == "push"
        )
        details = json.loads(
            subprocess.check_output(
                ["gh", "run", "view", str(run["databaseId"]), "--json", "jobs"],
                stderr=subprocess.DEVNULL,
            )
        )
        if {j["name"] for j in details["jobs"] if j["conclusion"] == "success"} != EXPECTED:
            raise ValueError("CI jobs incomplete")
        print('{"status":"passed"}')
        return 0
    except Exception:
        print('{"status":"failed","error_code":"release_ci_gate_failed"}')
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
