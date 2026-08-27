import re
from datetime import datetime, timezone, timedelta

HACKATHON_KEYWORDS = [
    "hackathon", "hack-a-thon", "buildathon", "game jam", "dev contest",
]
MEME_KEYWORDS = [
    "meme contest", "meme competition", "meme challenge", "create a meme",
    "best meme", "meme battle", "memecoin contest",
]
VIDEO_KEYWORDS = [
    "video contest", "video competition", "video challenge", "reels contest",
    "shorts contest", "make a video", "video creation contest", "tiktok contest",
]
GIVEAWAY_KEYWORDS = [
    "giveaway", "raffle",
    "like and retweet", "like and rt", "love and retweet", "love and rt",
    "follow and retweet", "follow and rt", "rt to enter", "retweet to enter",
    "comment to enter", "comment below to enter",
    "tag 3 friends", "tag a friend",
    "random winner", "winners announced", "winner picked",
]

LOW_ENGAGEMENT_CRITERIA = [
    {"likes": 80, "retweets": 20},
    {"likes": 150},
    {"replies": 25},
]
HIGH_ENGAGEMENT_CRITERIA = [
    {"likes": 1500, "retweets": 350},
    {"likes": 3000},
    {"retweets": 800},
    {"replies": 300},
]


def classify_giveaway_engagement(engagement: dict) -> dict:
    """Grade a giveaway tweet's engagement as high/low against the two threshold lists."""
    metrics = {
        "likes": int(engagement.get("likes") or 0),
        "retweets": int(engagement.get("retweets") or 0),
        "replies": int(engagement.get("replies") or 0),
    }

    def meets(criteria: list[dict]) -> bool:
        for criterion in criteria:
            if all(metrics.get(metric, 0) >= minimum for metric, minimum in criterion.items()):
                return True
        return False

    if meets(HIGH_ENGAGEMENT_CRITERIA):
        tier = "high"
    elif meets(LOW_ENGAGEMENT_CRITERIA):
        tier = "low"
    else:
        tier = "none"

    return {"tier": tier, "metrics": metrics}

DEADLINE_PATTERNS = [
    r"(?:deadline|due|closes|close|ends|ending|end date|last day|apply by|before|until|by)\s*(?::|is|:)\s*([A-Za-z0-9,/:.\- ]{3,40})",
    r"(?:submissions?|entries?|applications?)\s*(?:due|close|end|deadline)(?:\s*(?:by|on|:))?\s*([A-Za-z0-9,/:.\- ]{3,40})",
    r"(?:deadline|due date|closes|ends)(?:\s*(?:on|:))?\s*([A-Za-z0-9.\-]+[\s,]*[A-Za-z0-9.\-]*[\s,]*[0-9]{2,4})",
]

MONTH_MAP = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}
WEEKDAYS = {
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
    "friday": 4, "saturday": 5, "sunday": 6,
}


def _try_fixed_formats(text: str) -> datetime | None:
    t = text.strip()
    fmts = [
        "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%m-%d-%Y",
        "%Y/%m/%d", "%d.%m.%Y", "%B %d %Y", "%b %d %Y", "%B %d, %Y",
        "%b %d, %Y", "%d %B %Y", "%d %b %Y", "%d %B, %Y",
    ]
    now = datetime.now()
    for fmt in fmts:
        try:
            parsed = datetime.strptime(t, fmt)
        except ValueError:
            continue
        if "%Y" not in fmt and not re.search(r"\d{4}", fmt):
            parsed = parsed.replace(year=now.year)
            if parsed < now:
                parsed = parsed.replace(year=now.year + 1)
        return parsed.replace(tzinfo=timezone.utc)
    return None


def _parse_relative(text: str, now: datetime) -> datetime | None:
    t = text.strip().lower()
    num_map = {
        "tomorrow": 1, "tmrw": 1, "today": 0, "tonight": 0,
        "next week": 7, "in a week": 7, "next month": 30, "in a month": 30,
    }
    for phrase, days in num_map.items():
        if phrase in t:
            return now + timedelta(days=days)

    m = re.search(r"(\d+)\s*(day|week|month|hour)s?", t)
    if m:
        n = int(m.group(1))
        unit = m.group(2)
        if "hour" in unit:
            return now + timedelta(hours=n)
        if "week" in unit:
            return now + timedelta(weeks=n)
        if "month" in unit:
            return now + timedelta(days=n * 30)
        return now + timedelta(days=n)

    for wd, idx in WEEKDAYS.items():
        if wd in t:
            days_ahead = (idx - now.weekday()) % 7
            if days_ahead == 0:
                days_ahead = 7
            return (now + timedelta(days=days_ahead)).replace(hour=0, minute=0, second=0)

    m = re.search(r"([A-Za-z]+)\s*(\d{1,2})(?:st|nd|rd|th)?\s*,?\s*(\d{2,4})?", t)
    if m:
        month = MONTH_MAP.get(m.group(1)[:3].lower())
        if month:
            day = int(m.group(2))
            year = int(m.group(3)) if m.group(3) else now.year
            try:
                dt = datetime(year, month, day, tzinfo=timezone.utc)
                if dt < now and not m.group(3):
                    dt = datetime(year + 1, month, day, tzinfo=timezone.utc)
                return dt
            except ValueError:
                return None

    m = re.search(r"(\d{1,2})\s+([A-Za-z]+)(?:\s*,?\s*(\d{2,4}))?", t)
    if m:
        month = MONTH_MAP.get(m.group(2)[:3].lower())
        if month:
            day = int(m.group(1))
            year = int(m.group(3)) if m.group(3) else now.year
            try:
                dt = datetime(year, month, day, tzinfo=timezone.utc)
                if dt < now and not m.group(3):
                    dt = datetime(year + 1, month, day, tzinfo=timezone.utc)
                return dt
            except ValueError:
                return None

    return None


def parse_deadline(text: str) -> datetime | None:
    """Extract a deadline datetime from text. Returns None if no deadline found."""
    text_lower = text.lower()
    now = datetime.now(timezone.utc)
    has_deadline_word = any(
        kw in text_lower
        for kw in ("deadline", "due", "closes", "ends", "ending", "apply by",
                   "before", "until", "submission", "registrations close",
                   "entries close", "last day")
    )
    if not has_deadline_word:
        return None

    for pattern in DEADLINE_PATTERNS:
        for m in re.finditer(pattern, text, re.IGNORECASE):
            candidate = m.group(1).strip(" :,.\t\n")
            if not candidate or len(candidate) < 3:
                continue
            dt = _try_fixed_formats(candidate) or _parse_relative(candidate, now)
            if dt:
                if now - dt > timedelta(days=30):
                    return None
                return dt

    dt = _parse_relative(text, now)
    if dt and "deadline" in text_lower:
        return dt

    return None


def _event_type(text: str) -> str:
    t = text.lower()
    if any(kw in t for kw in HACKATHON_KEYWORDS):
        return "hackathon"
    if any(kw in t for kw in MEME_KEYWORDS):
        return "meme_contest"
    if any(kw in t for kw in VIDEO_KEYWORDS):
        return "video_contest"
    if any(kw in t for kw in GIVEAWAY_KEYWORDS):
        return "giveaway"
    return "contest"


def _extract_name(text: str, username: str) -> str:
    patterns = [
        r"(?:hackathon|meme contest|video contest|competition|challenge)\s*(?:for|in|on)?\s*([A-Z][A-Za-z0-9]+)",
        r"([A-Z][a-zA-Z0-9]+)\s*(?:hackathon|meme contest|video contest|competition|challenge)",
        r"(?:join|enter|participate in|win)\s+([A-Z][A-Za-z0-9 ]{1,30})",
    ]
    for pattern in patterns:
        m = re.search(pattern, text)
        if m:
            return m.group(1).strip()
    return f"{_event_type(text).replace('_', ' ')} by @{username}"


def _extract_url(text: str, username: str) -> str:
    url_match = re.search(r"https?://[^\s]+", text)
    if url_match:
        return url_match.group(0)
    return f"https://x.com/{username}"


def extract_event_from_tweet(
    event_tweet: str,
    username: str,
    engagement: dict | None = None,
) -> dict | None:
    """Extract hackathon/meme/video/giveaway event with deadline from a tweet."""
    if not event_tweet:
        return None

    ev_type = _event_type(event_tweet)
    deadline = parse_deadline(event_tweet)

    if not deadline:
        return None
    if deadline < datetime.now(timezone.utc):
        return None

    prizes_match = re.search(
        r"(?:prizes?|rewards?|prize pool|wins?|winning|bounty|pool)[^$\d]*(?:[$]([0-9][0-9,]*)|([0-9][0-9,]*)\s+(USDT|USD|ETH|SOL|BNB|TON|points))",
        event_tweet,
        re.IGNORECASE,
    )
    prizes = ""
    if prizes_match:
        if prizes_match.group(1):
            prizes = f"${prizes_match.group(1)}"
        elif prizes_match.group(2):
            prizes = f"{prizes_match.group(2)} {prizes_match.group(3)}"

    signals = []
    if ev_type == "hackathon":
        signals.append("hackathon")
    elif ev_type == "meme_contest":
        signals.append("meme contest")
    elif ev_type == "video_contest":
        signals.append("video contest")
    elif ev_type == "giveaway":
        signals.append("giveaway")
    if prizes:
        signals.append(f"prizes: {prizes}")
    signals.append(f"deadline: {deadline.strftime('%b %d')}")

    event = {
        "event_type": ev_type,
        "name": _extract_name(event_tweet, username),
        "username": username,
        "description": event_tweet[:300],
        "deadline": deadline.isoformat(),
        "days_left": round((deadline - datetime.now(timezone.utc)).total_seconds() / 86400, 1),
        "prizes": prizes,
        "url": _extract_url(event_tweet, username),
        "discovered_at": datetime.now(timezone.utc).isoformat(),
        "signals": signals,
        "tweet_text": event_tweet[:500],
        "followers": 0,
    }

    if ev_type == "giveaway":
        tier_result = classify_giveaway_engagement(engagement or {})
        event["engagement_tier"] = tier_result["tier"]
        event["likes"] = tier_result["metrics"]["likes"]
        event["retweets"] = tier_result["metrics"]["retweets"]
        event["replies"] = tier_result["metrics"]["replies"]
        if tier_result["tier"] != "none":
            event["signals"].append(f"giveaway ({tier_result['tier']} engagement)")
    elif engagement:
        event["engagement_tier"] = ""

    return event