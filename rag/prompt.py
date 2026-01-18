# rag/prompt.py
from __future__ import annotations

from typing import List

from rag.retrieve import RetrievalHit


def build_rag_user_message(question: str, hits: List[RetrievalHit], *, max_chars: int = 3500) -> str:
    """
    Baut die User-Nachricht für das LLM inkl. Kontext.

    Ziel:
    - Wenn der Kontext die Frage DIREKT beantwortet: antworte daraus.
    - Wenn der Kontext nur TEILWEISE passt: sage, dass es nicht direkt drinsteht,
      aber nenne die relevanten Hinweise aus dem Kontext (ohne zu halluzinieren).
    - Wenn kein Kontext da ist: Hinweis "Keine passenden Quellen gefunden" und normal antworten.
    """

    # Kein Kontext → LLM darf allgemein antworten, muss aber den Hinweis geben
    if not hits:
        return (
            "Du hast KEINE passenden Kurs-Quellen gefunden.\n"
            "Antworte deshalb allgemein aus deinem Wissen.\n"
            "WICHTIG: Schreibe am Anfang der Antwort: 'Keine passenden Quellen gefunden.'\n\n"
            f"Frage: {question}"
        )

    # Kontextblöcke (kompakt, nummeriert)
    blocks = []
    used = 0
    for i, h in enumerate(hits, start=1):
        text = " ".join((h.text or "").split())
        meta = (
            f"file={h.file_origin} | section={h.context_section} | "
            f"activity={h.context_activity} | url={h.url}"
        )
        block = f"[{i}] {text}\nMETA: {meta}"
        if used + len(block) > max_chars:
            break
        blocks.append(block)
        used += len(block)

    context = "\n\n".join(blocks)

    # Neue, robustere Instruktion:
    return (
        "Du bist TutorAI, ein deutschsprachiger Studienassistent.\n"
        "Nutze den folgenden KONTEXT als Quelle.\n\n"
        "Regeln:\n"
        "1) Antworte zuerst so gut wie möglich anhand des Kontexts.\n"
        "2) Wenn der Kontext die Frage NICHT direkt beantwortet, dann:\n"
        "   - Sage das klar (z.B. 'Der genaue Ablauf steht so nicht in den Quellen.'),\n"
        "   - Nenne aber trotzdem die relevanten HINWEISE, die im Kontext stehen (z.B. Fristen, Begriffe, Teilaspekte).\n"
        "   - Sage, welche Information für eine vollständige Antwort fehlt.\n"
        "3) Erfinde nichts. Keine Details, die nicht im Kontext stehen.\n"
        "4) Halte die Antwort strukturiert und kurz.\n\n"
        f"Frage: {question}\n\n"
        f"KONTEXT:\n{context}\n"
    )


def format_sources(hits: List[RetrievalHit], *, max_items: int = 5) -> str:
    """
    Formatiert Quellenliste kurz & eindeutig.
    """
    if not hits:
        return "Keine passenden Quellen gefunden."

    seen = set()
    out = []
    for h in hits:
        # Bevorzugt URL, sonst file_origin
        src = (h.url or "").strip() or (h.file_origin or "").strip() or "unbekannt"
        if src in seen:
            continue
        seen.add(src)
        out.append(f"- {src}")
        if len(out) >= max_items:
            break
    return "\n".join(out)
