"""Unit tests for dividend_analysis.ticker_loader (pure functions)."""
from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from dividend_analysis.ticker_loader import (
    filter_tickers_with_dividends,
    find_favorable_tickers,
    get_dividend_events,
    get_ticker_info,
    sample_tickers,
)


class TestSampleTickers:
    def test_returns_correct_count(self):
        qualified = [f"T{i}" for i in range(40)]
        assert len(sample_tickers(qualified, n=25, seed=0)) == 25

    def test_returns_subset_of_input(self):
        qualified = ["AAPL", "MSFT", "INTC", "CSCO", "TXN"]
        result = sample_tickers(qualified, n=3, seed=1)
        assert set(result).issubset(set(qualified))

    def test_returns_all_when_fewer_than_n(self):
        assert len(sample_tickers(["AAPL", "MSFT"], n=25)) == 2

    def test_deterministic_with_seed(self):
        pool = [f"T{i}" for i in range(50)]
        assert sample_tickers(pool, n=10, seed=99) == sample_tickers(pool, n=10, seed=99)

    def test_empty_input(self):
        assert sample_tickers([], n=10) == []


class TestFindFavorableTickers:
    def _df(self, rows):
        return pd.DataFrame(
            rows,
            columns=[
                "ticker", "ex_date", "dividend_amount",
                "price_day_before", "price_on_ex_date",
                "price_drop", "drop_less_than_div",
            ],
        )

    def test_sorts_by_favorable_pct_desc(self):
        df = self._df([
            ("AAPL", date(2024, 3, 1), 0.25, 180.0, 179.8, 0.2, True),
            ("AAPL", date(2024, 6, 1), 0.25, 182.0, 181.7, 0.3, False),
            ("MSFT", date(2024, 3, 1), 0.75, 420.0, 419.0, 1.0, False),
            ("MSFT", date(2024, 6, 1), 0.75, 422.0, 421.5, 0.5, True),
            ("MSFT", date(2024, 9, 1), 0.75, 418.0, 417.8, 0.2, True),
        ])
        result = find_favorable_tickers(df)
        assert result.iloc[0]["ticker"] == "MSFT"

    def test_empty_returns_empty(self):
        assert find_favorable_tickers(pd.DataFrame()).empty

    def test_favorable_pct_calculation(self):
        df = self._df([
            ("TXN", date(2024, 1, 1), 1.0, 150.0, 149.5, 0.5, True),
            ("TXN", date(2024, 4, 1), 1.0, 152.0, 151.0, 1.0, False),
            ("TXN", date(2024, 7, 1), 1.0, 155.0, 154.7, 0.3, True),
            ("TXN", date(2024, 10, 1), 1.0, 153.0, 152.8, 0.2, True),
        ])
        assert find_favorable_tickers(df).iloc[0]["favorable_pct"] == pytest.approx(75.0)

    def test_all_unfavorable_gives_zero_pct(self):
        df = self._df([
            ("INTC", date(2024, 1, 1), 0.13, 30.0, 28.5, 1.5, False),
            ("INTC", date(2024, 4, 1), 0.13, 31.0, 29.0, 2.0, False),
        ])
        assert find_favorable_tickers(df).iloc[0]["favorable_pct"] == 0.0


class TestFilterTickersWithDividends:
    def _make_divs(self, dates):
        return pd.Series([0.25] * len(dates), index=pd.to_datetime(dates))

    def test_includes_ticker_with_matching_dividend(self):
        mock_t = MagicMock()
        mock_t.dividends = self._make_divs(["2024-03-15"])
        with patch("dividend_analysis.ticker_loader.yf.Ticker", return_value=mock_t):
            assert "AAPL" in filter_tickers_with_dividends(["AAPL"], 2024)

    def test_excludes_ticker_with_older_dividend(self):
        mock_t = MagicMock()
        mock_t.dividends = self._make_divs(["2022-03-15"])
        with patch("dividend_analysis.ticker_loader.yf.Ticker", return_value=mock_t):
            assert "MSFT" not in filter_tickers_with_dividends(["MSFT"], 2024)

    def test_skips_on_exception(self):
        with patch("dividend_analysis.ticker_loader.yf.Ticker", side_effect=Exception):
            assert filter_tickers_with_dividends(["FAIL"], 2024) == []


class TestGetTickerInfo:
    def test_happy_path(self):
        mock_t = MagicMock()
        mock_t.info = {"longName": "Apple Inc.", "sector": "Technology"}
        with patch("dividend_analysis.ticker_loader.yf.Ticker", return_value=mock_t):
            info = get_ticker_info("AAPL")
        assert info == {"ticker": "AAPL", "company_name": "Apple Inc.", "sector": "Technology"}

    def test_fallback_on_exception(self):
        with patch("dividend_analysis.ticker_loader.yf.Ticker", side_effect=Exception):
            info = get_ticker_info("AAPL")
        assert info["sector"] == "Unknown"


class TestGetDividendEvents:
    def test_empty_when_no_dividends(self):
        mock_t = MagicMock()
        mock_t.dividends = pd.Series(dtype=float)
        with patch("dividend_analysis.ticker_loader.yf.Ticker", return_value=mock_t):
            assert get_dividend_events("AAPL").empty

    def test_drop_less_than_div_true(self):
        divs = pd.Series([0.25], index=pd.to_datetime(["2024-03-15"]))
        hist = pd.DataFrame({"Close": [180.0, 179.8]}, index=pd.to_datetime(["2024-03-14", "2024-03-15"]))
        mock_t = MagicMock()
        mock_t.dividends = divs
        mock_t.history.return_value = hist
        with patch("dividend_analysis.ticker_loader.yf.Ticker", return_value=mock_t):
            df = get_dividend_events("AAPL", years=5)
        assert df.iloc[0]["drop_less_than_div"] == True   # 0.2 < 0.25

    def test_drop_greater_than_div_false(self):
        divs = pd.Series([0.10], index=pd.to_datetime(["2024-03-15"]))
        hist = pd.DataFrame({"Close": [100.0, 99.5]}, index=pd.to_datetime(["2024-03-14", "2024-03-15"]))
        mock_t = MagicMock()
        mock_t.dividends = divs
        mock_t.history.return_value = hist
        with patch("dividend_analysis.ticker_loader.yf.Ticker", return_value=mock_t):
            df = get_dividend_events("AAPL", years=5)
        assert df.iloc[0]["drop_less_than_div"] == False   # 0.5 > 0.10
