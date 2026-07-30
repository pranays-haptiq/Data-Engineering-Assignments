"""Main entry point: load Nasdaq dividend tickers, analyse and persist to PostgreSQL."""
from __future__ import annotations

import logging
from datetime import date

import pandas as pd

from dividend_analysis.db_utils import (
    create_tables,
    upsert_dividend_events,
    upsert_tickers,
)
from dividend_analysis.ticker_loader import (
    NASDAQ_CANDIDATE_TICKERS,
    filter_tickers_with_dividends,
    find_favorable_tickers,
    get_dividend_events,
    get_ticker_info,
    sample_tickers,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def run() -> None:
    last_year = date.today().year - 1

    # ── Step 1: Create DB tables ────────────────────────────────────────────
    logger.info("Creating tables …")
    create_tables()

    # ── Step 2: Filter & sample 25 tickers ─────────────────────────────────
    logger.info("Filtering Nasdaq tickers with dividends in %d …", last_year)
    qualified = filter_tickers_with_dividends(NASDAQ_CANDIDATE_TICKERS, last_year)
    logger.info("%d tickers qualified.", len(qualified))

    selected = sample_tickers(qualified, n=25, seed=42)
    logger.info("Selected tickers: %s", selected)

    # ── Step 3: Persist ticker info ─────────────────────────────────────────
    ticker_infos = [get_ticker_info(t) for t in selected]
    upsert_tickers(ticker_infos)

    # ── Step 4: Load 5-year dividend events for all selected tickers ────────
    all_events: list[pd.DataFrame] = []
    for ticker in selected:
        logger.info("Fetching dividend events for %s …", ticker)
        df = get_dividend_events(ticker, years=5)
        if not df.empty:
            all_events.append(df)

    if not all_events:
        logger.error("No dividend events found. Exiting.")
        return

    events_df = pd.concat(all_events, ignore_index=True)
    upsert_dividend_events(events_df)
    logger.info("Persisted %d dividend events.", len(events_df))

    # ── Step 5: Find tickers where drop < dividend most of the time ─────────
    summary = find_favorable_tickers(events_df)
    logger.info("\n%s", summary.to_string(index=False))

    favorable = summary[summary["drop_less_than_div"] if "drop_less_than_div" in summary.columns
                        else summary["favorable_pct"] > 50]
    logger.info(
        "\nTickers where price drop < dividend amount > 50%% of the time:\n%s",
        favorable[["ticker", "total_events", "favorable_events", "favorable_pct"]].to_string(index=False),
    )

    top2 = summary.head(2)["ticker"].tolist()
    logger.info("Top 2 tickers for dbt model: %s", top2)


if __name__ == "__main__":
    run()
