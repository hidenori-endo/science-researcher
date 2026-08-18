from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class OpenAIEmbeddingProvider:
    """Embedding provider for OpenAI's `/embeddings` API.

    The default model is `text-embedding-3-small`. `dimensions` is optional and
    is useful when each scientific node has multiple axis-specific vectors.
    """

    api_key: str
    model: str = "text-embedding-3-small"
    base_url: str = "https://api.openai.com/v1"
    dimensions: int | None = None
    timeout_seconds: float = 60.0

    @classmethod
    def from_env(
        cls,
        *,
        api_key_env: str = "OPENAI_API_KEY",
        model: str = "text-embedding-3-small",
        base_url: str | None = None,
        dimensions: int | None = None,
        timeout_seconds: float = 60.0,
    ) -> "OpenAIEmbeddingProvider":
        api_key = os.environ.get(api_key_env)
        if not api_key:
            raise RuntimeError(f"{api_key_env} is not set")
        return cls(
            api_key=api_key,
            model=model,
            base_url=base_url or os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            dimensions=dimensions,
            timeout_seconds=timeout_seconds,
        )

    def embed(self, text: str) -> list[float]:
        payload: dict[str, Any] = {
            "model": self.model,
            "input": text,
        }
        if self.dimensions is not None:
            payload["dimensions"] = self.dimensions

        request = urllib.request.Request(
            url=self.base_url.rstrip("/") + "/embeddings",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:  # pragma: no cover - network path
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"OpenAI embeddings request failed: {exc.code} {body}") from exc
        except urllib.error.URLError as exc:  # pragma: no cover - network path
            raise RuntimeError(f"OpenAI embeddings request failed: {exc.reason}") from exc

        data = json.loads(raw)
        try:
            embedding = data["data"][0]["embedding"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError(f"unexpected embeddings response shape: {data!r}") from exc
        return [float(value) for value in embedding]
