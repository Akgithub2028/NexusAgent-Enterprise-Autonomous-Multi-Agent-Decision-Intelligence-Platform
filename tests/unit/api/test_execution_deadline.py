"""Cancellation and native-thread serialization required by restricted P6 serving."""

import asyncio
import threading
from types import SimpleNamespace

import pytest
from httpx import ASGITransport, AsyncClient

from decision_agent.api import create_app
from decision_agent.config import Settings
from decision_agent.retrieval._threading import locked_call


@pytest.mark.asyncio
async def test_deadline_cancels_executor_and_keeps_health_responsive():
    cancelled = asyncio.Event()
    entered = asyncio.Event()

    async def execute(request):
        entered.set()
        try:
            await asyncio.sleep(10)
        finally:
            cancelled.set()

    app = create_app(
        Settings(
            app_name="P6",
            environment="test",
            _env_file=None,
            request_execution_timeout_seconds=0.03,
        ),
        formal_request_executor=SimpleNamespace(execute=execute),
    )
    async with AsyncClient(transport=ASGITransport(app), base_url="https://demo.test") as client:
        task = asyncio.create_task(
            client.post(
                "/api/v1/agent/execute", json={"request_id": "deadline", "query": "synthetic"}
            )
        )
        await entered.wait()
        assert (await client.get("/health")).status_code == 200
        response = await task
        assert response.status_code == 504
        assert response.json()["code"] == "execution_deadline_exceeded"
        assert cancelled.is_set()


@pytest.mark.asyncio
async def test_dependency_timeout_is_not_misreported_as_total_deadline():
    async def execute(request):
        raise TimeoutError("private provider message")

    app = create_app(
        Settings(app_name="P6", environment="test", _env_file=None),
        formal_request_executor=SimpleNamespace(execute=execute),
    )
    async with AsyncClient(transport=ASGITransport(app), base_url="https://demo.test") as client:
        response = await client.post(
            "/api/v1/agent/execute", json={"request_id": "inner", "query": "test"}
        )
        assert response.status_code == 500
        assert "private" not in response.text


@pytest.mark.asyncio
async def test_cancelled_native_call_retains_thread_serialization():
    lock = threading.Lock()
    entered, release, second_entered = threading.Event(), threading.Event(), threading.Event()

    def first():
        entered.set()
        assert release.wait(2)

    task = asyncio.create_task(asyncio.to_thread(locked_call, lock, first))
    try:
        await asyncio.to_thread(entered.wait, 1)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        second = asyncio.create_task(asyncio.to_thread(locked_call, lock, second_entered.set))
        await asyncio.sleep(0.02)
        assert not second_entered.is_set()
        release.set()
        await second
        assert second_entered.is_set()
    finally:
        release.set()
