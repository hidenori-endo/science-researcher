from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import asdict
from typing import Any

from .models import Critique, HypothesisDraft, ProofObligation, Reframing, ScientificNode
from .provider import ReasoningProvider


class ProviderError(RuntimeError):
    pass


def _expect_mapping(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ProviderError("LLM response must be a JSON object")
    return value


def _expect_list(value: Any) -> list[Any]:
    if not isinstance(value, list):
        raise ProviderError("LLM response field must be a JSON array")
    return value


class OpenAICompatibleChatProvider(ReasoningProvider):
    """LLM provider for OpenAI-compatible `/chat/completions` endpoints.

    The class intentionally depends only on the Python standard library. It can
    be used with local servers or hosted providers that implement the common
    chat-completions wire format. Generator and critic should be instantiated
    separately to avoid accidental conversational anchoring.
    """

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        api_key: str | None = None,
        timeout_seconds: float = 120.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds

    @classmethod
    def from_env(
        cls,
        *,
        model: str,
        base_url: str | None = None,
        api_key_env: str = "SCIENCE_RESEARCHER_API_KEY",
    ) -> "OpenAICompatibleChatProvider":
        resolved_url = base_url or os.environ.get(
            "SCIENCE_RESEARCHER_BASE_URL", "http://localhost:11434/v1"
        )
        return cls(
            base_url=resolved_url,
            model=model,
            api_key=os.environ.get(api_key_env),
        )

    def _complete_json(self, *, role: str, task: str, payload: dict[str, Any]) -> dict[str, Any]:
        system = (
            "You are one isolated stage in a scientific discovery pipeline. "
            "Return JSON only. Separate established facts from speculation. "
            "Never treat an analogy, numerical pattern, or reformulation as evidence or proof. "
            f"Your stage role is: {role}."
        )
        user = json.dumps({"task": task, "input": payload}, ensure_ascii=False, sort_keys=True)
        request_body = json.dumps(
            {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "temperature": 0.7 if role in {"reframer", "mutation-generator"} else 0.2,
            }
        ).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=request_body,
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                data = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise ProviderError(f"LLM request failed: {exc}") from exc

        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError("unexpected chat-completions response shape") from exc
        if not isinstance(content, str):
            raise ProviderError("LLM message content must be text")

        stripped = content.strip()
        if stripped.startswith("```"):
            lines = stripped.splitlines()
            if len(lines) >= 3:
                stripped = "\n".join(lines[1:-1])
                if stripped.lstrip().startswith("json"):
                    stripped = stripped.lstrip()[4:].lstrip()
        try:
            return _expect_mapping(json.loads(stripped))
        except json.JSONDecodeError as exc:
            raise ProviderError(f"LLM did not return valid JSON: {content[:300]}") from exc

    def reframe(self, problem: ScientificNode) -> list[Reframing]:
        result = self._complete_json(
            role="reframer",
            task=(
                "Rewrite the scientific problem in 4 structurally distinct, domain-light ways. "
                "For each item return label, text, mechanism_query, structure_query, "
                "problem_shape_query, and forbidden_shortcuts (array). Avoid proposing solutions. "
                "Output: {\"reframings\": [...]}"
            ),
            payload=problem.to_dict(),
        )
        items = _expect_list(result.get("reframings"))
        return [
            Reframing(
                label=str(item["label"]),
                text=str(item["text"]),
                mechanism_query=str(item["mechanism_query"]),
                structure_query=str(item["structure_query"]),
                problem_shape_query=str(item["problem_shape_query"]),
                forbidden_shortcuts=[str(x) for x in _expect_list(item.get("forbidden_shortcuts", []))],
            )
            for item in map(_expect_mapping, items)
        ]

    def mutate(
        self,
        problem: ScientificNode,
        reframing: Reframing,
        analogy: ScientificNode,
    ) -> HypothesisDraft:
        result = self._complete_json(
            role="mutation-generator",
            task=(
                "Do not transplant the source method literally. Extract its enabling mechanism, mutate it "
                "for the target, and propose one falsifiable bridge. Penalize assumptions that encode the "
                "target conclusion. Output keys: title, bridge, prediction, rationale."
            ),
            payload={
                "problem": problem.to_dict(),
                "reframing": asdict(reframing),
                "analogy": analogy.to_dict(),
            },
        )
        return HypothesisDraft(
            title=str(result["title"]),
            bridge=str(result["bridge"]),
            prediction=str(result["prediction"]),
            rationale=str(result["rationale"]),
            source_node_id=analogy.id,
        )

    def critique(
        self,
        problem: ScientificNode,
        analogy: ScientificNode,
        hypothesis: HypothesisDraft,
    ) -> Critique:
        result = self._complete_json(
            role="adversarial-critic",
            task=(
                "Try to kill the hypothesis. Check circularity, loss of the source method's enabling "
                "structure, assumptions equivalent to the original problem, non-uniform limits, vacuous "
                "universal representation, and cheap finite counterexamples. Score 0..1 where 1 means "
                "worth testing, not probability of truth. Output score, verdict, failure_reason, checks."
            ),
            payload={
                "problem": problem.to_dict(),
                "analogy": analogy.to_dict(),
                "hypothesis": asdict(hypothesis),
            },
        )
        return Critique(
            score=float(result["score"]),
            verdict=str(result["verdict"]),
            failure_reason=str(result.get("failure_reason", "")),
            checks=[str(x) for x in _expect_list(result.get("checks", []))],
        )

    def extract_obligations(
        self,
        problem: ScientificNode,
        analogy: ScientificNode,
        hypothesis: HypothesisDraft,
        critique: Critique,
    ) -> list[ProofObligation]:
        result = self._complete_json(
            role="proof-decomposer",
            task=(
                "Decompose the proposed bridge into the smallest independently falsifiable implications. "
                "Do not ask to prove the final open problem. For each obligation return statement, status "
                "(usually unknown), verification_method, and notes. Prefer a cheap counterexample search "
                "before expensive proof work. Output {\"obligations\": [...]}"
            ),
            payload={
                "problem": problem.to_dict(),
                "analogy": analogy.to_dict(),
                "hypothesis": asdict(hypothesis),
                "critique": asdict(critique),
            },
        )
        items = _expect_list(result.get("obligations"))
        return [
            ProofObligation(
                statement=str(item["statement"]),
                status=str(item.get("status", "unknown")),
                verification_method=str(item.get("verification_method", "literature-or-proof")),
                notes=str(item.get("notes", "")),
            )
            for item in map(_expect_mapping, items)
        ]
