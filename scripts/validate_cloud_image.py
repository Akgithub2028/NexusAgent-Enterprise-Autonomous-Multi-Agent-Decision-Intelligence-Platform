"""Run in the serving image, without network, from any working directory."""

from __future__ import annotations

import asyncio
import json
import math
import os
import resource
import time
from importlib.resources import files

from decision_agent.config import Settings
from decision_agent.mcp_client.enterprise_data_client import EnterpriseDataMCPClient
from decision_agent.release import verify_release
from decision_agent.retrieval.embeddings import SentenceTransformerEmbeddingProvider
from decision_agent.retrieval.reranking import (
    RerankCandidate,
    SentenceTransformerCrossEncoderReranker,
)


async def main() -> None:
    started = time.perf_counter()
    if os.getuid() == 0:
        raise RuntimeError("image must run as non-root")
    import torch

    if torch.version.cuda is not None:
        raise RuntimeError("CUDA dependencies are forbidden in the CPU image")
    settings = Settings(_env_file=None)
    manifest = verify_release(settings)
    assert manifest is not None
    for name in ("index.html", "app.js", "styles.css"):
        assert files("decision_agent").joinpath("web", name).is_file()
    embedding = SentenceTransformerEmbeddingProvider.from_settings(settings)
    vector = await embedding.embed_query("库存补货规则")
    assert len(vector) == 512 and math.isclose(sum(x * x for x in vector), 1, abs_tol=1e-5)
    reranker = SentenceTransformerCrossEncoderReranker(
        model_name=settings.reranker_model_name,
        model_revision=settings.reranker_model_revision,
        local_files_only=True,
    )
    ranked = await reranker.rerank(
        "库存", [RerankCandidate(document_id="smoke", content="库存补货政策", upstream_rank=1)]
    )
    assert len(ranked) == 1 and math.isfinite(ranked[0].reranker_score)
    child_settings = settings.model_copy(
        update={"db_readonly_password": __import__("pydantic").SecretStr("unused-offline-smoke")}
    )
    async with EnterpriseDataMCPClient.from_settings(child_settings) as client:
        schema = await client.get_enterprise_schema()
        await client.get_business_definitions()
        assert schema
    print(
        json.dumps(
            {
                "status": "passed",
                "uid": os.getuid(),
                "dimension": len(vector),
                "torch": torch.__version__,
                "corpus_release_id": manifest["corpus_release_id"],
                "seconds": round(time.perf_counter() - started, 3),
                "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                "sql_queries": 0,
            }
        )
    )


if __name__ == "__main__":
    asyncio.run(main())
