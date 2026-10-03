"""Public-demo identity and pre-execution admission, without live provider calls."""

from __future__ import annotations

import asyncio
import secrets
from dataclasses import dataclass, field

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError

from decision_agent.api.public_demo import (
    COOKIE_NAME,
    EXECUTE_ENDPOINT,
    SESSION_ENDPOINT,
    DemoAdmission,
    VisitorCookie,
    create_deployment_app,
    create_public_demo_app,
)
from decision_agent.application import (
    FormalRequest,
    FormalRequestExecutor,
    FormalResponse,
    MemoryContextStatus,
)
from decision_agent.config import Settings
from decision_agent.context.conversation_memory import ConversationMemoryProjector
from decision_agent.coordination.models import CoordinatorResult, CoordinatorStatus
from decision_agent.memory.in_memory import InMemorySessionMemoryStore
from decision_agent.routing.models import RequestRoute
from decision_agent.security import (
    DefaultDenyAuthorizationPolicy,
    DeterministicProviderRedactor,
    InMemoryAuditSink,
    PrincipalType,
    ProviderGovernance,
    ProviderPolicy,
    RequestPrincipal,
    SecurityAuthorizationError,
)

ORIGIN = "https://demo.test"
HEADERS = {"Origin": ORIGIN}
pytestmark = pytest.mark.offline_integration


@pytest.fixture(autouse=True)
def isolate_environment(monkeypatch):
    for name in Settings.model_fields:
        monkeypatch.delenv(f"DECISION_AGENT_{name.upper()}", raising=False)


def settings(**overrides):
    values = dict(
        app_name="P1 tests",
        environment="test",
        deployment_mode="public_demo",
        public_demo_origin=ORIGIN,
        public_demo_signing_secret=secrets.token_urlsafe(32),
        llm_api_key=secrets.token_urlsafe(32),
        llm_base_url="https://provider.test/v1",
        llm_model_name="demo-model",
        milvus_uri="https://vectors.test",
        milvus_token=secrets.token_urlsafe(32),
        db_host="sql.test",
        db_readonly_password=secrets.token_urlsafe(32),
        knowledge_dataset_root="datasets/enterprise_kb/m2c1",
        controlled_workflow_enabled=True,
        _env_file=None,
    )
    values.update(overrides)
    return Settings(**values)


def payload(query="normal question", session="shared-label", request_id="request-1"):
    return {"request_id": request_id, "session_id": session, "query": query}


@dataclass
class Executor:
    requires_security_context: bool = True
    calls: list[FormalRequest] = field(default_factory=list)
    entered: asyncio.Event | None = None
    blocked: asyncio.Event | None = None
    fail: bool = False

    async def execute(self, request):
        self.calls.append(request)
        if self.entered:
            self.entered.set()
        if self.blocked:
            await self.blocked.wait()
        if self.fail:
            raise RuntimeError("private failure")
        return FormalResponse(
            request_id=request.request_id,
            result=CoordinatorResult(
                status=CoordinatorStatus.COMPLETED,
                route=RequestRoute.KNOWLEDGE,
                skill_name="enterprise-knowledge-qa",
                answer="Grounded [E1]",
                citations=["[E1]"],
                tool_steps=("run_knowledge_agent",),
            ),
            memory_context_status=MemoryContextStatus.NOT_REQUESTED,
        )


def app_for(config=None, executor=None, *, private=False):
    executor = executor or Executor()

    async def builder(_stack):
        return executor

    factory = create_deployment_app if private else create_public_demo_app
    return factory(config or settings(), builder), executor


def bootstrap(client):
    response = client.get(SESSION_ENDPOINT)
    assert response.status_code == 200
    return client.cookies.get(COOKIE_NAME)


def test_default_private_app_rejects_and_does_not_bootstrap():
    config = Settings(app_name="private", environment="test", _env_file=None)
    app, executor = app_for(config, private=True)
    with TestClient(app, base_url=ORIGIN) as client:
        assert client.get(SESSION_ENDPOINT).status_code == 404
        assert client.post(EXECUTE_ENDPOINT, json=payload()).status_code == 401
    assert not executor.calls


@pytest.mark.parametrize(
    "overrides",
    [
        {"deployment_mode": "typo"},
        {"deployment_mode": ""},
        {"public_demo_origin": None},
        {"public_demo_origin": "http://demo.test"},
        {"public_demo_origin": "https://demo.test/path"},
        {"public_demo_origin": "https://user@demo.test"},
        {"public_demo_origin": "https://demo.test:443"},
        {"public_demo_origin": "https://demo.test:bad"},
        {"public_demo_signing_secret": None},
        {"public_demo_signing_secret": "x" * 60},
        {"llm_api_key": "replace-with-runtime-api-key"},
        {"milvus_token": None},
        {"db_readonly_password": "change-me"},
        {"llm_base_url": "http://provider.test/v1"},
        {"milvus_uri": "https://localhost:19530"},
        {"db_host": "127.0.0.1"},
        {"db_host": "::1"},
        {"db_host": "0.0.0.0"},
        {"db_host": "127.1"},
        {"db_host": "2130706433"},
        {"controlled_workflow_enabled": False},
        {"knowledge_dataset_root": None},
        {"llm_model_name": "replace-with-model"},
        {"public_demo_max_active": 0},
        {"public_demo_cookie_ttl_seconds": 0},
    ],
)
def test_invalid_public_configuration_fails_closed(overrides):
    with pytest.raises(ValidationError):
        settings(**overrides)


def test_factory_revalidates_model_copy_bypass():
    forged = settings().model_copy(update={"public_demo_origin": "http://localhost"})
    with pytest.raises(ValidationError):
        create_deployment_app(forged)
    with pytest.raises(ValueError, match="explicit"):
        create_public_demo_app(Settings(app_name="private", _env_file=None))


def test_unsigned_visitor_cannot_construct_verified_demo_principal():
    with pytest.raises(ValidationError, match="explicit demo factory"):
        RequestPrincipal(
            principal_type="demo",
            authentication_method="demo_cookie",
            subject_id="caller",
            tenant_id="caller",
            roles={"admin"},
        )


def test_bootstrap_cookie_flags_stability_and_frozen_grants():
    app, executor = app_for()
    with TestClient(app, base_url=ORIGIN) as client:
        response = client.get(SESSION_ENDPOINT)
        cookie = client.cookies.get(COOKIE_NAME)
        flags = response.headers["set-cookie"]
        assert all(flag in flags for flag in ("HttpOnly", "Secure", "SameSite=strict", "Path=/"))
        assert "Domain=" not in flags and response.headers["cache-control"] == "no-store"
        assert cookie not in response.text
        assert bootstrap(client) == cookie
        response = client.post(
            EXECUTE_ENDPOINT,
            json=payload(),
            headers={
                **HEADERS,
                "X-Tenant-ID": "enterprise",
                "X-User-ID": "admin",
                "X-Knowledge-Scope": "all",
                "X-Forwarded-For": "127.0.0.1",
            },
        )
        assert response.status_code == 200
        assert response.headers["cache-control"] == "no-store"
        assert cookie not in response.text
    context = executor.calls[0].security_context
    assert context.principal.principal_type is PrincipalType.DEMO
    assert context.principal.tenant_id == "nexus-public-demo"
    assert context.session_scope.subject_id == context.principal.subject_id
    assert context.knowledge_scope.allowed_document_ids == {
        "DOC-ORG-001",
        "DOC-AGENT-001",
        "DOC-INV-001",
    }
    assert context.data_scope.allowed_resources == {
        "products",
        "inventory_snapshots",
        "purchase_orders",
        "suppliers",
    }
    for resource in ("sales_orders", "sales_order_items"):
        assert not context.data_scope.permits(domain="enterprise_operations", resource=resource)
    assert not context.knowledge_scope.permits_document("DOC-HR-001")


def test_extra_scope_fields_rejected_before_execution():
    app, executor = app_for()
    with TestClient(app, base_url=ORIGIN) as client:
        bootstrap(client)
        for field in ("tenant_id", "user_id", "data_scope", "knowledge_scope"):
            response = client.post(
                EXECUTE_ENDPOINT, json={**payload(), field: "admin"}, headers=HEADERS
            )
            assert response.status_code == 422
    assert not executor.calls


@pytest.mark.parametrize(
    "origin", [None, "null", "https://attacker.test", "http://demo.test", "https://sub.demo.test"]
)
def test_cookie_does_not_allow_foreign_or_missing_origin(origin):
    app, executor = app_for()
    with TestClient(app, base_url=ORIGIN) as client:
        bootstrap(client)
        headers = {} if origin is None else {"Origin": origin}
        assert client.post(EXECUTE_ENDPOINT, json=payload(), headers=headers).status_code == 403
    assert not executor.calls


def test_fetch_metadata_and_duplicate_origin_fail_closed():
    app, executor = app_for()
    with TestClient(app, base_url=ORIGIN) as client:
        bootstrap(client)
        assert (
            client.get(SESSION_ENDPOINT, headers={"Sec-Fetch-Site": "cross-site"}).status_code
            == 403
        )
        assert (
            client.post(
                EXECUTE_ENDPOINT, json=payload(), headers={**HEADERS, "Sec-Fetch-Site": "same-site"}
            ).status_code
            == 403
        )
        assert (
            client.post(
                EXECUTE_ENDPOINT, json=payload(), headers=[("Origin", ORIGIN), ("Origin", ORIGIN)]
            ).status_code
            == 403
        )
    assert not executor.calls


@pytest.mark.parametrize("bad", [None, "", "garbage", "v1.a.1.2.signature", "x" * 257])
def test_missing_or_invalid_cookie_never_executes(bad):
    app, executor = app_for()
    with TestClient(app, base_url=ORIGIN) as client:
        if bad is not None:
            client.cookies.set(COOKIE_NAME, bad)
        assert client.post(EXECUTE_ENDPOINT, json=payload(), headers=HEADERS).status_code == 401
    assert not executor.calls


def test_cookie_tamper_expiry_key_and_origin_binding():
    now = [1000]
    config = settings()
    cookie = VisitorCookie(config, clock=lambda: now[0])
    value = cookie.issue()
    assert VisitorCookie(config, clock=lambda: now[0]).verify(value) == cookie.verify(value)
    tampered = value[:-1] + ("0" if value[-1] != "0" else "1")
    for codec, token in [
        (cookie, tampered),
        (VisitorCookie(settings(), clock=lambda: now[0]), value),
        (
            VisitorCookie(
                config.model_copy(update={"public_demo_origin": "https://other.test"}),
                clock=lambda: now[0],
            ),
            value,
        ),
    ]:
        with pytest.raises(SecurityAuthorizationError):
            codec.verify(token)
    now[0] = 999
    with pytest.raises(SecurityAuthorizationError):
        cookie.verify(value)
    now[0] = 1000 + config.public_demo_cookie_ttl_seconds
    with pytest.raises(SecurityAuthorizationError):
        cookie.verify(value)


def test_visitor_rate_limit_body_and_json_bounds_precede_execution():
    app, executor = app_for(settings(public_demo_requests_per_visitor=1))
    with TestClient(app, base_url=ORIGIN) as client:
        bootstrap(client)
        assert client.post(EXECUTE_ENDPOINT, json=payload(), headers=HEADERS).status_code == 200
        response = client.post(EXECUTE_ENDPOINT, json=payload(), headers=HEADERS)
        assert response.status_code == 429 and response.headers["retry-after"]
    assert len(executor.calls) == 1
    app, executor = app_for(settings(public_demo_max_body_bytes=1024))
    with TestClient(app, base_url=ORIGIN) as client:
        bootstrap(client)
        assert client.post(EXECUTE_ENDPOINT, content="plain", headers=HEADERS).status_code == 415
        assert (
            client.post(EXECUTE_ENDPOINT, json=payload("x" * 1500), headers=HEADERS).status_code
            == 413
        )
        assert (
            client.post(EXECUTE_ENDPOINT, json=payload("x" * 8001), headers=HEADERS).status_code
            == 413
        )
    assert not executor.calls


def test_bounded_limiter_does_not_evict_live_visitors_and_recovers_after_window():
    now = [0.0]
    limiter = DemoAdmission(settings(public_demo_max_visitors=1), clock=lambda: now[0])
    assert limiter.acquire("one")
    limiter.release()
    assert not limiter.acquire("two")
    now[0] = 60.0
    assert limiter.acquire("two")
    limiter.release()


def test_global_quota_survives_new_cookie_and_bootstrap_is_bounded():
    app, executor = app_for(
        settings(public_demo_requests_global=1, public_demo_bootstraps_global=2)
    )
    with TestClient(app, base_url=ORIGIN) as client:
        first = bootstrap(client)
        assert client.post(EXECUTE_ENDPOINT, json=payload(), headers=HEADERS).status_code == 200
        client.cookies.clear()
        assert bootstrap(client) != first
        assert client.post(EXECUTE_ENDPOINT, json=payload(), headers=HEADERS).status_code == 429
        assert client.get(SESSION_ENDPOINT).status_code == 429
    assert len(executor.calls) == 1


@pytest.mark.asyncio
async def test_active_limit_releases_on_cancellation_and_execution_failure():
    executor = Executor(entered=asyncio.Event(), blocked=asyncio.Event())
    app, _ = app_for(settings(public_demo_max_active=1), executor)
    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=ASGITransport(app), base_url=ORIGIN) as client,
    ):
        bootstrap_response = await client.get(SESSION_ENDPOINT)
        assert bootstrap_response.status_code == 200
        task = asyncio.create_task(client.post(EXECUTE_ENDPOINT, json=payload(), headers=HEADERS))
        await asyncio.wait_for(executor.entered.wait(), 2)
        assert (
            await client.post(EXECUTE_ENDPOINT, json=payload(), headers=HEADERS)
        ).status_code == 429
        assert (await client.get("/health")).status_code == 200
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        executor.blocked.set()
        executor.fail = True
        assert (
            await client.post(EXECUTE_ENDPOINT, json=payload(), headers=HEADERS)
        ).status_code == 500
        executor.fail = False
        assert (
            await client.post(EXECUTE_ENDPOINT, json=payload(), headers=HEADERS)
        ).status_code == 200


def test_public_factory_refuses_executor_without_authorization():
    app, executor = app_for(executor=Executor(requires_security_context=False))
    with TestClient(app, base_url=ORIGIN) as client:
        bootstrap(client)
        assert client.get("/ready").status_code == 503
        assert client.post(EXECUTE_ENDPOINT, json=payload(), headers=HEADERS).status_code == 503
    assert not executor.calls


def test_actual_executor_memory_isolated_for_same_label_and_new_session():
    class Coordinator:
        def __init__(self):
            self.calls = []

        async def execute(self, **kwargs):
            self.calls.append(kwargs)
            return CoordinatorResult(
                status=CoordinatorStatus.COMPLETED,
                route=RequestRoute.KNOWLEDGE,
                skill_name="enterprise-knowledge-qa",
                answer="Grounded [E1]",
                citations=["[E1]"],
                tool_steps=("run_knowledge_agent",),
                memory_context_selected="conversation_memory" in kwargs,
            )

    coordinator = Coordinator()
    executor = FormalRequestExecutor(
        coordinator=coordinator,
        memory_store=InMemorySessionMemoryStore(),
        memory_projector=ConversationMemoryProjector(),
        authorization_policy=DefaultDenyAuthorizationPolicy(),
        provider_governance=ProviderGovernance(
            policy=ProviderPolicy.controlled_mixed(),
            audit_sink=InMemoryAuditSink(),
            redactor=DeterministicProviderRedactor(),
        ),
    )
    app, _ = app_for(executor=executor)
    with TestClient(app, base_url=ORIGIN) as client:
        first = bootstrap(client)
        response = client.post(
            EXECUTE_ENDPOINT, json=payload("visitor-one-private", request_id="one"), headers=HEADERS
        )
        assert response.json()["memory_persistence_status"] == "persisted"
        client.cookies.clear()
        second = bootstrap(client)
        assert first != second
        response = client.post(EXECUTE_ENDPOINT, json=payload(request_id="two"), headers=HEADERS)
        assert response.json()["memory_context_status"] == "empty"
        assert "conversation_memory" not in coordinator.calls[-1]
        client.cookies.clear()
        client.cookies.set(COOKIE_NAME, first)
        response = client.post(EXECUTE_ENDPOINT, json=payload(request_id="three"), headers=HEADERS)
        assert response.json()["memory_context_status"] == "projected"
        assert "visitor-one-private" in coordinator.calls[-1]["conversation_memory"].content
        response = client.post(
            EXECUTE_ENDPOINT, json=payload(session="new-label", request_id="four"), headers=HEADERS
        )
        assert response.json()["memory_context_status"] == "empty"
        assert (
            coordinator.calls[0]["security_context"].principal.subject_id
            == coordinator.calls[-1]["security_context"].principal.subject_id
        )


@pytest.mark.asyncio
async def test_streaming_body_limit_and_timeout_release_capacity():
    executor = Executor()
    app, _ = app_for(
        settings(
            public_demo_max_active=1,
            public_demo_max_body_bytes=1024,
            public_demo_body_timeout_seconds=0.02,
        ),
        executor,
    )
    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=ASGITransport(app), base_url=ORIGIN) as client,
    ):
        assert (await client.get(SESSION_ENDPOINT)).status_code == 200

        async def oversize():
            yield b"x" * 800
            yield b"x" * 800

        async def slow():
            yield b"{"
            await asyncio.sleep(1)
            yield b"}"

        headers = {**HEADERS, "Content-Type": "application/json"}
        assert (
            await client.post(EXECUTE_ENDPOINT, content=oversize(), headers=headers)
        ).status_code == 413
        assert (
            await client.post(EXECUTE_ENDPOINT, content=slow(), headers=headers)
        ).status_code == 408
        assert not executor.calls
        assert (
            await client.post(EXECUTE_ENDPOINT, json=payload(), headers=HEADERS)
        ).status_code == 200


def test_existing_query_length_limit_preserved():
    app, executor = app_for()
    with TestClient(app, base_url=ORIGIN) as client:
        bootstrap(client)
        assert (
            client.post(EXECUTE_ENDPOINT, json=payload("x" * 8001), headers=HEADERS).status_code
            == 422
        )
    assert not executor.calls


def test_upgraded_pyjwt_does_not_mutate_reused_verification_options():
    import jwt

    options = {"verify_signature": False}
    key = secrets.token_urlsafe(32)
    token = jwt.encode({"exp": 1}, key, algorithm="HS256")
    jwt.decode(token, options=options)
    assert options == {"verify_signature": False}
    options["verify_signature"] = True
    with pytest.raises(jwt.ExpiredSignatureError):
        jwt.decode(token, key, algorithms=["HS256"], options=options)


@pytest.mark.asyncio
async def test_public_table_scope_filters_schema_and_blocks_mcp_query():
    from decision_agent.mcp_client.contracts import EnterpriseSchema
    from decision_agent.workflows.data_agent import ScopedEnterpriseDataClient

    app, executor = app_for()
    with TestClient(app, base_url=ORIGIN) as client:
        bootstrap(client)
        assert client.post(EXECUTE_ENDPOINT, json=payload(), headers=HEADERS).status_code == 200

    class Client:
        async def get_enterprise_schema(self):
            return EnterpriseSchema(
                tables={"products": ["product_id"], "sales_orders": ["order_id"]}
            )

        async def execute_safe_query(self, _sql):
            raise AssertionError("forbidden table must not reach MCP execution")

    scoped = ScopedEnterpriseDataClient(
        client=Client(), scope=executor.calls[0].security_context.data_scope
    )
    assert set((await scoped.get_enterprise_schema()).tables) == {"products"}
    result = await scoped.execute_safe_query("SELECT order_id FROM sales_orders")
    assert result.error_code == "data_scope_violation"


@pytest.mark.asyncio
async def test_execution_deadline_releases_public_admission_slot():
    executor = Executor(blocked=asyncio.Event())
    app, _ = app_for(
        settings(public_demo_max_active=1, request_execution_timeout_seconds=0.02), executor
    )
    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=ASGITransport(app), base_url=ORIGIN) as client,
    ):
        assert (await client.get(SESSION_ENDPOINT)).status_code == 200
        response = await client.post(EXECUTE_ENDPOINT, json=payload(), headers=HEADERS)
        assert response.status_code == 504
        executor.blocked.set()
        assert (
            await client.post(EXECUTE_ENDPOINT, json=payload(), headers=HEADERS)
        ).status_code == 200
