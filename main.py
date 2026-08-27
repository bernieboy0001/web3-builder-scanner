import asyncio
import logging
import os
import time
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask

from config import settings
from discovery.twitter import discover_builders
from enrichment.profile import extract_bio_signals
from enrichment.github import get_github_data
from enrichment.onchain import get_onchain_data
from scoring.signals import score_content
from scoring.llm_judge import llm_judge
from scoring.thresholds import compute_profile_score, compute_engagement_score, compute_final_score
from notification.telegram import send_telegram
from storage.database import (
    init_db, save_account, mark_notified, save_run, get_stats, is_notified,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def run_pipeline():
    start = time.time()
    logger.info("=== Web3 Builder Scanner - Starting run ===")

    await init_db()

    stats = await get_stats()
    logger.info(
        f"DB stats: {stats['total_accounts']} accounts, "
        f"{stats['qualified']} qualified, {stats['notified']} notified"
    )

    logger.info("Step 1: Discovering builder accounts from Twitter...")
    try:
        accounts = await discover_builders()
    except Exception as e:
        logger.error(f"Discovery failed: {e}")
        accounts = []

    logger.info(f"Found {len(accounts)} candidate accounts")

    qualified = 0
    notified = 0
    errors = 0

    for i, account in enumerate(accounts[: settings.max_accounts_per_run]):
        username = account["username"]
        logger.info(f"[{i+1}/{len(accounts)}] Processing @{username}...")

        try:
            logger.info(f"  Enriching @{username}...")
            bio_signals = extract_bio_signals(account.get("description", ""))

            github_data = None
            if bio_signals.get("has_github_link"):
                gh_url = bio_signals.get("github_url", "")
                gh_user = gh_url.split("github.com/")[-1].split("/")[0] if gh_url else username
                github_data = await get_github_data(gh_user)
                await asyncio.sleep(1)

            onchain_data = None
            if bio_signals.get("has_wallet") and bio_signals.get("wallet_address"):
                onchain_data = await get_onchain_data(bio_signals["wallet_address"])
                await asyncio.sleep(1)

            content_result = score_content(
                [account.get("sample_tweet", "")] if account.get("sample_tweet") else []
            )

            profile_result = compute_profile_score(bio_signals, account.get("followers", 0))
            engagement_result = compute_engagement_score(account)

            onchain_score_data = {"score": 0, "signals": []}
            if onchain_data and onchain_data.get("has_wallet"):
                oc_score = 0
                oc_signals = []
                if onchain_data.get("chain_count", 0) >= 2:
                    oc_score += 30
                    oc_signals.append(f"multi-chain ({onchain_data['chain_count']} chains)")
                elif onchain_data.get("chain_count", 0) == 1:
                    oc_score += 15
                    oc_signals.append("single chain active")
                if onchain_data.get("total_deploys", 0) > 0:
                    oc_score += 25
                    oc_signals.append(f"{onchain_data['total_deploys']} contract deploy(s)")
                if onchain_data.get("verification_rate", 0) > 0.5:
                    oc_score += 20
                    oc_signals.append("high verification rate")
                onchain_score_data = {"score": min(oc_score, 100), "signals": oc_signals}

            github_score_data = {"score": 0, "signals": []}
            if github_data and github_data.get("exists"):
                gh_score = 0
                gh_signals = []
                if github_data.get("web3_repos", 0) > 0:
                    gh_score += 30
                    gh_signals.append(f"{github_data['web3_repos']} Web3 repo(s)")
                if github_data.get("has_recent_commit"):
                    gh_score += 25
                    gh_signals.append("recent activity")
                if github_data.get("total_stars", 0) > 10:
                    gh_score += 15
                    gh_signals.append(f"{github_data['total_stars']} stars")
                if github_data.get("recent_prs", 0) > 0:
                    gh_score += 10
                    gh_signals.append(f"{github_data['recent_prs']} recent PR(s)")
                if github_data.get("public_repos", 0) > 0:
                    gh_score += 10
                    gh_signals.append(f"{github_data['public_repos']} public repos")
                github_score_data = {"score": min(gh_score, 100), "signals": gh_signals}

            account_enriched = {
                **account,
                "bio_signals": bio_signals,
                "github": github_data or {},
                "onchain": onchain_data or {},
                "content_score": content_result["score"],
            }

            logger.info(f"  Scoring @{username}...")
            llm_result = await llm_judge(account_enriched)
            await asyncio.sleep(1)

            final = compute_final_score(
                profile_result,
                content_result,
                engagement_result,
                onchain_score_data,
                github_score_data,
                llm_result,
            )

            save_data = {
                **account,
                "final_score": final["final_score"],
                "qualifies": final["qualifies"],
                "breakdown": final["breakdown"],
                "signals": final["signals"],
                "llm_score": llm_result.get("llm_score"),
                "llm_verdict": llm_result.get("llm_verdict"),
                "llm_reasoning": llm_result.get("llm_reasoning"),
                "github": github_data or {},
                "onchain": onchain_data or {},
            }
            await save_account(username, save_data)

            if final["qualifies"]:
                qualified += 1
                logger.info(
                    f"  QUALIFIED @{username}: {final['final_score']}/100 "
                    f"(signals: {', '.join(final['signals'][:3])})"
                )

                if not await is_notified(username):
                    sent = await send_telegram(save_data)
                    if sent:
                        await mark_notified(username)
                        notified += 1
            else:
                logger.info(
                    f"  Rejected @{username}: {final['final_score']}/100 "
                    f"(needed {final['threshold']})"
                )

        except Exception as e:
            errors += 1
            logger.error(f"  Error processing @{username}: {e}")

    duration = time.time() - start
    run_data = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "accounts_found": len(accounts),
        "accounts_qualified": qualified,
        "accounts_notified": notified,
        "errors": errors,
        "duration_seconds": round(duration, 1),
    }
    await save_run(run_data)

    logger.info(
        f"=== Run complete: {len(accounts)} found, {qualified} qualified, "
        f"{notified} notified, {errors} errors, {duration:.1f}s ==="
    )
    return run_data


def scheduled_run():
    asyncio.run(run_pipeline())


def create_app():
    from web import app
    return app


def main():
    asyncio.run(init_db())

    scheduler = BackgroundScheduler()
    scheduler.add_job(scheduled_run, "interval", hours=1, id="scanner")
    scheduler.start()
    logger.info("Scheduler started - will run every hour")

    app = create_app()
    port = int(os.environ.get("PORT", 5000))
    logger.info(f"Web dashboard starting on port {port}")
    app.run(host="0.0.0.0", port=port, debug=False)


if __name__ == "__main__":
    main()
