from __future__ import annotations

import math
import re
from collections import Counter

TOKEN_RE = re.compile(r"[a-zA-Z0-9_+#.-]+")


def tokenize(text: str | None) -> list[str]:
    if not text:
        return []
    return [token.lower() for token in TOKEN_RE.findall(text) if len(token) > 1]


def vectorize(text: str | None) -> dict[str, float]:
    counts = Counter(tokenize(text))
    total = sum(counts.values()) or 1
    return {token: count / total for token, count in counts.items()}


def cosine(left: dict[str, float], right: dict[str, float]) -> float:
    if not left or not right:
        return 0.0
    shared = set(left) & set(right)
    dot = sum(left[token] * right[token] for token in shared)
    left_norm = math.sqrt(sum(value * value for value in left.values()))
    right_norm = math.sqrt(sum(value * value for value in right.values()))
    if not left_norm or not right_norm:
        return 0.0
    return dot / (left_norm * right_norm)


def snippet(text: str, query: str, length: int = 220) -> str:
    words = tokenize(query)
    lower = text.lower()
    index = min((lower.find(word) for word in words if word in lower), default=0)
    start = max(index - 50, 0)
    clipped = text[start : start + length].strip()
    return clipped + ("..." if len(text) > start + length else "")
