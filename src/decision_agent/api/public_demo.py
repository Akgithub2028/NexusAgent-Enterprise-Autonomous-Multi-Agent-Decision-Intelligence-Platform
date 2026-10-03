"""Opt-in public synthetic demo with signed visitor ownership and bounded admission."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import re
import secrets
import time
from collections.abc import Callable
from dataclasses import dataclass
from threading import Lock
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from decision_agent.api.runtime import create_bootstrapped_app
from decision_agent.application.bootstrap import (
    BootstrapErrorCode,
    RuntimeBootstrapError,
    RuntimeBuilder,
)
from decision_agent.application.configured_runtime import create_configured_runtime_builder
from decision_agent.config import Settings
from decision_agent.security import (
    DataScope,
    KnowledgeScope,
    SecurityAuthorizationError,
    SecurityContext,
    SecurityErrorCode,
    SessionScope,
    build_security_context,
)
from decision_agent.security.models import make_demo_principal

COOKIE_NAME = "__Host-nexus-demo"
SESSION_ENDPOINT = "/api/v1/demo/session"
EXECUTE_ENDPOINT = "/api/v1/agent/execute"
_TENANT = "nexus-public-demo"
_SUBJECT_PATTERN = re.compile(r"^[A-Za-z0-9_-]{43}$")


class VisitorCookie:
    """Fixed HMAC format: no client-selected claims, algorithm or authorization grants."""

    def __init__(self, settings: Settings, *, clock: Callable[[], float] = time.time) -> None:
        self._clock = clock
        self._ttl = settings.public_demo_cookie_ttl_seconds
        assert settings.public_demo_signing_secret is not None
        self._key = settings.public_demo_signing_secret.get_secret_value().encode()
        self._domain = f"nexus-public-demo-cookie\0{settings.public_demo_origin}\0".encode()

    def issue(self) -> str:
        now = int(self._clock())
        payload = f"v1.{secrets.token_urlsafe(32)}.{now}.{now + self._ttl}"
        return f"{payload}.{self._signature(payload)}"

    def verify(self, value: str | None) -> str:
        if value is None or len(value) > 256:
            raise SecurityAuthorizationError(SecurityErrorCode.UNAUTHENTICATED)
        parts = value.split(".")
        if len(parts) != 5 or parts[0] != "v1" or not _SUBJECT_PATTERN.fullmatch(parts[1]):
            raise SecurityAuthorizationError(SecurityErrorCode.UNAUTHENTICATED)
        payload = ".".join(parts[:4])
        if not re.fullmatch(r"[0-9a-f]{64}", parts[4]) or not hmac.compare_digest(
            parts[4], self._signature(payload)
        ):
            raise SecurityAuthorizationError(SecurityErrorCode.UNAUTHENTICATED)
        try:
            issued, expires = int(parts[2]), int(parts[3])
        except ValueError:
            raise SecurityAuthorizationError(SecurityErrorCode.UNAUTHENTICATED) from None
        now = int(self._clock())
        if issued > now or expires <= now or expires - issued != self._ttl:
            raise SecurityAuthorizationError(SecurityErrorCode.UNAUTHENTICATED)
        return parts[1]

    def _signature(self, payload: str) -> str:
        return hmac.new(self._key, self._domain + payload.encode(), hashlib.sha256).hexdigest()


def _same_origin(request: Request, origin: str, *, bootstrap: bool = False) -> bool:
    supplied = request.headers.getlist("origin")
    if supplied != [origin] and not (bootstrap and not supplied):
        return False
    return request.headers.get("sec-fetch-site") in (None, "same-origin", "none")


class PublicDemoSecurityContextResolver:
    """Resolve only server-issued demo visitors and frozen synthetic fixture grants."""

    def __init__(self, settings: Settings, cookie: VisitorCookie) -> None:
        self._cookie = cookie
        self._origin = settings.public_demo_origin or ""

    def resolve(self, *, request: Request, request_id: str) -> SecurityContext:
        if not _same_origin(request, self._origin):
            raise SecurityAuthorizationError(SecurityErrorCode.SECURITY_CONTEXT_INVALID)
        subject = self._cookie.verify(request.cookies.get(COOKIE_NAME))
        return build_security_context(
            principal=make_demo_principal(subject_id=subject, tenant_id=_TENANT),
            request_id=request_id,
            trace_id=f"public-demo-{uuid4().hex}",
            allowed_scenarios=frozenset({"knowledge", "data", "mixed"}),
            allowed_workflows=frozenset({"direct", "controlled_mixed"}),
            allowed_skills=frozenset(
                {"enterprise-knowledge-qa", "enterprise-data-analysis", "inventory-risk-diagnosis"}
            ),
            allowed_tools=frozenset({"run_knowledge_agent", "run_data_agent"}),
            knowledge_scope=KnowledgeScope(
                tenant_id=_TENANT,
                allowed_namespaces=frozenset({"enterprise_kb"}),
                allowed_document_ids=frozenset({"DOC-ORG-001", "DOC-AGENT-001", "DOC-INV-001"}),
            ),
            data_scope=DataScope(
                tenant_id=_TENANT,
                allowed_domains=frozenset({"enterprise_operations"}),
                allowed_resources=frozenset(
                    {"products", "inventory_snapshots", "purchase_orders", "suppliers"}
                ),
                allowed_query_capabilities=frozenset({"read"}),
            ),
            session_scope=SessionScope(tenant_id=_TENANT, subject_id=subject),
        )


@dataclass
class _Window:
    expires: float
    count: int = 0


class DemoAdmission:
    """Atomic process-local fixed-window quotas and non-waiting execution slots."""

    def __init__(self, settings: Settings, *, clock: Callable[[], float] = time.monotonic) -> None:
        self._settings = settings
        self._clock = clock
        self._lock = Lock()
        self._visitors: dict[str, _Window] = {}
        self._global = _Window(0)
        self._bootstrap = _Window(0)
        self._active = 0

    def bootstrap(self) -> bool:
        with self._lock:
            now = self._clock()
            if self._bootstrap.expires <= now:
                self._bootstrap = _Window(now + self._settings.public_demo_window_seconds)
            if self._bootstrap.count >= self._settings.public_demo_bootstraps_global:
                return False
            self._bootstrap.count += 1
            return True

    def acquire(self, subject: str) -> bool:
        with self._lock:
            now = self._clock()
            self._visitors = {k: v for k, v in self._visitors.items() if v.expires > now}
            if self._global.expires <= now:
                self._global = _Window(now + self._settings.public_demo_window_seconds)
            visitor = self._visitors.get(subject)
            if (
                self._active >= self._settings.public_demo_max_active
                or self._global.count >= self._settings.public_demo_requests_global
                or (
                    visitor is not None
                    and visitor.count >= self._settings.public_demo_requests_per_visitor
                )
                or (
                    visitor is None
                    and len(self._visitors) >= self._settings.public_demo_max_visitors
                )
            ):
                return False
            if visitor is None:
                visitor = _Window(now + self._settings.public_demo_window_seconds)
                self._visitors[subject] = visitor
            visitor.count += 1
            self._global.count += 1
            self._active += 1
            return True

    def release(self) -> None:
        with self._lock:
            self._active -= 1


def _denial(code: str, status: int, *, retry_after: int | None = None) -> JSONResponse:
    headers = {"Cache-Control": "no-store"}
    if retry_after is not None:
        headers["Retry-After"] = str(retry_after)
    return JSONResponse(
        {"code": code, "message": "The demo request could not be admitted."},
        status_code=status,
        headers=headers,
    )


class PublicDemoGuard:
    """Validate identity/origin/body bounds and reserve capacity before request execution."""

    def __init__(
        self, app: ASGIApp, *, settings: Settings, cookie: VisitorCookie, admission: DemoAdmission
    ) -> None:
        self._app = app
        self._settings = settings
        self._cookie = cookie
        self._admission = admission

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if (
            scope["type"] != "http"
            or scope["path"] != EXECUTE_ENDPOINT
            or scope["method"] != "POST"
        ):
            await self._app(scope, receive, send)
            return
        request = Request(scope)
        if not _same_origin(request, self._settings.public_demo_origin or ""):
            await _denial("demo_origin_forbidden", 403)(scope, receive, send)
            return
        try:
            subject = self._cookie.verify(request.cookies.get(COOKIE_NAME))
        except SecurityAuthorizationError:
            await _denial("unauthenticated", 401)(scope, receive, send)
            return
        if (
            request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
            != "application/json"
        ):
            await _denial("demo_json_required", 415)(scope, receive, send)
            return
        if not self._admission.acquire(subject):
            await _denial(
                "demo_capacity_exceeded", 429, retry_after=self._settings.public_demo_window_seconds
            )(scope, receive, send)
            return
        try:
            await self._execute(scope, receive, send)
        finally:
            self._admission.release()

    async def _execute(self, scope: Scope, receive: Receive, send: Send) -> None:
        body = bytearray()
        try:
            async with asyncio.timeout(self._settings.public_demo_body_timeout_seconds):
                while True:
                    message = await receive()
                    if message["type"] == "http.disconnect":
                        return
                    chunk = message.get("body", b"")
                    if len(body) + len(chunk) > self._settings.public_demo_max_body_bytes:
                        await _denial("demo_request_too_large", 413)(scope, receive, send)
                        return
                    body.extend(chunk)
                    if not message.get("more_body", False):
                        break
        except TimeoutError:
            await _denial("demo_body_timeout", 408)(scope, receive, send)
            return
        delivered = False

        async def replay() -> dict:
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": bytes(body), "more_body": False}
            return await receive()

        async def private_send(message: dict) -> None:
            if message["type"] == "http.response.start":
                headers = [
                    (k, v) for k, v in message.get("headers", []) if k.lower() != b"cache-control"
                ]
                message = {**message, "headers": [*headers, (b"cache-control", b"no-store")]}
            await send(message)

        await self._app(scope, replay, private_send)


def create_public_demo_app(
    settings: Settings, runtime_builder: RuntimeBuilder | None = None
) -> FastAPI:
    """Reuse formal lifecycle; install public grants only for validated explicit demo mode."""
    # Revalidate even if an internal caller used model_copy/model_construct.
    settings = Settings.model_validate(settings.model_dump())
    if settings.deployment_mode != "public_demo":
        raise ValueError("public demo factory requires explicit public_demo mode")
    cookie = VisitorCookie(settings)
    admission = DemoAdmission(settings)
    builder = runtime_builder or create_configured_runtime_builder(settings)

    async def secured_builder(stack):
        executor = await builder(stack)
        if not executor.requires_security_context:
            raise RuntimeBootstrapError(BootstrapErrorCode.CONFIGURATION_INVALID)
        return executor

    app = create_bootstrapped_app(
        settings,
        secured_builder,
        security_context_resolver=PublicDemoSecurityContextResolver(settings, cookie),
    )

    @app.get(SESSION_ENDPOINT, include_in_schema=True)
    async def session(request: Request) -> JSONResponse:
        if not _same_origin(request, settings.public_demo_origin or "", bootstrap=True):
            return _denial("demo_origin_forbidden", 403)
        if not admission.bootstrap():
            return _denial(
                "demo_capacity_exceeded", 429, retry_after=settings.public_demo_window_seconds
            )
        existing = request.cookies.get(COOKIE_NAME)
        try:
            cookie.verify(existing)
            value = existing
        except SecurityAuthorizationError:
            value = cookie.issue()
        response = JSONResponse(
            {"mode": "public_demo", "session_ttl_seconds": settings.public_demo_cookie_ttl_seconds},
            headers={"Cache-Control": "no-store"},
        )
        if value != existing:
            response.set_cookie(
                COOKIE_NAME,
                value or "",
                max_age=settings.public_demo_cookie_ttl_seconds,
                secure=True,
                httponly=True,
                samesite="strict",
                path="/",
            )
        return response

    app.add_middleware(PublicDemoGuard, settings=settings, cookie=cookie, admission=admission)
    return app


def create_deployment_app(
    settings: Settings, runtime_builder: RuntimeBuilder | None = None
) -> FastAPI:
    """Keep private execution rejecting by default; public access is explicit and validated."""
    settings = Settings.model_validate(settings.model_dump())
    if settings.deployment_mode == "public_demo":
        return create_public_demo_app(settings, runtime_builder)
    return create_bootstrapped_app(
        settings, runtime_builder or create_configured_runtime_builder(settings)
    )
