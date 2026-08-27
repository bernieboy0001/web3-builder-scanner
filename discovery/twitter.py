import asyncio
import json
import logging
import re
from pathlib import Path
from datetime import datetime, timezone

from twikit import Client

from config import settings

logger = logging.getLogger(__name__)

SEARCH_QUERIES = [
    "#buildinpublic deployed",
    "#buildinpublic shipped",
    "#buildinpublic launched",
    "solidity contract deployed",
    "rust solana program deployed",
    "ERC-20 token live",
    "ERC-721 NFT contract",
    "my dapp is live",
    "just deployed to mainnet",
    "smart contract verified",
    "hackathon submission web3",
    "building protocol onchain",
    "ZK proof circuit built",
    "moved contract to base",
    "contracts deployed arbitrum",
    "first commit my dapp",
]

MIN_FOLLOWERS = 0
MAX_FOLLOWERS = 1000
MIN_ACCOUNT_AGE_DAYS = 90
MIN_TWEET_COUNT = 20


def _parse_cookies(path: str) -> list[dict]:
    import os

    env_cookies = os.environ.get("TWITTER_COOKIES_JSON", "")
    if env_cookies:
        raw = json.loads(env_cookies)
        if isinstance(raw, list):
            return raw
        if isinstance(raw, dict):
            return [raw]
        raise ValueError("TWITTER_COOKIES_JSON must be a JSON array or object")

    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(
            f"Cookies file not found: {p}\n"
            "Set TWITTER_COOKIES_JSON env var or place cookies.json in the project root."
        )
    raw = json.loads(p.read_text())
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict):
        return [raw]
    raise ValueError("cookies.json must be a JSON array or object")


def _cookies_to_dict(cookies: list[dict]) -> dict[str, str]:
    return {c["name"]: c["value"] for c in cookies if "name" in c and "value" in c}


async def _init_client() -> Client:
    client = Client("en-US")
    cookies = _parse_cookies(settings.twitter_cookies_path)
    cookie_dict = _cookies_to_dict(cookies)
    client.set_cookies(cookie_dict)
    return client


def _parse_twitter_date(date_str: str) -> datetime | None:
    """Parse Twitter's date format: 'Fri Jun 20 13:50:15 +0000 2025'"""
    if not date_str:
        return None
    try:
        from email.utils import parsedate_to_datetime
        return parsedate_to_datetime(date_str).replace(tzinfo=timezone.utc)
    except Exception:
        return None


def _account_passes_filters(user) -> tuple[bool, str]:
    followers = getattr(user, "followers_count", 0) or 0
    if followers > MAX_FOLLOWERS:
        return False, f"too many followers ({followers})"
    if followers < MIN_FOLLOWERS:
        return False, f"no followers ({followers})"

    created = getattr(user, "created_at", None)
    if created:
        dt = _parse_twitter_date(created) if isinstance(created, str) else created
        if dt:
            age_days = (datetime.now(timezone.utc) - dt).days
            if age_days < MIN_ACCOUNT_AGE_DAYS:
                return False, f"account too young ({age_days}d)"

    tweet_count = getattr(user, "statuses_count", 0) or 0
    if tweet_count < MIN_TWEET_COUNT:
        return False, f"too few tweets ({tweet_count})"

    return True, "ok"


def _extract_username(user) -> str:
    for attr in ("screen_name", "username", "name"):
        val = getattr(user, attr, None)
        if val:
            return val
    return "unknown"


async def discover_builders() -> list[dict]:
    """Search Twitter for Web3 builder accounts under 1k followers."""
    client = await _init_client()
    seen_users: dict[str, dict] = {}

    for query in SEARCH_QUERIES:
        try:
            logger.info(f"Searching: {query}")
            tweets = await client.search_tweet(query, "Latest", count=20)

            for tweet in tweets:
                user = tweet.user
                if not user:
                    continue

                username = _extract_username(user)
                if username in seen_users:
                    continue

                passed, reason = _account_passes_filters(user)
                if not passed:
                    logger.debug(f"Filtered @{username}: {reason}")
                    continue

                seen_users[username] = {
                    "username": username,
                    "user_id": getattr(user, "id", None),
                    "name": getattr(user, "name", ""),
                    "description": getattr(user, "description", ""),
                    "followers": getattr(user, "followers_count", 0) or 0,
                    "following": getattr(user, "following_count", 0) or 0,
                    "tweet_count": getattr(user, "statuses_count", 0) or 0,
                    "verified": getattr(user, "verified", False),
                    "profile_url": f"https://x.com/{username}",
                    "discovered_via": query,
                    "sample_tweet": tweet.text[:500] if tweet.text else "",
                    "discovered_at": datetime.now(timezone.utc).isoformat(),
                }

            await asyncio.sleep(3)

        except Exception as e:
            logger.warning(f"Search failed for '{query}': {e}")
            await asyncio.sleep(5)

    logger.info(f"Discovered {len(seen_users)} unique accounts")
    return list(seen_users.values())
