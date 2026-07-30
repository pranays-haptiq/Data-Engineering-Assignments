"""
Unit tests for Prefect tasks in dividend_analysis.flows.tasks.

Prefect tasks expose a `.fn` attribute that lets us call the underlying
function directly without spinning up a Prefect server or run context.
"""
from __future__ import annotations

import logging
import subprocess
from datetime import date
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from dividend_analysis.flows.tasks import (
    analyze_favorable_task,
    concat_events_task,
    create_tables_task,
    fetch_events_task,
    filter_tickers_task,
    get_ticker_info_task,
    run_dbt_task,
    sample_tickers_task,
    upsert_events_task,
    upsert_tickers_task,
)

# ── patch _logger so task.fn() doesn't need a Prefect run context ────────────

@pytest.fixture(autouse=True)
def mock_prefect_logger(monkeypatch):
    """Replace _logger() in tasks with a plain stdlib logger for all tests."""
    monkeypatch.setattr(
        "dividend_analysis.flows.tasks._logger",
        lambda name=__name__: logging.getLogger("test"),
    )

class TestCreateTablesTask:
    def test_delegates_to_create_tables(self):
        with patch("dividend_analysis.flows.tasks.create_tables") as mock_ct:
            create_tables_task.fn()
        mock_ct.assert_called_once()


# ── filter_tickers_task ───────────────────────────────────────────────────────

class TestFilterTickersTask:
    def test_delegates_and_returns_result(self):
        with patch(
            "dividend_analysis.flows.tasks.filter_tickers_with_dividends",
            return_value=["AAPL", "MSFT"],
        ) as mock_f:
            result = filter_tickers_task.fn(["AAPL", "MSFT", "INTC"], 2024)
        mock_f.assert_called_once_with(["AAPL", "MSFT", "INTC"], 2024)
        assert result == ["AAPL", "MSFT"]


# ── sample_tickers_task ───────────────────────────────────────────────────────

class TestSampleTickersTask:
    def test_delegates_with_correct_args(self):
        with patch(
            "dividend_analysis.flows.tasks.sample_tickers",
            return_value=["AAPL"],
        ) as mock_s:
            result = sample_tickers_task.fn(["AAPL", "MSFT"], 1, 42)
        mock_s.assert_called_once_with(["AAPL", "MSFT"], n=1, seed=42)
        assert result == ["AAPL"]


# ── get_ticker_info_task ──────────────────────────────────────────────────────

class TestGetTickerInfoTask:
    def test_delegates_and_returns_dict(self):
        expected = {"ticker": "AAPL", "company_name": "Apple Inc.", "sector": "Tech"}
        with patch(
            "dividend_analysis.flows.tasks.get_ticker_info",
            return_value=expected,
        ) as mock_g:
            result = get_ticker_info_task.fn("AAPL")
        mock_g.assert_called_once_with("AAPL")
        assert result == expected


# ── upsert_tickers_task ───────────────────────────────────────────────────────

class TestUpsertTickersTask:
    def test_delegates_list_of_dicts(self):
        records = [{"ticker": "AAPL"}]
        with patch("dividend_analysis.flows.tasks.upsert_tickers") as mock_u:
            upsert_tickers_task.fn(records)
        mock_u.assert_called_once_with(records)


# ── fetch_events_task ─────────────────────────────────────────────────────────

class TestFetchEventsTask:
    def test_delegates_with_years(self):
        with patch(
            "dividend_analysis.flows.tasks.get_dividend_events",
            return_value=pd.DataFrame(),
        ) as mock_g:
            fetch_events_task.fn("AAPL", 5)
        mock_g.assert_called_once_with("AAPL", years=5)


# ── concat_events_task ────────────────────────────────────────────────────────

class TestConcatEventsTask:
    def test_ignores_empty_dataframes(self):
        df1 = pd.DataFrame([{"ticker": "AAPL", "ex_date": date(2024, 1, 1)}])
        result = concat_events_task.fn([pd.DataFrame(), df1, pd.DataFrame()])
        assert len(result) == 1
        assert result.iloc[0]["ticker"] == "AAPL"

    def test_returns_empty_when_all_empty(self):
        assert concat_events_task.fn([pd.DataFrame(), pd.DataFrame()]).empty


# ── upsert_events_task ────────────────────────────────────────────────────────

class TestUpsertEventsTask:
    def test_delegates_dataframe(self):
        df = pd.DataFrame([{"ticker": "AAPL"}])
        with patch("dividend_analysis.flows.tasks.upsert_dividend_events") as mock_u:
            upsert_events_task.fn(df)
        mock_u.assert_called_once()
        pd.testing.assert_frame_equal(mock_u.call_args[0][0], df)


# ── analyze_favorable_task ────────────────────────────────────────────────────

class TestAnalyzeFavorableTask:
    def test_delegates_and_returns_summary(self):
        df = pd.DataFrame([{"ticker": "AAPL", "drop_less_than_div": True,
                            "dividend_amount": 0.25, "price_drop": 0.2}])
        with patch(
            "dividend_analysis.flows.tasks.find_favorable_tickers",
            return_value=pd.DataFrame([{"ticker": "AAPL", "favorable_pct": 100.0}]),
        ) as mock_f:
            result = analyze_favorable_task.fn(df)
        mock_f.assert_called_once()
        assert result.iloc[0]["ticker"] == "AAPL"


# ── run_dbt_task ──────────────────────────────────────────────────────────────

class TestRunDbtTask:
    def test_runs_three_dbt_commands(self):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""
        with patch("dividend_analysis.flows.tasks.subprocess.run", return_value=mock_result) as mock_run:
            run_dbt_task.fn("dbt_dividend")
        assert mock_run.call_count == 3
        cmds = [c[0][0] for c in mock_run.call_args_list]
        assert any("deps" in cmd for cmd in cmds)
        assert any("run" in cmd for cmd in cmds)
        assert any("test" in cmd for cmd in cmds)

    def test_raises_on_non_zero_returncode(self):
        bad = MagicMock()
        bad.returncode = 1
        bad.stdout = ""
        bad.stderr = "dbt failed"
        with patch("dividend_analysis.flows.tasks.subprocess.run", return_value=bad):
            with pytest.raises(RuntimeError):
                run_dbt_task.fn("dbt_dividend")
