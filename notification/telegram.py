import json
import logging

import httpx

from config import settings

logger = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org/bot{token}"


def _format_message(account: dict) -> str:
    username = account.get("username", "unknown")
    score = account.get("final_score", 0)
    signals = account.get("signals", "")
    if isinstance(signals, str):
        try:
            signals = json.loads(signals)
        except (json.JSONDecodeError, TypeError):
            signals = []

    github_data = account.get("github_data", "")
    if isinstance(github_data, str):
        try:
            github_data = json.loads(github_data)
        except (json.JSONDecodeError, TypeError):
            github_data = {}

    onchain_data = account.get("onchain_data", "")
    if isinstance(onchain_data, str):
        try:
            onchain_data = json.loads(onchain_data)
        except (json.JSONDecodeError, TypeError):
            onchain_data = {}

    lines = [
        f"Web3 Builder Found",
        f"",
        f"@{username} - Score: {score}/100",
        f"Name: {account.get('name', 'N/A')}",
        f"Followers: {account.get('followers', 0)}",
        f"",
    ]

    if signals:
        top_signals = signals[:5]
        lines.append("Top signals:")
        for s in top_signals:
            lines.append(f"  - {s}")
        lines.append("")

    gh_repos = github_data.get("web3_repos", 0)
    if gh_repos > 0:
        stars = github_data.get("total_stars", 0)
        lines.append(f"GitHub: {gh_repos} Web3 repos, {stars} stars")

    chains = onchain_data.get("chains_active", [])
    if chains:
        deploys = onchain_data.get("total_deploys", 0)
        lines.append(f"On-chain: {deploys} deploys on {', '.join(chains)}")

    llm_reason = account.get("llm_reasoning", "")
    if llm_reason:
        lines.append("")
        lines.append(f"AI verdict: {llm_reason}")

    lines.append("")
    lines.append(f"https://x.com/{username}")

    return "\n".join(lines)


async def send_telegram(account: dict) -> bool:
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        logger.warning("Telegram not configured, skipping send")
        return False

    message = _format_message(account)
    url = f"{TELEGRAM_API.format(token=settings.telegram_bot_token)}/sendMessage"

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                url,
                json={
                    "chat_id": settings.telegram_chat_id,
                    "text": message,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": True,
                },
                timeout=10,
            )
            if resp.status_code == 200:
                logger.info(f"Sent @{account.get('username')} to Telegram")
                return True
            else:
                logger.warning(f"Telegram send failed: {resp.status_code} {resp.text[:200]}")
                return False
    except Exception as e:
        logger.error(f"Telegram error: {e}")
        return False
