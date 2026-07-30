"""Unit tests for dividend_analysis.ticker_loader."""
from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from dividend_analysis.ticker_loader import (
    find_favorable_tickers,
    get_dividend_events,
    get_ticker_info,
    sample_tickers,
    filter_tickers_with_dividends,
)


# ─── sample_tickers ────────────────────────────────────────────────────────────

class TestSampleTickers:
    def test_returns_correct_count(self):
        qualified = [f"T{i}" for i in range(40)]
        result = sample_tickers(qualified, n=25, seed=0)
        assert len(result) == 25

    def test_returns_subset_of_input(self):
        qualified = ["AAPL", "MSFT", "INTC", "CSCO", "TXN"]
        result = sample_tickers(qualified, n=3, seed=1)
        assert set(result).issubset(set(qualified))

    def test_returns_all_when_fewer_than_n(self):
        qualified = ["AAPL", "MSFT"]
        result = sample_tickers(qualified, n=25, seed=0)
        assert len(result) == 2

    def test_deterministic_with_seed(self):
        qualified = [f"T{i}" for i in range(50)]
        r1 = sample_tickers(qualified, n=10, seed=99)
        r2 = sample_tickers(qualified, n=10, seed=99)
        assert r1 == r2

    def test_empty_input(self):
        assert sample_tickers([], n=10) == []


# ─── find_favorable_tickers ───────────────────────────────────────────────────

class TestFindFavorableTickers:
    def _make_df(self, rows):
        return pd.DataFrame(rows, columns=[
            "ticker", "ex_date", "dividend_amount",
            "price_day_before", "price_on_ex_date",
            "price_drop", "drop_less_than_div",
        ])

    def test_sorts_by_favorable_pct_desc(self):
        df = self._make_df([
            ("AAPL", date(2024, 3, 1), 0.25, 180.0, 179.8, 0.2, True),
            ("AAPL", date(2024, 6, 1), 0.25, 182.0, 181.7, 0.3, False),
            ("MSFT", date(2024, 3, 1), 0.75, 420.0, 419.0, 1.0, False),
            ("MSFT", date(2024, 6, 1), 0.75, 422.0, 421.5, 0.5, True),
            ("MSFT", date(2024, 9, 1), 0.75, 418.0, 417.8, 0.2, True),
        ])
        result = find_favorable_tickers(df)
        assert result.iloc[0]["ticker"] == "MSFT"
        assert result.iloc[1]["ticker"] == "AAPL"

    def test_empty_input_returns_empty_df(self):
        result = find_favorable_tickers(pd.DataFrame())
        assert result.empty

    def test_favorable_pct_calculation(self):
        df = self._make_df([
            ("TXN", date(2024, 1, 1), 1.0, 150.0, 149.5, 0.5, True),
            ("TXN", date(2024, 4, 1), 1.0, 152.0, 151.0, 1.0, False),
            ("TXN", date(2024, 7, 1), 1.0, 155.0, 154.7, 0.3, True),
            ("TXN", date(2024, 10, 1), 1.0, 153.0, 152.8, 0.2, True),
        ])
        result = find_favorable_tickers(df)
        assert result.iloc[0]["favorable_pct"] == pytest.approx(75.0)

    def test_all_unfavorable(self):
        df = self._make_df([
            ("INTC", date(2024, 1, 1), 0.13, 30.0, 28.5, 1.5, False),
            ("INTC", date(2024, 4, 1), 0.13, 31.0, 29.0, 2.0, False),
        ])
        result = find_favorable_tickers(df)
        assert result.iloc[0]["favorable_pct"] == 0.0


# ─── filter_tickers_with_dividends ────────────────────────────────────────────

class TestFilterTickersWithDividends:
    def _make_dividends(self, dates: list[str]) -> pd.Series:
        idx = pd.to_datetime(dates)
        return pd.Series([0.25] * len(dates), index=idx)

    def test_returns_tickers_with_dividends_in_year(self):
        mock_ticker = MagicMock()
        mock_ticker.dividends = self._make_dividends(["2024-03-15", "2024-06-14"])
        with patch("dividend_analysis.ticker_loader.yf.Ticker", return_value=mock_ticker):
            result = filter_tickers_with_dividends(["AAPL"], 2024)
        assert "AAPL" in result

    def test_excludes_tickers_with_no_dividends_in_year(self):
        mock_ticker = MagicMock()
        mock_ticker.dividends = self._make_dividends(["2022-03-15"])
        with patch("dividend_analysis.ticker_loader.yf.Ticker", return_value=mock_ticker):
            result = filter_tickers_with_dividends(["MSFT"], 2024)
        assert "MSFT" not in result

    def test_skips_ticker_on_exception(self):
        with patch("dividend_analysis.ticker_loader.yf.Ticker", side_effect=Exception("network")):
            result = filter_tickers_with_dividends(["FAIL"], 2024)
        assert result == []

    def test_excludes_ticker_with_empty_dividends(self):
        mock_ticker = MagicMock()
        mock_ticker.dividends = pd.Series(dtype=float)
        with patch("dividend_analysis.ticker_loader.yf.Ticker", return_value=mock_ticker):
            result = filter_tickers_with_dividends(["AAPL"], 2024)
        assert "AAPL" not in result


# ─── get_ticker_info ──────────────────────────────────────────────────────────

class TestGetTickerInfo:
    def test_returns_expected_fields(self):
        mock_ticker = MagicMock()
        mock_ticker.info = {"longName": "Apple Inc.", "sector": "Technology"}
        with patch("dividend_analysis.ticker_loader.yf.Ticker", return_value=mock_ticker):
            info = get_ticker_info("AAPL")
        assert info["ticker"] == "AAPL"
        assert info["company_name"] == "Apple Inc."
        assert info["sector"] == "Technology"

    def test_falls_back_on_exception(self):
        with patch("dividend_analysis.ticker_loader.yf.Ticker", side_effect=Exception("err")):
            info = get_ticker_info("AAPL")
        assert info["ticker"] == "AAPL"
        assert info["sector"] == "Unknown"


# ─── get_dividend_events ──────────────────────────────────────────────────────

class TestGetDividendEvents:
    def test_returns_empty_when_no_dividends(self):
        mock_ticker = MagicMock()
        mock_ticker.dividends = pd.Series(dtype=float)
        with patch("dividend_analysis.ticker_loader.yf.Ticker", return_value=mock_ticker):
            result = get_dividend_events("AAPL", years=1)
        assert result.empty

    def test_calculates_price_drop_correctly(self):
        ex_date = date.today() - timedelta(days=90)
        day_before = ex_date - timedelta(days=1)
        divs = pd.Series([0.25], index=pd.to_datetime([ex_date]))
        hist = pd.DataFrame({"Close": [180.0, 179.8]}, index=pd.to_datetime([day_before, ex_date]))

        mock_ticker = MagicMock()
        mock_ticker.dividends = divs
        mock_ticker.history.return_value = hist

        with patch("dividend_analysis.ticker_loader.yf.Ticker", return_value=mock_ticker):
            result = get_dividend_events("AAPL", years=1)

        assert len(result) == 1
        assert result.iloc[0]["price_drop"] == pytest.approx(0.2, abs=1e-4)
        assert result.iloc[0]["drop_less_than_div"] == True  # 0.2 < 0.25

    def test_drop_false_when_drop_exceeds_dividend(self):
        ex_date = date.today() - timedelta(days=90)
        day_before = ex_date - timedelta(days=1)
        divs = pd.Series([0.10], index=pd.to_datetime([ex_date]))
        hist = pd.DataFrame({"Close": [100.0, 99.5]}, index=pd.to_datetime([day_before, ex_date]))

        mock_ticker = MagicMock()
        mock_ticker.dividends = divs
        mock_ticker.history.return_value = hist

        with patch("dividend_analysis.ticker_loader.yf.Ticker", return_value=mock_ticker):
            result = get_dividend_events("AAPL", years=1)

        assert result.iloc[0]["drop_less_than_div"] == False  # 0.5 > 0.10

    def test_returns_empty_when_hist_is_empty(self):
        ex_date = date.today() - timedelta(days=90)
        divs = pd.Series([0.25], index=pd.to_datetime([ex_date]))

        mock_ticker = MagicMock()
        mock_ticker.dividends = divs
        mock_ticker.history.return_value = pd.DataFrame()

        with patch("dividend_analysis.ticker_loader.yf.Ticker", return_value=mock_ticker):
            result = get_dividend_events("AAPL", years=1)

        assert result.empty

    def test_skips_dividend_date_not_in_hist(self):
        ex_date = date.today() - timedelta(days=90)
        divs = pd.Series([0.25], index=pd.to_datetime([ex_date]))
        # History only contains a date after ex_date, not the ex_date itself
        other_date = ex_date + timedelta(days=5)
        hist = pd.DataFrame({"Close": [180.0]}, index=pd.to_datetime([other_date]))

        mock_ticker = MagicMock()
        mock_ticker.dividends = divs
        mock_ticker.history.return_value = hist

        with patch("dividend_analysis.ticker_loader.yf.Ticker", return_value=mock_ticker):
            result = get_dividend_events("AAPL", years=1)

        assert result.empty
