from datetime import datetime, timezone
from enrichment.events import (
    extract_event_from_tweet,
    parse_deadline,
    _event_type,
    classify_giveaway_engagement,
    LOW_ENGAGEMENT_CRITERIA,
    HIGH_ENGAGEMENT_CRITERIA,
)


class TestDeadlineParsing:
    def test_absolute_date(self):
        dt = parse_deadline("Deadline: 2026-12-15")
        assert dt is not None
        assert dt.year == 2026 and dt.month == 12 and dt.day == 15

    def test_named_month(self):
        dt = parse_deadline("Submissions due by December 31")
        assert dt is not None
        assert dt.year == 2026 and dt.month == 12

    def test_relative_days(self):
        dt = parse_deadline("Deadline is in 5 days")
        assert dt is not None
        days = (dt - datetime.now(timezone.utc)).days
        assert 4 <= days <= 6

    def test_tomorrow(self):
        dt = parse_deadline("Hackathon submissions close tomorrow")
        assert dt is not None
        hours = (dt - datetime.now(timezone.utc)).total_seconds() / 3600
        assert 0 < hours <= 48

    def test_no_deadline_returns_none(self):
        assert parse_deadline("We love building cool stuff!") is None

    def test_past_deadline_rejected(self):
        assert parse_deadline("Deadline: 2020-01-01") is None


class TestEventType:
    def test_hackathon(self):
        assert _event_type("Join our hackathon this weekend") == "hackathon"

    def test_meme_contest(self):
        assert _event_type("Create a meme contest! Win prizes") == "meme_contest"

    def test_video_contest(self):
        assert _event_type("Video contest: make a short video") == "video_contest"

    def test_giveaway(self):
        assert _event_type("Giveaway! Like and retweet to enter") == "giveaway"

    def test_raffle(self):
        assert _event_type("Solana raffle ends next Friday") == "giveaway"


class TestGiveawayEngagement:
    def test_criteria_are_two_separate_lists(self):
        assert isinstance(LOW_ENGAGEMENT_CRITERIA, list)
        assert isinstance(HIGH_ENGAGEMENT_CRITERIA, list)
        assert LOW_ENGAGEMENT_CRITERIA and HIGH_ENGAGEMENT_CRITERIA

    def test_high_engagement(self):
        result = classify_giveaway_engagement({"likes": 3000, "retweets": 900, "replies": 200})
        assert result["tier"] == "high"
        assert result["metrics"]["likes"] == 3000

    def test_high_engagement_retweets_only(self):
        assert classify_giveaway_engagement({"retweets": 900})["tier"] == "high"

    def test_low_engagement(self):
        result = classify_giveaway_engagement({"likes": 150, "retweets": 30})
        assert result["tier"] == "low"

    def test_no_engagement(self):
        assert classify_giveaway_engagement({"likes": 10, "retweets": 2})["tier"] == "none"

    def test_empty_metrics(self):
        assert classify_giveaway_engagement({})["tier"] == "none"


class TestEventExtraction:
    def test_hackathon_extraction(self):
        tweet = (
            "The Base Hackathon is live! Build on Base and win from a $50000 prize pool. "
            "Submissions due January 30. Apply at base.org/hackathon"
        )
        event = extract_event_from_tweet(tweet, "thebase")
        assert event is not None
        assert event["event_type"] == "hackathon"
        assert "base" in event["name"].lower()
        assert "$50000" in event["prizes"]
        assert event["days_left"] is not None
        assert event["username"] == "thebase"

    def test_meme_contest_extraction(self):
        tweet = (
            "Meme contest on Solana! Best meme wins $1000 USDC. Entries close March 1."
        )
        event = extract_event_from_tweet(tweet, "solana")
        assert event is not None
        assert event["event_type"] == "meme_contest"
        assert "$1000" in event["prizes"]

    def test_no_deadline_returns_none(self):
        tweet = "We are building the future of DeFi. Check out our docs!"
        assert extract_event_from_tweet(tweet, "project") is None

    def test_past_event_returns_none(self):
        tweet = "Meme contest that already ended. Deadline: 2020-05-01"
        assert extract_event_from_tweet(tweet, "project") is None

    def test_empty_tweet_returns_none(self):
        assert extract_event_from_tweet("", "project") is None

    def test_giveaway_extraction(self):
        tweet = (
            "Giveaway! Like & retweet to enter. $1000 USDC prize, 3 random winners. "
            "Giveaway ends: in 3 days."
        )
        engagement = {"likes": 120, "retweets": 40, "replies": 12}
        event = extract_event_from_tweet(tweet, "token", engagement)
        assert event is not None
        assert event["event_type"] == "giveaway"
        assert event["engagement_tier"] == "low"
        assert event["likes"] == 120
        assert event["retweets"] == 40
        assert event["replies"] == 12
        assert any("giveaway" in s for s in event["signals"])

    def test_giveaway_high_tier_extraction(self):
        tweet = "Mega giveaway ends: in 24 hours. Like and retweet to enter."
        engagement = {"likes": 5000, "retweets": 1200, "replies": 400}
        event = extract_event_from_tweet(tweet, "project", engagement)
        assert event is not None
        assert event["event_type"] == "giveaway"
        assert event["engagement_tier"] == "high"

    def test_contest_ignores_engagement(self):
        tweet = "The Base Hackathon is live! Submissions due January 30."
        event = extract_event_from_tweet(tweet, "thebase", {"likes": 99999, "retweets": 99999})
        assert event is not None
        assert event["event_type"] == "hackathon"
        assert event.get("engagement_tier") == ""