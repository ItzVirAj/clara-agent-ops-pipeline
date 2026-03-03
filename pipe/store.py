# pipe/store.py
# sqlite registry — tracks every account processed through pipeline

import os
import sqlite3
from pathlib import Path
from pipe.utils import get_lgr, utc_now

lgr = get_lgr("store")

DB_PATH = Path("out/acct_registry.db")


# ── connection ────────────────────────────────────────────
def _conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(DB_PATH)


# ── init db ───────────────────────────────────────────────
def init_db():
    """
    creates accounts table if not exists
    safe to call multiple times — idempotent
    """
    with _conn() as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS accounts (
                acct_id      TEXT PRIMARY KEY,
                co_name      TEXT,
                status       TEXT DEFAULT 'demo_processed',
                v1_at        TEXT,
                v2_at        TEXT,
                memo_v1_path TEXT,
                memo_v2_path TEXT,
                spec_v1_path TEXT,
                spec_v2_path TEXT,
                open_qs_cnt  INTEGER DEFAULT 0,
                created_at   TEXT,
                updated_at   TEXT
            )
        """)
    lgr.info(f"db ready → {DB_PATH}")


# ── upsert account ────────────────────────────────────────
def upsert_acct(acct_id: str, data: dict):
    """
    inserts or updates account row
    data keys match column names
    """
    init_db()
    now = utc_now()

    with _conn() as c:
        existing = c.execute(
            "SELECT acct_id FROM accounts WHERE acct_id = ?",
            (acct_id,)
        ).fetchone()

        if existing:
            # build update from data keys
            cols = ", ".join(f"{k} = ?" for k in data)
            vals = list(data.values()) + [now, acct_id]
            c.execute(
                f"UPDATE accounts SET {cols}, updated_at = ? WHERE acct_id = ?",
                vals
            )
            lgr.info(f"acct updated | {acct_id}")
        else:
            data["acct_id"]   = acct_id
            data["created_at"] = now
            data["updated_at"] = now
            cols = ", ".join(data.keys())
            plch = ", ".join("?" * len(data))
            c.execute(
                f"INSERT INTO accounts ({cols}) VALUES ({plch})",
                list(data.values())
            )
            lgr.info(f"acct inserted | {acct_id}")


# ── get account ───────────────────────────────────────────
def get_acct(acct_id: str) -> dict | None:
    """returns account row as dict or None if not found"""
    init_db()
    with _conn() as c:
        c.row_factory = sqlite3.Row
        row = c.execute(
            "SELECT * FROM accounts WHERE acct_id = ?",
            (acct_id,)
        ).fetchone()
    return dict(row) if row else None


# ── list all accounts ─────────────────────────────────────
def list_accts() -> list[dict]:
    """returns all accounts as list of dicts"""
    init_db()
    with _conn() as c:
        c.row_factory = sqlite3.Row
        rows = c.execute(
            "SELECT * FROM accounts ORDER BY created_at DESC"
        ).fetchall()
    return [dict(r) for r in rows]


# ── register v1 ──────────────────────────────────────────
def reg_v1(memo: dict, spec: dict):
    """
    called after pipeline A completes
    registers v1 outputs in db
    """
    acct_id  = memo["acct_id"]
    base     = Path(os.getenv("ACCT_OUT_DIR", "out/accounts"))
    v1_dir   = base / acct_id / "v1"

    upsert_acct(acct_id, {
        "co_name"      : memo.get("co_name"),
        "status"       : "v1_done",
        "v1_at"        : utc_now(),
        "memo_v1_path" : str(v1_dir / "memo.json"),
        "spec_v1_path" : str(v1_dir / "agent_spec.json"),
        "open_qs_cnt"  : len(memo.get("open_qs", []))
    })


# ── register v2 ──────────────────────────────────────────
def reg_v2(memo: dict, spec: dict):
    """
    called after pipeline B completes
    updates row with v2 outputs
    """
    acct_id  = memo["acct_id"]
    base     = Path(os.getenv("ACCT_OUT_DIR", "out/accounts"))
    v2_dir   = base / acct_id / "v2"

    upsert_acct(acct_id, {
        "status"       : "v2_done",
        "v2_at"        : utc_now(),
        "memo_v2_path" : str(v2_dir / "memo.json"),
        "spec_v2_path" : str(v2_dir / "agent_spec.json"),
        "open_qs_cnt"  : len(memo.get("open_qs", []))
    })