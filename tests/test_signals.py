import pytest
from enrichment.profile import extract_bio_signals


class TestBioExtraction:
    def test_github_url(self):
        result = extract_bio_signals("Check my work github.com/alice/cool-dapp")
        assert result["has_github_link"] is True
        assert "github.com/alice/cool-dapp" in result["github_url"]

    def test_wallet_address(self):
        result = extract_bio_signals("My wallet: 0xabcdef1234567890abcdef1234567890abcdef12")
        assert result["has_wallet"] is True
        assert result["wallet_address"].startswith("0x")

    def test_ens(self):
        result = extract_bio_signals("Building at alice.eth")
        assert result["has_ens"] is True

    def test_farcaster(self):
        result = extract_bio_signals("Find me on warpcast.com/alice")
        assert result["has_farcaster"] is True

    def test_tech_keywords(self):
        result = extract_bio_signals(
            "Solidity developer building DeFi protocols with ZK proofs on Ethereum"
        )
        assert result["tech_keyword_count"] >= 3
        assert "solidity" in result["tech_keywords"]

    def test_no_signals(self):
        result = extract_bio_signals("Just a regular person")
        assert result["has_github_link"] is False
        assert result["has_wallet"] is False
        assert result["tech_keyword_count"] == 0

    def test_multiple_signals(self):
        result = extract_bio_signals(
            "Solidity dev | 0xabcdef1234567890abcdef1234567890abcdef12 | "
            "github.com/builder/protocol | building DeFi on Ethereum"
        )
        assert result["has_github_link"] is True
        assert result["has_wallet"] is True
        assert result["tech_keyword_count"] >= 2
