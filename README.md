# Web3 Builder Scanner

Automated hourly scanner that finds Twitter accounts under 1,000 followers building real Web3 projects, scores them with AI, and sends qualified builders to Telegram.

## How It Works

1. **Discover** - Searches Twitter for builder signals (#buildinpublic, deploy keywords, etc.)
2. **Enrich** - Checks GitHub repos, on-chain deployments, and bio signals
3. **Score** - Deterministic weighted scoring + LLM judgment
4. **Notify** - Sends qualified builders (score >= 60) to your Telegram


## Rate Limits

- Twitter: ~3 searches per run, 3s delay between searches
- GitHub: 60 req/hr unauthenticated, 5000/hr with token
- Blockscout: No official limits
- Telegram: 30 messages/second to groups, 1/second to DMs
- OpenRouter: Depends on model (free tier: ~20 req/min)

