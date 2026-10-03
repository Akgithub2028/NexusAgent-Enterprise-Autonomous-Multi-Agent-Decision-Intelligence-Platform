"""Add a README badge only after checking the cloud receipt and current public URL."""

import argparse
import json
import re
import subprocess
from pathlib import Path
from urllib.parse import urlsplit

import httpx


def badge(url: str) -> str:
    parsed = urlsplit(url)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or not parsed.hostname.endswith(".run.app")
        or parsed.netloc != parsed.hostname
        or parsed.path
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("verified Cloud Run origin required")
    return f'<a href="{url}"><img src="https://img.shields.io/badge/Live%20Demo-Synthetic%20Data-10B981?style=for-the-badge" alt="Verified live synthetic demo" /></a>'


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    try:
        if not re.fullmatch(r"[0-9]+", args.run_id):
            raise ValueError("numeric release ID required")
        config = json.loads(args.config.read_text())
        record = json.loads(
            subprocess.check_output(
                [
                    "gcloud",
                    "storage",
                    "cat",
                    f"gs://{config['release_bucket']}/public/{args.run_id}.json",
                ],
                stderr=subprocess.DEVNULL,
            )
        )
        if record["status"] != "verified_public" or record["url"] != config["production_origin"]:
            raise ValueError("no verified public receipt")
        markup = badge(record["url"])
        current = json.loads(
            subprocess.check_output(
                [
                    "gcloud",
                    "run",
                    "services",
                    "describe",
                    config["production_service"],
                    "--project",
                    config["project"],
                    "--region",
                    config["region"],
                    "--format=json",
                ],
                stderr=subprocess.DEVNULL,
            )
        )
        if not any(
            t.get("revisionName") == record["revision"] and t.get("percent") == 100
            for t in current["status"]["traffic"]
        ):
            raise ValueError("public receipt is no longer current")
        with httpx.Client(timeout=15, follow_redirects=False) as client:
            for path in ("/", "/assets/app.js", "/health", "/ready"):
                response = client.get(record["url"] + path)
                if response.status_code != 200:
                    raise ValueError("public URL not ready")
                if path == "/ready" and response.json().get("status") != "ready":
                    raise ValueError("not ready")
        p = Path("README.md")
        text = p.read_text()
        if 'alt="Verified live synthetic demo"' in text:
            raise ValueError("review existing badge before replacement")
        if "<!-- VERIFIED_LIVE_BADGE -->" not in text:
            raise ValueError("README placeholder missing")
        p.write_text(text.replace("<!-- VERIFIED_LIVE_BADGE -->", markup))
        print('{"status":"updated"}')
        return 0
    except Exception:
        print('{"status":"failed","error_code":"live_badge_verification_failed"}')
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
