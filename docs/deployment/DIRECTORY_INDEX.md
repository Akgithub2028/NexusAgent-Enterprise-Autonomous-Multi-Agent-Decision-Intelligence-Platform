# Directory navigation and maintenance

Reviewed source: `2e2b34c220158c1711409ddb1335fba00fbe375f` on 2026-10-03.

READMEs are maintained maps, not an automatic documentation generator. Runtime boundaries
received detailed source tracing; supporting packages received an entrypoint/contract inventory.
Existing root, corpus and frozen-artifact READMEs are preserved. No notes are added to
virtual environments, caches, Git internals or generated/frozen dataset leaves.

| Directory | Purpose | Review depth |
| --- | --- | --- |
| [.github](../../.github/README.md) | GitHub automation | supporting inventory / contracts |
| [.github/workflows](../../.github/workflows/README.md) | Continuous integration workflows | supporting inventory / contracts |
| [artifacts](../../artifacts/README.md) | Frozen dataset and evaluation evidence | supporting inventory / contracts |
| [datasets](../../datasets/README.md) | Synthetic fixtures and versioned evaluation data | supporting inventory / contracts |
| [datasets/enterprise_kb](../../datasets/enterprise_kb/README.md) | Enterprise document corpus | supporting inventory / contracts |
| [datasets/enterprise_operations](../../datasets/enterprise_operations/README.md) | Synthetic relational data and business checks | supporting inventory / contracts |
| [datasets/agent_tasks](../../datasets/agent_tasks/README.md) | Versioned end-to-end evaluation cases | supporting inventory / contracts |
| [datasets/retrieval](../../datasets/retrieval/README.md) | Retrieval evaluation fixtures | supporting inventory / contracts |
| [datasets/security](../../datasets/security/README.md) | Case-bound security evaluation inputs | supporting inventory / contracts |
| [docker](../../docker/README.md) | Local infrastructure initialization assets | supporting inventory / contracts |
| [docker/mysql](../../docker/mysql/README.md) | Local MySQL bootstrap | supporting inventory / contracts |
| [docker/mysql/init](../../docker/mysql/init/README.md) | Local schema, seed and read-only user initialization | supporting inventory / contracts |
| [docs](../README.md) | Architecture, security and local operation documentation | supporting inventory / contracts |
| [docs/assets](../assets/README.md) | Documentation graphics | supporting inventory / contracts |
| [scripts](../../scripts/README.md) | Explicit demos, ingestion and evaluation commands | supporting inventory / contracts |
| [scripts/runtime](../../scripts/runtime/README.md) | PowerShell helpers for local infrastructure | supporting inventory / contracts |
| [scripts/testing](../../scripts/testing/README.md) | Supervised local test execution | supporting inventory / contracts |
| [src](../../src/README.md) | Installable Python source tree | supporting inventory / contracts |
| [src/decision_agent](../../src/decision_agent/README.md) | NexusAgent application package | supporting inventory / contracts |
| [tests](../../tests/README.md) | Deterministic regression and opt-in live tests | supporting inventory / contracts |
| [tests/unit](../../tests/unit/README.md) | Unit regression contracts | supporting inventory / contracts |
| [tests/integration](../../tests/integration/README.md) | Integration tests with explicit offline/live markers | supporting inventory / contracts |
| [tests/e2e](../../tests/e2e/README.md) | End-to-end evaluation and runtime scenarios | supporting inventory / contracts |
| [tests/fixtures](../../tests/fixtures/README.md) | Deterministic external-I/O substitutes | supporting inventory / contracts |
| [src/decision_agent/agent_workflow](../../src/decision_agent/agent_workflow/README.md) | Controlled planning, execution and review | supporting inventory / contracts |
| [src/decision_agent/agents](../../src/decision_agent/agents/README.md) | Structured model-driven planning and answers | supporting inventory / contracts |
| [src/decision_agent/api](../../src/decision_agent/api/README.md) | FastAPI transport, readiness and identity seam | runtime boundary traced |
| [src/decision_agent/application](../../src/decision_agent/application/README.md) | Formal composition, execution and preflight | runtime boundary traced |
| [src/decision_agent/config](../../src/decision_agent/config/README.md) | Environment-backed settings | runtime boundary traced |
| [src/decision_agent/context](../../src/decision_agent/context/README.md) | Deterministic context and token budgets | supporting inventory / contracts |
| [src/decision_agent/coordination](../../src/decision_agent/coordination/README.md) | Routing and registered skill coordination | supporting inventory / contracts |
| [src/decision_agent/data](../../src/decision_agent/data/README.md) | Read-only SQL validation and execution | runtime boundary traced |
| [src/decision_agent/data_agent](../../src/decision_agent/data_agent/README.md) | Compatibility namespace and Data Evidence models | supporting inventory / contracts |
| [src/decision_agent/demo](../../src/decision_agent/demo/README.md) | Local-only fixed-scope adapters | runtime boundary traced |
| [src/decision_agent/domain](../../src/decision_agent/domain/README.md) | Shared typed domain contracts | supporting inventory / contracts |
| [src/decision_agent/evaluation](../../src/decision_agent/evaluation/README.md) | Deterministic scoring and frozen evidence verification | supporting inventory / contracts |
| [src/decision_agent/infrastructure](../../src/decision_agent/infrastructure/README.md) | Compatibility namespace | supporting inventory / contracts |
| [src/decision_agent/ingestion](../../src/decision_agent/ingestion/README.md) | Local parsers and deterministic chunking | supporting inventory / contracts |
| [src/decision_agent/mcp](../../src/decision_agent/mcp/README.md) | Compatibility namespace | supporting inventory / contracts |
| [src/decision_agent/mcp_client](../../src/decision_agent/mcp_client/README.md) | Owned stdio subprocess transport | runtime boundary traced |
| [src/decision_agent/mcp_server](../../src/decision_agent/mcp_server/README.md) | Internal enterprise-data stdio server | runtime boundary traced |
| [src/decision_agent/memory](../../src/decision_agent/memory/README.md) | Ephemeral and Redis session stores | runtime boundary traced |
| [src/decision_agent/observability](../../src/decision_agent/observability/README.md) | Payload-safe tracing and sinks | runtime boundary traced |
| [src/decision_agent/providers](../../src/decision_agent/providers/README.md) | OpenAI-compatible transport helpers | supporting inventory / contracts |
| [src/decision_agent/retrieval](../../src/decision_agent/retrieval/README.md) | Dense/BM25 fusion, reranking and parent evidence | runtime boundary traced |
| [src/decision_agent/routing](../../src/decision_agent/routing/README.md) | Structured request classification | supporting inventory / contracts |
| [src/decision_agent/security](../../src/decision_agent/security/README.md) | Identity, authorization, provider governance and audit | runtime boundary traced |
| [src/decision_agent/skills](../../src/decision_agent/skills/README.md) | Registered knowledge/data/mixed business skills | supporting inventory / contracts |
| [src/decision_agent/tool_calling](../../src/decision_agent/tool_calling/README.md) | Bounded native high-level tool dispatch | supporting inventory / contracts |
| [src/decision_agent/tools](../../src/decision_agent/tools/README.md) | Compatibility namespace | supporting inventory / contracts |
| [src/decision_agent/web](../../src/decision_agent/web/README.md) | Package-local Web Workbench assets | runtime boundary traced |
| [src/decision_agent/workflows](../../src/decision_agent/workflows/README.md) | LangGraph knowledge and data execution | runtime boundary traced |

## Updating a note

When changing a directory, read its note and only the relevant entry files. Check
the manifest fingerprint; reread affected contracts if it differs. Update behavior,
phase status, review commit and fingerprint with the implementation. A matching hash
does not replace reviewing newly introduced interfaces. Markdown is excluded from
source fingerprints to avoid circular hashes of these notes. Deployment evidence JSON
under `docs/deployment/` is also excluded because it describes this review itself.

Run this read-only check from the repository root (Python standard library only):

```bash
python3 - <<'PY'
import hashlib, json, subprocess
from pathlib import Path
manifest = json.loads(Path("docs/deployment/DIRECTORY_MANIFEST.json").read_text())
tracked = subprocess.check_output(["git", "ls-files", "-z"]).decode().split("\0")
tracked = [p for p in tracked if p and not p.lower().endswith(".md") and not p.startswith("docs/deployment/")]
stale = []
for entry in manifest["directories"]:
    files = sorted(p for p in tracked if p.startswith(entry["path"] + "/"))
    payload = "".join(p + "\0" + hashlib.sha256(Path(p).read_bytes()).hexdigest() + "\n" for p in files)
    digest = hashlib.sha256(payload.encode()).hexdigest()
    if digest != entry["source_sha256"] or len(files) != entry["source_file_count"]:
        stale.append(entry["path"])
print("Notes needing review:", stale)
assert not stale
PY
```

For newly added source files, include them in the Git index before the check. When
refreshing fingerprints, use the same algorithm and record the reviewed source commit.
The manifest is a review aid, not a build input or an authorization source.
