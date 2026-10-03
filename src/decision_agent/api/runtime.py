"""FastAPI lifespan integration for one app-local formal runtime."""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Mapping
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI

from decision_agent.api.app import ReadinessCheck, create_app
from decision_agent.api.security import ApiSecurityContextResolver
from decision_agent.application.bootstrap import (
    BootstrapErrorCode,
    FormalRuntimeHandle,
    RuntimeBootstrapError,
    RuntimeBuilder,
    build_bootstrapped_runtime,
)
from decision_agent.config import Settings


def _emit_lifecycle(state: str, error_code: str | None = None) -> None:
    payload = {
        "event": "decision_agent.runtime_lifecycle",
        "state": state,
        "error_code": error_code,
    }
    # Lifecycle telemetry is best effort, unlike governance audit.
    with suppress(OSError, TypeError, ValueError):
        logging.getLogger("decision_agent.observability").info(
            json.dumps(payload), extra={"decision_agent_payload": payload}
        )


def create_bootstrapped_app(
    settings: Settings,
    runtime_builder: RuntimeBuilder,
    readiness_checks: Mapping[str, ReadinessCheck] | None = None,
    *,
    security_context_resolver: ApiSecurityContextResolver | None = None,
) -> FastAPI:
    """Create an app whose lifespan owns one injected runtime builder."""
    handle = FormalRuntimeHandle()
    return create_app(
        settings,
        readiness_checks,
        runtime_handle=handle,
        lifespan=_runtime_lifespan(handle=handle, runtime_builder=runtime_builder),
        runtime_readiness_required=True,
        security_context_resolver=security_context_resolver,
    )


def _runtime_lifespan(
    *,
    handle: FormalRuntimeHandle,
    runtime_builder: RuntimeBuilder,
):
    @asynccontextmanager
    async def lifespan(_: FastAPI):
        handle.mark_starting()
        _emit_lifecycle("starting")
        runtime = None
        try:
            runtime = await build_bootstrapped_runtime(runtime_builder)
        except (asyncio.CancelledError, KeyboardInterrupt, SystemExit):
            handle.fail(BootstrapErrorCode.RUNTIME_UNAVAILABLE)
            _emit_lifecycle("failed", BootstrapErrorCode.RUNTIME_UNAVAILABLE.value)
            raise
        except RuntimeBootstrapError as exc:
            handle.fail(BootstrapErrorCode(exc.code))
            _emit_lifecycle("failed", exc.code)
        else:
            handle.publish(runtime.executor)
            _emit_lifecycle("ready")

        try:
            yield
        finally:
            handle.revoke_executor()
            try:
                if runtime is not None:
                    await runtime.aclose()
            finally:
                handle.stop()
                _emit_lifecycle("stopped")

    return lifespan
