import json
import re
from groq import Groq
from ..config import GROQ_API_KEY, GROQ_MODEL, GROQ_FALLBACK_MODEL

_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None


def _strip_fences(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(json)?", "", text)
    text = re.sub(r"```$", "", text)
    return text.strip()


def call_llm(system_prompt: str, user_prompt: str, json_mode: bool = False) -> str:
    """Calls Groq openai/gpt-oss-20b, falls back to openai/gpt-oss-120b on failure."""
    if _client is None:
        raise RuntimeError("GROQ_API_KEY not configured")

    models_to_try = [GROQ_MODEL, GROQ_FALLBACK_MODEL]
    last_err = None
    for model in models_to_try:
        try:
            resp = _client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.2,
                max_tokens=1024,
            )
            return resp.choices[0].message.content
        except Exception as e:  # noqa
            last_err = e
            continue
    raise RuntimeError(f"All Groq models failed: {last_err}")


def call_llm_json(system_prompt: str, user_prompt: str) -> dict:
    raw = call_llm(system_prompt, user_prompt, json_mode=True)
    cleaned = _strip_fences(raw)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise
