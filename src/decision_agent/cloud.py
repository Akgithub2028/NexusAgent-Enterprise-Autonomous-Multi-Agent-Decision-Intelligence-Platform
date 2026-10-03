"""Single-process container launcher: python -m decision_agent.cloud."""

from __future__ import annotations

import json
import os
import re
import sys

import uvicorn

from decision_agent.api.public_demo import create_deployment_app
from decision_agent.config import Settings
from decision_agent.observability.cloud_logging import CloudLogMetadata, configure_cloud_logging


def container_port(value: str | None) -> int:
    """Accept only an explicit decimal TCP port; never silently replace invalid input."""
    raw = "8080" if value is None else value
    if not re.fullmatch(r"[0-9]{1,5}", raw) or not 1 <= int(raw) <= 65535:
        raise ValueError("cloud_port_invalid")
    return int(raw)


def main() -> int:
    """Keep configuration failures safe and reuse the application's formal lifecycle."""
    try:
        port = container_port(os.environ.get("PORT"))
        revision = os.environ.get("K_REVISION")
        settings = Settings(**({} if revision is None else {"runtime_revision": revision}))
        metadata = CloudLogMetadata(
            release_id=settings.release_id,
            corpus_release_id=settings.corpus_release_id,
            revision=settings.runtime_revision,
        )
        app = create_deployment_app(settings)
    except Exception:
        print(json.dumps({"error_code": "cloud_configuration_invalid"}), file=sys.stderr)
        return 2
    configure_cloud_logging(metadata)
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        workers=1,
        reload=False,
        log_config=None,
        access_log=False,
        timeout_graceful_shutdown=8,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
