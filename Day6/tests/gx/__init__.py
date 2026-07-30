"""
Great Expectations data quality tests for dividend_events and nasdaq_dividend_tickers.

Run with:  pytest tests/gx/test_gx_expectations.py
These tests connect to the live PostgreSQL database and validate the loaded data.
"""
from __future__ import annotations

import pytest
import pandas as pd
import great_expectations as gx
from great_expectations.core.batch import RuntimeBatchRequest
from sqlalchemy import create_engine, text

from dividend_analysis.config import DB_URL


# ── helpers ───────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def engine():
    return create_engine(DB_URL)


def _table_exists(engine, table: str) -> bool:
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT to_regclass(:t)"), {"t": table}
        ).scalar()
    return result is not None


def _load_table(engine, table: str) -> pd.DataFrame:
    with engine.connect() as conn:
        return pd.read_sql(text(f"SELECT * FROM {table}"), conn)


# ── GX context ────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def gx_context():
    return gx.get_context(mode="ephemeral")


# ── dividend_events suite ─────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def dividend_events_df(engine):
    if not _table_exists(engine, "dividend_events"):
        pytest.skip("dividend_events table not found — run main.py first.")
    return _load_table(engine, "dividend_events")


@pytest.fixture(scope="module")
def de_validator(gx_context, dividend_events_df):
    ds = gx_context.sources.add_pandas("dividend_events_source")
    asset = ds.add_dataframe_asset("dividend_events_asset")
    batch_request = asset.build_batch_request(dataframe=dividend_events_df)
    return gx_context.get_validator(batch_request=batch_request)


class TestDividendEventsExpectations:
    def test_ticker_not_null(self, de_validator):
        result = de_validator.expect_column_values_to_not_be_null("ticker")
        assert result.success, result.result

    def test_ex_date_not_null(self, de_validator):
        result = de_validator.expect_column_values_to_not_be_null("ex_date")
        assert result.success, result.result

    def test_dividend_amount_positive(self, de_validator):
        result = de_validator.expect_column_values_to_be_between(
            "dividend_amount", min_value=0, strict_min=True
        )
        assert result.success, result.result

    def test_price_day_before_positive(self, de_validator):
        result = de_validator.expect_column_values_to_be_between(
            "price_day_before", min_value=0, strict_min=True
        )
        assert result.success, result.result

    def test_price_on_ex_date_positive(self, de_validator):
        result = de_validator.expect_column_values_to_be_between(
            "price_on_ex_date", min_value=0, strict_min=True
        )
        assert result.success, result.result

    def test_table_has_rows(self, de_validator):
        result = de_validator.expect_table_row_count_to_be_between(min_value=1)
        assert result.success, result.result

    def test_ticker_column_has_reasonable_length(self, de_validator):
        result = de_validator.expect_column_value_lengths_to_be_between(
            "ticker", min_value=1, max_value=10
        )
        assert result.success, result.result

    def test_price_drop_in_realistic_range(self, de_validator):
        result = de_validator.expect_column_values_to_be_between(
            "price_drop", min_value=-500, max_value=500
        )
        assert result.success, result.result

    def test_drop_less_than_div_is_boolean(self, de_validator):
        result = de_validator.expect_column_values_to_be_in_set(
            "drop_less_than_div", {True, False}
        )
        assert result.success, result.result


# ── nasdaq_dividend_tickers suite ─────────────────────────────────────────────

@pytest.fixture(scope="module")
def tickers_df(engine):
    if not _table_exists(engine, "nasdaq_dividend_tickers"):
        pytest.skip("nasdaq_dividend_tickers table not found — run main.py first.")
    return _load_table(engine, "nasdaq_dividend_tickers")


@pytest.fixture(scope="module")
def tickers_validator(gx_context, tickers_df):
    ds = gx_context.sources.add_pandas("tickers_source")
    asset = ds.add_dataframe_asset("tickers_asset")
    batch_request = asset.build_batch_request(dataframe=tickers_df)
    return gx_context.get_validator(batch_request=batch_request)


class TestNasdaqTickersExpectations:
    def test_ticker_not_null(self, tickers_validator):
        result = tickers_validator.expect_column_values_to_not_be_null("ticker")
        assert result.success, result.result

    def test_ticker_unique(self, tickers_validator):
        result = tickers_validator.expect_column_values_to_be_unique("ticker")
        assert result.success, result.result

    def test_row_count_between_1_and_25(self, tickers_validator):
        result = tickers_validator.expect_table_row_count_to_be_between(
            min_value=1, max_value=25
        )
        assert result.success, result.result

    def test_company_name_not_null(self, tickers_validator):
        result = tickers_validator.expect_column_values_to_not_be_null("company_name")
        assert result.success, result.result
