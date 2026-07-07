"""Shared LightRAG configuration (Layer 3 backbone).

One place to build a LightRAG instance so ingest / retrieve / synthesize all use
the *same* models and storage. Local + reproducible: Ollama at temperature 0.

Models (pull once): `ollama pull llama3.1:8b` and `ollama pull nomic-embed-text`.
"""
from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import ollama

from lightrag import LightRAG
from lightrag.llm.ollama import ollama_model_complete
from lightrag.utils import EmbeddingFunc

ROOT = Path(__file__).resolve().parents[3]
RAG_STORAGE = ROOT / "rag_storage"
KB_DIR = ROOT / "knowledge_base"

LLM_MODEL = os.environ.get("CCIR_LLM", "llama3.1:8b")
EMBED_MODEL = os.environ.get("CCIR_EMBED", "nomic-embed-text")
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
EMBED_DIM = 768  # nomic-embed-text (do NOT use lightrag.llm.ollama.ollama_embed —
                 # it is pre-decorated with embedding_dim=1024 and will mismatch nomic)


async def _embed(texts: list[str]) -> np.ndarray:
    """Call Ollama directly and return an (N, 768) float array — one embedding
    path with exactly one declared dimension, so no wrapper conflict."""
    client = ollama.AsyncClient(host=OLLAMA_HOST)
    resp = await client.embed(model=EMBED_MODEL, input=list(texts))
    return np.array(resp["embeddings"], dtype=np.float32)


async def build_rag(working_dir: Path | None = None) -> LightRAG:
    """A LightRAG bound to local Ollama; temperature 0 for reproducibility."""
    rag = LightRAG(
        working_dir=str(working_dir or RAG_STORAGE),
        llm_model_func=ollama_model_complete,
        llm_model_name=LLM_MODEL,
        llm_model_kwargs={"host": OLLAMA_HOST, "options": {"temperature": 0}},
        embedding_func=EmbeddingFunc(embedding_dim=EMBED_DIM, func=_embed),
    )
    await rag.initialize_storages()
    return rag
