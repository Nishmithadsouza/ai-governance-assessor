"""
Storage layer. Two interchangeable backends behind one connection object:

- Local file SQLite (stdlib `sqlite3`) — used automatically when no remote
  credentials are configured. This is what you get when you run the app
  locally with `streamlit run app.py`.
- Turso (libSQL, a wire-compatible SQLite fork) — used automatically when
  `TURSO_DATABASE_URL` / `TURSO_AUTH_TOKEN` are present in `st.secrets`.
  This is what keeps data alive across Streamlit Community Cloud container
  restarts, since that platform's local disk is ephemeral.

Both backends speak the same DB-API-ish surface (`execute`, `?` placeholders,
`commit`), so every other module in this app is written once and works
against either.
"""

import json
import os
import sqlite3
import threading

import streamlit as st

LOCAL_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "governance.db")
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

SCHEMA = """
CREATE TABLE IF NOT EXISTS sources (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    publisher TEXT NOT NULL,
    source_type TEXT NOT NULL,
    url TEXT NOT NULL,
    jurisdiction TEXT,
    published_date TEXT,
    retrieved_date TEXT,
    summary TEXT
);

CREATE TABLE IF NOT EXISTS criteria (
    id TEXT PRIMARY KEY,
    dimension TEXT NOT NULL,
    industry TEXT NOT NULL DEFAULT 'Healthcare & Life Sciences',
    condition_json TEXT NOT NULL,
    keyword_json TEXT NOT NULL,
    risk_weight INTEGER NOT NULL,
    risk_level_if_matched TEXT,
    rationale TEXT NOT NULL,
    source_ids_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS use_cases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    industry TEXT NOT NULL DEFAULT 'Healthcare & Life Sciences',
    function TEXT NOT NULL,
    data_types_json TEXT NOT NULL,
    autonomy TEXT NOT NULL,
    affects_vulnerable INTEGER NOT NULL DEFAULT 0,
    vulnerable_groups_json TEXT NOT NULL DEFAULT '[]',
    jurisdictions_json TEXT NOT NULL,
    model_type TEXT NOT NULL,
    is_samd INTEGER NOT NULL DEFAULT 0,
    third_party TEXT NOT NULL,
    monitoring TEXT NOT NULL,
    explainability_method TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    is_seed INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS assessments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    use_case_id INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    overall_score REAL NOT NULL,
    overall_level TEXT NOT NULL,
    critical_flags_json TEXT NOT NULL DEFAULT '[]',
    narrative TEXT NOT NULL DEFAULT '',
    narrative_source TEXT NOT NULL DEFAULT 'template',
    model_used TEXT NOT NULL DEFAULT '',
    FOREIGN KEY (use_case_id) REFERENCES use_cases(id)
);

CREATE TABLE IF NOT EXISTS assessment_dimensions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    assessment_id INTEGER NOT NULL,
    dimension TEXT NOT NULL,
    score REAL NOT NULL,
    level TEXT NOT NULL,
    matched_criteria_json TEXT NOT NULL DEFAULT '[]',
    FOREIGN KEY (assessment_id) REFERENCES assessments(id)
);

CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT
);
"""

_local_lock = threading.Lock()


def get_secret(key, default=""):
    """st.secrets raises StreamlitSecretNotFoundError (not KeyError) when no
    secrets.toml exists at all anywhere on the machine, which defeats a plain
    `.get()`/hasattr check. This treats "no secrets configured" the same as
    "key not present" -> the default, everywhere secrets are read."""
    try:
        return st.secrets.get(key, default)
    except Exception:  # noqa: BLE001
        return default


class _Backend:
    """Tags which storage backend is actually in use, for display in the UI."""
    LOCAL_SQLITE = "Local SQLite file"
    TURSO = "Turso (libSQL, remote persistent SQLite)"


@st.cache_resource(show_spinner=False)
def get_connection():
    """Returns (connection, backend_label). Cached for the life of the app process."""
    turso_url = get_secret("TURSO_DATABASE_URL", "")
    turso_token = get_secret("TURSO_AUTH_TOKEN", "")

    if turso_url and turso_token:
        conn = _try_connect_turso(turso_url, turso_token)
        if conn is not None:
            _init_schema(conn)
            return conn, _Backend.TURSO
        st.warning(
            "TURSO_DATABASE_URL/TURSO_AUTH_TOKEN are set but no supported Turso/libSQL Python "
            "package could connect (tried `libsql`, `turso_serverless`, `libsql_client`). "
            "Falling back to local SQLite file — data will not survive a container restart on "
            "hosted deployments until this is fixed. See README for the current package name."
        )

    conn = sqlite3.connect(LOCAL_DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON")
    _init_schema(conn)
    return conn, _Backend.LOCAL_SQLITE


def _try_connect_turso(url, token):
    """The Turso/libSQL Python SDK's package name has moved more than once
    (`libsql`, `turso_serverless`, `libsql_client` have all been current at
    different times). Try each known shape rather than hard-coding one, so
    this keeps working whichever version ends up installed."""
    attempts = [
        lambda: __import__("libsql").connect(database=url, auth_token=token),
        lambda: __import__("turso_serverless").connect(url, auth_token=token),
        lambda: __import__("libsql_client").create_client_sync(url=url, auth_token=token),
    ]
    for attempt in attempts:
        try:
            conn = attempt()
            conn.execute("SELECT 1")
            return conn
        except Exception:  # noqa: BLE001 - try the next candidate
            continue
    return None


def _init_schema(conn):
    with _local_lock:
        for statement in SCHEMA.strip().split(";\n\n"):
            statement = statement.strip()
            if statement:
                conn.execute(statement)
        conn.commit()


def run(conn, sql, params=(), commit=True):
    """Execute a write statement. Commits by default; pass commit=False to batch
    several writes into one transaction (see assessment_service.py), which matters
    at scale — committing on every single statement means every assessment costs
    as many fsyncs as it has rows (11+), not one."""
    with _local_lock:
        cur = conn.execute(sql, params)
        if commit:
            conn.commit()
        return cur


def query(conn, sql, params=()):
    """Execute a read statement and return all rows as list of tuples."""
    with _local_lock:
        cur = conn.execute(sql, params)
        return cur.fetchall()


def query_one(conn, sql, params=()):
    rows = query(conn, sql, params)
    return rows[0] if rows else None


def load_json(filename):
    with open(os.path.join(DATA_DIR, filename), "r", encoding="utf-8") as f:
        return json.load(f)
