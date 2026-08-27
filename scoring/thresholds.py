PROFILE_WEIGHT = 0.10
CONTENT_WEIGHT = 0.25
ENGAGEMENT_WEIGHT = 0.15
ONCHAIN_WEIGHT = 0.30
GITHUB_WEIGHT = 0.20
LLM_BONUS_WEIGHT = 0.40

QUALIFYING_THRESHOLD = 60


def compute_profile_score(bio_signals: dict, followers: int) -> dict:
    score = 0
    signals = []

    if bio_signals.get("has_github_link"):
        score += 25
        signals.append("GitHub link in bio")
    if bio_signals.get("has_wallet") or bio_signals.get("has_ens"):
        score += 20
        signals.append("Wallet/ENS in bio")
    if bio_signals.get("has_farcaster"):
        score += 10
        signals.append("Farcaster presence")
    if bio_signals.get("tech_keyword_count", 0) >= 3:
        score += 25
        signals.append(f"{bio_signals['tech_keyword_count']} tech keywords")
    elif bio_signals.get("tech_keyword_count", 0) >= 1:
        score += 15
        signals.append(f"{bio_signals['tech_keyword_count']} tech keyword(s)")

    if 100 <= followers <= 500:
        score += 10
        signals.append("sweet spot followers (100-500)")
    elif 50 < followers < 100:
        score += 5
        signals.append("very small audience")

    return {"score": min(score, 100), "signals": signals}


def compute_engagement_score(account: dict) -> dict:
    score = 50
    signals = ["baseline engagement"]

    bio = (account.get("description") or "").lower()
    if "dm" in bio or "open to" in bio:
        score += 10
        signals.append("DMs open")

    followers = account.get("followers", 0)
    following = account.get("following", 0)
    if followers > 0 and following > 0:
        ratio = followers / following
        if 0.5 < ratio < 5:
            score += 15
            signals.append("healthy follow ratio")
        elif ratio > 10:
            score += 5
            signals.append("high follow ratio")

    return {"score": min(score, 100), "signals": signals}


def compute_final_score(
    profile: dict,
    content: dict,
    engagement: dict,
    onchain: dict,
    github: dict,
    llm: dict,
) -> dict:
    profile_s = profile["score"] * PROFILE_WEIGHT
    content_s = content["score"] * CONTENT_WEIGHT
    engagement_s = engagement["score"] * ENGAGEMENT_WEIGHT
    onchain_s = onchain["score"] * ONCHAIN_WEIGHT
    github_s = github["score"] * GITHUB_WEIGHT

    deterministic = profile_s + content_s + engagement_s + onchain_s + github_s

    llm_bonus = 0
    if llm.get("llm_score") is not None:
        llm_normalized = llm["llm_score"] * LLM_BONUS_WEIGHT
        llm_bonus = llm_normalized - (50 * LLM_BONUS_WEIGHT)
        deterministic += llm_bonus

    final = min(max(deterministic, 0), 100)
    qualifies = final >= QUALIFYING_THRESHOLD

    all_signals = []
    for s in [profile, content, engagement, onchain, github]:
        all_signals.extend(s.get("signals", []))

    return {
        "final_score": round(final, 1),
        "qualifies": qualifies,
        "breakdown": {
            "profile": round(profile_s, 1),
            "content": round(content_s, 1),
            "engagement": round(engagement_s, 1),
            "onchain": round(onchain_s, 1),
            "github": round(github_s, 1),
            "llm_bonus": round(llm_bonus, 1),
        },
        "signals": all_signals,
        "threshold": QUALIFYING_THRESHOLD,
    }
