#!/usr/bin/env bash
# Launch the LightRAG web UI over the existing rag_storage graph.
# Interactive knowledge-graph browser + a query playground at http://localhost:9621
#
# Config matches src/caie/contextualizer/rag.py exactly — Ollama llama3.1:8b +
# nomic-embed-text at 768 dims. EMBEDDING_DIM=768 is load-bearing: a wrong dim is
# the mismatch that broke Phase-3 ingestion, so do not change it without changing rag.py.
#
# Prereq: ollama running (brew services start ollama) + models pulled.
# Run:   bash scripts/serve_lightrag.sh      (Ctrl-C to stop)
set -euo pipefail
cd "$(dirname "$0")/.."

export LLM_BINDING=ollama
export LLM_MODEL=llama3.1:8b
export LLM_BINDING_HOST=http://localhost:11434
export EMBEDDING_BINDING=ollama
export EMBEDDING_MODEL=nomic-embed-text
export EMBEDDING_DIM=768
export EMBEDDING_BINDING_HOST=http://localhost:11434

exec conda run -n xai --no-capture-output lightrag-server \
  --working-dir rag_storage \
  --llm-binding ollama \
  --embedding-binding ollama \
  --host 127.0.0.1 --port 9621
