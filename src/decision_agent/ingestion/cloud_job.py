"""Independent immutable-corpus ingestion; never imported by API startup."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import re
import sys
import uuid
from urllib.error import HTTPError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from decision_agent.config import Settings
from decision_agent.release import verify_release
from decision_agent.retrieval.factory import build_production_retrieval_runtime
from decision_agent.retrieval.pipeline import _load_generated_chunks


def canonical(value: dict) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def release_descriptor(manifest: dict, image: str) -> dict:
    """Bind completion to the entire manifest and an immutable registry digest."""
    if not re.fullmatch(r"[a-z0-9.-]+/[A-Za-z0-9_./-]+@sha256:[a-f0-9]{64}", image):
        raise ValueError("immutable image required")
    return {
        "schema_version": 1,
        "status": "validated",
        "image": image,
        "manifest_sha256": hashlib.sha256(canonical(manifest)).hexdigest(),
        "corpus_release_id": manifest["corpus_release_id"],
        "collection": manifest["collection"],
        "children": manifest["children"],
        "parents": manifest["parents"],
    }


class GCSControl:
    """Generation-precondition lock/receipt storage using the job's metadata identity.

    Locks never expire automatically: an interrupted writer requires an operator to
    confirm the execution stopped before removing its exact object generation.
    """

    def __init__(self, bucket: str):
        if not re.fullmatch(r"[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]", bucket):
            raise ValueError("invalid control bucket")
        self.bucket = bucket

    def request(self, method: str, name: str, *, body=None, generation=None):
        token_request = Request(
            "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token",
            headers={"Metadata-Flavor": "Google"},
        )
        with urlopen(token_request, timeout=10) as response:
            token = json.load(response)["access_token"]
        query = {}
        if method == "POST":
            url = f"https://storage.googleapis.com/upload/storage/v1/b/{self.bucket}/o"
            query = {"uploadType": "media", "name": name, "ifGenerationMatch": "0"}
        else:
            url = f"https://storage.googleapis.com/storage/v1/b/{self.bucket}/o/{quote(name, safe='')}"
            if method == "GET":
                query["alt"] = "media"
            else:
                query["ifGenerationMatch"] = str(generation)
        request = Request(
            url + "?" + urlencode(query),
            method=method,
            data=body,
            headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"},
        )
        try:
            with urlopen(request, timeout=30) as response:
                return json.load(response) if method != "DELETE" else None
        except HTTPError as exc:
            if exc.code == 404 and method == "GET":
                return None
            raise RuntimeError("control_storage_failed") from None

    def acquire(self, name: str) -> str:
        result = self.request("POST", name, body=canonical({"owner": uuid.uuid4().hex}))
        return result["generation"]

    def release(self, name: str, generation: str) -> None:
        self.request("DELETE", name, generation=generation)


async def validate_runtime(runtime, manifest: dict, root) -> None:
    parents, children = _load_generated_chunks(root)
    if len(parents) != manifest["parents"] or len(children) != manifest["children"]:
        raise ValueError("manifest counts differ")
    expected = [
        {
            "record_id": c.chunk_id,
            "parent_id": c.parent_id,
            "document_id": c.document_id,
            "document_version": c.document_version,
            "content": c.content,
            "source": c.source,
            "page_number": c.page_number,
            "metadata": dict(c.metadata),
            "schema_version": "v1",
        }
        for c in children
    ]
    await runtime.vector_store.verify_record_fields(expected)
    # Exercise the actual embedding/vector/BM25/reranker/parent chain in a scoped sample.
    sample = children[0]
    result = await runtime.pipeline.retrieve(
        sample.content[:300], allowed_document_ids=frozenset({sample.document_id})
    )
    if (
        not result.dense_results
        or not result.expanded_parent_results
        or any(hit.document_id != sample.document_id for hit in result.dense_results)
    ):
        raise ValueError("sample retrieval failed")


async def ingest(settings, image, control, *, factory=build_production_retrieval_runtime):
    manifest = verify_release(settings)
    if manifest is None:
        raise ValueError("baked release required")
    descriptor = release_descriptor(manifest, image)
    # Keyed by collection, not image: different builds of one corpus cannot write concurrently.
    lock = "locks/" + manifest["collection"] + ".json"
    receipt = "validated/" + manifest["collection"] + ".json"
    generation = control.acquire(lock)
    try:
        binding_name = "bindings/" + manifest["collection"] + ".json"
        binding = {"manifest_sha256": descriptor["manifest_sha256"]}
        existing_binding = control.request("GET", binding_name)
        if existing_binding is None:
            control.request("POST", binding_name, body=canonical(binding))
        elif existing_binding != binding:
            raise ValueError("collection already bound to another manifest")
        previous = control.request("GET", receipt)
        if previous is not None and previous != descriptor:
            raise ValueError("immutable completion differs; use original image")
        runtime = factory(settings)
        try:
            if previous is None:
                await runtime.initialize_for_ingestion()
            else:
                # Published releases are immutable. Repeat runs validate without any writes.
                await runtime.initialize()
            await validate_runtime(runtime, manifest, settings.knowledge_dataset_root)
        finally:
            await runtime.aclose()
        if previous is None:
            control.request("POST", receipt, body=canonical(descriptor))
    finally:
        control.release(lock, generation)
    return descriptor


def main() -> int:
    logging.getLogger("pymilvus").setLevel(logging.CRITICAL)
    try:
        if os.environ.get("CLOUD_RUN_TASK_COUNT", "1") != "1":
            raise ValueError("single task required")
        # Job identity has only the writer secret; no LLM, SQL or public-demo identity needed.
        descriptor = asyncio.run(
            ingest(
                Settings(),
                os.environ["NEXUS_RELEASE_IMAGE"],
                GCSControl(os.environ["NEXUS_RELEASE_BUCKET"]),
            )
        )
        print(json.dumps(descriptor, sort_keys=True))
        return 0
    except Exception:
        print('{"status":"failed","error_code":"cloud_ingestion_failed"}', file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
