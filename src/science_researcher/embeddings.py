from __future__ import annotations

import hashlib
import math
import re
from collections.abc import Iterable

_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")


def tokenize(text: str) -> list[str]:
    return [token.lower() for token in _TOKEN_RE.findall(text)]


class HashEmbedder:
    """Deterministic dependency-free feature-hashing embedder.

    This is not intended to compete with learned embeddings. It exists so the
    architecture, vector storage, scoring, and tests are executable offline.
    """

    def __init__(self, dimensions: int = 128) -> None:
        if dimensions <= 0:
            raise ValueError("dimensions must be positive")
        self.dimensions = dimensions

    def embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        tokens = tokenize(text)
        if not tokens:
            return vector

        features: list[str] = tokens[:]
        features.extend(f"{a}::{b}" for a, b in zip(tokens, tokens[1:]))

        for feature in features:
            digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=8).digest()
            value = int.from_bytes(digest, "big")
            index = value % self.dimensions
            sign = -1.0 if (value >> 8) & 1 else 1.0
            vector[index] += sign

        norm = math.sqrt(sum(x * x for x in vector))
        if norm == 0:
            return vector
        return [x / norm for x in vector]


def cosine_similarity(a: Iterable[float], b: Iterable[float]) -> float:
    a_values = list(a)
    b_values = list(b)
    if len(a_values) != len(b_values):
        raise ValueError("vector dimensions do not match")
    dot = sum(x * y for x, y in zip(a_values, b_values))
    norm_a = math.sqrt(sum(x * x for x in a_values))
    norm_b = math.sqrt(sum(y * y for y in b_values))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def overlap_ratio(query: str, candidate: str) -> float:
    q = set(tokenize(query))
    c = set(tokenize(candidate))
    if not q or not c:
        return 0.0
    return len(q & c) / len(q | c)
