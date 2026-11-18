"""Ollama and optional Gemini answer providers.

Embeddings never go through these providers. Gemini is constructed only when
the caller selects it. Local request limits are safeguards for this process.
They are not Google account quotas or billing totals.
"""

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path


class LLMConfigError(Exception):
    """The provider setting or API key is missing or invalid."""


class LLMResponseError(Exception):
    """The provider returned an empty or unusable answer."""


class GeminiLimitError(Exception):
    """A local safeguard stopped the request before any Gemini API call."""


class GeminiAPIError(Exception):
    """Gemini failed after the allowed retries."""


_RETRYABLE_CODES = {408, 429, 500, 502, 503, 504}


class OllamaProvider:
    """Local llama3.2:1b answer generation at temperature 0."""

    def __init__(self, model=None):
        from langchain_ollama import ChatOllama

        self.model_name = model or os.getenv("OLLAMA_MODEL", "llama3.2:1b")
        self.model = ChatOllama(model=self.model_name, temperature=0)

    def generate(self, prompt):
        response = self.model.invoke(prompt)
        content = response.content
        if isinstance(content, list):
            content = "".join(str(part) for part in content)
        if not isinstance(content, str) or not content.strip():
            raise LLMResponseError("Ollama returned an empty answer")
        return content


class GeminiUsage:
    """Session counters plus a persisted UTC-day request count.

    total_attempted, successful, and failed reset when the process restarts.
    requests_today is stored in a local file and resets at the next UTC date.
    Neither number is Google's billing usage.
    """

    def __init__(self, path, clock=None):
        self.path = Path(path)
        self.clock = clock or time.time
        self.total_attempted = 0
        self.successful = 0
        self.failed = 0
        self._sent_at = []

    def requests_last_minute(self):
        cutoff = self.clock() - 60
        self._sent_at = [stamp for stamp in self._sent_at if stamp >= cutoff]
        return len(self._sent_at)

    def requests_today(self):
        record = self._read()
        if record.get("day") != _utc_day():
            return 0
        return int(record.get("count", 0))

    def mark_sent(self, succeeded):
        now = self.clock()
        self.total_attempted += 1
        self._sent_at.append(now)
        self._write(self.requests_today() + 1)
        if succeeded:
            self.successful += 1
        else:
            self.failed += 1

    def snapshot(self, minute_limit, daily_limit):
        today = self.requests_today()
        return {
            "total_attempted": self.total_attempted,
            "successful": self.successful,
            "failed": self.failed,
            "requests_last_minute": self.requests_last_minute(),
            "requests_today": today,
            "daily_limit": daily_limit,
            "minute_limit": minute_limit,
            "remaining_daily_requests": max(0, daily_limit - today),
        }

    def _read(self):
        if not self.path.exists():
            return {}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise LLMConfigError(
                f"Gemini usage file is unreadable: {self.path}"
            ) from exc

    def _write(self, count):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(
            json.dumps({"day": _utc_day(), "count": count}) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, self.path)


class GeminiProvider:
    """Optional Gemini answer generation. Callers must opt in explicitly."""

    def __init__(
        self,
        client=None,
        usage_path=None,
        clock=None,
        sleep=None,
    ):
        self.api_key = os.getenv("GEMINI_API_KEY", "").strip()
        if not self.api_key:
            raise LLMConfigError(
                "GEMINI_API_KEY is required when LLM_PROVIDER=gemini"
            )
        self.model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        self.minute_limit = _positive_int("GEMINI_MAX_REQUESTS_PER_MINUTE", 5)
        self.daily_limit = _positive_int("GEMINI_MAX_REQUESTS_PER_DAY", 50)
        self.max_input_tokens = _positive_int("GEMINI_MAX_INPUT_TOKENS", 12000)
        self.max_output_tokens = _positive_int("GEMINI_MAX_OUTPUT_TOKENS", 1000)
        self.max_retries = _nonnegative_int("GEMINI_MAX_RETRIES", 2)
        self.retry_delay = _nonnegative_float("GEMINI_RETRY_DELAY_SECONDS", 2)
        self.clock = clock or time.time
        self.sleep = sleep or time.sleep
        self.usage = GeminiUsage(
            usage_path or os.getenv("GEMINI_USAGE_PATH", "data/gemini_usage.json"),
            clock=self.clock,
        )
        self.client = client if client is not None else _build_gemini_client(self.api_key)

    def generate(self, prompt):
        estimated = estimate_tokens(prompt)
        if estimated > self.max_input_tokens:
            raise GeminiLimitError(
                "Gemini input is about "
                f"{estimated} tokens, above the local limit of {self.max_input_tokens}. "
                "This estimate counts about 4 characters per token and is approximate."
            )
        delay = self.retry_delay
        last_error = None
        for attempt in range(self.max_retries + 1):
            self._require_capacity()
            call_number = self.usage.total_attempted + 1
            print(f"[Gemini] API call #{call_number} | Model: {self.model_name}")
            try:
                text = self._request(prompt)
            except Exception as exc:
                self.usage.mark_sent(succeeded=False)
                print(f"[Gemini] API call #{call_number} failed: {type(exc).__name__}")
                self._print_usage()
                last_error = exc
                if attempt >= self.max_retries or not _retryable(exc):
                    raise GeminiAPIError(
                        f"Gemini request failed: {exc}"
                    ) from exc
                self.sleep(_retry_delay(exc, delay))
                delay *= 2
                continue
            if not text.strip():
                self.usage.mark_sent(succeeded=False)
                print(f"[Gemini] API call #{call_number} failed: empty response")
                self._print_usage()
                raise LLMResponseError("Gemini returned an empty answer")
            self.usage.mark_sent(succeeded=True)
            print(f"[Gemini] API call #{call_number} succeeded")
            self._print_usage()
            return text
        raise GeminiAPIError(f"Gemini request failed: {last_error}")

    def _require_capacity(self):
        if self.usage.requests_last_minute() >= self.minute_limit:
            raise GeminiLimitError(
                "Local Gemini limit reached: "
                f"{self.minute_limit} requests in the current 60-second window"
            )
        if self.usage.requests_today() >= self.daily_limit:
            raise GeminiLimitError(
                "Local Gemini daily limit reached: "
                f"{self.daily_limit} requests for {_utc_day()} UTC. "
                "The count is stored in the local usage file and resets on the next UTC date."
            )

    def _request(self, prompt):
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=_generation_config(self.max_output_tokens),
        )
        text = getattr(response, "text", None)
        if text is None:
            raise LLMResponseError("Gemini returned no text")
        return str(text)

    def _print_usage(self):
        usage = self.usage.snapshot(self.minute_limit, self.daily_limit)
        print(
            "[Gemini] usage | "
            f"attempted={usage['total_attempted']} "
            f"successful={usage['successful']} "
            f"failed={usage['failed']} "
            f"last_minute={usage['requests_last_minute']} "
            f"today={usage['requests_today']}/{usage['daily_limit']}"
        )


def estimate_tokens(text):
    """Approximate token count. This does not call Gemini.

    The estimate is len(text) / 4, which is a rough character rule rather
    than the model's tokenizer.
    """

    return max(1, len(text) // 4)


def _build_gemini_client(api_key):
    try:
        from google import genai
    except ImportError as exc:
        raise LLMConfigError(
            "The google-genai package is not installed. "
            "Install it before setting LLM_PROVIDER=gemini."
        ) from exc
    try:
        return genai.Client(api_key=api_key)
    except Exception as exc:
        raise LLMConfigError(f"Gemini client could not be created: {exc}") from exc


def _generation_config(max_output_tokens):
    try:
        from google.genai import types
    except ImportError:
        return {"max_output_tokens": max_output_tokens, "temperature": 0}
    return types.GenerateContentConfig(
        max_output_tokens=max_output_tokens,
        temperature=0,
    )


def _retryable(exc):
    if isinstance(exc, (LLMConfigError, LLMResponseError, GeminiLimitError)):
        return False
    code = getattr(exc, "code", None)
    if code is None:
        code = getattr(exc, "status_code", None)
    if code in _RETRYABLE_CODES:
        return True
    if code in {400, 401, 403, 404}:
        return False
    if isinstance(exc, (TimeoutError, ConnectionError)):
        return True
    text = str(exc).lower()
    retryable_text = ("timeout", "timed out", "unavailable", "connection")
    return any(token in text for token in retryable_text)


def _retry_delay(exc, fallback):
    retry_after = getattr(exc, "retry_after", None)
    if retry_after is None:
        return fallback
    try:
        return max(0, float(retry_after))
    except (TypeError, ValueError):
        return fallback


def _positive_int(name, default):
    value = _nonnegative_int(name, default)
    if value <= 0:
        raise LLMConfigError(f"{name} must be greater than 0")
    return value


def _nonnegative_int(name, default):
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise LLMConfigError(f"{name} must be an integer") from exc
    if value < 0:
        raise LLMConfigError(f"{name} cannot be negative")
    return value


def _nonnegative_float(name, default):
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        value = float(raw)
    except ValueError as exc:
        raise LLMConfigError(f"{name} must be a number") from exc
    if value < 0:
        raise LLMConfigError(f"{name} cannot be negative")
    return value


def _utc_day():
    return datetime.now(timezone.utc).date().isoformat()
