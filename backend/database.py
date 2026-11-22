from datetime import datetime, timezone
import os
from pathlib import Path
import sqlite3

_BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.getenv("DATA_DIR", "").strip() or _BASE_DIR)
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "app.db"
MANAGED_SETTING_KEYS = (
    "GEMINI_API_KEY",
    "GEMINI_MODEL",
    "ELEVENLABS_API_KEY",
    "ELEVENLABS_VOICE_ID",
)


def get_connection() -> sqlite3.Connection:
    """Open a SQLite connection to app.db with row access by column name."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create database tables if missing and seed the default admin user."""
    conn = get_connection()
    try:
        with conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    access_key TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    expires_at TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS video_chunks (
                    video_id TEXT NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    start_sec REAL NOT NULL,
                    end_sec REAL NOT NULL,
                    raw_json TEXT NOT NULL,
                    prev_context TEXT,
                    PRIMARY KEY (video_id, chunk_index)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS audio_cache (
                    video_id TEXT NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    voice TEXT NOT NULL,
                    audio_url TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (video_id, chunk_index, voice)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS vip_usage (
                    access_key TEXT NOT NULL,
                    usage_date TEXT NOT NULL,
                    count INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY (access_key, usage_date)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS app_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS api_usage (
                    usage_date TEXT PRIMARY KEY,
                    gemini_calls INTEGER NOT NULL DEFAULT 0,
                    gemini_tokens INTEGER NOT NULL DEFAULT 0
                )
                """
            )
            # Eski bazalar uchun migratsiya: VIP va admin ustunlarini qo'shish
            existing_cols = {row[1] for row in conn.execute("PRAGMA table_info(users)")}
            if "allow_vip" not in existing_cols:
                conn.execute(
                    "ALTER TABLE users ADD COLUMN allow_vip INTEGER NOT NULL DEFAULT 0"
                )
            if "vip_daily_limit" not in existing_cols:
                conn.execute(
                    "ALTER TABLE users ADD COLUMN vip_daily_limit INTEGER NOT NULL DEFAULT 0"
                )
            if "is_admin" not in existing_cols:
                conn.execute(
                    "ALTER TABLE users ADD COLUMN is_admin INTEGER NOT NULL DEFAULT 0"
                )
            if "bound_device_id" not in existing_cols:
                conn.execute(
                    "ALTER TABLE users ADD COLUMN bound_device_id TEXT"
                )
            conn.execute(
                """
                INSERT OR IGNORE INTO users (access_key, name, is_active, expires_at)
                VALUES ('ADMIN-1234', 'Admin', 1, NULL)
                """
            )
            # Admin har doim VIP va admin huquqiga ega
            conn.execute(
                """
                UPDATE users
                SET allow_vip = 1,
                    vip_daily_limit = CASE WHEN vip_daily_limit = 0 THEN 1000 ELSE vip_daily_limit END,
                    is_admin = 1
                WHERE access_key = 'ADMIN-1234'
                """
            )
            conn.commit()
    finally:
        conn.close()


def get_user_by_key(access_key: str) -> sqlite3.Row | None:
    """Fetch a user row by access key, or return None if not found."""
    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            SELECT access_key, name, is_active, expires_at, allow_vip, vip_daily_limit, is_admin, bound_device_id
            FROM users WHERE access_key = ?
            """,
            (access_key,),
        )
        return cursor.fetchone()
    finally:
        conn.close()


def bind_user_device(access_key: str, device_id: str) -> bool:
    """Bind access_key to device_id if unbound or already bound to the same device."""
    conn = get_connection()
    try:
        with conn:
            cur = conn.execute(
                """
                UPDATE users SET bound_device_id = ?
                WHERE access_key = ?
                  AND (bound_device_id IS NULL OR bound_device_id = '' OR bound_device_id = ?)
                """,
                (device_id, access_key, device_id),
            )
            conn.commit()
            return cur.rowcount == 1
    finally:
        conn.close()


def load_settings_to_env() -> None:
    """Apply settings stored in SQLite app_settings onto os.environ."""
    conn = get_connection()
    try:
        rows = conn.execute("SELECT key, value FROM app_settings").fetchall()
        for row in rows:
            if row["key"] in MANAGED_SETTING_KEYS:
                os.environ[row["key"]] = row["value"]
    finally:
        conn.close()


def get_settings_dict() -> dict[str, str]:
    """Return effective settings (DB overrides .env/environment)."""
    result = {k: os.getenv(k, "").strip() for k in MANAGED_SETTING_KEYS}
    conn = get_connection()
    try:
        for row in conn.execute("SELECT key, value FROM app_settings").fetchall():
            if row["key"] in MANAGED_SETTING_KEYS:
                result[row["key"]] = row["value"]
    finally:
        conn.close()
    return result


def save_settings_dict(updates: dict[str, str]) -> dict[str, str]:
    """Persist managed API settings to SQLite and apply immediately to os.environ."""
    conn = get_connection()
    try:
        with conn:
            for key, value in updates.items():
                if key not in MANAGED_SETTING_KEYS:
                    continue
                cleaned = value.strip()
                conn.execute(
                    """
                    INSERT INTO app_settings (key, value, updated_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(key) DO UPDATE SET
                        value = excluded.value,
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    (key, cleaned),
                )
                os.environ[key] = cleaned
            conn.commit()
    finally:
        conn.close()
    return get_settings_dict()


def list_all_users() -> list[dict]:
    """Return all users along with today's VIP usage count."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT u.access_key, u.name, u.is_active, u.expires_at,
                   u.allow_vip, u.vip_daily_limit, u.is_admin, u.bound_device_id,
                   COALESCE(v.count, 0) AS vip_used_today
            FROM users u
            LEFT JOIN vip_usage v
                ON v.access_key = u.access_key AND v.usage_date = ?
            ORDER BY u.is_admin DESC, u.name ASC
            """,
            (today,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def create_user_record(
    access_key: str,
    name: str,
    expires_at: str | None,
    allow_vip: bool,
    vip_daily_limit: int,
) -> dict:
    """Insert a new subscriber into users."""
    conn = get_connection()
    try:
        with conn:
            conn.execute(
                """
                INSERT INTO users (access_key, name, is_active, expires_at, allow_vip, vip_daily_limit, is_admin)
                VALUES (?, ?, 1, ?, ?, ?, 0)
                """,
                (access_key, name, expires_at, 1 if allow_vip else 0, vip_daily_limit),
            )
            conn.commit()
    finally:
        conn.close()
    row = get_user_by_key(access_key)
    return dict(row) if row else {}


def update_user_record(
    access_key: str,
    is_active: bool | None = None,
    allow_vip: bool | None = None,
    vip_daily_limit: int | None = None,
    expires_at: str | None = "__KEEP__",
    reset_device: bool = False,
) -> dict | None:
    """Update subscriber fields and return updated row or None if missing."""
    existing = get_user_by_key(access_key)
    if existing is None:
        return None
    fields: list[str] = []
    params: list[object] = []
    if is_active is not None:
        fields.append("is_active = ?")
        params.append(1 if is_active else 0)
    if allow_vip is not None:
        fields.append("allow_vip = ?")
        params.append(1 if allow_vip else 0)
    if vip_daily_limit is not None:
        fields.append("vip_daily_limit = ?")
        params.append(max(0, int(vip_daily_limit)))
    if expires_at != "__KEEP__":
        fields.append("expires_at = ?")
        params.append(expires_at)
    if reset_device:
        fields.append("bound_device_id = NULL")
    if not fields:
        return dict(existing)
    params.append(access_key)
    conn = get_connection()
    try:
        with conn:
            conn.execute(f"UPDATE users SET {', '.join(fields)} WHERE access_key = ?", params)
            conn.commit()
    finally:
        conn.close()
    row = get_user_by_key(access_key)
    return dict(row) if row else None


def delete_user_record(access_key: str) -> bool:
    """Delete a non-admin user by access_key."""
    conn = get_connection()
    try:
        with conn:
            cur = conn.execute(
                "DELETE FROM users WHERE access_key = ? AND is_admin = 0",
                (access_key,),
            )
            conn.commit()
            return cur.rowcount > 0
    finally:
        conn.close()


def change_access_key(old_key: str, new_key: str) -> str:
    """Change a user's access_key (and update vip_usage) atomically."""
    cleaned = new_key.strip()
    if len(cleaned) < 6:
        raise ValueError("Yangi parol kamida 6 ta belgidan iborat bo'lishi kerak")
    if cleaned == old_key:
        return cleaned

    conn = get_connection()
    try:
        with conn:
            exists = conn.execute(
                "SELECT 1 FROM users WHERE access_key = ?", (cleaned,)
            ).fetchone()
            if exists:
                raise ValueError("Bu parol band, boshqa parol tanlang")
            cur = conn.execute(
                "UPDATE users SET access_key = ? WHERE access_key = ?",
                (cleaned, old_key),
            )
            if cur.rowcount == 0:
                raise ValueError("Foydalanuvchi topilmadi")
            conn.execute(
                "UPDATE vip_usage SET access_key = ? WHERE access_key = ?",
                (cleaned, old_key),
            )
            conn.commit()
            return cleaned
    finally:
        conn.close()


def record_gemini_usage(tokens: int = 0) -> None:
    """Increment today's Gemini request and token counters."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    conn = get_connection()
    try:
        with conn:
            conn.execute(
                """
                INSERT INTO api_usage (usage_date, gemini_calls, gemini_tokens)
                VALUES (?, 1, ?)
                ON CONFLICT(usage_date) DO UPDATE SET
                    gemini_calls = gemini_calls + 1,
                    gemini_tokens = gemini_tokens + excluded.gemini_tokens
                """,
                (today, max(0, int(tokens))),
            )
            conn.commit()
    finally:
        conn.close()


def get_gemini_usage_summary() -> dict:
    """Return today's and all-time Gemini usage recorded by this backend."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    conn = get_connection()
    try:
        t_row = conn.execute(
            "SELECT gemini_calls, gemini_tokens FROM api_usage WHERE usage_date = ?",
            (today,),
        ).fetchone()
        a_row = conn.execute(
            "SELECT COALESCE(SUM(gemini_calls), 0) AS calls, COALESCE(SUM(gemini_tokens), 0) AS tokens FROM api_usage"
        ).fetchone()
        return {
            "today_calls": int(t_row["gemini_calls"]) if t_row else 0,
            "today_tokens": int(t_row["gemini_tokens"]) if t_row else 0,
            "total_calls": int(a_row["calls"]) if a_row else 0,
            "total_tokens": int(a_row["tokens"]) if a_row else 0,
        }
    finally:
        conn.close()


def reserve_vip_usage(access_key: str, daily_limit: int) -> bool:
    """Atomik ravishda bugungi VIP hisobini oshiradi; limit tugagan bo'lsa False qaytaradi."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    conn = get_connection()
    try:
        with conn:
            conn.execute(
                "INSERT OR IGNORE INTO vip_usage (access_key, usage_date, count) VALUES (?, ?, 0)",
                (access_key, today),
            )
            cursor = conn.execute(
                """
                UPDATE vip_usage SET count = count + 1
                WHERE access_key = ? AND usage_date = ? AND count < ?
                """,
                (access_key, today, daily_limit),
            )
            return cursor.rowcount == 1
    finally:
        conn.close()


def get_video_chunks(video_id: str) -> list[sqlite3.Row]:
    """Return all saved chunks for a video ordered by chunk_index ascending."""
    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            SELECT video_id, chunk_index, start_sec, end_sec, raw_json, prev_context
            FROM video_chunks
            WHERE video_id = ?
            ORDER BY chunk_index ASC
            """,
            (video_id,),
        )
        return cursor.fetchall()
    finally:
        conn.close()


def get_video_chunk(video_id: str, chunk_index: int) -> sqlite3.Row | None:
    """Return a single chunk row for (video_id, chunk_index), or None."""
    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            SELECT video_id, chunk_index, start_sec, end_sec, raw_json, prev_context
            FROM video_chunks
            WHERE video_id = ? AND chunk_index = ?
            """,
            (video_id, chunk_index),
        )
        return cursor.fetchone()
    finally:
        conn.close()


def save_video_chunks(video_id: str, chunks: list[dict]) -> None:
    """Persist chunk metadata and subtitle payloads for a video."""
    rows = [
        (
            video_id,
            c["chunk_index"],
            c["start_sec"],
            c["end_sec"],
            c["raw_json"],
            c.get("prev_context", ""),
        )
        for c in chunks
    ]
    conn = get_connection()
    try:
        with conn:
            conn.executemany(
                """
                INSERT OR REPLACE INTO video_chunks
                    (video_id, chunk_index, start_sec, end_sec, raw_json, prev_context)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
            conn.commit()
    finally:
        conn.close()


def get_cached_audio(video_id: str, chunk_index: int, voice: str) -> str | None:
    """Return cached audio_url for (video_id, chunk_index, voice), or None."""
    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            SELECT audio_url
            FROM audio_cache
            WHERE video_id = ? AND chunk_index = ? AND voice = ?
            """,
            (video_id, chunk_index, voice),
        )
        row = cursor.fetchone()
        return row["audio_url"] if row is not None else None
    finally:
        conn.close()


def save_cached_audio(video_id: str, chunk_index: int, voice: str, audio_url: str) -> None:
    """Insert or update the cached audio_url for (video_id, chunk_index, voice)."""
    conn = get_connection()
    try:
        with conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO audio_cache (video_id, chunk_index, voice, audio_url)
                VALUES (?, ?, ?, ?)
                """,
                (video_id, chunk_index, voice, audio_url),
            )
            conn.commit()
    finally:
        conn.close()

