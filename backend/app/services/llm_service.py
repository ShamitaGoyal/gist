"""Choose an answer provider and give it the shared grounded prompt.

LLM_PROVIDER=ollama is the default. Gemini is created only when the provider
is explicitly gemini. Embeddings are not selected here.
"""

import os
from pathlib import Path

from app.services.grounding import build_grounded_prompt
from app.services.llm_providers import (
    GeminiProvider,
    LLMConfigError,
    OllamaProvider,
)


class LLMService:
    def __init__(
        self,
        provider=None,
        provider_impl=None,
        gemini_client=None,
        usage_path=None,
        clock=None,
        sleep=None,
    ):
        load_env_file()
        if provider_impl is not None:
            self.provider_name = (provider or "ollama").strip().lower()
            self._provider = provider_impl
            self._gemini = provider_impl if self.provider_name == "gemini" else None
            return

        self.provider_name = (
            provider or os.getenv("LLM_PROVIDER") or "ollama"
        ).strip().lower()
        if self.provider_name == "ollama":
            self._provider = OllamaProvider()
            self._gemini = None
        elif self.provider_name == "gemini":
            self._provider = GeminiProvider(
                client=gemini_client,
                usage_path=usage_path,
                clock=clock,
                sleep=sleep,
            )
            self._gemini = self._provider
        else:
            raise LLMConfigError(
                f"Unknown LLM provider {self.provider_name!r}. Use ollama or gemini."
            )

    def generate_answer(self, question, context):
        prompt = build_grounded_prompt(question, context)
        return self._provider.generate(prompt)

    def get_gemini_usage(self):
        if self._gemini is None:
            return {
                "total_attempted": 0,
                "successful": 0,
                "failed": 0,
                "requests_last_minute": 0,
                "requests_today": 0,
                "daily_limit": 50,
                "minute_limit": 5,
                "remaining_daily_requests": 50,
            }
        return self._gemini.usage.snapshot(
            self._gemini.minute_limit,
            self._gemini.daily_limit,
        )


def load_env_file():
    """Load a local .env file without overriding variables already set.

    This is a small reader, not a Gemini client. Missing files are ignored.
    """

    for path in (Path.cwd() / ".env", Path(__file__).resolve().parents[2] / ".env"):
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            name, value = stripped.split("=", 1)
            name = name.strip()
            if name and name not in os.environ:
                os.environ[name] = value.strip().strip('"').strip("'")
        return
