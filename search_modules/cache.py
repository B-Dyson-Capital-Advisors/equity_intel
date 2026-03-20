"""
SQLite-based cache for SEC EDGAR search results.

Caches expensive search results so repeated queries (and graph pivots) are instant.
TTL: 24 hours by default.
"""

import sqlite3
import json
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta

DB_PATH = Path(__file__).parent.parent / "data" / "equity_intel.db"
CACHE_TTL_HOURS = 24


def _get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS search_cache (
            cache_key  TEXT PRIMARY KEY,
            result_json TEXT NOT NULL,
            created_at  TEXT NOT NULL
        )
    """)
    conn.commit()
    return conn


def _make_key(entity_type: str, entity_name: str, start_date, end_date) -> str:
    return f"{entity_type}::{entity_name.lower().strip()}::{start_date}::{end_date}"


def get_cached(entity_type: str, entity_name: str, start_date, end_date) -> pd.DataFrame | None:
    """Return cached DataFrame or None if not found / expired."""
    key = _make_key(entity_type, entity_name, start_date, end_date)
    try:
        conn = _get_conn()
        row = conn.execute(
            "SELECT result_json, created_at FROM search_cache WHERE cache_key = ?", (key,)
        ).fetchone()
        conn.close()
        if row:
            result_json, created_at = row
            age = datetime.now() - datetime.fromisoformat(created_at)
            if age < timedelta(hours=CACHE_TTL_HOURS):
                df = pd.read_json(result_json, orient="records")
                return df
    except Exception:
        pass
    return None


def set_cached(entity_type: str, entity_name: str, start_date, end_date, df: pd.DataFrame) -> None:
    """Store a DataFrame result in the cache."""
    key = _make_key(entity_type, entity_name, start_date, end_date)
    try:
        conn = _get_conn()
        conn.execute(
            "INSERT OR REPLACE INTO search_cache (cache_key, result_json, created_at) VALUES (?, ?, ?)",
            (key, df.to_json(orient="records", date_format="iso"), datetime.now().isoformat()),
        )
        conn.commit()
        conn.close()
    except Exception:
        pass


def clear_expired() -> int:
    """Delete entries older than TTL. Returns count removed."""
    try:
        conn = _get_conn()
        cutoff = (datetime.now() - timedelta(hours=CACHE_TTL_HOURS)).isoformat()
        cur = conn.execute("DELETE FROM search_cache WHERE created_at < ?", (cutoff,))
        removed = cur.rowcount
        conn.commit()
        conn.close()
        return removed
    except Exception:
        return 0


def clear_all() -> None:
    """Wipe the entire cache (for debugging / forced refresh)."""
    try:
        conn = _get_conn()
        conn.execute("DELETE FROM search_cache")
        conn.commit()
        conn.close()
    except Exception:
        pass


def get_cache_stats() -> dict:
    """Return basic cache stats for display in UI."""
    try:
        conn = _get_conn()
        total = conn.execute("SELECT COUNT(*) FROM search_cache").fetchone()[0]
        cutoff = (datetime.now() - timedelta(hours=CACHE_TTL_HOURS)).isoformat()
        fresh = conn.execute(
            "SELECT COUNT(*) FROM search_cache WHERE created_at >= ?", (cutoff,)
        ).fetchone()[0]
        conn.close()
        return {"total": total, "fresh": fresh, "expired": total - fresh}
    except Exception:
        return {"total": 0, "fresh": 0, "expired": 0}
