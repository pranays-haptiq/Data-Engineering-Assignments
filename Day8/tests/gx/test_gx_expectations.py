"""
Great Expectations data quality tests.

Run after the Prefect pipeline has populated the database:
  pytest tests/gx/test_gx_expectations.py
"""
from __future__ import annotations

import pandas as pd
import pytest
import great_expectations as gx
from sqlalchemy import create_engine, text

from dividend_analysis.config import DB_URL


# ── helpers ───────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def engine():
    return create_engine(DB_URL)


def _table_exists(engine, table: str) -> bool:
    with engine.connect() as conn:
        return conn.execute(text("SELECT to_regclass(:t)"), {"t": table}).scalar() is not None


def _load(engine, table: str) -> pd.DataFrame:
    with engine.connect() as conn:
        return pd.read_sql(text(f"SELECT * FROM {table}"), conn)


@pytest.fixture(scope="module")
def ctx():
    return gx.get_context(mode="ephemeral")


# ── dividend_events ───────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def de_df(engine):
    if not _table_exists(engine, "dividend_events"):
        pytest.skip("dividend_events not found — run the Prefect pipeline first.")
    return _load(engine, "dividend_events")


@pytest.fixture(scope="module")
def de_validator(ctx, de_df):
    ds = ctx.sources.add_pandas("de_source")
    asset = ds.add_dataframe_asset("de_asset")
    return ctx.get_validator(batch_request=asset.build_batch_request(dataframe=de_df))


class TestDividendEventsGX:
    def test_ticker_not_null(self, de_validator):
        assert de_validator.expect_column_values_to_not_be_null("ticker").success

    def test_ex_date_not_null(self, de_validator):
        assert de_validator.expect_column_values_to_not_be_null("ex_date").success

    def test_dividend_amount_positive(self, de_validator):
        assert de_validator.expect_column_values_to_be_between(
            "dividend_amount", min_value=0, strict_min=True
        ).success

    def test_price_day_before_positive(self, de_validator):
        assert de_validator.expect_column_values_to_be_between(
            "price_day_before", min_value=0, strict_min=True
        ).success

    def test_price_on_ex_date_positive(self, de_validator):
        assert de_validator.expect_column_values_to_be_between(
            "price_on_ex_date", min_value=0, strict_min=True
        ).success

    def test_table_not_empty(self, de_validator):
        assert de_validator.expect_table_row_count_to_be_between(min_value=1).success

    def test_ticker_length_reasonable(self, de_validator):
        assert de_validator.expect_column_value_lengths_to_be_between(
            "ticker", min_value=1, max_value=10
        ).success

    def test_price_drop_realistic_range(self, de_validator):
        assert de_validator.expect_column_values_to_be_between(
            "price_drop", min_value=-500, max_value=500
        ).success

    def test_drop_flag_is_boolean(self, de_validator):
        assert de_validator.expect_column_values_to_be_in_set(
            "drop_less_than_div", {True, False}
        ).success


# ── nasdaq_dividend_tickers ───────────────────────────────────────────────────

@pytest.fixture(scope="module")
def tickers_df(engine):
    if not _table_exists(engine, "nasdaq_dividend_tickers"):
        pytest.skip("nasdaq_dividend_tickers not found — run the Prefect pipeline first.")
    return _load(engine, "nasdaq_dividend_tickers")


@pytest.fixture(scope="module")
def tickers_validator(ctx, tickers_df):
    ds = ctx.sources.add_pandas("tickers_source")
    asset = ds.add_dataframe_asset("tickers_asset")
    return ctx.get_validator(batch_request=asset.build_batch_request(dataframe=tickers_df))


class TestNasdaqTickersGX:
    def test_ticker_not_null(self, tickers_validator):
        assert tickers_validator.expect_column_values_to_not_be_null("ticker").success

    def test_ticker_unique(self, tickers_validator):
        assert tickers_validator.expect_column_values_to_be_unique("ticker").success

    def test_row_count_max_25(self, tickers_validator):
        assert tickers_validator.expect_table_row_count_to_be_between(
            min_value=1, max_value=25
        ).success

    def test_company_name_not_null(self, tickers_validator):
        assert tickers_validator.expect_column_values_to_not_be_null("company_name").success
