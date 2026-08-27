import asyncio
import logging

import httpx

from config import settings

logger = logging.getLogger(__name__)

GITHUB_API = "https://api.github.com"
HEADERS = {"Accept": "application/vnd.github.v3+json"}
if settings.github_token:
    HEADERS["Authorization"] = f"token {settings.github_token}"

WEB3_LANGUAGES = {"solidity", "rust", "move", "cairo", "vyper", "toml", "json"}
WEB3_REPO_KEYWORDS = [
    "ethers", "viem", "wagmi", "hardhat", "foundry", "anchor",
    "solana", "ethereum", "defi", "nft", "token", "contract",
    "bridge", "oracle", "zk", "rollup", "dapp", "protocol",
]


async def _get(client: httpx.AsyncClient, url: str) -> dict | None:
    try:
        resp = await client.get(url, headers=HEADERS, timeout=15)
        if resp.status_code == 200:
            return resp.json()
        logger.debug(f"GitHub {resp.status_code}: {url}")
    except Exception as e:
        logger.debug(f"GitHub request failed: {e}")
    return None


async def get_github_data(username: str) -> dict | None:
    """Fetch GitHub profile and repo data for a Twitter username."""
    async with httpx.AsyncClient() as client:
        user_data = await _get(client, f"{GITHUB_API}/users/{username}")
        if not user_data:
            return None

        public_repos = user_data.get("public_repos", 0)
        if public_repos == 0:
            return {"exists": True, "public_repos": 0, "web3_repos": 0}

        repos_data = await _get(
            client, f"{GITHUB_API}/users/{username}/repos?per_page=30&sort=updated"
        )
        repos = repos_data or []

        web3_repos = 0
        total_stars = 0
        languages = set()
        has_recent_commit = False

        for repo in repos:
            lang = (repo.get("language") or "").lower()
            languages.add(lang)

            name_lower = (repo.get("name", "") + " " + (repo.get("description") or "")).lower()
            if lang in WEB3_LANGUAGES or any(kw in name_lower for kw in WEB3_REPO_KEYWORDS):
                web3_repos += 1

            total_stars += repo.get("stargazers_count", 0)

            pushed = repo.get("pushed_at", "")
            if pushed and pushed > "2026-07-01":
                has_recent_commit = True

        events = await _get(client, f"{GITHUB_API}/users/{username}/events/public?per_page=10")
        recent_prs = 0
        if events:
            for event in events[:10]:
                if event.get("type") == "PullRequestEvent":
                    recent_prs += 1

        return {
            "exists": True,
            "public_repos": public_repos,
            "web3_repos": web3_repos,
            "total_stars": total_stars,
            "languages": list(languages),
            "has_recent_commit": has_recent_commit,
            "recent_prs": recent_prs,
        }
