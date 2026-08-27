import asyncio
import json
import pytest
from scoring.signals import score_content
from scoring.thresholds import compute_profile_score, compute_engagement_score, compute_final_score
from enrichment.profile import extract_bio_signals


class TestContentScoring:
    def test_empty_tweets(self):
        result = score_content([])
        assert result["score"] == 0
        assert result["signals"] == []

    def test_code_block_detection(self):
        tweets = ["Just shipped this contract: ```solidity\npragma solidity ^0.8.0;\n```"]
        result = score_content(tweets)
        assert result["score"] > 0
        assert any("code snippet" in s for s in result["signals"])

    def test_github_link_detection(self):
        tweets = ["Check out my repo: github.com/user/my-dapp"]
        result = score_content(tweets)
        assert result["score"] > 0
        assert any("GitHub link" in s for s in result["signals"])

    def test_deploy_keywords(self):
        tweets = ["Just deployed my token to mainnet!"]
        result = score_content(tweets)
        assert result["score"] > 0
        assert any("deploy keyword" in s for s in result["signals"])

    def test_engagement_farming_penalty(self):
        tweets = ["🔥", "🚀", "💯", "gm", "lfg"]
        result = score_content(tweets)
        assert result["score"] < 0 or any("farming" in s for s in result["signals"])

    def test_block_explorer_link(self):
        tweets = ["Contract verified on etherscan.io/address/0x1234"]
        result = score_content(tweets)
        assert result["score"] > 0
        assert any("block explorer" in s for s in result["signals"])


class TestProfileScoring:
    def test_github_in_bio(self):
        signals = extract_bio_signals("Building cool stuff | github.com/user/project")
        result = compute_profile_score(signals, 500)
        assert result["score"] > 0
        assert any("GitHub" in s for s in result["signals"])

    def test_wallet_in_bio(self):
        signals = extract_bio_signals("Dev | 0x1234567890abcdef1234567890abcdef12345678")
        result = compute_profile_score(signals, 500)
        assert result["score"] > 0
        assert any("Wallet" in s or "wallet" in s for s in result["signals"])

    def test_tech_keywords(self):
        signals = extract_bio_signals("Solidity dev | Building DeFi protocols | ZK enthusiast")
        result = compute_profile_score(signals, 500)
        assert result["score"] > 0
        assert any("keyword" in s for s in result["signals"])

    def test_sweet_spot_followers(self):
        signals = extract_bio_signals("Builder")
        result = compute_profile_score(signals, 300)
        assert any("sweet spot" in s for s in result["signals"])


class TestEngagementScoring:
    def test_baseline(self):
        result = compute_engagement_score({"followers": 100, "following": 100})
        assert result["score"] > 0

    def test_healthy_ratio(self):
        result = compute_engagement_score({"followers": 500, "following": 200})
        assert any("ratio" in s for s in result["signals"])


class TestFinalScoring:
    def test_high_score_qualifies(self):
        profile = {"score": 80, "signals": ["github"]}
        content = {"score": 70, "signals": ["code"]}
        engagement = {"score": 60, "signals": ["baseline"]}
        onchain = {"score": 50, "signals": ["deployed"]}
        github = {"score": 40, "signals": ["repos"]}
        llm = {"llm_score": 75, "llm_verdict": "builder"}

        result = compute_final_score(profile, content, engagement, onchain, github, llm)
        assert result["qualifies"] is True
        assert result["final_score"] >= 60

    def test_low_score_rejects(self):
        profile = {"score": 10, "signals": []}
        content = {"score": 5, "signals": []}
        engagement = {"score": 50, "signals": []}
        onchain = {"score": 0, "signals": []}
        github = {"score": 0, "signals": []}
        llm = {"llm_score": None, "llm_verdict": "skipped"}

        result = compute_final_score(profile, content, engagement, onchain, github, llm)
        assert result["qualifies"] is False
