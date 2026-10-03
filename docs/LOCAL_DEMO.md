# Local Run Guide

## Prerequisites

- Python 3.11+;
- Docker and Docker Compose;
- Local environment capable of running MySQL, Milvus, etcd, and MinIO;
- OpenAI-compatible model provider configuration.

The repository provides synthetic enterprise documents, MySQL schemas, and seed data for local execution and end-to-end task verification.

## Installation

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .\.venv\Scripts\Activate.ps1
pip install -r requirements.lock
pip install -e . --no-deps
cp .env.example .env
```

Configure local model endpoint settings and infrastructure credentials in `.env` (`.env` is excluded from git tracking).

## Start Infrastructure

```bash
docker compose config
docker compose up -d
docker compose ps
```

Docker Compose launches MySQL and Milvus dependencies. MySQL initializes automatically with the provided schema and seed data.

## Initialize Knowledge Corpus

Once MySQL, etcd, MinIO, and Milvus are healthy:

```bash
python scripts/initialize_knowledge_corpus.py
```

This script loads canonical generated chunks, generates embeddings, writes vector records into Milvus, and validates exact child record IDs. Re-running updates existing records deterministically by chunk ID.

Verify retrieval evidence independently:

```bash
python scripts/verify_retrieval_v2_evidence.py
```

## Running Tasks

```bash
# Enterprise Knowledge QA
python scripts/run_local_demo.py knowledge

# Operational Data Analysis
python scripts/run_local_demo.py data

# Joint Knowledge & Data Decision
python scripts/run_local_demo.py mixed
```

The output JSON includes the Request ID, execution status, classified route, dispatched Skill, grounded answer, citations, and trace summary.

To launch the interactive Web Workbench:

```bash
python scripts/run_local_web_demo.py mixed
```

In the web interface, test multi-turn dialogs such as:
1. "Which products are currently below safety stock?"
2. "Which one has the highest risk?"
3. "Provide recommendations based on our inventory policy."

Clicking "New Session" starts a fresh session ID without carrying over previous conversation context.

## Inspecting Results

Key indicators to inspect:

- Router classified task category;
- Executed Skill and Tool names;
- Grounded Knowledge Evidence and Data Evidence;
- Final citations in the generated answer;
- Stage statuses, elapsed times, and error codes in Trace;
- Context and session memory state updates.

## Offline Verification

```bash
python scripts/verify_retrieval_v2_evidence.py
python scripts/verify_retrieval_evidence.py
python scripts/calculate_m9_metrics.py artifacts/evaluation/m9-final-eval-v1/case_records.jsonl --dataset datasets/agent_tasks/m9_final_eval_v1.json --adjudications artifacts/evaluation/m9-final-eval-v1/adjudications.json --output /tmp/m9-public-metrics.json --manifest-output /tmp/m9-public-manifest.json
```

Verify MCP and MySQL query execution standalone:

```bash
python scripts/run_safe_query_demo.py
```

## Stop Services

```bash
docker compose down
```

Ingestion currently loads the committed canonical generated parent/child corpus, embeds and upserts it; parser/chunker regeneration is separate. Compose has MySQL/etcd/MinIO/Milvus only. Local launchers remain loopback-only; cloud operators must follow deployment/P7_RELEASE.md.
