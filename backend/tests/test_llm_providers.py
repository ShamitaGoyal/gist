"""Provider selection and Gemini safeguards. Gemini responses are fake.

Run from the backend directory:

    python3 tests/test_llm_providers.py
"""

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.grounding import build_grounded_prompt
from app.services.llm_providers import (
    GeminiAPIError,
    GeminiLimitError,
    LLMConfigError,
)
from app.services.llm_service import LLMService


class APIError(Exception):
    def __init__(self, message, code, retry_after=None):
        super().__init__(message)
        self.code = code
        self.retry_after = retry_after


class FakeModels:
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.calls = []

    def generate_content(self, model, contents, config):
        self.calls.append({"model": model, "contents": contents, "config": config})
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


class FakeClient:
    def __init__(self, outcomes):
        self.models = FakeModels(outcomes)


class Response:
    def __init__(self, text):
        self.text = text


class Clock:
    def __init__(self):
        self.now = 1_000.0

    def __call__(self):
        return self.now


def env(updates):
    previous = {key: os.environ.get(key) for key in updates}
    for key, value in updates.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value
    return previous


def restore(previous):
    for key, value in previous.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


def gemini_env(directory, **extra):
    values = {
        "LLM_PROVIDER": "ollama",
        "GEMINI_API_KEY": "test-key",
        "GEMINI_MODEL": "gemini-2.5-flash",
        "GEMINI_MAX_REQUESTS_PER_MINUTE": "5",
        "GEMINI_MAX_REQUESTS_PER_DAY": "50",
        "GEMINI_MAX_INPUT_TOKENS": "12000",
        "GEMINI_MAX_OUTPUT_TOKENS": "1000",
        "GEMINI_MAX_RETRIES": "2",
        "GEMINI_RETRY_DELAY_SECONDS": "2",
        "GEMINI_USAGE_PATH": str(directory / "usage.json"),
    }
    values.update(extra)
    return values


def output_limit(config):
    if isinstance(config, dict):
        return config["max_output_tokens"]
    return config.max_output_tokens


def test_default_is_ollama_and_gemini_is_not_created():
    previous = env({"LLM_PROVIDER": None, "GEMINI_API_KEY": None})
    try:
        service = LLMService(provider="ollama")
        assert service.provider_name == "ollama"
        assert type(service._provider).__name__ == "OllamaProvider"
        assert service._gemini is None
        usage = service.get_gemini_usage()
        assert usage["total_attempted"] == 0
        assert usage["remaining_daily_requests"] == 50
    finally:
        restore(previous)
    print("Default provider is Ollama. Gemini was not created.")


def test_ollama_generation():
    previous = env({"LLM_PROVIDER": "ollama"})
    try:
        answer = LLMService(provider="ollama").generate_answer(
            "What is two plus two?",
            "Two plus two equals four.",
        )
    finally:
        restore(previous)
    assert answer.strip()
    print("Ollama generation returned an answer.")


def test_gemini_uses_the_same_prompt_and_records_success():
    directory = Path(tempfile.mkdtemp())
    previous = env(gemini_env(directory))
    client = FakeClient([Response("Meridian provides twelve default roles.")])
    try:
        service = LLMService(
            provider="gemini",
            gemini_client=client,
            usage_path=directory / "usage.json",
            clock=Clock(),
            sleep=lambda seconds: None,
        )
        answer = service.generate_answer(
            "How many roles?",
            "Meridian provides twelve default roles.",
        )
    finally:
        restore(previous)
    assert answer == "Meridian provides twelve default roles."
    sent = client.models.calls[0]
    assert sent["contents"] == build_grounded_prompt(
        "How many roles?",
        "Meridian provides twelve default roles.",
    )
    assert sent["model"] == "gemini-2.5-flash"
    assert output_limit(sent["config"]) == 1000
    usage = service.get_gemini_usage()
    assert usage["total_attempted"] == 1
    assert usage["successful"] == 1
    assert usage["failed"] == 0
    assert usage["requests_today"] == 1
    assert usage["remaining_daily_requests"] == 49
    print("Gemini received the shared prompt and counted one success.")


def test_missing_key_and_unknown_provider():
    previous = env({"GEMINI_API_KEY": None, "LLM_PROVIDER": "gemini"})
    try:
        try:
            LLMService(provider="gemini")
        except LLMConfigError as exc:
            assert "GEMINI_API_KEY" in str(exc)
        else:
            raise AssertionError("A missing Gemini key should fail")
        try:
            LLMService(provider="openai")
        except LLMConfigError as exc:
            assert "Unknown LLM provider" in str(exc)
        else:
            raise AssertionError("An unknown provider should fail")
    finally:
        restore(previous)
    print("Missing Gemini key and unknown provider fail clearly.")


def test_limits_retries_and_persistence():
    directory = Path(tempfile.mkdtemp())
    clock = Clock()
    sleeps = []
    previous = env(
        gemini_env(
            directory,
            GEMINI_MAX_REQUESTS_PER_MINUTE="10",
            GEMINI_MAX_REQUESTS_PER_DAY="3",
            GEMINI_MAX_INPUT_TOKENS="12000",
            GEMINI_MAX_RETRIES="2",
            GEMINI_RETRY_DELAY_SECONDS="2",
        )
    )
    try:
        blocked = FakeClient([Response("unused")])
        limited = LLMService(
            provider="gemini",
            gemini_client=blocked,
            usage_path=directory / "usage.json",
            clock=clock,
            sleep=lambda seconds: sleeps.append(seconds),
        )
        limited._provider.max_input_tokens = 20
        try:
            limited._provider.generate("x" * 200)
        except GeminiLimitError as exc:
            assert "approximate" in str(exc)
        else:
            raise AssertionError("A long prompt should be blocked locally")
        assert blocked.models.calls == []
        assert limited.get_gemini_usage()["total_attempted"] == 0

        retry_client = FakeClient([
            APIError("unavailable", 503, retry_after=7),
            Response("Meridian provides roles."),
        ])
        retrying = LLMService(
            provider="gemini",
            gemini_client=retry_client,
            usage_path=directory / "retry.json",
            clock=clock,
            sleep=lambda seconds: sleeps.append(seconds),
        )
        answer = retrying.generate_answer("How many roles?", "Meridian provides roles.")
        assert answer == "Meridian provides roles."
        assert len(retry_client.models.calls) == 2
        assert sleeps == [7]
        assert retrying.get_gemini_usage()["failed"] == 1
        assert retrying.get_gemini_usage()["successful"] == 1

        auth_client = FakeClient([APIError("denied", 401)])
        denied = LLMService(
            provider="gemini",
            gemini_client=auth_client,
            usage_path=directory / "auth.json",
            clock=clock,
            sleep=lambda seconds: sleeps.append(seconds),
        )
        try:
            denied.generate_answer("How many roles?", "Meridian provides roles.")
        except GeminiAPIError:
            pass
        else:
            raise AssertionError("An authentication error should fail")
        assert len(auth_client.models.calls) == 1
        assert denied.get_gemini_usage()["failed"] == 1

        exhausted = FakeClient([
            APIError("unavailable", 503),
            APIError("unavailable", 503),
            APIError("unavailable", 503),
            Response("should not be called"),
        ])
        failing = LLMService(
            provider="gemini",
            gemini_client=exhausted,
            usage_path=directory / "exhausted.json",
            clock=clock,
            sleep=lambda seconds: None,
        )
        try:
            failing.generate_answer("How many roles?", "Meridian provides roles.")
        except GeminiAPIError:
            pass
        else:
            raise AssertionError("Retries should stop at the maximum")
        assert len(exhausted.models.calls) == 3
        assert failing.get_gemini_usage()["failed"] == 3
        assert failing.get_gemini_usage()["successful"] == 0

        minute = FakeClient([
            Response("one"),
            Response("two"),
            Response("three"),
        ])
        paced = LLMService(
            provider="gemini",
            gemini_client=minute,
            usage_path=directory / "minute.json",
            clock=clock,
            sleep=lambda seconds: None,
        )
        paced._provider.minute_limit = 2
        paced._provider.generate("one")
        paced._provider.generate("two")
        try:
            paced._provider.generate("three")
        except GeminiLimitError as exc:
            assert "60-second" in str(exc)
        else:
            raise AssertionError("The third call should hit the minute limit")
        assert len(minute.models.calls) == 2
        assert paced.get_gemini_usage()["total_attempted"] == 2

        daily_client = FakeClient([Response("one"), Response("two"), Response("three"), Response("four")])
        daily = LLMService(
            provider="gemini",
            gemini_client=daily_client,
            usage_path=directory / "daily.json",
            clock=Clock(),
            sleep=lambda seconds: None,
        )
        daily._provider.minute_limit = 10
        for _ in range(3):
            daily._provider.generate("Meridian provides roles.")
        restarted = LLMService(
            provider="gemini",
            gemini_client=FakeClient([Response("after restart")]),
            usage_path=directory / "daily.json",
            clock=Clock(),
            sleep=lambda seconds: None,
        )
        assert restarted.get_gemini_usage()["requests_today"] == 3
        assert restarted.get_gemini_usage()["total_attempted"] == 0
        try:
            restarted._provider.generate("one more")
        except GeminiLimitError as exc:
            assert "daily limit" in str(exc)
        else:
            raise AssertionError("A restarted process should keep the daily count")
        assert restarted.get_gemini_usage()["total_attempted"] == 0
    finally:
        restore(previous)
    print("Limits, retries, and persisted daily usage behaved as configured.")


def main():
    test_default_is_ollama_and_gemini_is_not_created()
    test_missing_key_and_unknown_provider()
    test_gemini_uses_the_same_prompt_and_records_success()
    test_limits_retries_and_persistence()
    test_ollama_generation()
    print("Passed.")


if __name__ == "__main__":
    main()
