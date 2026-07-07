"""Phase 3.1: build the LightRAG knowledge graph from knowledge_base/ (run once).

Graph construction uses the LLM (slow, costs tokens), so build once into
rag_storage/ and reuse. Ingests every .md under knowledge_base/ except the entity
registry (entities.yaml is structured config, not prose to graph).

Run: conda run -n xai python -m ccir.contextualizer.ingest
Then visualize (§3.1b): lightrag-server, or open rag_storage/*.graphml in Gephi.
"""
from __future__ import annotations

import asyncio

from lightrag.kg.shared_storage import initialize_pipeline_status

from ccir.contextualizer.rag import KB_DIR, build_rag


async def main() -> None:
    docs = sorted(KB_DIR.rglob("*.md"))
    if not docs:
        raise FileNotFoundError(f"no .md files under {KB_DIR} — author the KB first")

    rag = await build_rag()
    await initialize_pipeline_status()

    for path in docs:
        text = path.read_text()
        # file_path tags each chunk with its source doc — used for provenance later
        await rag.ainsert(text, file_paths=str(path.relative_to(KB_DIR)))
        print(f"ingested {path.relative_to(KB_DIR)} ({len(text)} chars)")

    print(f"\ndone: {len(docs)} documents -> {rag.working_dir}")
    print("visualize: run `lightrag-server` or open the .graphml in Gephi (§3.1b)")


if __name__ == "__main__":
    asyncio.run(main())
