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
    "new token launched",
    "token launch today",
    "presale live",
    "IDO going live",
    "just deployed token",
    "new memecoin",
    "meme coin launched",
    "new crypto project launch",
    "mainnet launch",
    "testnet live",
    "new NFT mint live",
    "contract deployed base",
    "contract deployed solana",
    "new DeFi protocol live",
    "token listed DEX",
    "this token launched",
    "new project announcement crypto",
    "crypto project update",
    "existin project roadmap",
    "project milestones crypto",
]

EVENT_SEARCH_QUERIES = [
    "hackathon deadline",
    "hackathon submissions open",
    "hackathon registration open",
    "hackathon late deadline",
    "hackathon until",
    "hackathon apply before",
    "hackathon entry deadline",
    "hackathon prize pool",
    "meme contest",
    "meme competition",
    "meme contest deadline",
    "meme competition ends",
    "create a meme contest crypto",
    "best meme wins",
    "video contest crypto",
    "video competition",
    "video contest deadline",
    "reels contest crypto",
    "shorts contest crypto",
    "make a video win prizes crypto",
    "content creator contest crypto",
    "video challenge crypto",
    "reels challenge",
    "shorts challenge",
    "best video wins prizes",
    "video contest submissions",
    "make a reel to enter",
    "content creator challenge",
    "film contest crypto",
    "tiktok challenge crypto",
    "video creator contest",
    "video editing contest crypto",
    "video edit contest",
    "editing contest crypto",
    "motion graphics contest crypto",
    "edit to win crypto",
    "crypto giveaway ends",
    "giveaway ends soon",
    "raffle ends",
    "giveaway like and retweet",
    "giveaway follow to enter",
    "giveaway winner announced",
    "random winner giveaway",
    "last day giveaway",
    "nft giveaway ends",
    "token giveaway",
]

MIN_FOLLOWERS = 0
MAX_FOLLOWERS = 1000
MAX_EVENT_FOLLOWERS = 100000
MIN_ACCOUNT_AGE_DAYS = 90
MIN_TWEET_COUNT = 20
MIN_EVENT_TWEET_COUNT = 5


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


async def _search_pages(
    client: Client,
    query: str,
    count: int,
    max_pages: int,
    product: str = "Latest",
) -> list:
    """Search with pagination to gather deeper results beyond a single page."""
    tweets: list = []
    result = await client.search_tweet(query, product, count=count)
    page = 0
    while result is not None and len(result) > 0 and page < max(max_pages, 1):
        for tweet in result:
            tweets.append(tweet)
        cursor = getattr(result, "next_cursor", None)
        if not cursor:
            break
        next_result = await result.next()
        if next_result is None or len(next_result) == 0:
            break
        result = next_result
        page += 1
        await asyncio.sleep(3)
    return tweets


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
            tweets = await _search_pages(
                client, query, settings.search_tweets_per_query, settings.search_max_pages
            )

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


async def discover_events() -> list[dict]:
    """Search Twitter for hackathons, meme contests, and video contests with deadlines."""
    client = await _init_client()
    seen_tweets: dict[str, dict] = {}

    for query in EVENT_SEARCH_QUERIES:
        products = ["Latest", "Top"]
        if any(k in query for k in ("video", "reel", "shorts", "tiktok", "film", "edit", "meme")):
            products.append("Media")

        for product in products:
            try:
                logger.info(f"Event search [{product}]: {query}")
                tweets = await _search_pages(
                    client, query, settings.search_tweets_per_query,
                    settings.event_max_pages, product=product,
                )

                for tweet in tweets:
                    user = tweet.user
                    if not user:
                        continue

                    followers = getattr(user, "followers_count", 0) or 0
                    if followers > MAX_EVENT_FOLLOWERS:
                        continue

                    tweet_count = getattr(user, "statuses_count", 0) or 0
                    if tweet_count < MIN_EVENT_TWEET_COUNT:
                        continue

                    tweet_id = getattr(tweet, "id", None) or tweet.text[:100]
                    if tweet_id in seen_tweets:
                        continue

                    username = _extract_username(user)
                    seen_tweets[tweet_id] = {
                        "username": username,
                        "user_id": getattr(user, "id", None),
                        "name": getattr(user, "name", ""),
                        "description": getattr(user, "description", ""),
                        "followers": followers,
                        "following": getattr(user, "following_count", 0) or 0,
                        "tweet_count": tweet_count,
                        "profile_url": f"https://x.com/{username}",
                        "event_tweet": tweet.text[:500] if tweet.text else "",
                        "engagement": {
                            "likes": getattr(tweet, "favorite_count", None) or 0,
                            "retweets": getattr(tweet, "retweet_count", None) or 0,
                            "replies": getattr(tweet, "reply_count", None) or 0,
                        },
                        "discovered_via": f"{query} [{product}]",
                        "discovered_at": datetime.now(timezone.utc).isoformat(),
                    }

                await asyncio.sleep(3)

            except Exception as e:
                logger.warning(f"Event search failed [{product}] '{query}': {e}")
                await asyncio.sleep(5)

    logger.info(f"Discovered {len(seen_tweets)} event tweets")
    return list(seen_tweets.values())
