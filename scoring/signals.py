import re

CODE_BLOCK_PATTERN = re.compile(r"```[\s\S]*?```")
SOLIDITY_PATTERN = re.compile(r"pragma solidity|contract\s+\w+|function\s+\w+")
RUST_PATTERN = re.compile(r"fn\s+\w+|pub\s+fn|use\s+anchor|use\s+solana")
REPO_LINK_PATTERN = re.compile(r"github\.com/[a-zA-Z0-9_\-.]+/[a-zA-Z0-9_\-.]+")
EXPLORER_PATTERN = re.compile(
    r"etherscan\.io|basescan\.io|arbiscan\.io|polygonscan\.io|solscan\.io|explorer\."
)
DEPLOY_KEYWORDS = [
    "deployed", "shipped", "launched", "live on", "just deployed",
    "deploying", "contract live", "mainnet", "testnet live",
]
VERSION_PATTERN = re.compile(r"v\d+\.\d+|version\s+\d+|milestone|changelog")
BUILD_HASHTAGS = {"buildinpublic", "shiplogs", "devlogs", "web3dev"}
ANTI_FARM_PATTERNS = re.compile(
    r"^(🔥|🚀|💯|moon|pump|gm|wen|lfg)[\s!]*$", re.IGNORECASE
)


def score_content(tweets: list[str]) -> dict:
    """Score tweet content quality from sample tweets."""
    if not tweets:
        return {"score": 0, "signals": []}

    signals = []
    score = 0

    all_text = " ".join(tweets)

    code_blocks = CODE_BLOCK_PATTERN.findall(all_text)
    if code_blocks:
        score += 15
        signals.append(f"{len(code_blocks)} code snippet(s)")

    if SOLIDITY_PATTERN.search(all_text):
        score += 5
        signals.append("Solidity code found")
    if RUST_PATTERN.search(all_text):
        score += 5
        signals.append("Rust code found")

    repo_links = REPO_LINK_PATTERN.findall(all_text)
    if repo_links:
        score += 10
        signals.append(f"{len(repo_links)} GitHub link(s)")

    explorer_links = EXPLORER_PATTERN.findall(all_text)
    if explorer_links:
        score += 10
        signals.append(f"{len(explorer_links)} block explorer link(s)")

    deploy_count = sum(1 for kw in DEPLOY_KEYWORDS if kw in all_text.lower())
    if deploy_count > 0:
        score += min(deploy_count * 5, 15)
        signals.append(f"{deploy_count} deploy keyword(s)")

    if VERSION_PATTERN.search(all_text):
        score += 5
        signals.append("version/milestone mentioned")

    hashtag_set = set(re.findall(r"#(\w+)", all_text.lower()))
    build_tags = hashtag_set & BUILD_HASHTAGS
    if build_tags:
        score += 5
        signals.append(f"build hashtags: {', '.join(build_tags)}")

    anti_farm = sum(1 for t in tweets if ANTI_FARM_PATTERNS.match(t.strip()))
    if anti_farm > len(tweets) * 0.5:
        score -= 20
        signals.append(f"engagement farming detected ({anti_farm}/{len(tweets)})")

    return {"score": min(max(score, 0), 100), "signals": signals}
