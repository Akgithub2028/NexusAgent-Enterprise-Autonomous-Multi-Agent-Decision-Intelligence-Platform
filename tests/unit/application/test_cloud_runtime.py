"""Cloud launcher, safe logging and real SIGTERM lifespan verification."""

import io
import json
import logging
import os
import signal
import socket
import subprocess
import sys
import time
from urllib.request import urlopen

import pytest
from tests.unit.observability.test_sinks import _trace

from decision_agent import cloud
from decision_agent.config import Settings
from decision_agent.observability.cloud_logging import CloudJsonFormatter, CloudLogMetadata
from decision_agent.observability.sinks import StructuredLoggingTraceSink

pytestmark = pytest.mark.offline_integration


@pytest.mark.parametrize(
    "value,expected", [(None, 8080), ("9000", 9000), ("1", 1), ("65535", 65535)]
)
def test_container_port(value, expected):
    assert cloud.container_port(value) == expected


@pytest.mark.parametrize("value", ["", "0", "65536", "-1", "1.5", " 8000", "abc", "8000\n"])
def test_invalid_port_never_defaults(value):
    with pytest.raises(ValueError, match="cloud_port_invalid"):
        cloud.container_port(value)


def test_launcher_uses_formal_factory_one_worker_and_json_logging(monkeypatch):
    settings = Settings(app_name="P2", _env_file=None, audit_mode="stdout")
    monkeypatch.setenv("PORT", "9001")
    monkeypatch.setenv("K_REVISION", "rev-test")
    captured = {}

    def make_settings(**kwargs):
        return settings.model_copy(update=kwargs)

    monkeypatch.setattr(cloud, "Settings", make_settings)
    app = object()
    monkeypatch.setattr(cloud, "create_deployment_app", lambda s: app)
    monkeypatch.setattr(cloud, "configure_cloud_logging", lambda m: captured.update(metadata=m))
    monkeypatch.setattr(cloud.uvicorn, "run", lambda a, **kw: captured.update(app=a, **kw))
    assert cloud.main() == 0
    assert captured["app"] is app
    assert captured["host"] == "0.0.0.0" and captured["port"] == 9001
    assert captured["workers"] == 1 and captured["reload"] is False
    assert captured["log_config"] is None and captured["access_log"] is False
    assert captured["metadata"].revision == "rev-test"


def test_invalid_launch_configuration_does_not_start_or_leak_values(monkeypatch, capsys):
    monkeypatch.setenv("PORT", "PRIVATE_PORT_SECRET")
    monkeypatch.setattr(cloud.uvicorn, "run", lambda *a, **k: pytest.fail("must not start"))
    assert cloud.main() == 2
    assert capsys.readouterr().err == '{"error_code": "cloud_configuration_invalid"}\n'


def test_json_formatter_preserves_safe_trace_and_discards_library_exception_payload():
    metadata = CloudLogMetadata(release_id="image-123", corpus_release_id="corpus-1")
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(CloudJsonFormatter(metadata))
    logger = logging.getLogger("decision_agent.observability")
    old = logger.handlers[:], logger.level, logger.propagate
    try:
        logger.handlers[:] = [handler]
        logger.setLevel(logging.INFO)
        logger.propagate = False
        StructuredLoggingTraceSink(logger=logger).emit(_trace())
        record = logging.LogRecord(
            "httpx",
            logging.ERROR,
            "",
            0,
            "PRIVATE_QUERY_SECRET %s",
            ("PRIVATE_URL_SECRET",),
            (ValueError, ValueError("PRIVATE_EXCEPTION_SECRET"), None),
        )
        handler.handle(record)
    finally:
        logger.handlers[:], logger.level, logger.propagate = old
    first, second = map(json.loads, stream.getvalue().splitlines())
    assert first["event"] == "decision_agent.request_trace"
    assert first["severity"] == "INFO" and first["runtime"] == metadata.model_dump()
    assert second["event"] == "runtime_diagnostic"
    assert "PRIVATE_" not in stream.getvalue()


def test_real_server_sigterm_revokes_and_closes_lifespan_resources(tmp_path):
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    marker = tmp_path / "closed.json"
    # Same launcher and lifespan, deterministic builder only; no SQL/provider/model I/O.
    driver = """
import json, pathlib
from decision_agent import cloud
from decision_agent.api.runtime import create_bootstrapped_app
from decision_agent.config import Settings
marker = pathlib.Path(__import__('sys').argv[1])
def factory(settings):
    async def builder(stack):
        stack.callback(lambda: marker.write_text(json.dumps({"closed": True})))
        return object()
    return create_bootstrapped_app(settings, builder)
cloud.create_deployment_app = factory
raise SystemExit(cloud.main())
"""
    env = {k: v for k, v in os.environ.items() if not k.startswith("DECISION_AGENT_")}
    env.update(PORT=str(port), DECISION_AGENT_APP_NAME="P2 lifecycle")
    with (tmp_path / "server.log").open("w") as log:
        process = subprocess.Popen(
            [sys.executable, "-c", driver, str(marker)], env=env, stdout=log, stderr=log
        )
        try:
            deadline = time.monotonic() + 15
            while time.monotonic() < deadline:
                assert process.poll() is None
                try:
                    with urlopen(f"http://127.0.0.1:{port}/ready", timeout=0.5) as response:
                        if response.status == 200:
                            break
                except OSError:
                    time.sleep(0.05)
            else:
                pytest.fail("server did not become ready")
            process.send_signal(signal.SIGTERM)
            process.wait(timeout=10)
            assert process.returncode in (0, -signal.SIGTERM)
            assert json.loads(marker.read_text()) == {"closed": True}
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=5)


def test_best_effort_handler_failure_never_prints_exception_or_payload(capsys):
    from tests.unit.security.test_stdout_audit import FailingStream

    from decision_agent.observability.cloud_logging import SafeCloudHandler

    handler = SafeCloudHandler(FailingStream())
    handler.setFormatter(CloudJsonFormatter(CloudLogMetadata()))
    record = logging.LogRecord("httpx", logging.INFO, "", 0, "PRIVATE_PAYLOAD", (), None)
    handler.handle(record)
    assert capsys.readouterr() == ("", "")


@pytest.mark.parametrize(
    "values",
    [
        {"audit_mode": "off"},
        {"memory_max_sessions": 0},
        {"memory_max_sessions": 100001},
        {"release_id": "https://secret.invalid"},
        {"corpus_release_id": "a b"},
        {"runtime_revision": "bad\nvalue"},
    ],
)
def test_runtime_settings_reject_invalid_sink_capacity_or_metadata(values):
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        Settings(app_name="P2", _env_file=None, **values)
