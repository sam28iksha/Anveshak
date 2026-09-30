"""SQLite data access layer. Loads the whole dataset into pandas DataFrames once —
the volumes involved (tens of thousands of rows) are small enough that in-memory
pandas operations are simpler and fast enough than pushing every rule into SQL.
"""

import sqlite3
from pathlib import Path
from functools import lru_cache

import pandas as pd

DB_PATH = Path(__file__).parent.parent / "data" / "anveshak.db"


def get_connection(db_path: Path = DB_PATH) -> sqlite3.Connection:
    return sqlite3.connect(db_path)


@lru_cache(maxsize=1)
def load_all(db_path_str: str = str(DB_PATH)) -> dict:
    conn = get_connection(Path(db_path_str))
    tables = {}
    for name in ["entities", "assets", "alerts", "cases", "case_alerts", "escalations", "audit_logs"]:
        df = pd.read_sql(f"SELECT * FROM {name}", conn)
        tables[name] = df
    conn.close()

    for col in ["created_at", "acknowledged_at", "closed_at"]:
        if col in tables["alerts"].columns:
            tables["alerts"][col] = pd.to_datetime(tables["alerts"][col], format="ISO8601", errors="coerce")
    for col in ["opened_at", "closed_at"]:
        tables["cases"][col] = pd.to_datetime(tables["cases"][col], format="ISO8601", errors="coerce")
    tables["escalations"]["escalated_at"] = pd.to_datetime(tables["escalations"]["escalated_at"], format="ISO8601")
    tables["audit_logs"]["timestamp"] = pd.to_datetime(tables["audit_logs"]["timestamp"], format="ISO8601")

    tables["alerts"]["closure_minutes"] = (
        tables["alerts"]["closed_at"] - tables["alerts"]["acknowledged_at"]
    ).dt.total_seconds() / 60.0

    return tables


def clear_cache():
    load_all.cache_clear()
