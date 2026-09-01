from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    twitter_cookies_path: str = "cookies.json"
    openrouter_api_key: str = ""
    openrouter_model: str = "nvidia/nemotron-3-ultra-550b-a55b:free"
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    score_threshold: int = 60
    max_accounts_per_run: int = 50
    search_tweets_per_query: int = 40
    search_max_pages: int = 2
    event_max_pages: int = 3
    github_token: str = ""
    db_path: str = "scanner.db"
    llm_min_score: int = 35

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
