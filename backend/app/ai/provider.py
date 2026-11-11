"""Providers: the real OpenAI call, plus a deterministic mock used by tests and offline demos."""
import asyncio
import json
import time
from dataclasses import dataclass
from typing import Optional

from app.config import settings


class ProviderError(Exception):
    """code: timeout | http | invalid | refusal | config"""

    def __init__(self, code: str, detail: str = ""):
        super().__init__(code)
        self.code = code
        self.detail = detail


@dataclass
class AIResult:
    data: dict
    input_tokens: int
    output_tokens: int
    latency_ms: int
    model: str


class OpenAIProvider:
    name = "openai"

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None, base_url: Optional[str] = None,
                 timeout: Optional[float] = None, retries: Optional[int] = None, transport=None):
        self.api_key = api_key if api_key is not None else settings.openai_api_key
        self.model = model or settings.openai_model
        self.base_url = (base_url or settings.openai_base_url).rstrip("/")
        self.timeout = timeout if timeout is not None else settings.ai_timeout_seconds
        self.retries = retries if retries is not None else settings.ai_max_retries
        self.transport = transport            # tests pass an httpx.MockTransport here; production leaves it None

    async def complete_json(self, system: str, user: str, schema_name: str, schema: dict, max_tokens: Optional[int] = None,
                            timeout: Optional[float] = None) -> AIResult:
        if not self.api_key:
            raise ProviderError("config", "no key")
        import httpx                                            # imported here so the app starts without the package in tests
        body = {"model": self.model, "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
                "response_format": {"type": "json_schema", "json_schema": {"name": schema_name, "strict": True, "schema": schema}},
                "max_completion_tokens": max_tokens or settings.ai_max_output_tokens}
        effort = (settings.ai_reasoning_effort or "").strip().lower()
        if effort in ("none", "low", "medium", "high"):
            body["reasoning_effort"] = effort
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        attempt = 0
        t0 = time.perf_counter()
        last: Optional[ProviderError] = None
        deadline = timeout if timeout is not None else settings.ai_total_deadline_seconds
        per_try = min(self.timeout, deadline) if timeout is None else timeout
        async with httpx.AsyncClient(timeout=per_try, transport=self.transport) as client:
            while attempt <= self.retries:
                left = deadline - (time.perf_counter() - t0)
                if attempt > 0 and left < 1.0:
                    break                                   # out of time: fall back to the rules rather than keep the student waiting
                try:
                    r = await client.post(f"{self.base_url}/chat/completions", headers=headers, json=body,
                                          timeout=max(1.0, min(per_try, left)))
                except httpx.TimeoutException:
                    last = ProviderError("timeout")
                except httpx.HTTPError:
                    last = ProviderError("http", "network")
                else:
                    if r.status_code == 200:
                        return self._parse(r, t0)
                    if r.status_code in (429, 500, 502, 503, 504):
                        last = ProviderError("http", str(r.status_code))
                        try:
                            wait = min(5.0, float(r.headers.get("retry-after", "")))
                        except ValueError:
                            wait = None
                        if wait is not None and attempt < self.retries:
                            await asyncio.sleep(wait)
                            attempt += 1
                            continue
                    else:
                        raise ProviderError("http", str(r.status_code))          # 400/401/403/404: retrying cannot help
                attempt += 1
                if attempt <= self.retries:
                    await asyncio.sleep(min(2.0, 0.5 * (2 ** (attempt - 1))))
        raise last or ProviderError("http")

    def _parse(self, r, t0: float) -> AIResult:
        try:
            j = r.json()
            choice = j["choices"][0]
            msg = choice["message"]
        except (ValueError, KeyError, IndexError, TypeError):
            raise ProviderError("invalid", "shape")
        if msg.get("refusal"):
            raise ProviderError("refusal")
        if choice.get("finish_reason") != "stop":
            raise ProviderError("invalid", "unfinished")
        try:
            data = json.loads(msg.get("content") or "")
        except ValueError:
            raise ProviderError("invalid", "json")
        if not isinstance(data, dict):
            raise ProviderError("invalid", "not an object")
        u = j.get("usage") or {}
        return AIResult(data=data, input_tokens=int(u.get("prompt_tokens") or 0), output_tokens=int(u.get("completion_tokens") or 0),
                        latency_ms=int((time.perf_counter() - t0) * 1000), model=str(j.get("model") or self.model))


class GeminiProvider:
    """
    Google Gemini through the plain REST `generateContent` method (no extra library). Same interface as OpenAIProvider, so the rest
    of MindSync does not know which company answers. The key is sent in the `x-goog-api-key` header from the backend only.
    The JSON shape is requested with responseMimeType and checked again by MindSync's own validators, so a wrong answer is
    thrown away whichever provider wrote it.
    """
    name = "gemini"

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None, base_url: Optional[str] = None,
                 timeout: Optional[float] = None, retries: Optional[int] = None, transport=None):
        self.api_key = api_key if api_key is not None else settings.gemini_api_key
        self.model = (model or settings.gemini_model).replace("models/", "")
        self.base_url = (base_url or settings.gemini_base_url).rstrip("/")
        self.timeout = timeout if timeout is not None else settings.ai_timeout_seconds
        self.retries = retries if retries is not None else settings.ai_max_retries
        self.transport = transport

    async def complete_json(self, system: str, user: str, schema_name: str, schema: dict, max_tokens: Optional[int] = None,
                            timeout: Optional[float] = None) -> AIResult:
        if not self.api_key:
            raise ProviderError("config", "no key")
        import httpx
        body = {"systemInstruction": {"parts": [{"text": system}]}, "contents": [{"role": "user", "parts": [{"text": user}]}],
                "generationConfig": {"responseMimeType": "application/json", "maxOutputTokens": max_tokens or settings.ai_max_output_tokens}}      # no temperature/top_p/top_k: Google ignores them now and rejects them in future models
        url = f"{self.base_url}/models/{self.model}:generateContent"
        headers = {"x-goog-api-key": self.api_key, "Content-Type": "application/json"}
        t0 = time.perf_counter()
        deadline = timeout if timeout is not None else settings.ai_total_deadline_seconds
        per_try = deadline if timeout is not None else min(self.timeout, deadline)
        attempt, last = 0, None
        async with httpx.AsyncClient(timeout=per_try, transport=self.transport) as client:
            while attempt <= self.retries:
                left = deadline - (time.perf_counter() - t0)
                if attempt > 0 and left < 1.0:
                    break
                try:
                    r = await client.post(url, headers=headers, json=body, timeout=max(1.0, min(per_try, left)))
                except httpx.TimeoutException:
                    last = ProviderError("timeout")
                except httpx.HTTPError:
                    last = ProviderError("http", "network")
                else:
                    if r.status_code == 200:
                        return self._parse(r, t0)
                    if r.status_code == 429:
                        raise ProviderError("quota", "429")        # the free allowance is used up: retrying now only wastes the allowance
                    if r.status_code in (500, 502, 503, 504):
                        last = ProviderError("http", str(r.status_code))
                    else:
                        raise ProviderError("http", str(r.status_code))
                attempt += 1
                if attempt <= self.retries:
                    await asyncio.sleep(min(2.0, 0.5 * (2 ** (attempt - 1))))
        raise last or ProviderError("http")

    def _parse(self, r, t0: float) -> AIResult:
        try:
            j = r.json()
            cand = j["candidates"][0]
            text = "".join(p.get("text", "") for p in cand["content"]["parts"])
        except (ValueError, KeyError, IndexError, TypeError, AttributeError):
            if isinstance(j, dict) and (j.get("promptFeedback") or {}).get("blockReason"):
                raise ProviderError("refusal")
            raise ProviderError("invalid", "shape")
        if cand.get("finishReason") not in (None, "STOP"):
            raise ProviderError("refusal" if cand.get("finishReason") in ("SAFETY", "PROHIBITED_CONTENT", "RECITATION") else "invalid", "unfinished")
        text = text.strip()
        if text.startswith("```"):                                  # some models wrap JSON in a code fence
            text = text.strip("`")
            text = text[4:] if text.lower().startswith("json") else text
        try:
            data = json.loads(text)
        except ValueError:
            raise ProviderError("invalid", "json")
        if not isinstance(data, dict):
            raise ProviderError("invalid", "not an object")
        u = j.get("usageMetadata") or {}
        return AIResult(data=data, input_tokens=int(u.get("promptTokenCount") or 0),
                        output_tokens=int(u.get("candidatesTokenCount") or 0) + int(u.get("thoughtsTokenCount") or 0),
                        latency_ms=int((time.perf_counter() - t0) * 1000), model=str(j.get("modelVersion") or self.model))


class MockProvider:
    """
    Deterministic stand-in. `script` maps a schema name to a dict (or a callable(system, user) -> dict) so tests can make
    the 'model' answer well, answer badly, obey an injection, or fail. With no script it returns a plain valid answer.
    """
    name = "mock"
    model = "mock-1"

    def __init__(self, script: Optional[dict] = None):
        self.script = script or {}
        self.calls: list = []

    async def complete_json(self, system: str, user: str, schema_name: str, schema: dict, max_tokens: Optional[int] = None,
                            timeout: Optional[float] = None) -> AIResult:
        self.calls.append({"schema": schema_name, "system": system, "user": user})
        item = self.script.get(schema_name)
        if isinstance(item, Exception):
            raise item
        data = item(system, user) if callable(item) else item
        if data is None:
            data = _default_answer(schema_name)
        return AIResult(data=data, input_tokens=max(1, len(system + user) // 4), output_tokens=max(1, len(json.dumps(data)) // 4),
                        latency_ms=1, model=self.model)


def _default_answer(schema_name: str) -> dict:
    if schema_name == "understand":
        return {"tasks": [], "questions": [], "summary": "Mock summary."}
    if schema_name == "narrate":
        return {"headline": "Mock headline", "what_first": "Start with the first block.", "why": "It is due first.", "risks": [], "tips": []}
    if schema_name == "answer":
        return {"answer": "Mock answer.", "follow_ups": [], "suggest_action": "none"}
    if schema_name == "review":
        return {"summary": "Mock review.", "went_well": [], "to_improve": [], "next_week": []}
    return {}


def build_provider():
    """
    Which company answers is decided ONLY here, from backend/.env:
      AI_PROVIDER=off     never call a model (the default: nothing is activated until the owner chooses)
      AI_PROVIDER=gemini  Google Gemini (needs GEMINI_API_KEY)
      AI_PROVIDER=openai  OpenAI (needs OPENAI_API_KEY)
      AI_PROVIDER=auto    the first one that has a key (Gemini, then OpenAI)
      AI_PROVIDER=mock    tests and demos
    """
    mode = (settings.ai_provider or "off").lower()
    if mode == "mock":
        return MockProvider()
    if mode in ("gemini", "auto") and settings.gemini_api_key.strip():
        return GeminiProvider()
    if mode in ("openai", "auto") and settings.openai_api_key.strip():
        return OpenAIProvider()
    return None
