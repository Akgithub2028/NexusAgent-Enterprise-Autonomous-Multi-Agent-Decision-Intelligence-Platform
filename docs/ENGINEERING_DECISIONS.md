# Key Engineering Decisions

## Explicit Workflow Orchestration

The project implements an explicit execution chain structured around Router, Planner, Skill, Tool, and Reviewer modules. LangGraph manages state transitions and conditional branches, while Pydantic guarantees strict stage contracts. This ensures that Knowledge, Data, and Mixed pipelines can be tested, observed, and debugged independently.

## Hybrid Retrieval

Dense retrieval excels at semantic similarity, while BM25 excels at exact keyword and technical term matching. Reciprocal Rank Fusion (RRF) merges dual rank lists, Cross-Encoder reranking optimizes top candidates, and Parent Expansion restores the full context required for grounded answers. This combination balances recall, ranking precision, and Evidence completeness.

## MCP Tooling Layer

The Data Agent accesses schemas, business definitions, and query capabilities through the Model Context Protocol (MCP). MCP decouples agent workflow orchestration, SQL security validation, and database execution into clear modular boundaries, facilitating datasource substitution, tool contract testing, and extension of operational data features.

## Context and Session Memory

Session state is supported via both Redis and In-Memory implementations, strictly isolated by tenant, user, and session ID. Configurable TTL, rolling summarization, and token budget management govern multi-turn context size while retaining essential history for current queries.

## End-to-End Tracing and Offline Evaluation

Request-level Traces record structured spans across Routing, Planning, Skill dispatch, Tool Calling, Retrieval, Evidence Selection, and Reviewer stages. Offline evaluation suites validate retrieval ranking metrics, end-to-end workflow execution, and failure-mode defenses, enabling confident regression testing when modifying prompts, retrieval parameters, or tool integrations.

## Verifiable Evaluation Artifacts

The Retrieval Benchmark v2 persists queries, relevance ground-truth labels, ranking records, aggregated metrics, and SHA-256 integrity checksums. Verification scripts reproduce Hit@1, Hit@5, and MRR@5 metrics directly from version-controlled artifact snapshots.

Deployment decisions: serve API/UI together; use managed SQL/vectors, pinned offline CPU models, generation-locked ingestion and separate private preview. Protected OIDC releases preserve explicit managed acceptance; live execution remains deferred by billing. See deployment/P7_RELEASE.md.
