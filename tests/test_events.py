from datetime import datetime, timezone
from enrichment.events import (
    extract_event_from_tweet,
    parse_deadline,
    _event_type,
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