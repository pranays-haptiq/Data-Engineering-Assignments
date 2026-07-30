"""Unit tests for dividend_analysis.db_utils."""
from __future__ import annotations

from unittest.mock import MagicMock, call, patch, ANY

import pandas as pd
import pytest

from dividend_analysis.db_utils import create_tables, upsert_tickers, upsert_dividend_events, read_table


MOCK_CONN_CTX = "dividend_analysis.db_utils.get_connection"


class TestCreateTables:
    def test_executes_two_ddl_statements(self):
        mock_cur = MagicMock()
        mock_conn = MagicMock()
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        with patch(MOCK_CONN_CTX, return_value=mock_conn):
            create_tables()

        assert mock_cur.execute.call_count == 2


class TestUpsertTickers:
    def test_skips_empty_list(self):
        with patch(MOCK_CONN_CTX) as mock_ctx:
            upsert_tickers([])
        mock_ctx.assert_not_called()

    def test_calls_execute_values_with_correct_rows(self):
        mock_cur = MagicMock()
        mock_conn = MagicMock()
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        records = [
            {"ticker": "AAPL", "company_name": "Apple Inc.", "sector": "Technology"},
            {"ticker": "MSFT", "company_name": "Microsoft", "sector": "Technology"},
        ]
        with patch(MOCK_CONN_CTX, return_value=mock_conn):
            with patch("dividend_analysis.db_utils.execute_values") as mock_ev:
                upsert_tickers(records)
                rows_arg = mock_ev.call_args[0][2]
                assert ("AAPL", "Apple Inc.", "Technology") in rows_arg
                assert ("MSFT", "Microsoft", "Technology") in rows_arg

    def test_handles_missing_optional_fields(self):
        mock_conn = MagicMock()
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        with patch(MOCK_CONN_CTX, return_value=mock_conn):
            with patch("dividend_analysis.db_utils.execute_values") as mock_ev:
                upsert_tickers([{"ticker": "TXN"}])
                rows_arg = mock_ev.call_args[0][2]
                assert rows_arg[0] == ("TXN", "", "")


class TestUpsertDividendEvents:
    def test_skips_empty_dataframe(self):
        with patch(MOCK_CONN_CTX) as mock_ctx:
            upsert_dividend_events(pd.DataFrame())
        mock_ctx.assert_not_called()

    def test_inserts_correct_number_of_rows(self):
        from datetime import date
        df = pd.DataFrame([
            {
                "ticker": "AAPL",
                "ex_date": date(2024, 3, 15),
                "dividend_amount": 0.25,
                "price_day_before": 180.0,
                "price_on_ex_date": 179.8,
                "price_drop": 0.2,
                "drop_less_than_div": True,
            },
            {
                "ticker": "MSFT",
                "ex_date": date(2024, 3, 15),
                "dividend_amount": 0.75,
                "price_day_before": 420.0,
                "price_on_ex_date": 419.5,
                "price_drop": 0.5,
                "drop_less_than_div": True,
            },
        ])

        mock_cur = MagicMock()
        mock_conn = MagicMock()
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        with patch(MOCK_CONN_CTX, return_value=mock_conn):
            with patch("dividend_analysis.db_utils.execute_values") as mock_ev:
                upsert_dividend_events(df)
                rows_arg = mock_ev.call_args[0][2]
                assert len(rows_arg) == 2


class TestReadTable:
    def test_returns_dataframe(self):
        expected_df = pd.DataFrame([{"ticker": "AAPL", "sector": "Technology"}])
        mock_conn = MagicMock()
        mock_engine = MagicMock()
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)

        with patch("dividend_analysis.db_utils.create_engine", return_value=mock_engine):
            with patch("dividend_analysis.db_utils.pd.read_sql", return_value=expected_df):
                result = read_table("nasdaq_dividend_tickers")

        assert list(result.columns) == ["ticker", "sector"]
        assert len(result) == 1
