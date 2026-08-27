import re
from datetime import datetime, timezone

CONTRACT_PATTERN = re.compile(r"\b0x[0-9a-fA-F]{40}\b")
GITHUB_REPO_PATTERN = re.compile(r"github\.com/([a-zA-Z0-9_\-.]+/[a-zA-Z0-9_\-.]+)")
explorer_links = {
    "etherscan.io": "Ethereum",
    "basescan.io": "Base",
    "arbiscan.io": "Arbitrum",
    "polygonscan.io": "Polygon",
    "solscan.io": "Solana",
    "bscscan.com": "BSC",
    "ftmscan.com": "Fantom",
    "snowtrace.io": "Avalanche",
}
LAUNCH_KEYWORDS = [
    "launched", "deployed", "live on", "just shipped", "mainnet",
    "testnet live", "contract live", "token live", "nft live",
    "going live", "now live", "is live", "public launch",
    "mainnet launch", "beta launch", "alpha launch",
]
PROJECT_TYPE_KEYWORDS = {
    "DeFi": ["defi", "dex", "amm", "lending", "borrowing", "yield", "farming", "staking", "swap", "liquidity"],
    "NFT": ["nft", "erc-721", "erc-1155", "collection", "mint", "pfp", "art"],
    "Token": ["erc-20", "token", "governance", "dao", "vote"],
    "Infrastructure": ["bridge", "oracle", "l2", "rollup", "zk", "layer 2", "infra", "rpc", "indexer"],
    "Tooling": ["sdk", "api", "framework", "cli", "devtool", "tooling", "hardhat", "foundry"],
    "GameFi": ["game", "gaming", "play to earn", "metaverse", "voxel"],
    "Social": ["social", "identity", "attestation", "reputation", "profile"],
}


def extract_projects_from_tweet(tweet_text: str, username: str, followers: int) -> list[dict]:
    """Extract project info from a single tweet."""
    projects = []
    text_lower = tweet_text.lower()

    is_launch = any(kw in text_lower for kw in LAUNCH_KEYWORDS)
    if not is_launch:
        return projects

    chains = []
    for domain, chain in explorer_links.items():
        if domain in text_lower:
            chains.append(chain)

    contract_match = CONTRACT_PATTERN.search(tweet_text)
    contract_address = contract_match.group(0) if contract_match else None

    gh_match = GITHUB_REPO_PATTERN.search(tweet_text)
    github_url = f"https://{gh_match.group(0)}" if gh_match else None

    project_url = None
    for domain in explorer_links:
        if domain in text_lower:
            idx = tweet_text.lower().find(domain)
            start = max(0, tweet_text.rfind(" ", 0, idx))
            end = tweet_text.find(" ", idx + len(domain))
            if end == -1:
                end = len(tweet_text)
            project_url = tweet_text[start:end].strip()
            break

    if not project_url and contract_address:
        chain_slug = chains[0].lower() if chains else "ethereum"
        explorer_map = {
            "Ethereum": "etherscan.io",
            "Base": "basescan.io",
            "Arbitrum": "arbiscan.io",
            "Polygon": "polygonscan.io",
            "Solana": "solscan.io",
        }
        explorer = explorer_map.get(chains[0], "etherscan.io") if chains else "etherscan.io"
        project_url = f"https://{explorer}/address/{contract_address}"

    project_type = "Other"
    for ptype, keywords in PROJECT_TYPE_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            project_type = ptype
            break

    if chains or contract_address or github_url:
        name = _extract_project_name(tweet_text, username)
        score = 0
        signals = []
        if is_launch:
            score += 30
            signals.append("launch announcement")
        if contract_address:
            score += 25
            signals.append("contract address shared")
        if chains:
            score += 15
            signals.append(f"on {', '.join(chains)}")
        if github_url:
            score += 15
            signals.append("open source")
        if followers < 500:
            score += 10
            signals.append("microbuilder")

        projects.append({
            "name": name,
            "username": username,
            "description": tweet_text[:300],
            "chain": ", ".join(chains) if chains else "unknown",
            "project_type": project_type,
            "url": project_url or "",
            "github_url": github_url or "",
            "contract_address": contract_address or "",
            "discovered_at": datetime.now(timezone.utc).isoformat(),
            "score": min(score, 100),
            "signals": signals,
            "tweet_text": tweet_text[:500],
        })

    return projects


def _extract_project_name(text: str, username: str) -> str:
    patterns = [
        r"(?:introducing|presenting|meet|say hello to)\s+([A-Z][a-zA-Z0-9]+)",
        r"([A-Z][a-zA-Z0-9]+)\s+(?:is|goes|just)\s+(?:live|live on|launched)",
        r"(?:my|our|the)\s+([A-Z][a-zA-Z0-9]+)\s+(?:is|contract|token|nft|protocol|dapp|app)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)

    words = text.split()
    for word in words:
        if word.istitle() and len(word) > 2 and word not in ("Just", "The", "This", "That", "My", "Our", "New"):
            return word

    return f"@{username}'s project"


def has_website(account: dict) -> bool:
    """Check if an account has a website/project link."""
    desc = (account.get("description") or "").lower()
    website_indicators = [
        "http://", "https://", ".com", ".io", ".xyz", ".org",
        "linktree", "calendly", "lu.ma",
    ]
    return any(ind in desc for ind in website_indicators)
