from __future__ import annotations

from typing import List


def chunk_text(text: str, max_chars: int = 2000, overlap: int = 200) -> List[str]:
    if max_chars <= 0:
        raise ValueError("max_chars must be positive.")
    if overlap < 0:
        raise ValueError("overlap must be >= 0.")

    cleaned = " ".join(text.split())
    if len(cleaned) <= max_chars:
        return [cleaned]

    chunks: List[str] = []
    start = 0
    text_len = len(cleaned)
    min_cut = int(max_chars * 0.6)

    while start < text_len:
        end = min(text_len, start + max_chars)
        cut = end
        if end < text_len:
            scan_start = min(text_len, start + min_cut)
            for idx in range(end, scan_start, -1):
                if cleaned[idx - 1].isspace():
                    cut = idx
                    break

        if cut <= start:
            cut = end

        chunk = cleaned[start:cut].strip()
        if chunk:
            chunks.append(chunk)

        if cut >= text_len:
            break
        start = max(0, cut - overlap)

    return chunks
