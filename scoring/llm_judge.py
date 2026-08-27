import asyncio
import json
import logging
import re

import httpx

from config import settings

logger = logging.getLogger(__name__)

OPENROUTER_API = "https://openrouter.ai/api/v1/chat/completions"


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
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                OPENROUTER_API,
                headers={
                    "Authorization": f"Bearer {settings.openrouter_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.openrouter_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3,
                    "max_tokens": 500,
                },
                timeout=30,
            )

            if resp.status_code != 200:
                logger.warning(f"OpenRouter {resp.status_code}: {resp.text[:200]}")
                return {
                    "llm_score": None,
                    "llm_verdict": "error",
                    "llm_reasoning": f"API error {resp.status_code}",
                }

            content = resp.json()["choices"][0]["message"]["content"]
            result = _clean_json(content)

            if not result or "score" not in result:
                return {
                    "llm_score": None,
                    "llm_verdict": "parse_error",
                    "llm_reasoning": content[:200],
                }

            return {
                "llm_score": int(result["score"]),
                "llm_verdict": result.get("verdict", "unknown"),
                "llm_reasoning": result.get("reasoning", ""),
            }

    except Exception as e:
        logger.error(f"LLM judge failed: {e}")
        return {
            "llm_score": None,
            "llm_verdict": "error",
            "llm_reasoning": str(e),
        }
