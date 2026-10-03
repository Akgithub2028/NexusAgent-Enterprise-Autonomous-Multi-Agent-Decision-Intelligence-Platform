"""Build immutable model/corpus assets; no provider or database credentials required."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

MODELS = {
    "embedding": ("BAAI/bge-small-zh-v1.5", "7999e1d3359715c523056ef9478215996d62a620"),
    "reranker": ("BAAI/bge-reranker-base", "2cfc18c9415c912f9d8155881c133215df768a70"),
}


def digest(path: Path) -> str:
    checksum = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            checksum.update(block)
    return checksum.hexdigest()


def prepare(source: Path, output: Path) -> dict:
    from huggingface_hub import HfApi, snapshot_download

    output.mkdir(parents=True, exist_ok=True)
    corpus = output / "corpus"
    selected = [
        *sorted((source / "documents").glob("*.md")),
        source / "document_manifest.json",
        source / "generated/parent_chunks.jsonl",
        source / "generated/child_chunks.jsonl",
    ]
    for path in selected:
        target = corpus / path.relative_to(source)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
    models = {}
    for role, (name, revision) in MODELS.items():
        info = HfApi().model_info(name, revision=revision)
        if info.sha != revision or info.card_data.get("license") != "mit":
            raise RuntimeError("pinned model revision/license mismatch")
        snapshot_download(
            name,
            revision=revision,
            local_dir=output / "models" / role,
            allow_patterns=[
                "*.json",
                "*.txt",
                "*.model",
                "*.safetensors",
                "README.md",
                "1_Pooling/*",
            ],
        )
        # Download metadata is build-only; inference uses immutable local directories.
        shutil.rmtree(output / "models" / role / ".cache", ignore_errors=True)
        models[role] = {"repository": name, "revision": revision, "license": "MIT"}
    hashes = {
        str(p.relative_to(output)): digest(p)
        for p in sorted(output.rglob("*"))
        if p.is_file() and p.name != "release.json"
    }
    corpus_hashes = {k: v for k, v in hashes.items() if k.startswith("corpus/")}
    release = hashlib.sha256(json.dumps(corpus_hashes, sort_keys=True).encode()).hexdigest()[:16]
    manifest = {
        "schema_version": 1,
        "corpus_release_id": f"m2c1_{release}",
        "collection": f"nexus_m2c1_{release}",
        "vector_schema": "decision-agent-vector-schema-v1",
        "dimension": 512,
        "metric": "COSINE",
        "models": models,
        "documents": len(list((corpus / "documents").glob("*.md"))),
        "parents": len((corpus / "generated/parent_chunks.jsonl").read_text().splitlines()),
        "children": len((corpus / "generated/child_chunks.jsonl").read_text().splitlines()),
        "sha256": hashes,
    }
    if (manifest["documents"], manifest["parents"], manifest["children"]) != (12, 36, 101):
        raise RuntimeError("unexpected corpus counts; review the release specification")
    (output / "release.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path("datasets/enterprise_kb/m2c1"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = prepare(args.source.resolve(), args.output.resolve())
    print(
        json.dumps(
            {
                k: manifest[k]
                for k in ("corpus_release_id", "collection", "documents", "parents", "children")
            }
        )
    )


if __name__ == "__main__":
    main()
