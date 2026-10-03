# syntax=docker/dockerfile:1.7
# Python 3.11, Debian bookworm; reviewed multi-platform manifest, amd64 build required.
ARG PYTHON_IMAGE=python:3.11.14-slim-bookworm@sha256:65a93d69fa75478d554f4ad27c85c1e69fa184956261b4301ebaf6dbb0a3543d
FROM ${PYTHON_IMAGE} AS dependencies
WORKDIR /build
COPY deploy/cloud-run/requirements-runtime.lock /build/runtime.lock
RUN python -m venv /opt/venv && /opt/venv/bin/pip install --require-hashes --no-deps --no-cache-dir -r runtime.lock && /opt/venv/bin/pip check

FROM dependencies AS build
COPY deploy/cloud-run/requirements-build.lock /build/build.lock
RUN python -m venv /build-venv && /build-venv/bin/pip install --require-hashes --no-deps --no-cache-dir -r build.lock
COPY pyproject.toml README.md /build/
COPY src /build/src
RUN /build-venv/bin/python -m hatchling build -t wheel && /opt/venv/bin/pip install --no-deps /build/dist/*.whl
COPY scripts/prepare_cloud_release.py /build/prepare_cloud_release.py
COPY datasets/enterprise_kb/m2c1/documents /build/corpus/documents
COPY datasets/enterprise_kb/m2c1/document_manifest.json /build/corpus/document_manifest.json
COPY datasets/enterprise_kb/m2c1/generated/parent_chunks.jsonl datasets/enterprise_kb/m2c1/generated/child_chunks.jsonl /build/corpus/generated/
RUN /opt/venv/bin/python /build/prepare_cloud_release.py --source /build/corpus --output /opt/release

FROM ${PYTHON_IMAGE} AS runtime
ENV PATH=/opt/venv/bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_HOME=/tmp/huggingface \
    OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 TOKENIZERS_PARALLELISM=false \
    DECISION_AGENT_APP_NAME=NexusAgent DECISION_AGENT_ENVIRONMENT=production \
    DECISION_AGENT_AUDIT_MODE=stdout DECISION_AGENT_MEMORY_MODE=in_memory \
    DECISION_AGENT_EMBEDDING_MODEL_NAME=/opt/release/models/embedding \
    DECISION_AGENT_RERANKER_MODEL_NAME=/opt/release/models/reranker \
    DECISION_AGENT_EMBEDDING_LOCAL_FILES_ONLY=true DECISION_AGENT_RERANKER_LOCAL_FILES_ONLY=true \
    DECISION_AGENT_KNOWLEDGE_DATASET_ROOT=/opt/release/corpus \
    DECISION_AGENT_RELEASE_MANIFEST_PATH=/opt/release/release.json \
    DECISION_AGENT_MILVUS_COLLECTION=nexus_m2c1_9e02a989eace4274 \
    DECISION_AGENT_CORPUS_RELEASE_ID=m2c1_9e02a989eace4274
COPY --from=build /opt/venv /opt/venv
COPY --from=build /opt/release /opt/release
COPY scripts/validate_cloud_image.py /opt/validate_cloud_image.py
COPY deploy/cloud-run/corpus-release.json /opt/expected-release.json
RUN cmp /opt/release/release.json /opt/expected-release.json && groupadd --gid 10001 nexus && useradd --uid 10001 --gid nexus --no-create-home --home-dir /tmp nexus && mkdir /app && chown nexus:nexus /app
WORKDIR /app
USER 10001:10001
EXPOSE 8080
CMD ["python", "-m", "decision_agent.cloud"]
