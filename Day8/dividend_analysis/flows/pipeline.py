"""Prefect flow: end-to-end Nasdaq dividend analysis pipeline."""
from __future__ import annotations

from datetime import date

import pandas as pd
from prefect import flow, get_run_logger

from dividend_analysis.ticker_loader import NASDAQ_CANDIDATE_TICKERS
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


@flow(
    name="nasdaq-dividend-analysis",
    description=(
        "Loads 25 Nasdaq dividend-paying tickers via yfinance, stores events in "
        "PostgreSQL, analyses price-drop patterns, and builds dbt models for the "
        "2 most consistent tickers."
    ),
    log_prints=True,
)
def dividend_pipeline(
    n_tickers: int = 25,
    seed: int = 42,
    dbt_project_dir: str | None = "dbt_dividend",
) -> pd.DataFrame:
    """
    Parameters
    ----------
    n_tickers:       Number of tickers to sample (max 25).
    seed:            Random seed for reproducible sampling.
    dbt_project_dir: Path to the dbt project. Pass None to skip dbt.
    """
    logger = get_run_logger()
    last_year = date.today().year - 1

    # ── Step 1: Ensure tables exist ─────────────────────────────────────────
    create_tables_task()

    # ── Step 2: Filter & sample tickers ────────────────────────────────────
    qualified = filter_tickers_task(NASDAQ_CANDIDATE_TICKERS, last_year)
    selected: list[str] = sample_tickers_task(qualified, n_tickers, seed)

    # ── Step 3: Fetch and store ticker metadata (parallel) ──────────────────
    info_futures = [get_ticker_info_task.submit(ticker) for ticker in selected]
    ticker_infos = [f.result() for f in info_futures]
    upsert_tickers_task(ticker_infos)

    # ── Step 4: Fetch 5-year dividend events for each ticker (parallel) ─────
    event_futures = [fetch_events_task.submit(ticker, 5) for ticker in selected]
    event_dfs: list[pd.DataFrame] = [f.result() for f in event_futures]

    # ── Step 5: Combine, persist, analyse ───────────────────────────────────
    events_df = concat_events_task(event_dfs)

    if events_df.empty:
        logger.warning("No dividend events found. Aborting pipeline.")
        return pd.DataFrame()

    upsert_events_task(events_df)
    summary = analyze_favorable_task(events_df)

    favorable = summary[summary["favorable_pct"] > 50]
    logger.info(
        "%d tickers where price drop < dividend > 50%% of the time.",
        len(favorable),
    )

    # ── Step 6: Run dbt models (staging → marts → tests) ────────────────────
    if dbt_project_dir:
        run_dbt_task(dbt_project_dir)

    return summary


if __name__ == "__main__":
    dividend_pipeline()
