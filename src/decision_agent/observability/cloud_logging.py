"""Cloud JSON logging with explicit safe metadata and no arbitrary exception payloads."""

from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime
from typing import TextIO
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

_PROCESS_ID = uuid4().hex


class CloudLogMetadata(BaseModel):
    """Release identifiers only; never infer metadata from connection URLs or identity."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    release_id: str = Field(default="unversioned", pattern=r"^[A-Za-z0-9_.-]{1,128}$")
    corpus_release_id: str = Field(default="unversioned", pattern=r"^[A-Za-z0-9_.-]{1,128}$")
    revision: str = Field(default="local", pattern=r"^[A-Za-z0-9_.-]{1,128}$")
    process_id: str = Field(default=_PROCESS_ID, pattern=r"^[a-f0-9]{32}$")


class CloudJsonFormatter(logging.Formatter):
    """Format approved trace payloads; other log records carry fixed diagnostics only."""

    def __init__(self, metadata: CloudLogMetadata) -> None:
        super().__init__()
        self._metadata = metadata

    def format(self, record: logging.LogRecord) -> str:
        # Do not render arbitrary library messages, arguments, exception text or access URLs.
        payload = getattr(record, "decision_agent_payload", None)
        if record.name != "decision_agent.observability" or not isinstance(payload, dict):
            payload = {"event": "runtime_diagnostic"}
        return json.dumps(
            {
                **payload,
                "severity": record.levelname,
                "timestamp": datetime.now(UTC).isoformat(),
                "runtime": self._metadata.model_dump(),
            },
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        )


class SafeCloudHandler(logging.StreamHandler):
    """Do not let logging's default error fallback print records or exception details."""

    def handleError(self, record: logging.LogRecord) -> None:
        return  # Trace output is best effort; mandatory audit uses its own direct writer.


def configure_cloud_logging(metadata: CloudLogMetadata, *, stream: TextIO | None = None) -> None:
    """Install JSON output once for this launcher; INFO makes request traces visible."""
    handler = SafeCloudHandler(sys.stdout if stream is None else stream)
    handler.setFormatter(CloudJsonFormatter(metadata))
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(logging.INFO)
    for name in ("decision_agent", "decision_agent.observability", "uvicorn", "uvicorn.error"):
        logger = logging.getLogger(name)
        logger.handlers.clear()
        logger.setLevel(logging.INFO)
        logger.propagate = True
    # Access records contain client-controlled URLs; the cloud launcher also disables them.
    logging.getLogger("uvicorn.access").disabled = True
