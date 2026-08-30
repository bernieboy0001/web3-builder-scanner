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
    project_type TEXT,
    is_launch INTEGER DEFAULT 0,
    is_existing INTEGER DEFAULT 0,
    is_hiring INTEGER DEFAULT 0
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
    events_found INTEGER DEFAULT 0,
    events_notified INTEGER DEFAULT 0,
    errors INTEGER,
    duration_seconds REAL
);

CREATE TABLE IF NOT EXISTS errors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT,
    message TEXT,
    timestamp TEXT
);

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT,
    name TEXT,
    username TEXT,
    description TEXT,
    deadline TEXT,
    days_left REAL,
    prizes TEXT,
    url TEXT,
    followers INTEGER DEFAULT 0,
    discovered_at TEXT,
    signals TEXT,
    tweet_text TEXT,
    notified INTEGER DEFAULT 0,
    likes INTEGER DEFAULT 0,
    retweets INTEGER DEFAULT 0,
    replies INTEGER DEFAULT 0,
    engagement_tier TEXT DEFAULT '',
    UNIQUE(name, username, deadline)
);

CREATE TABLE IF NOT EXISTS app_settings (
    key TEXT PRIMARY KEY,
    value TEXT
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
            ("is_launch", "INTEGER DEFAULT 0"),
            ("is_existing", "INTEGER DEFAULT 0"),
            ("is_hiring", "INTEGER DEFAULT 0"),
        ]:
            try:
                await db.execute(f"ALTER TABLE accounts ADD COLUMN {col} {typ}")
            except Exception:
                pass
        try:
            await db.execute("ALTER TABLE runs ADD COLUMN projects_found INTEGER DEFAULT 0")
        except Exception:
            pass
        try:
            await db.execute("ALTER TABLE runs ADD COLUMN events_found INTEGER DEFAULT 0")
        except Exception:
            pass
        try:
            await db.execute("ALTER TABLE runs ADD COLUMN events_notified INTEGER DEFAULT 0")
        except Exception:
            pass
        for col, typ in [
            ("likes", "INTEGER DEFAULT 0"),
            ("retweets", "INTEGER DEFAULT 0"),
            ("replies", "INTEGER DEFAULT 0"),
            ("engagement_tier", "TEXT DEFAULT ''"),
        ]:
            try:
                await db.execute(f"ALTER TABLE events ADD COLUMN {col} {typ}")
            except Exception:
                pass
        await db.execute("INSERT OR IGNORE INTO app_settings (key, value) VALUES ('telegram_enabled', '1')")
        await db.commit()
        logger.info("Database initialized")


async def log_error(username: str, message: str):
    from datetime import datetime, timezone

    try:
        async with aiosqlite.connect(settings.db_path) as db:
            await db.execute(
                "INSERT INTO errors (username, message, timestamp) VALUES (?, ?, ?)",
                (username, message[:500], datetime.now(timezone.utc).isoformat()),
            )
            await db.commit()
    except Exception:
        pass


async def account_exists(username: str) -> bool:
    async with aiosqlite.connect(settings.db_path) as db:
        cursor = await db.execute(
            "SELECT 1 FROM accounts WHERE username = ?", (username,)
        )
        return await cursor.fetchone() is not None


async def event_exists(name: str, username: str, deadline: str) -> bool:
    async with aiosqlite.connect(settings.db_path) as db:
        cursor = await db.execute(
            "SELECT 1 FROM events WHERE name = ? AND username = ? AND deadline = ?",
            (name, username, deadline),
        )
        return await cursor.fetchone() is not None


async def get_setting(key: str, default: str | None = None) -> str | None:
    async with aiosqlite.connect(settings.db_path) as db:
        cursor = await db.execute(
            "SELECT value FROM app_settings WHERE key = ?", (key,)
        )
        row = await cursor.fetchone()
    return row[0] if row else default


async def set_setting(key: str, value: str):
    async with aiosqlite.connect(settings.db_path) as db:
        await db.execute(
            "INSERT OR REPLACE INTO app_settings (key, value) VALUES (?, ?)",
            (key, value),
        )
        await db.commit()


async def save_account(username: str, data: dict):
    import json

    async with aiosqlite.connect(settings.db_path) as db:
        await db.execute(
            """INSERT INTO accounts
            (username, name, description, followers, discovered_at, first_seen, last_seen,
             final_score, qualifies, notified, profile_score, content_score,
             engagement_score, onchain_score, github_score, llm_score, llm_verdict,
             signals, github_data, onchain_data, discovered_via,
             has_website, project_url, project_name, project_description, project_chain, project_type,
             is_launch, is_existing, is_hiring)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(username) DO UPDATE SET
                name=excluded.name, description=excluded.description,
                followers=excluded.followers, last_seen=excluded.last_seen,
                final_score=excluded.final_score, qualifies=excluded.qualifies,
                profile_score=excluded.profile_score, content_score=excluded.content_score,
                engagement_score=excluded.engagement_score, onchain_score=excluded.onchain_score,
                github_score=excluded.github_score, llm_score=excluded.llm_score,
                llm_verdict=excluded.llm_verdict, signals=excluded.signals,
                github_data=excluded.github_data, onchain_data=excluded.onchain_data,
                discovered_via=excluded.discovered_via, has_website=excluded.has_website,
                project_url=excluded.project_url, project_name=excluded.project_name,
                project_description=excluded.project_description, project_chain=excluded.project_chain,
                project_type=excluded.project_type, is_launch=excluded.is_launch,
                is_existing=excluded.is_existing, is_hiring=excluded.is_hiring,
                notified=accounts.notified, first_seen=accounts.first_seen""",
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
                1 if data.get("is_launch") else 0,
                1 if data.get("is_existing") else 0,
                1 if data.get("is_hiring") else 0,
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


async def save_event(event: dict):
    import json

    async with aiosqlite.connect(settings.db_path) as db:
        await db.execute(
            """INSERT OR IGNORE INTO events
            (event_type, name, username, description, deadline, days_left,
             prizes, url, followers, discovered_at, signals, tweet_text, notified,
             likes, retweets, replies, engagement_tier)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                event.get("event_type", ""),
                event.get("name", ""),
                event.get("username", ""),
                event.get("description", ""),
                event.get("deadline", ""),
                event.get("days_left", 0),
                event.get("prizes", ""),
                event.get("url", ""),
                event.get("followers", 0),
                event.get("discovered_at", ""),
                json.dumps(event.get("signals", [])),
                event.get("tweet_text", ""),
                1 if event.get("notified") else 0,
                event.get("likes", 0),
                event.get("retweets", 0),
                event.get("replies", 0),
                event.get("engagement_tier", ""),
            ),
        )
        await db.commit()


async def mark_event_notified(event_id: int):
    async with aiosqlite.connect(settings.db_path) as db:
        await db.execute(
            "UPDATE events SET notified = 1 WHERE id = ?", (event_id,)
        )
        await db.commit()


async def get_upcoming_events() -> list[tuple]:
    from datetime import datetime, timezone

    async with aiosqlite.connect(settings.db_path) as db:
        cursor = await db.execute(
            """SELECT id, event_type, name, username, deadline, days_left, prizes, url,
            engagement_tier, likes, retweets, replies
            FROM events WHERE deadline > ? AND notified = 0 ORDER BY deadline ASC""",
            (datetime.now(timezone.utc).isoformat(),),
        )
        rows = await cursor.fetchall()
        return [tuple(row) for row in rows]


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
            accounts_notified, projects_found, events_found, events_notified, errors, duration_seconds)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                run_data.get("timestamp", ""),
                run_data.get("accounts_found", 0),
                run_data.get("accounts_qualified", 0),
                run_data.get("accounts_notified", 0),
                run_data.get("projects_found", 0),
                run_data.get("events_found", 0),
                run_data.get("events_notified", 0),
                run_data.get("errors", 0),
                run_data.get("duration_seconds", 0),
            ),
        )
        await db.commit()


async def get_stats() -> dict:
    from datetime import datetime, timezone

    async with aiosqlite.connect(settings.db_path) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM accounts")
        total = (await cursor.fetchone())[0]

        cursor = await db.execute("SELECT COUNT(*) FROM accounts WHERE qualifies = 1")
        qualified = (await cursor.fetchone())[0]

        cursor = await db.execute("SELECT COUNT(*) FROM accounts WHERE notified = 1")
        notified = (await cursor.fetchone())[0]

        cursor = await db.execute("SELECT COUNT(*) FROM projects")
        projects = (await cursor.fetchone())[0]

        cursor = await db.execute(
            "SELECT COUNT(*) FROM events WHERE deadline > ?",
            (datetime.now(timezone.utc).isoformat(),),
        )
        events_upcoming = (await cursor.fetchone())[0]

        cursor = await db.execute(
            "SELECT COUNT(*) FROM events WHERE event_type = 'hackathon' AND deadline > ?",
            (datetime.now(timezone.utc).isoformat(),),
        )
        hackathons = (await cursor.fetchone())[0]

        cursor = await db.execute(
            "SELECT timestamp FROM runs ORDER BY id DESC LIMIT 1"
        )
        row = await cursor.fetchone()
        last_run = row[0] if row else "never"

        return {
            "total_accounts": total,
            "qualified": qualified,
            "notified": notified,
            "projects": projects,
            "events_upcoming": events_upcoming,
            "hackathons": hackathons,
            "last_run": last_run,
        }
