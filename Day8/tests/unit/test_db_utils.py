"""Unit tests for dividend_analysis.db_utils (mocked psycopg2)."""
from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from dividend_analysis.db_utils import create_tables, upsert_dividend_events, upsert_tickers

PATCH_CONN = "dividend_analysis.db_utils.get_connection"


def _mock_conn():
    cur = MagicMock()
    conn = MagicMock()
    conn.__enter__ = MagicMock(return_value=conn)
    conn.__exit__ = MagicMock(return_value=False)
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cur)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    return conn, cur


class TestCreateTables:
    def test_executes_two_ddl_statements(self):
        conn, cur = _mock_conn()
        with patch(PATCH_CONN, return_value=conn):
            create_tables()
        assert cur.execute.call_count == 2


class TestUpsertTickers:
    def test_skips_empty_list(self):
        with patch(PATCH_CONN) as mock_ctx:
            upsert_tickers([])
        mock_ctx.assert_not_called()

    def test_passes_correct_rows(self):
        conn, _ = _mock_conn()
        records = [{"ticker": "AAPL", "company_name": "Apple", "sector": "Tech"}]
        with patch(PATCH_CONN, return_value=conn):
            with patch("dividend_analysis.db_utils.execute_values") as ev:
                upsert_tickers(records)
                rows = ev.call_args[0][2]
        assert ("AAPL", "Apple", "Tech") in rows

    def test_missing_optional_fields_default_to_empty_string(self):
        conn, _ = _mock_conn()
        with patch(PATCH_CONN, return_value=conn):
            with patch("dividend_analysis.db_utils.execute_values") as ev:
                upsert_tickers([{"ticker": "TXN"}])
                rows = ev.call_args[0][2]
        assert rows[0] == ("TXN", "", "")


class TestUpsertDividendEvents:
    def test_skips_empty_dataframe(self):
        with patch(PATCH_CONN) as mock_ctx:
            upsert_dividend_events(pd.DataFrame())
        mock_ctx.assert_not_called()

    def test_inserts_correct_row_count(self):
        df = pd.DataFrame([
            {"ticker": "AAPL", "ex_date": date(2024, 3, 15), "dividend_amount": 0.25,
             "price_day_before": 180.0, "price_on_ex_date": 179.8,
             "price_drop": 0.2, "drop_less_than_div": True},
            {"ticker": "MSFT", "ex_date": date(2024, 3, 15), "dividend_amount": 0.75,
             "price_day_before": 420.0, "price_on_ex_date": 419.5,
             "price_drop": 0.5, "drop_less_than_div": True},
        ])
        conn, _ = _mock_conn()
        with patch(PATCH_CONN, return_value=conn):
            with patch("dividend_analysis.db_utils.execute_values") as ev:
                upsert_dividend_events(df)
                assert len(ev.call_args[0][2]) == 2
