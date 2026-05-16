"""Deterministic pseudo-embeddings for pytest (no torch / sentence-transformers)."""

import hashlib
from typing import List


def deterministic_stub_embedding(text: str, dim: int) -> List[float]:
    buf = hashlib.sha256(text.encode("utf-8", errors="ignore")).digest()
    out: List[float] = []
    rnd = 0
    while len(out) < dim:
        for b in buf:
            out.append((b / 127.5) - 1.0)
            if len(out) >= dim:
                break
        rnd += 1
        buf = hashlib.sha256(buf + str(rnd).encode()).digest()
    return out[:dim]
