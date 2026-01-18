import asyncio
import os
import sys
from pathlib import Path

# Ensure project root is importable even when running this file directly
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import Config
from llm.ollama import OllamaClient
from rag.retrieve import QdrantRetriever


def _format_context(hits, max_chars: int = 3500) -> str:
    """Create compact numbered context blocks for the LLM."""
    blocks = []
    used = 0
    for i, h in enumerate(hits, start=1):
        text = " ".join((h.text or "").split())
        meta = f"file={getattr(h, 'file_origin', '')} url={getattr(h, 'url', '')}"
        block = f"[{i}] {text}\nMETA: {meta}"
        if used + len(block) > max_chars:
            break
        blocks.append(block)
        used += len(block)
    return "\n\n".join(blocks)


def _format_sources(hits, max_items: int = 5) -> str:
    if not hits:
        return "Keine passenden Quellen gefunden."
    seen = set()
    out = []
    for h in hits:
        src = getattr(h, "url", "") or getattr(h, "file_origin", "") or "unbekannt"
        if src in seen:
            continue
        seen.add(src)
        out.append(f"- {src}")
        if len(out) >= max_items:
            break
    return "\n".join(out)


async def main() -> None:
    cfg_path = os.environ.get("CONFIG_PATH", "config.yaml")
    cfg = Config.load(cfg_path)

    # LLM (Antwort-Generator)
    llm = OllamaClient(
        model=cfg.ollama.model,
        system_prompt=cfg.ollama.system_prompt,
        host=cfg.ollama.host,
    )

    # Retriever (Qdrant)
    if not cfg.qdrant:
        print("❌ In config.yaml fehlt der Block 'qdrant:' (url/collection).")
        return

    retriever = QdrantRetriever(cfg.qdrant, cfg.embeddings, top_k=5)

    # Score-Schwelle: unterhalb davon gilt es als "keine passenden Quellen"
    min_score = float(os.environ.get("RAG_MIN_SCORE", "0.60"))

    print("TutorAI Local Chat (mit Retrieval)")
    print("- Tippe normale Fragen (RAG läuft automatisch).")
    print("- !retrieve <frage>  -> zeigt nur die Treffer")
    print("- !exit              -> beenden")
    print()

    while True:
        user = await asyncio.to_thread(input, "Du: ")
        user = user.strip()
        if not user:
            continue
        if user in {"!exit", "exit", "quit"}:
            break

        # Nur Retrieval anzeigen (Debug)
        if user.startswith("!retrieve "):
            q = user[len("!retrieve ") :].strip()
            hits = retriever.retrieve(q)
            print(f"\nTreffer: {len(hits)}")
            for i, h in enumerate(hits[:5], start=1):
                preview = (" ".join((h.text or "").split())[:160] + "...")
                print(f"{i}) score={h.score:.3f} file={h.file_origin}  {preview}")
            print()
            continue

        # Normaler Chat: Retrieval + Antwort
        hits = retriever.retrieve(user)
        top_score = hits[0].score if hits else 0.0

        # Fürs Testen: immer kurz anzeigen, ob RAG was gefunden hat
        print(f"\n[RAG] hits={len(hits)} top_score={top_score:.3f}")

        if (not hits) or (top_score < min_score):
            # Fallback: ohne Quellen antworten + Hinweis für dich im Output
            answer = await llm.generate(user)
            print("\nTutorAI:", answer)
            print("\nQuellen:\nKeine passenden Quellen gefunden.\n")
            continue

        context = _format_context(hits)
        prompt = (
            "Nutze AUSSCHLIESSLICH den folgenden Kontext, um die Frage zu beantworten.\n"
            "Wenn es nicht im Kontext steht, sage: 'Das steht nicht in den Quellen.'\n\n"
            f"Frage: {user}\n\n"
            f"Kontext:\n{context}"
        )
        answer = await llm.generate(prompt)
        print("\nTutorAI:", answer)
        print("\nQuellen:\n" + _format_sources(hits) + "\n")


if __name__ == "__main__":
    asyncio.run(main())
