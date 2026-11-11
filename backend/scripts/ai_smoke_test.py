"""
ONE tiny real AI request, run by YOU after you have switched an AI provider on. Nothing runs by itself.

    python -m scripts.ai_smoke_test            (or double-click run-ai-smoke-test.bat)

What it does:
  1. Reads backend/.env. If AI_PROVIDER is "off" (the default) or there is no key, it STOPS and sends nothing.
  2. Asks you to type YES before it contacts the provider. Anything else cancels.
  3. Sends one very short question (about 30 words) and checks that a valid answer comes back.
  4. Prints which provider and model answered, how long it took and how many tokens were used. It NEVER prints your key.

On the free Gemini plan this costs nothing. On a paid plan one request like this costs a tiny fraction of a cent.
It does not touch the database and does not save anything.
"""
import asyncio
import sys

from app.ai.provider import ProviderError, build_provider
from app.config import settings

SCHEMA = {"type": "object", "properties": {"reply": {"type": "string"}}, "required": ["reply"]}


async def main() -> int:
    mode = (settings.ai_provider or "off").lower()
    print(f"AI_PROVIDER in backend/.env is: {mode}")
    if mode == "off":
        print("AI is OFF. Nothing was sent. To switch it on, follow docs/AI_ACTIVATION_GUIDE.md first.")
        return 0
    if mode == "mock":
        print("AI_PROVIDER=mock is for tests only. Nothing real was contacted.")
        return 0
    provider = build_provider()
    if provider is None:
        print(f"AI_PROVIDER is {mode} but the matching key is empty in backend/.env, so nothing can be sent.")
        print("Put the key on its own line in backend/.env (GEMINI_API_KEY=... or OPENAI_API_KEY=...), save, and run this again.")
        return 1
    print(f"Provider: {provider.name}   Model: {getattr(provider, 'model', '?')}")
    print("This will send ONE short test question to that company. It uses a very small part of your allowance.")
    if input("Type YES (capital letters) to continue, anything else to cancel: ").strip() != "YES":
        print("Cancelled. Nothing was sent.")
        return 0
    try:
        res = await provider.complete_json(
            "You are a test. Reply with JSON only.", 'Reply with the JSON {"reply": "MindSync test OK"}.', "smoke", SCHEMA, max_tokens=60, timeout=30)
    except ProviderError as exc:
        hints = {"quota": "You have used up the free allowance for now. Wait and try later (see docs/AI_ACTIVATION_GUIDE.md).",
                 "timeout": "No answer in 30 seconds. Check your internet connection and try again.",
                 "config": "The key or model name looks wrong. Check backend/.env.",
                 "http": "The provider refused the request. The key may be wrong or switched off, or the model name may have changed.",
                 "invalid": "The provider answered, but not in the expected form. Check the model name.",
                 "refusal": "The provider refused to answer this test."}
        print(f"FAILED ({exc.code}). {hints.get(exc.code, '')}")
        return 1
    ok = isinstance(res.data, dict) and "reply" in res.data
    print(f"{'OK' if ok else 'ODD ANSWER'}: reply = {str(res.data)[:120]}")
    print(f"Took {res.latency_ms} ms, {res.input_tokens} tokens in, {res.output_tokens} tokens out, model {res.model}.")
    print("The AI connection works. Restart the backend (restart-backend.bat) so the website uses it." if ok else "The connection works but check the model name.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
