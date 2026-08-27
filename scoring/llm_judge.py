import asyncio
import json
import logging
import re
import threading
from datetime import date

import httpx

from config import settings

logger = logging.getLogger(__name__)

OPENROUTER_API = "https://openrouter.ai/api/v1/chat/completions"

FALLBACK_MODELS = [
    "nvidia/nemotron-3-ultra-550b-a55b:free",
    "qwen/qwen3-coder:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "google/gemma-3-12b-it:free",
    "mistralai/mistral-small-3.1-24b-instruct:free",
]

MAX_LLM_CALLS_PER_DAY = 40

_daily_lock = threading.Lock()
_daily_calls = 0
_daily_date = date.today()


def _can_call_llm() -> bool:
    global _daily_calls, _daily_date
    with _daily_lock:
        today = date.today()
        if today != _daily_date:
            _daily_date = today
            _daily_calls = 0
        if _daily_calls >= MAX_LLM_CALLS_PER_DAY:
            return False
        _daily_calls += 1
        return True


def _clean_json(text: str) -> dict | list | None:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    first_brace = text.find("{")
    first_bracket = text.find("[")
    if first_brace == -1 and first_bracket == -1:
        return None
    start = first_brace
    if first_bracket != -1 and (first_brace == -1 or first_bracket < first_brace):
        start = first_bracket
    text = text[start:]
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


async def llm_judge(account: dict) -> dict:
    """Use LLM to judge if an account is genuinely building Web3."""
    if not settings.openrouter_api_key:
        return {
            "llm_score": None,
            "llm_verdict": "skipped",
            "llm_reasoning": "No OPENROUTER_API_KEY configured",
        }

    if not _can_call_llm():
        return {
            "llm_score": None,
            "llm_verdict": "skipped",
            "llm_reasoning": f"Daily LLM budget reached ({MAX_LLM_CALLS_PER_DAY}/day)",
        }

    prompt = f"""You are a Web3 builder scout. Analyze this Twitter account and determine if they are GENUINELY BUILDING a Web3 project (not just shilling, farming engagement, or pretending).

Account: @{account.get('username', 'unknown')}
Name: {account.get('name', '')}
Bio: {account.get('description', '')}
Followers: {account.get('followers', 0)}

Sample tweets:
{account.get('sample_tweet', 'N/A')}

Enrichment data:
- GitHub: {json.dumps(account.get('github', {}), indent=2)}
- On-chain: {json.dumps(account.get('onchain', {}), indent=2)}
- Bio signals: {json.dumps(account.get('bio_signals', {}), indent=2)}
- Content score: {account.get('content_score', 0)}

Score this account 1-100 for genuine Web3 building activity.
Return ONLY a JSON object: {{"score": <int 1-100>, "verdict": "builder"|"maybe"|"not_builder", "reasoning": "<1-2 sentences>"}}"""

    try:
        models = [settings.openrouter_model] if settings.openrouter_model else FALLBACK_MODELS
        models = list(dict.fromkeys([m for m in models if m]) or FALLBACK_MODELS)

        for model in models:
            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.post(
                        OPENROUTER_API,
                        headers={
                            "Authorization": f"Bearer {settings.openrouter_api_key}",
                            "Content-Type": "application/json",
                        },
                        json={
                            "model": model,
                            "messages": [{"role": "user", "content": prompt}],
                            "temperature": 0.3,
                            "max_tokens": 500,
                        },
                        timeout=30,
                    )

                if resp.status_code == 200:
                    content = resp.json()["choices"][0]["message"]["content"]
                    result = _clean_json(content)

                    if result and "score" in result:
                        return {
                            "llm_score": int(result["score"]),
                            "llm_verdict": result.get("verdict", "unknown"),
                            "llm_reasoning": result.get("reasoning", ""),
                            "llm_model": model,
                        }

                    logger.warning(f"{model} returned unparseable response, trying next")
                    continue

                if resp.status_code == 429:
                    err = resp.text[:200]
                    logger.warning(f"{model} rate-limited (429): {err}")
                    continue

                if resp.status_code == 401:
                    logger.warning(f"{model} unauthorized (401), skipping")
                    continue

                if resp.status_code == 404:
                    logger.warning(f"{model} not found (404), trying next")
                    continue

                logger.warning(f"{model}: HTTP {resp.status_code}: {resp.text[:200]}")
                continue

            except httpx.HTTPError as e:
                logger.warning(f"LLM HTTP error on {model}: {e}")
                continue

        return {
            "llm_score": None,
            "llm_verdict": "error",
            "llm_reasoning": "All OpenRouter models failed (likely daily free limit)",
        }

    except Exception as e:
        logger.error(f"LLM judge failed: {e}")
        return {
            "llm_score": None,
            "llm_verdict": "error",
            "llm_reasoning": str(e),
        }
