"""Database utilities: table creation and data persistence."""
from __future__ import annotations

import logging
from contextlib import contextmanager

import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from sqlalchemy import create_engine, text

from dividend_analysis.config import DB_CONFIG, DB_URL

logger = logging.getLogger(__name__)

DDL_TICKER_INFO = """
CREATE TABLE IF NOT EXISTS nasdaq_dividend_tickers (
    ticker          VARCHAR(20)  PRIMARY KEY,
    company_name    VARCHAR(200),
    sector          VARCHAR(100),
    loaded_at       TIMESTAMPTZ  DEFAULT NOW()
);
"""

DDL_DIVIDEND_EVENTS = """
CREATE TABLE IF NOT EXISTS dividend_events (
    id                  SERIAL       PRIMARY KEY,
    ticker              VARCHAR(20)  NOT NULL,
    ex_date             DATE         NOT NULL,
    dividend_amount     NUMERIC(12, 6),
    price_day_before    NUMERIC(12, 4),
    price_on_ex_date    NUMERIC(12, 4),
    price_drop          NUMERIC(12, 4),
    drop_less_than_div  BOOLEAN,
    loaded_at           TIMESTAMPTZ  DEFAULT NOW(),
    UNIQUE (ticker, ex_date)
);
"""


@contextmanager
def get_connection():
    conn = psycopg2.connect(**DB_CONFIG)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def create_tables() -> None:
    """Create required tables if they don't exist."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(DDL_TICKER_INFO)
            cur.execute(DDL_DIVIDEND_EVENTS)
    logger.info("Tables ensured.")


def upsert_tickers(records: list[dict]) -> None:
    """Insert or update rows in nasdaq_dividend_tickers."""
    if not records:
        return
    sql = """
        INSERT INTO nasdaq_dividend_tickers (ticker, company_name, sector)
        VALUES %s
        ON CONFLICT (ticker) DO UPDATE
            SET company_name = EXCLUDED.company_name,
                sector       = EXCLUDED.sector,
                loaded_at    = NOW();
    """
    rows = [(r["ticker"], r.get("company_name", ""), r.get("sector", "")) for r in records]
    with get_connection() as conn:
        with conn.cursor() as cur:
            execute_values(cur, sql, rows)
    logger.info("Upserted %d tickers.", len(rows))


def upsert_dividend_events(df: pd.DataFrame) -> None:
    """Insert or update rows in dividend_events from a DataFrame."""
    if df.empty:
        return
    sql = """
        INSERT INTO dividend_events
            (ticker, ex_date, dividend_amount, price_day_before, price_on_ex_date,
             price_drop, drop_less_than_div)
        VALUES %s
        ON CONFLICT (ticker, ex_date) DO UPDATE
            SET dividend_amount  = EXCLUDED.dividend_amount,
                price_day_before = EXCLUDED.price_day_before,
                price_on_ex_date = EXCLUDED.price_on_ex_date,
                price_drop       = EXCLUDED.price_drop,
                drop_less_than_div = EXCLUDED.drop_less_than_div,
                loaded_at        = NOW();
    """
    rows = [
        (
            row["ticker"],
            row["ex_date"],
            row["dividend_amount"],
            row["price_day_before"],
            row["price_on_ex_date"],
            row["price_drop"],
            bool(row["drop_less_than_div"]),
        )
        for _, row in df.iterrows()
    ]
    with get_connection() as conn:
        with conn.cursor() as cur:
            execute_values(cur, sql, rows)
    logger.info("Upserted %d dividend events.", len(rows))


def read_table(table: str) -> pd.DataFrame:
    """Read an entire table into a DataFrame."""
    engine = create_engine(DB_URL)
    with engine.connect() as conn:
        return pd.read_sql(text(f"SELECT * FROM {table}"), conn)
