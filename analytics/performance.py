"""Performance calculations: returns, Sharpe, CDI+, ranking."""
import numpy as np
import pandas as pd
from datetime import date


def _total_return(prices: pd.Series) -> float | None:
    """Cumulative return from first to last price in series."""
    prices = prices.dropna()
    if len(prices) < 2:
        return None
    return prices.iloc[-1] / prices.iloc[0] - 1


def _period_return(df: pd.DataFrame, start: date, end: date) -> float | None:
    """Return for prices between start and end dates."""
    mask = (df["date"] >= start) & (df["date"] <= end)
    sub = df[mask].sort_values("date")
    if len(sub) < 2:
        return None
    return sub["close"].iloc[-1] / sub["close"].iloc[0] - 1


def _cdi_period_return(cdi_df: pd.DataFrame, start: date, end: date) -> float | None:
    """Compound CDI return between two dates."""
    if cdi_df.empty:
        return None
    mask = (cdi_df["date"] >= start) & (cdi_df["date"] <= end)
    sub = cdi_df[mask]
    if sub.empty:
        return None
    return (1 + sub["daily_rate"]).prod() - 1


def calculate_returns(price_df: pd.DataFrame, cdi_df: pd.DataFrame) -> dict:
    """
    Calculate MTD, YTD, 12M, since-inception returns and CDI comparison.
    price_df: columns [date, close] sorted ascending
    cdi_df:   columns [date, daily_rate]
    """
    if price_df.empty or "close" not in price_df.columns:
        return {}

    price_df = price_df.sort_values("date")
    today = price_df["date"].max()
    today_dt = today if isinstance(today, date) else today.date()

    def safe_date(d):
        return d if isinstance(d, date) else d.date()

    dates = [safe_date(d) for d in price_df["date"]]
    price_df = price_df.copy()
    price_df["date"] = dates

    first_date = price_df["date"].min()
    today_dt = price_df["date"].max()

    month_start = today_dt.replace(day=1)
    year_start = today_dt.replace(month=1, day=1)
    twelve_m_start = today_dt.replace(year=today_dt.year - 1)

    mtd = _period_return(price_df, month_start, today_dt)
    ytd = _period_return(price_df, year_start, today_dt)
    twelve_m = _period_return(price_df, twelve_m_start, today_dt)
    inception = _period_return(price_df, first_date, today_dt)

    cdi_mtd = _cdi_period_return(cdi_df, month_start, today_dt)
    cdi_ytd = _cdi_period_return(cdi_df, year_start, today_dt)
    cdi_12m = _cdi_period_return(cdi_df, twelve_m_start, today_dt)
    cdi_inception = _cdi_period_return(cdi_df, first_date, today_dt)

    def cdi_plus(fund_ret, cdi_ret):
        if fund_ret is None or cdi_ret is None or cdi_ret <= -1:
            return None
        return (1 + fund_ret) / (1 + cdi_ret) - 1

    return {
        "mtd": mtd,
        "ytd": ytd,
        "twelve_m": twelve_m,
        "inception": inception,
        "cdi_mtd": cdi_mtd,
        "cdi_ytd": cdi_ytd,
        "cdi_12m": cdi_12m,
        "cdi_inception": cdi_inception,
        "cdi_plus_12m": cdi_plus(twelve_m, cdi_12m),
        "cdi_plus_inception": cdi_plus(inception, cdi_inception),
        "first_date": first_date,
    }


def calculate_sharpe(price_df: pd.DataFrame, cdi_df: pd.DataFrame, annualize: int = 252) -> float | None:
    """Sharpe ratio = (annualized return - risk-free) / annualized vol."""
    if price_df.empty or len(price_df) < 30:
        return None
    price_df = price_df.sort_values("date").copy()
    price_df["ret"] = price_df["close"].pct_change()
    ret = price_df["ret"].dropna()
    if len(ret) < 10:
        return None

    # Merge with CDI for risk-free daily rate
    merged = pd.merge(
        price_df[["date", "ret"]].dropna(),
        cdi_df[["date", "daily_rate"]],
        on="date", how="left",
    )
    merged["daily_rate"] = merged["daily_rate"].fillna(0)
    excess = merged["ret"] - merged["daily_rate"]

    ann_excess = excess.mean() * annualize
    ann_vol = excess.std() * np.sqrt(annualize)
    if ann_vol == 0:
        return None
    return ann_excess / ann_vol


def build_base100(price_df: pd.DataFrame, cdi_df: pd.DataFrame, start: date | None = None) -> pd.DataFrame:
    """
    Return DataFrame with columns [date, fund_base100, cdi_base100]
    normalized to 100 at the start date.
    """
    if price_df.empty:
        return pd.DataFrame()

    price_df = price_df.sort_values("date").copy()
    price_df["date"] = [d if isinstance(d, date) else d.date() for d in price_df["date"]]

    if start:
        price_df = price_df[price_df["date"] >= start]
    if price_df.empty:
        return pd.DataFrame()

    # Fund base 100
    first_price = price_df["close"].iloc[0]
    price_df["fund_base100"] = price_df["close"] / first_price * 100

    # CDI base 100
    cdi_sub = cdi_df[cdi_df["date"] >= price_df["date"].min()].sort_values("date")
    cdi_sub = cdi_sub.copy()
    cdi_sub["cdi_cum"] = (1 + cdi_sub["daily_rate"]).cumprod() * 100

    merged = pd.merge(price_df[["date", "fund_base100"]], cdi_sub[["date", "cdi_cum"]],
                      on="date", how="left")
    merged["cdi_base100"] = merged["cdi_cum"].ffill()
    return merged[["date", "fund_base100", "cdi_base100"]]


def calculate_ranking(fund_metrics: list[dict]) -> pd.DataFrame:
    """
    Given a list of dicts {ticker, sharpe, twelve_m, inception, pvp, ...}
    return a ranked DataFrame.
    """
    if not fund_metrics:
        return pd.DataFrame()
    df = pd.DataFrame(fund_metrics)
    numeric_cols = ["sharpe", "twelve_m", "inception", "mtd", "ytd"]
    for col in numeric_cols:
        if col in df.columns:
            df[f"rank_{col}"] = df[col].rank(ascending=False, na_option="bottom")

    score_cols = [c for c in ["rank_sharpe", "rank_twelve_m"] if c in df.columns]
    if score_cols:
        df["composite_score"] = df[score_cols].mean(axis=1)
        df = df.sort_values("composite_score")
    return df


def risk_score(sharpe: float | None, vol: float | None, pvp: float | None) -> str:
    """Simple qualitative risk label: Baixo / Moderado / Alto."""
    score = 0
    if sharpe is not None:
        score += 0 if sharpe > 0.5 else (1 if sharpe > 0 else 2)
    if vol is not None:
        ann_vol_pct = vol * 100
        score += 0 if ann_vol_pct < 5 else (1 if ann_vol_pct < 12 else 2)
    if pvp is not None:
        score += 0 if 0.85 <= pvp <= 1.10 else (1 if 0.70 <= pvp <= 1.25 else 2)
    if score <= 1:
        return "Baixo"
    if score <= 3:
        return "Moderado"
    return "Alto"
