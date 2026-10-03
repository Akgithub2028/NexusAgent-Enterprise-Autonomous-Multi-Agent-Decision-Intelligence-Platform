"""Focused contracts for managed transport, offline models and release integrity."""

import hashlib
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from decision_agent.config import Settings
from decision_agent.data.executor import SQLAlchemyQueryExecutor
from decision_agent.exceptions import ConfigurationError
from decision_agent.release import verify_release
from decision_agent.retrieval.reranking import SentenceTransformerCrossEncoderReranker


@pytest.mark.parametrize(
    "socket",
    [
        "/tmp/mysql.sock",
        "/cloudsql/p:r:i/../x",
        "/cloudsql/project:region:instance/extra",
        "relative",
        "/cloudsql/" + "a" * 90 + ":us-west1:db",
    ],
)
def test_socket_rejects_unintended_paths(socket: str) -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, app_name="test", db_unix_socket=socket)


@pytest.mark.parametrize("socket", [None, "/cloudsql/nexus-agent-510512:us-west1:nexus-demo-mysql"])
def test_sql_engine_preserves_tcp_and_bounds_managed_pool(monkeypatch, socket: str | None) -> None:
    captured = {}
    sentinel = object()

    def engine(url, **kwargs):
        captured.update(url=url, **kwargs)
        return sentinel

    monkeypatch.setattr("decision_agent.data.executor.create_engine", engine)
    settings = Settings(
        _env_file=None,
        app_name="test",
        db_host="db.internal",
        db_readonly_password="unit-marker",
        db_unix_socket=socket,
    )
    executor = SQLAlchemyQueryExecutor.from_settings(settings)
    assert executor.engine is sentinel
    assert captured["max_overflow"] == 0 and captured["pool_size"] == 2
    assert captured["url"].host == (None if socket else "db.internal")
    assert captured["connect_args"].get("unix_socket") == socket
    assert captured["connect_args"]["read_timeout"] == settings.db_query_timeout_seconds


@pytest.mark.asyncio
async def test_reranker_passes_offline_cache_and_disables_remote_code() -> None:
    captured = {}

    def factory(**kwargs):
        captured.update(kwargs)
        return object()

    model = SentenceTransformerCrossEncoderReranker(
        model_factory=factory, cache_folder="/cache", local_files_only=True
    )
    await model.initialize()
    assert captured["cache_folder"] == "/cache"
    assert captured["local_files_only"] is True
    assert captured["trust_remote_code"] is False


def test_release_checksum_and_collection_mismatch_fail_closed(tmp_path: Path) -> None:
    for name in ("corpus/a", "models/embedding/a", "models/reranker/a"):
        p = tmp_path / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"asset")
    settings = Settings(
        _env_file=None,
        app_name="test",
        release_manifest_path=tmp_path / "release.json",
        knowledge_dataset_root=tmp_path / "corpus",
        corpus_release_id="test",
        milvus_collection="test",
        embedding_model_name=str(tmp_path / "models/embedding"),
        reranker_model_name=str(tmp_path / "models/reranker"),
        embedding_local_files_only=True,
        reranker_local_files_only=True,
    )
    manifest = {
        "schema_version": 1,
        "vector_schema": "decision-agent-vector-schema-v1",
        "dimension": 512,
        "metric": "COSINE",
        "collection": "test",
        "corpus_release_id": "test",
        "models": {
            role: {"revision": getattr(settings, f"{role}_model_revision"), "license": "MIT"}
            for role in ("embedding", "reranker")
        },
        "sha256": {
            name: hashlib.sha256(b"asset").hexdigest()
            for name in ("corpus/a", "models/embedding/a", "models/reranker/a")
        },
    }
    settings.release_manifest_path.write_text(json.dumps(manifest))
    assert verify_release(settings) == manifest
    with pytest.raises(ConfigurationError):
        verify_release(settings.model_copy(update={"milvus_collection": "wrong"}))
    (tmp_path / "corpus/a").write_bytes(b"changed")
    with pytest.raises(ConfigurationError, match="release_manifest_invalid"):
        verify_release(settings)
