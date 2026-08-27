# Web3 Builder Scanner

Automated hourly scanner that finds Twitter accounts under 1,000 followers building real Web3 projects, scores them with AI, and sends qualified builders to Telegram.

## How It Works

1. **Discover** - Searches Twitter for builder signals (#buildinpublic, deploy keywords, etc.)
2. **Enrich** - Checks GitHub repos, on-chain deployments, and bio signals
3. **Score** - Deterministic weighted scoring + LLM judgment
4. **Notify** - Sends qualified builders (score >= 60) to your Telegram

## Setup

### 1. Twitter Cookies (Required)

You need a disposable Twitter/X account for scraping.

1. Create a throwaway X account (or use an existing one)
2. Install the **EditThisCookie** browser extension
3. Log into X/Twitter in your browser
4. Click EditThisCookie icon -> Export -> copy the JSON
5. Save as `cookies.json` in the project root

**Important:** Use a disposable account. There's a small risk of account suspension.

### 2. Telegram Bot (Required)

1. Open Telegram and message **@BotFather**
2. Send `/newbot`
3. Name your bot (e.g., "Web3 Builder Scanner")
4. Choose a username (must end in `bot`)
5. Copy the **bot token** from BotFather's response
6. Message your new bot (send `/start`)
7. Get your chat ID:
   - Message `@userinfobot` or `@getmyid_bot`
   - Copy your **Chat ID**
8. Set both in `.env`:
   ```
   TELEGRAM_BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
   TELEGRAM_CHAT_ID=987654321
   ```

### 3. OpenRouter (Required for AI Scoring)

1. Go to [openrouter.ai](https://openrouter.ai)
2. Sign up (free)
3. Create an API key
4. Free models available: `deepseek/deepseek-chat:free`
5. Set in `.env`:
   ```
   OPENROUTER_API_KEY=sk-or-v1-...
   OPENROUTER_MODEL=deepseek/deepseek-chat:free
   ```

**Note:** The scanner works without OpenRouter but scoring quality drops. Without it, only deterministic signals are used.

### 4. GitHub Token (Optional)

Increases rate limit from 60 to 5,000 requests/hour.

1. Go to GitHub Settings -> Developer settings -> Personal access tokens
2. Create a classic token with `public_repo` scope
3. Set `GITHUB_TOKEN=ghp_...` in `.env`

### 5. Environment Variables

Copy `.env.example` to `.env` and fill in:

```bash
cp .env.example .env
```

### 6. Run Locally

```bash
pip install -r requirements.txt
python main.py
```

### 7. Deploy to Render (Free)

1. Push this repo to GitHub
2. Go to [render.com](https://render.com) -> New -> Cron Job
3. Connect your GitHub repo
4. Set schedule: `0 * * * *` (every hour)
5. Set build command: `pip install -r requirements.txt`
6. Set start command: `python main.py`
7. Add environment variables from your `.env`
8. Deploy

**Render free tier:** 750 hours/month. Hourly runs use ~12 hours/month.

## Architecture

```
main.py (orchestrator)
  -> discovery/twitter.py    (twifork - X GraphQL scraping)
  -> enrichment/
      -> profile.py          (bio signal extraction)
      -> github.py           (GitHub API - repos, commits, languages)
      -> onchain.py          (Blockscout API - deployments, verification)
  -> scoring/
      -> signals.py          (deterministic tweet content scoring)
      -> thresholds.py       (weighted scoring engine)
      -> llm_judge.py        (OpenRouter LLM verdict)
  -> notification/telegram.py (Telegram Bot API)
  -> storage/database.py     (SQLite persistence)
```

## Scoring System

| Category | Weight | What It Checks |
|----------|--------|----------------|
| Profile | 10% | GitHub link, wallet/ENS, tech keywords in bio |
| Content | 25% | Code snippets, deploy threads, repo links in tweets |
| Engagement | 15% | Reply quality, follow ratio, community presence |
| On-Chain | 30% | Contract deployments, verification, multi-chain |
| GitHub | 20% | Web3 repos, recent commits, stars |
| LLM Judge | 40% | AI verdict on genuine building (bonus/penalty) |

Accounts scoring >= 60/100 qualify for Telegram notification.

## Customization

Edit `scoring/thresholds.py` to adjust:
- `QUALIFYING_THRESHOLD` - minimum score to qualify (default: 60)
- Category weights
- Signal detection logic

Edit `discovery/twitter.py` to adjust:
- `SEARCH_QUERIES` - search terms
- `MAX_FOLLOWERS` - follower cap (default: 1000)
- `MIN_ACCOUNT_AGE_DAYS` - minimum account age (default: 90)

## State

SQLite database (`scanner.db`) tracks:
- All discovered accounts with scores
- Which accounts have been notified
- Run history with timing

## Rate Limits

- Twitter: ~3 searches per run, 3s delay between searches
- GitHub: 60 req/hr unauthenticated, 5000/hr with token
- Blockscout: No official limits
- Telegram: 30 messages/second to groups, 1/second to DMs
- OpenRouter: Depends on model (free tier: ~20 req/min)

## Troubleshooting

**"Cookies file not found"** - Export cookies from your browser using EditThisCookie extension.

**"OpenRouter 401"** - Check your API key is valid at openrouter.ai/keys.

**"Telegram send failed"** - Make sure you've messaged your bot first (/start), and the chat ID is correct.

**No accounts found** - Twitter search queries may need updating. Check the queries in `discovery/twitter.py`.
