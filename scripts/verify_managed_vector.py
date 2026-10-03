"""Verify managed AUTOINDEX using an isolated disposable collection; never ingest corpus."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import uuid

from pydantic import SecretStr

from decision_agent.retrieval.milvus_store import MilvusVectorStore
from decision_agent.retrieval.models import VectorRecord, VectorSearchFilter


async def verify() -> None:
    name = "nexus_connection_check_" + uuid.uuid4().hex
    writer = MilvusVectorStore(
        dimension=512,
        uri=os.environ["DECISION_AGENT_MILVUS_URI"],
        token=SecretStr(os.environ["DECISION_AGENT_MILVUS_WRITE_TOKEN"]),
        collection_name=name,
        index_type="AUTOINDEX",
        timeout_seconds=30,
    )
    reader = MilvusVectorStore(
        dimension=512,
        uri=os.environ["DECISION_AGENT_MILVUS_URI"],
        token=SecretStr(os.environ["DECISION_AGENT_MILVUS_TOKEN"]),
        collection_name=name,
        index_type="AUTOINDEX",
        timeout_seconds=30,
    )
    owned = False
    try:
        await writer.initialize()
        owned = True
        rows = [
            VectorRecord(
                record_id=f"check-{i}",
                parent_id="check-parent",
                document_id="allowed" if i < 2 else "excluded",
                document_version="v1",
                content="synthetic connection check",
                vector=[1.0] + [0.0] * 511,
                metadata={"connection_check": True},
            )
            for i in range(3)
        ]
        await writer.upsert(rows)
        await reader.initialize_reader()
        for attempt in range(15):
            ids = await reader.list_record_ids()
            hits = await reader.search(rows[0].vector, 3, VectorSearchFilter(document_id="allowed"))
            if ids == frozenset(r.record_id for r in rows) and {h.record_id for h in hits} == {
                "check-0",
                "check-1",
            }:
                break
            if attempt == 14:
                raise RuntimeError("managed vector visibility verification failed")
            await asyncio.sleep(2)
        result = {
            "status": "passed",
            "index": "AUTOINDEX",
            "dimension": 512,
            "metric": "COSINE",
            "exact_ids": len(ids),
            "filtered_hits": len(hits),
            "serving_provisioning": False,
        }
    finally:
        # Delete only the disposable collection owned by this invocation.
        # Serverless collection removal can take longer than search requests.
        try:
            if owned:
                try:
                    await asyncio.to_thread(
                        writer._client.drop_collection, collection_name=name, timeout=30
                    )
                except Exception:
                    # Serverless can complete deletion while its RPC times out.
                    # Accept only independently confirmed absence, never a timeout alone.
                    if await asyncio.to_thread(
                        writer._client.has_collection, collection_name=name, timeout=30
                    ):
                        raise
                if await asyncio.to_thread(
                    writer._client.has_collection, collection_name=name, timeout=30
                ):
                    raise RuntimeError("disposable collection cleanup unconfirmed")
        finally:
            try:
                await reader.close()
            finally:
                await writer.close()
    print(json.dumps(result))


def main() -> None:
    logging.getLogger("pymilvus").setLevel(logging.CRITICAL)
    try:
        asyncio.run(verify())
    except Exception as exc:
        # SDK errors can contain endpoints/authentication details. Never print their text.
        print(json.dumps({"status": "failed", "error_class": type(exc).__name__}))
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
