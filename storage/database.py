import aiosqlite
import logging

from config import settings

logger = logging.getLogger(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS accounts (
    username TEXT PRIMARY KEY,
    name TEXT,
    description TEXT,
    followers INTEGER,
    discovered_at TEXT,
    first_seen TEXT,
    last_seen TEXT,
    final_score REAL,
    qualifies INTEGER,
    notified INTEGER DEFAULT 0,
    profile_score REAL DEFAULT 0,
    content_score REAL DEFAULT 0,
    engagement_score REAL DEFAULT 0,
    onchain_score REAL DEFAULT 0,
    github_score REAL DEFAULT 0,
    llm_score REAL,
    llm_verdict TEXT,
    signals TEXT,
    github_data TEXT,
    onchain_data TEXT,
    discovered_via TEXT,
    has_website INTEGER DEFAULT 0,
    project_url TEXT,
    project_name TEXT,
    project_description TEXT,
    project_chain TEXT,
    project_type TEXT
);

CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    username TEXT,
    description TEXT,
    chain TEXT,
    project_type TEXT,
    url TEXT,
    github_url TEXT,
    contract_address TEXT,
    discovered_at TEXT,
    score REAL,
    signals TEXT,
    notified INTEGER DEFAULT 0,
    tweet_text TEXT,
    UNIQUE(name, username)
);

CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT,
    accounts_found INTEGER,
    accounts_qualified INTEGER,
    accounts_notified INTEGER,
    projects_found INTEGER DEFAULT 0,
    errors INTEGER,
    duration_seconds REAL
);
"""


async def init_db():
    async with aiosqlite.connect(settings.db_path) as db:
        await db.executescript(SCHEMA)
        for col, typ in [
            ("has_website", "INTEGER DEFAULT 0"),
            ("project_url", "TEXT"),
            ("project_name", "TEXT"),
            ("project_description", "TEXT"),
            ("project_chain", "TEXT"),
            ("project_type", "TEXT"),
        ]:
            try:
                await db.execute(f"ALTER TABLE accounts ADD COLUMN {col} {typ}")
            except Exception:
                pass
        try:
            await db.execute("ALTER TABLE runs ADD COLUMN projects_found INTEGER DEFAULT 0")
        except Exception:
            pass
        await db.commit()
        logger.info("Database initialized")


async def account_exists(username: str) -> bool:
    async with aiosqlite.connect(settings.db_path) as db:
        cursor = await db.execute(
            "SELECT 1 FROM accounts WHERE username = ?", (username,)
        )
        return await cursor.fetchone() is not None


async def save_account(username: str, data: dict):
    import json

    async with aiosqlite.connect(settings.db_path) as db:
        await db.execute(
            """INSERT OR REPLACE INTO accounts
            (username, name, description, followers, discovered_at, first_seen, last_seen,
             final_score, qualifies, notified, profile_score, content_score,
             engagement_score, onchain_score, github_score, llm_score, llm_verdict,
             signals, github_data, onchain_data, discovered_via,
             has_website, project_url, project_name, project_description, project_chain, project_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                username,
                data.get("name", ""),
                data.get("description", ""),
                data.get("followers", 0),
                data.get("discovered_at", ""),
                data.get("first_seen", data.get("discovered_at", "")),
                data.get("last_seen", data.get("discovered_at", "")),
                data.get("final_score", 0),
                1 if data.get("qualifies") else 0,
                1 if data.get("notified") else 0,
                data.get("breakdown", {}).get("profile", 0),
                data.get("breakdown", {}).get("content", 0),
                data.get("breakdown", {}).get("engagement", 0),
                data.get("breakdown", {}).get("onchain", 0),
                data.get("breakdown", {}).get("github", 0),
                data.get("llm_score"),
                data.get("llm_verdict", ""),
                json.dumps(data.get("signals", [])),
                json.dumps(data.get("github", {})),
                json.dumps(data.get("onchain", {})),
                data.get("discovered_via", ""),
                1 if data.get("has_website") else 0,
                data.get("project_url", ""),
                data.get("project_name", ""),
                data.get("project_description", ""),
                data.get("project_chain", ""),
                data.get("project_type", ""),
            ),
        )
        await db.commit()


async def save_project(project: dict):
    import json

    async with aiosqlite.connect(settings.db_path) as db:
        await db.execute(
            """INSERT OR IGNORE INTO projects
            (name, username, description, chain, project_type, url, github_url,
             contract_address, discovered_at, score, signals, notified, tweet_text)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                project.get("name", ""),
                project.get("username", ""),
                project.get("description", ""),
                project.get("chain", ""),
                project.get("project_type", ""),
                project.get("url", ""),
                project.get("github_url", ""),
                project.get("contract_address", ""),
                project.get("discovered_at", ""),
                project.get("score", 0),
                json.dumps(project.get("signals", [])),
                1 if project.get("notified") else 0,
                project.get("tweet_text", ""),
            ),
        )
        await db.commit()


async def mark_notified(username: str):
    async with aiosqlite.connect(settings.db_path) as db:
        await db.execute(
            "UPDATE accounts SET notified = 1 WHERE username = ?", (username,)
        )
        await db.commit()


async def is_notified(username: str) -> bool:
    async with aiosqlite.connect(settings.db_path) as db:
        cursor = await db.execute(
            "SELECT notified FROM accounts WHERE username = ?", (username,)
        )
        row = await cursor.fetchone()
        return row is not None and row[0] == 1


async def get_unnotified_qualified() -> list[dict]:
    import json

    async with aiosqlite.connect(settings.db_path) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM accounts WHERE qualifies = 1 AND notified = 0 ORDER BY final_score DESC"
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def save_run(run_data: dict):
    async with aiosqlite.connect(settings.db_path) as db:
        await db.execute(
            """INSERT INTO runs (timestamp, accounts_found, accounts_qualified,
            accounts_notified, projects_found, errors, duration_seconds)
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                run_data.get("timestamp", ""),
                run_data.get("accounts_found", 0),
                run_data.get("accounts_qualified", 0),
                run_data.get("accounts_notified", 0),
                run_data.get("projects_found", 0),
                run_data.get("errors", 0),
                run_data.get("duration_seconds", 0),
            ),
        )
        await db.commit()


async def get_stats() -> dict:
    async with aiosqlite.connect(settings.db_path) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM accounts")
        total = (await cursor.fetchone())[0]

        cursor = await db.execute("SELECT COUNT(*) FROM accounts WHERE qualifies = 1")
        qualified = (await cursor.fetchone())[0]

        cursor = await db.execute("SELECT COUNT(*) FROM accounts WHERE notified = 1")
        notified = (await cursor.fetchone())[0]

        cursor = await db.execute(
            "SELECT timestamp FROM runs ORDER BY id DESC LIMIT 1"
        )
        row = await cursor.fetchone()
        last_run = row[0] if row else "never"

        return {
            "total_accounts": total,
            "qualified": qualified,
            "notified": notified,
            "last_run": last_run,
        }
