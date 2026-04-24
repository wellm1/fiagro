"""Fetch price data from yfinance and CDI from BCB API."""
import logging
from datetime import date, timedelta

import pandas as pd
import requests
import yfinance as yf

from config import BCB_CDI_URL, FIAGROS

logger = logging.getLogger(__name__)


def fetch_price_history(ticker: str, start: date, end: date | None = None) -> pd.DataFrame:
    """Return OHLCV DataFrame for a Brazilian ticker (appends .SA automatically)."""
    yf_ticker = ticker if ticker.endswith(".SA") else f"{ticker}.SA"
    end = end or date.today()
    try:
        df = yf.download(yf_ticker, start=start.isoformat(), end=end.isoformat(),
                         auto_adjust=True, progress=False)
        if df.empty:
            return pd.DataFrame()
        df = df.reset_index()
        df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
        df = df.rename(columns={
            "Date": "date", "Open": "open", "High": "high",
            "Low": "low", "Close": "close", "Volume": "volume",
        })
        df["date"] = pd.to_datetime(df["date"]).dt.date
        return df[["date", "open", "high", "low", "close", "volume"]]
    except Exception as e:
        logger.warning("Failed to fetch %s: %s", ticker, e)
        return pd.DataFrame()


def fetch_all_prices(start: date | None = None) -> dict[str, pd.DataFrame]:
    """Fetch price history for all configured FIAGROs."""
    start = start or date(2022, 1, 1)
    results = {}
    for fund in FIAGROS:
        ticker = fund["ticker"]
        df = fetch_price_history(ticker, start)
        if not df.empty:
            results[ticker] = df
            logger.info("Fetched %d rows for %s", len(df), ticker)
        else:
            logger.warning("No data found for %s", ticker)
    return results


def fetch_cdi_rates(start: date, end: date | None = None) -> pd.DataFrame:
    """Fetch daily CDI rates from BCB API. Returns date + daily_rate columns."""
    end = end or date.today()
    params = {
        "formato": "json",
        "dataInicial": start.strftime("%d/%m/%Y"),
        "dataFinal": end.strftime("%d/%m/%Y"),
    }
    try:
        resp = requests.get(BCB_CDI_URL, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        df = pd.DataFrame(data)
        df["date"] = pd.to_datetime(df["data"], dayfirst=True).dt.date
        df["daily_rate"] = df["valor"].astype(float) / 100  # convert % to decimal
        df["annualized"] = (1 + df["daily_rate"]) ** 252 - 1
        return df[["date", "daily_rate", "annualized"]]
    except Exception as e:
        logger.error("Failed to fetch CDI: %s", e)
        return pd.DataFrame()


def fetch_fund_info_yf(ticker: str) -> dict:
    """Get basic fund info from yfinance (name, market cap, etc.)."""
    yf_ticker = ticker if ticker.endswith(".SA") else f"{ticker}.SA"
    try:
        info = yf.Ticker(yf_ticker).info
        return {
            "name": info.get("longName") or info.get("shortName", ""),
            "market_cap": info.get("marketCap"),
        }
    except Exception:
        return {}
