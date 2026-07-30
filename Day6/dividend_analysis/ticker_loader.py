"""Nasdaq ticker loading and dividend analysis using yfinance."""
from __future__ import annotations

import logging
import random
from datetime import date, timedelta

import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)

# Curated list of Nasdaq-listed companies with established dividend histories
NASDAQ_CANDIDATE_TICKERS = [
    "AAPL", "MSFT", "INTC", "CSCO", "TXN", "AVGO", "QCOM",
    "PAYX", "ADI", "KLAC", "LRCX", "MCHP", "NXPI", "SWKS",
    "AMAT", "SNPS", "CDNS", "COST", "SBUX", "MDLZ", "PEP",
    "AMGN", "GILD", "CTAS", "FAST", "ODFL", "VRSK", "CINF",
    "CBOE", "TROW", "NDAQ", "CHRW", "EXPD", "ADP", "FISV",
    "MSCI", "EBAY", "CTSH", "INTU", "MRVL", "VRSN", "SGEN",
    "NTES", "JD", "BIDU", "BKNG", "REGN", "IDXX", "PCAR", "DLTR",
]


def filter_tickers_with_dividends(tickers: list[str], year: int) -> list[str]:
    """Return tickers that paid at least one dividend in the given calendar year."""
    qualified: list[str] = []
    start = date(year, 1, 1).isoformat()
    end = date(year, 12, 31).isoformat()
    for ticker in tickers:
        try:
            t = yf.Ticker(ticker)
            divs = t.dividends
            if divs is None or divs.empty:
                continue
            divs.index = divs.index.tz_localize(None) if divs.index.tzinfo else divs.index
            year_divs = divs[(divs.index >= start) & (divs.index <= end)]
            if not year_divs.empty:
                qualified.append(ticker)
        except Exception as exc:
            logger.warning("Could not fetch dividends for %s: %s", ticker, exc)
    return qualified


def sample_tickers(qualified: list[str], n: int = 25, seed: int | None = None) -> list[str]:
    """Randomly sample up to n tickers from the qualified list."""
    rng = random.Random(seed)
    return rng.sample(qualified, min(n, len(qualified)))


def get_ticker_info(ticker: str) -> dict:
    """Return basic info dict for a ticker."""
    try:
        info = yf.Ticker(ticker).info
        return {
            "ticker": ticker,
            "company_name": info.get("longName", ticker),
            "sector": info.get("sector", "Unknown"),
        }
    except Exception as exc:
        logger.warning("Could not fetch info for %s: %s", ticker, exc)
        return {"ticker": ticker, "company_name": ticker, "sector": "Unknown"}


def get_dividend_events(ticker: str, years: int = 5) -> pd.DataFrame:
    """
    For each ex-dividend date in the last `years` years, fetch:
      - dividend_amount
      - price_day_before  (adjusted close of T-1)
      - price_on_ex_date  (adjusted close of T)
      - price_drop        = price_day_before - price_on_ex_date
      - drop_less_than_div = price_drop < dividend_amount
    """
    end_dt = date.today()
    start_dt = end_dt - timedelta(days=365 * years + 30)

    t = yf.Ticker(ticker)
    divs = t.dividends
    if divs is None or divs.empty:
        return pd.DataFrame()

    divs.index = divs.index.tz_localize(None) if divs.index.tzinfo else divs.index
    divs = divs[(divs.index.date >= start_dt) & (divs.index.date <= end_dt)]
    if divs.empty:
        return pd.DataFrame()

    hist = t.history(start=start_dt.isoformat(), end=end_dt.isoformat(), auto_adjust=True)
    if hist.empty:
        return pd.DataFrame()
    hist.index = hist.index.tz_localize(None) if hist.index.tzinfo else hist.index

    rows = []
    for ex_ts, div_amount in divs.items():
        ex_date = ex_ts.date()
        # Find the trading day before ex_date
        before_mask = hist.index.date < ex_date
        on_mask = hist.index.date == ex_date
        if not before_mask.any() or not on_mask.any():
            continue
        price_before = float(hist.loc[before_mask, "Close"].iloc[-1])
        price_on = float(hist.loc[on_mask, "Close"].iloc[0])
        drop = price_before - price_on
        rows.append(
            {
                "ticker": ticker,
                "ex_date": ex_date,
                "dividend_amount": float(div_amount),
                "price_day_before": price_before,
                "price_on_ex_date": price_on,
                "price_drop": drop,
                "drop_less_than_div": drop < float(div_amount),
            }
        )
    return pd.DataFrame(rows)


def find_favorable_tickers(events_df: pd.DataFrame) -> pd.DataFrame:
    """
    Return per-ticker summary sorted by the percentage of events where
    price_drop < dividend_amount (descending).
    """
    if events_df.empty:
        return pd.DataFrame()

    summary = (
        events_df.groupby("ticker")
        .agg(
            total_events=("drop_less_than_div", "count"),
            favorable_events=("drop_less_than_div", "sum"),
            avg_dividend=("dividend_amount", "mean"),
            avg_drop=("price_drop", "mean"),
        )
        .reset_index()
    )
    summary["favorable_pct"] = (
        summary["favorable_events"] / summary["total_events"] * 100
    ).round(2)
    return summary.sort_values("favorable_pct", ascending=False)
