"""Mandatory stdout audit integrity and failure semantics; no cloud dependencies."""

import io
import json
from concurrent.futures import ThreadPoolExecutor

import pytest
from tests.unit.security.test_provider_policy_and_audit import _context, _event

from decision_agent.observability.cloud_logging import CloudLogMetadata
from decision_agent.security import (
    AuditChainError,
    DataClassification,
    DeterministicProviderRedactor,
    ProviderGovernance,
    ProviderPolicy,
    ProviderPolicyError,
    ProviderStage,
)
from decision_agent.security.audit import AuditEvent, StdoutAuditSink, _event_hash

pytestmark = pytest.mark.offline_integration


class FailingStream(io.StringIO):
    def __init__(self, *, fail_on=1, short=False, fail_flush=False):
        super().__init__()
        self.writes = 0
        self.fail_on = fail_on
        self.short = short
        self.fail_flush = fail_flush

    def write(self, value):
        self.writes += 1
        if self.writes >= self.fail_on:
            if self.short:
                return super().write(value[:10])
            if not self.fail_flush:
                raise OSError("PRIVATE_STREAM_SECRET")
        return super().write(value)

    def flush(self):
        if self.fail_flush:
            raise OSError("PRIVATE_FLUSH_SECRET")
        super().flush()


def test_stdout_chain_serializes_concurrent_events_with_release_metadata():
    stream = io.StringIO()
    metadata = CloudLogMetadata(release_id="p2", corpus_release_id="m2c1", revision="rev-1")
    sink = StdoutAuditSink(metadata=metadata, stream=stream)
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(lambda n: sink.append(_event(n)), range(30)))
    previous = ""
    for line in stream.getvalue().splitlines():
        envelope = json.loads(line)
        assert set(envelope) == {"event", "severity", "runtime", "audit"}
        assert envelope["runtime"] == metadata.model_dump()
        event = AuditEvent.model_validate(envelope["audit"])
        assert event.previous_event_hash == previous
        assert event.event_hash == _event_hash(event.model_copy(update={"event_hash": ""}))
        previous = event.event_hash
    sink.close()
    sink.close()
    assert not stream.closed
    with pytest.raises(AuditChainError):
        sink.append(_event())


@pytest.mark.parametrize("options", [{}, {"short": True}, {"fail_flush": True}])
def test_write_failures_poison_sink_and_do_not_expose_underlying_error(options):
    stream = FailingStream(**options)
    sink = StdoutAuditSink(metadata=CloudLogMetadata(), stream=stream)
    with pytest.raises(AuditChainError) as caught:
        sink.append(_event())
    assert str(caught.value) == "audit_write_failed"
    with pytest.raises(AuditChainError, match="audit_sink_unavailable"):
        sink.append(_event())
    assert stream.writes == 1


@pytest.mark.parametrize("fail_on,expected_calls", [(1, 0), (2, 1)])
async def test_governance_denies_before_transport_or_after_completion_audit_failure(
    fail_on, expected_calls
):
    stream = FailingStream(fail_on=fail_on)
    sink = StdoutAuditSink(metadata=CloudLogMetadata(), stream=stream)
    governance = ProviderGovernance(
        policy=ProviderPolicy.controlled_mixed(),
        audit_sink=sink,
        redactor=DeterministicProviderRedactor(),
    )
    calls = []

    async def transport(payload):
        calls.append(payload)
        return {"content": "safe response"}

    with (
        governance.bind_request(
            request_id="request-1", trace_id="trace-1", security_context=_context()
        ),
        pytest.raises(ProviderPolicyError if fail_on == 1 else AuditChainError),
    ):
        await governance.call(
            stage=ProviderStage.ROUTING,
            payload={"query": "business question"},
            classification=DataClassification.INTERNAL,
            evidence_count=0,
            transport=transport,
        )
    assert len(calls) == expected_calls
    assert "business question" not in stream.getvalue()
    assert "safe response" not in stream.getvalue()


@pytest.mark.parametrize("failing", [False, True])
async def test_actual_executor_blocks_answer_release_when_stdout_audit_fails(failing):
    from tests.unit.observability.test_executor_instrumentation import (
        _completed_result,
        _Coordinator,
    )

    from decision_agent.application.executor import FormalRequestExecutor
    from decision_agent.application.models import FormalRequest
    from decision_agent.context.conversation_memory import ConversationMemoryProjector

    stream = FailingStream(fail_on=3) if failing else io.StringIO()
    sink = StdoutAuditSink(metadata=CloudLogMetadata(), stream=stream)
    governance = ProviderGovernance(
        policy=ProviderPolicy.controlled_mixed(),
        audit_sink=sink,
        redactor=DeterministicProviderRedactor(),
    )
    executor = FormalRequestExecutor(
        coordinator=_Coordinator(_completed_result()),
        memory_store=None,
        memory_projector=ConversationMemoryProjector(),
        provider_governance=governance,
    )
    response = await executor.execute(
        FormalRequest(
            request_id="request-1",
            user_query="private business question",
            security_context=_context(),
        )
    )
    if failing:
        assert response.result.answer is None and not response.result.citations
        assert response.result.error_code == "response_release_blocked"
    else:
        assert response.result.answer == "ANSWER_SECRET_DO_NOT_LEAK"
        assert (
            json.loads(stream.getvalue().splitlines()[-1])["audit"]["event_type"]
            == "response_release_allowed"
        )
    assert "private business question" not in stream.getvalue()
    assert "ANSWER_SECRET_DO_NOT_LEAK" not in stream.getvalue()
