"""Prefect tasks wrapping core business logic."""
from __future__ import annotations

import subprocess
from datetime import timedelta

import pandas as pd
from prefect import get_run_logger, task
from prefect.tasks import task_input_hash

from dividend_analysis.db_utils import (
    create_tables,
    upsert_dividend_events,
    upsert_tickers,
)
from dividend_analysis.ticker_loader import (
    filter_tickers_with_dividends,
    find_favorable_tickers,
    get_dividend_events,
    get_ticker_info,
    sample_tickers,
)


@task(name="create-db-tables", retries=2, retry_delay_seconds=5)
def create_tables_task() -> None:
    logger = get_run_logger()
    logger.info("Creating database tables …")
    create_tables()


@task(
    name="filter-dividend-tickers",
    retries=3,
    retry_delay_seconds=30,
    cache_key_fn=task_input_hash,
    cache_expiration=timedelta(hours=6),
)
def filter_tickers_task(tickers: list[str], year: int) -> list[str]:
    logger = get_run_logger()
    logger.info("Filtering %d candidates for dividends paid in %d …", len(tickers), year)
    qualified = filter_tickers_with_dividends(tickers, year)
    logger.info("%d tickers qualified.", len(qualified))
    return qualified


@task(name="sample-tickers")
def sample_tickers_task(qualified: list[str], n: int, seed: int) -> list[str]:
    logger = get_run_logger()
    selected = sample_tickers(qualified, n=n, seed=seed)
    logger.info("Sampled %d tickers: %s", len(selected), selected)
    return selected


@task(
    name="fetch-ticker-info",
    retries=2,
    retry_delay_seconds=10,
    cache_key_fn=task_input_hash,
    cache_expiration=timedelta(hours=12),
)
def get_ticker_info_task(ticker: str) -> dict:
    return get_ticker_info(ticker)


@task(name="upsert-ticker-metadata", retries=2, retry_delay_seconds=5)
def upsert_tickers_task(ticker_infos: list[dict]) -> None:
    logger = get_run_logger()
    logger.info("Upserting metadata for %d tickers.", len(ticker_infos))
    upsert_tickers(ticker_infos)


@task(
    name="fetch-dividend-events",
    retries=3,
    retry_delay_seconds=30,
    cache_key_fn=task_input_hash,
    cache_expiration=timedelta(hours=6),
)
def fetch_events_task(ticker: str, years: int = 5) -> pd.DataFrame:
    logger = get_run_logger()
    logger.info("Fetching %d-year dividend events for %s …", years, ticker)
    return get_dividend_events(ticker, years=years)


@task(name="combine-event-dataframes")
def concat_events_task(dfs: list[pd.DataFrame]) -> pd.DataFrame:
    non_empty = [df for df in dfs if not df.empty]
    if not non_empty:
        return pd.DataFrame()
    return pd.concat(non_empty, ignore_index=True)


@task(name="upsert-dividend-events", retries=2, retry_delay_seconds=5)
def upsert_events_task(events_df: pd.DataFrame) -> None:
    logger = get_run_logger()
    logger.info("Upserting %d dividend events …", len(events_df))
    upsert_dividend_events(events_df)


@task(name="analyze-favorable-tickers")
def analyze_favorable_task(events_df: pd.DataFrame) -> pd.DataFrame:
    logger = get_run_logger()
    summary = find_favorable_tickers(events_df)
    if not summary.empty:
        logger.info("Ticker summary:\n%s", summary.to_string(index=False))
    return summary


@task(name="run-dbt-pipeline", retries=1, retry_delay_seconds=10)
def run_dbt_task(project_dir: str) -> None:
    """Run dbt deps → run → test using dbt-core's Python module."""
    logger = get_run_logger()

    for cmd in [
        ["python", "-m", "dbt", "deps", "--project-dir", project_dir],
        ["python", "-m", "dbt", "run", "--project-dir", project_dir],
        ["python", "-m", "dbt", "test", "--project-dir", project_dir],
    ]:
        logger.info("Running: %s", " ".join(cmd))
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.stdout:
            logger.info(result.stdout)
        if result.returncode != 0:
            logger.error(result.stderr)
            raise RuntimeError(f"dbt command failed: {' '.join(cmd)}\n{result.stderr}")
