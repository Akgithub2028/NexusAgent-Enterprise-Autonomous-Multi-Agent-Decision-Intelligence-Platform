"""Verify baked assets and configuration before opening runtime resources."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from decision_agent.config import Settings
from decision_agent.exceptions import ConfigurationError


def verify_release(settings: Settings) -> dict | None:
    if settings.release_manifest_path is None:
        return None
    try:
        path = settings.release_manifest_path.resolve(strict=True)
        root = path.parent
        manifest = json.loads(path.read_text())
        if (
            manifest["schema_version"] != 1
            or manifest["vector_schema"] != "decision-agent-vector-schema-v1"
            or manifest["dimension"] != settings.embedding_dimension
            or manifest["metric"] != settings.milvus_metric_type.value
            or manifest["collection"] != settings.milvus_collection
            or manifest["corpus_release_id"] != settings.corpus_release_id
            or settings.knowledge_dataset_root.resolve() != root / "corpus"
        ):
            raise ValueError("incompatible release")
        for role in ("embedding", "reranker"):
            model = manifest["models"][role]
            if (
                model["revision"] != getattr(settings, f"{role}_model_revision")
                or model["license"] != "MIT"
                or Path(getattr(settings, f"{role}_model_name")).resolve() != root / "models" / role
                or not getattr(settings, f"{role}_local_files_only")
            ):
                raise ValueError("incompatible offline model")
        files = manifest["sha256"]
        if not files or not all(
            any(k.startswith(prefix) for k in files)
            for prefix in ("corpus/", "models/embedding/", "models/reranker/")
        ):
            raise ValueError("incomplete assets")
        for name, expected in files.items():
            asset = (root / name).resolve(strict=True)
            if not asset.is_relative_to(root) or not asset.is_file():
                raise ValueError("invalid asset path")
            checksum = hashlib.sha256()
            with asset.open("rb") as stream:
                for block in iter(lambda: stream.read(1024 * 1024), b""):
                    checksum.update(block)
            if checksum.hexdigest() != expected:
                raise ValueError("asset checksum mismatch")
        return manifest
    except (OSError, KeyError, TypeError, ValueError, AttributeError):
        raise ConfigurationError("release_manifest_invalid") from None
