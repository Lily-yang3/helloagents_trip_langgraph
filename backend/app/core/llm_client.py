"""LLM helper with fallback behavior for local/demo mode."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Sequence, Union

from openai import OpenAI

from .config import get_settings

Message = Dict[str, str]


class LLMClient:
    """OpenAI-compatible chat helper with deterministic fallback."""

    def __init__(self) -> None:
        settings = get_settings()
        self.model = settings.llm_model_id
        self.timeout = settings.llm_timeout
        self._client: OpenAI | None = None
        if settings.llm_api_key:
            self._client = OpenAI(
                api_key=settings.llm_api_key,
                base_url=settings.llm_base_url,
                timeout=self.timeout,
            )

    @property
    def enabled(self) -> bool:
        return self._client is not None

    def generate_text(self, messages: Union[str, Sequence[Message]]) -> str:
        if isinstance(messages, str):
            payload: List[Message] = [{"role": "user", "content": messages}]
        else:
            payload = list(messages)

        if self._client is None:
            # Deterministic fallback used for local/demo mode.
            return payload[-1]["content"] if payload else ""

        attempts = [
            {"model": self.model, "messages": payload, "temperature": 0.2, "max_tokens": 1200},
            {"model": self.model, "messages": payload, "temperature": 0.2},
            {"model": self.model, "messages": payload},
        ]
        last_error: Exception | None = None
        for params in attempts:
            try:
                response = self._client.chat.completions.create(**params)
                content = response.choices[0].message.content
                return content or ""
            except Exception as exc:  # pragma: no cover
                last_error = exc
        raise RuntimeError(f"LLM request failed: {last_error}")

    def extract_json(self, text: str) -> Dict[str, Any]:
        """Best-effort json extraction from free text."""
        text = text.strip()
        if text.startswith("{") and text.endswith("}"):
            return json.loads(text)
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            return json.loads(text[start : end + 1])
        raise ValueError("No JSON object found")


_llm_client: LLMClient | None = None


def get_llm_client() -> LLMClient:
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client
