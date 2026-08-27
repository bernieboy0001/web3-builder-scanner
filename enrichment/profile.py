import re

TECH_KEYWORDS = [
    "solidity", "rust", "move", "cairo", "vyper",
    "smart contract", "protocol engineer", "blockchain developer",
    "web3 developer", "dapp", "defi", "nft", "zk", "zero knowledge",
    "rollup", "l2", "layer 2", "bridge", "oracle",
    "hardhat", "foundry", "anchor", "cosmwasm",
    "eth", "sol", "base", "arbitrum", "optimism", "polygon",
    "building on", "deploying on", "shipping on",
    "erc-20", "erc-721", "erc-1155", "token",
]

WALLET_PATTERN = re.compile(r"\b0x[0-9a-fA-F]{40}\b")
ENS_PATTERN = re.compile(r"\b[a-zA-Z0-9]+\.eth\b")
GITHUB_PATTERN = re.compile(r"github\.com/[a-zA-Z0-9_\-.]+/[a-zA-Z0-9_\-.]+")
FARCASTER_PATTERN = re.compile(r"(warpcast\.com/|\.fc\b|farcaster)")


def extract_bio_signals(description: str) -> dict:
    desc_lower = description.lower()

    has_github = bool(GITHUB_PATTERN.search(description))
    has_wallet = bool(WALLET_PATTERN.search(description))
    has_ens = bool(ENS_PATTERN.search(description))
    has_farcaster = bool(FARCASTER_PATTERN.search(description))

    tech_matches = [kw for kw in TECH_KEYWORDS if kw in desc_lower]

    github_url = None
    if has_github:
        match = GITHUB_PATTERN.search(description)
        github_url = f"https://{match.group(0)}" if match else None

    wallet_address = None
    if has_wallet:
        match = WALLET_PATTERN.search(description)
        wallet_address = match.group(0) if match else None

    return {
        "has_github_link": has_github,
        "github_url": github_url,
        "has_wallet": has_wallet,
        "wallet_address": wallet_address,
        "has_ens": has_ens,
        "has_farcaster": has_farcaster,
        "tech_keywords": tech_matches,
        "tech_keyword_count": len(tech_matches),
    }
