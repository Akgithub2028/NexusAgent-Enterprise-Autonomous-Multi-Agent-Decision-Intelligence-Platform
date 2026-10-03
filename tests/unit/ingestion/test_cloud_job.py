"""Release failure, immutable rerun and distributed-lock safety contracts."""

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from scripts.prepare_corpus_promotion import check_execution

from decision_agent.ingestion import cloud_job

IMAGE = "us-west1-docker.pkg.dev/project/repo/app@sha256:" + "a" * 64
MANIFEST = {"collection": "nexus_test", "corpus_release_id": "test", "children": 2, "parents": 1}


@pytest.mark.asyncio
async def test_first_repeat_and_failure(monkeypatch):
    monkeypatch.setattr(cloud_job, "verify_release", lambda _: MANIFEST)
    validate = AsyncMock()
    monkeypatch.setattr(cloud_job, "validate_runtime", validate)
    runtime = SimpleNamespace(
        initialize_for_ingestion=AsyncMock(), initialize=AsyncMock(), aclose=AsyncMock()
    )
    control = Mock()
    control.acquire.return_value = "19"
    control.request.return_value = None
    settings = SimpleNamespace(knowledge_dataset_root="unused")
    first = await cloud_job.ingest(settings, IMAGE, control, factory=lambda _: runtime)
    runtime.initialize_for_ingestion.assert_awaited_once()
    control.release.assert_called_with("locks/nexus_test.json", "19")
    published = next(
        c
        for c in control.request.call_args_list
        if c.args[0] == "POST" and c.args[1].startswith("validated/")
    )
    assert json.loads(published.kwargs["body"]) == first

    control.reset_mock()
    control.request.side_effect = lambda method, name, **kw: (
        {"manifest_sha256": first["manifest_sha256"]} if name.startswith("bindings/") else first
    )
    await cloud_job.ingest(settings, IMAGE, control, factory=lambda _: runtime)
    runtime.initialize.assert_awaited_once()
    assert not any(
        c.args[0] == "POST" and c.args[1].startswith("validated/")
        for c in control.request.call_args_list
    )

    control.reset_mock()
    control.request.side_effect = None
    control.request.return_value = None
    validate.side_effect = ValueError("partial corpus")
    with pytest.raises(ValueError):
        await cloud_job.ingest(settings, IMAGE, control, factory=lambda _: runtime)
    assert not any(
        c.args[0] == "POST" and c.args[1].startswith("validated/")
        for c in control.request.call_args_list
    )
    control.release.assert_called_once()
    assert runtime.aclose.await_count == 3


@pytest.mark.asyncio
async def test_lock_contention_never_opens_runtime(monkeypatch):
    monkeypatch.setattr(cloud_job, "verify_release", lambda _: MANIFEST)
    control = Mock()
    control.acquire.side_effect = RuntimeError("locked")
    factory = Mock()
    with pytest.raises(RuntimeError):
        await cloud_job.ingest(None, IMAGE, control, factory=factory)
    factory.assert_not_called()
    control.release.assert_not_called()


def test_image_and_execution_gates():
    with pytest.raises(ValueError):
        cloud_job.release_descriptor(MANIFEST, "app:latest")
    execution = {
        "status": {"succeededCount": 1, "conditions": [{"type": "Completed", "status": "True"}]},
        "spec": {"template": {"spec": {"containers": [{"image": IMAGE}]}}},
    }
    check_execution(execution, IMAGE)
    execution["status"]["failedCount"] = 1
    with pytest.raises(ValueError):
        check_execution(execution, IMAGE)
    assert cloud_job.release_descriptor(MANIFEST, IMAGE) != cloud_job.release_descriptor(
        {**MANIFEST, "children": 1, "collection": "nexus_new"}, IMAGE
    )


@pytest.mark.asyncio
async def test_cleanup_and_receipt_mismatch_block_completion(monkeypatch):
    monkeypatch.setattr(cloud_job, "verify_release", lambda _: MANIFEST)
    monkeypatch.setattr(cloud_job, "validate_runtime", AsyncMock())
    runtime = SimpleNamespace(
        initialize_for_ingestion=AsyncMock(),
        aclose=AsyncMock(side_effect=RuntimeError("close failure")),
    )
    control = Mock()
    control.request.return_value = None
    settings = SimpleNamespace(knowledge_dataset_root="unused")
    with pytest.raises(RuntimeError):
        await cloud_job.ingest(settings, IMAGE, control, factory=lambda _: runtime)
    assert not any(
        c.args[0] == "POST" and c.args[1].startswith("validated/")
        for c in control.request.call_args_list
    )
    control.release.assert_called_once()
    control.request.return_value = {"image": "mismatched"}
    factory = Mock()
    with pytest.raises(ValueError):
        await cloud_job.ingest(settings, IMAGE, control, factory=factory)
    factory.assert_not_called()


@pytest.mark.asyncio
async def test_validation_uses_canonical_fields_and_filtered_retrieval(monkeypatch):
    child = SimpleNamespace(
        chunk_id="c",
        parent_id="p",
        document_id="d",
        document_version="v1",
        content="synthetic",
        source=None,
        page_number=None,
        metadata={},
    )
    monkeypatch.setattr(cloud_job, "_load_generated_chunks", lambda _: ([object()], [child]))
    store = SimpleNamespace(verify_record_fields=AsyncMock())
    pipeline = SimpleNamespace(
        retrieve=AsyncMock(
            return_value=SimpleNamespace(
                dense_results=[SimpleNamespace(document_id="d")], expanded_parent_results=[object()]
            )
        )
    )
    runtime = SimpleNamespace(vector_store=store, pipeline=pipeline)
    await cloud_job.validate_runtime(runtime, {"parents": 1, "children": 1}, "unused")
    assert store.verify_record_fields.call_args.args[0][0]["schema_version"] == "v1"
    pipeline.retrieve.assert_awaited_once_with("synthetic", allowed_document_ids=frozenset({"d"}))
    pipeline.retrieve.return_value.dense_results[0].document_id = "excluded"
    with pytest.raises(ValueError):
        await cloud_job.validate_runtime(runtime, {"parents": 1, "children": 1}, "unused")


def test_storage_preconditions_and_safe_errors(monkeypatch):
    from io import BytesIO
    from urllib.error import HTTPError

    calls = []

    def open_request(request, timeout):
        calls.append(request)
        if "metadata.google" in request.full_url:
            return BytesIO(b'{"access_token":"private-test-token"}')
        return BytesIO(b'{"generation":"27"}' if request.method == "POST" else b"")

    monkeypatch.setattr(cloud_job, "urlopen", open_request)
    control = cloud_job.GCSControl("test-control-bucket")
    assert control.acquire("locks/a.json") == "27"
    assert "ifGenerationMatch=0" in calls[-1].full_url
    control.release("locks/a.json", "27")
    assert "ifGenerationMatch=27" in calls[-1].full_url

    def denied(request, timeout):
        if "metadata.google" in request.full_url:
            return BytesIO(b'{"access_token":"private-test-token"}')
        raise HTTPError(request.full_url, 412, "sensitive provider details", {}, None)

    monkeypatch.setattr(cloud_job, "urlopen", denied)
    with pytest.raises(RuntimeError, match=r"^control_storage_failed$"):
        control.acquire("locks/a.json")


@pytest.mark.asyncio
async def test_remote_field_and_obsolete_id_validation():
    from decision_agent.exceptions import VectorStoreOperationError
    from decision_agent.retrieval.milvus_store import MilvusVectorStore

    client = Mock()
    store = MilvusVectorStore(
        dimension=512, uri="http://localhost:19530", collection_name="test", client=client
    )
    store._initialized = True
    store.list_record_ids = AsyncMock(return_value=frozenset({"c"}))
    expected = [{"record_id": "c", "metadata": {"scope": "synthetic"}}]
    client.query.return_value = expected
    await store.verify_record_fields(expected)
    client.query.return_value = [{"record_id": "c", "metadata": {"scope": "wrong"}}]
    with pytest.raises(VectorStoreOperationError):
        await store.verify_record_fields(expected)
    store.list_record_ids.return_value = frozenset({"c", "obsolete"})
    with pytest.raises(VectorStoreOperationError):
        await store.verify_record_fields(expected)
