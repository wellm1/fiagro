"""Fetch fund data from CVM open data portal."""
import io
import logging
import zipfile
from datetime import date, timedelta

import pandas as pd
import requests

from config import CVM_CAD_URL, CVM_FII_BASE

logger = logging.getLogger(__name__)

# Subset of CNPJs for known FIAGROs — populated at runtime from cad_fii.csv
_FIAGRO_CNPJ_CACHE: dict[str, str] = {}  # ticker -> cnpj


def fetch_cvm_fund_catalog() -> pd.DataFrame:
    """Download the FII registration catalog from CVM."""
    try:
        resp = requests.get(CVM_CAD_URL, timeout=60)
        resp.raise_for_status()
        df = pd.read_csv(
            io.StringIO(resp.content.decode("latin-1")),
            sep=";",
            on_bad_lines="skip",
        )
        return df
    except Exception as e:
        logger.error("Failed to fetch CVM catalog: %s", e)
        return pd.DataFrame()


def find_cnpjs_by_tickers(tickers: list[str]) -> dict[str, str]:
    """Return {ticker: cnpj} mapping by searching CVM catalog."""
    df = fetch_cvm_fund_catalog()
    if df.empty:
        return {}

    result = {}
    ticker_set = {t.upper() for t in tickers}

    # Column names vary; try common ones
    name_col = next((c for c in df.columns if "DENOM" in c.upper()), None)
    cnpj_col = next((c for c in df.columns if "CNPJ" in c.upper()), None)

    if not name_col or not cnpj_col:
        return {}

    for _, row in df.iterrows():
        fund_name = str(row.get(name_col, "")).upper()
        cnpj = str(row.get(cnpj_col, "")).strip()
        for ticker in ticker_set:
            base = ticker.replace("11", "").replace("12", "")
            if base in fund_name and cnpj:
                result[ticker] = cnpj
    return result


def _monthly_report_url(year: int, month: int) -> str:
    return f"{CVM_FII_BASE}/inf_mensal_fii_{year}{month:02d}.zip"


def fetch_monthly_report(year: int, month: int) -> pd.DataFrame:
    """Download and parse CVM monthly FII report."""
    url = _monthly_report_url(year, month)
    try:
        resp = requests.get(url, timeout=60)
        if resp.status_code == 404:
            return pd.DataFrame()
        resp.raise_for_status()
        with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
            # File naming varies; pick the main complement file
            names = z.namelist()
            target = next((n for n in names if "complemento" in n.lower()), names[0])
            with z.open(target) as f:
                df = pd.read_csv(f, sep=";", encoding="latin-1", on_bad_lines="skip")
        return df
    except Exception as e:
        logger.warning("CVM monthly report %d/%d: %s", year, month, e)
        return pd.DataFrame()


def fetch_nav_data(cnpj: str, months: int = 24) -> pd.DataFrame:
    """
    Return DataFrame with date, nav (vl_quota), net_assets (vl_patrim_liq)
    for a specific fund CNPJ over the past N months.
    """
    rows = []
    today = date.today()
    for i in range(months):
        ref = today.replace(day=1) - timedelta(days=30 * i)
        df = fetch_monthly_report(ref.year, ref.month)
        if df.empty:
            continue

        cnpj_col = next((c for c in df.columns if "CNPJ" in c.upper() and "FUNDO" in c.upper()), None)
        if not cnpj_col:
            cnpj_col = next((c for c in df.columns if "CNPJ" in c.upper()), None)
        if not cnpj_col:
            continue

        cnpj_clean = cnpj.replace(".", "").replace("/", "").replace("-", "")
        mask = df[cnpj_col].astype(str).str.replace(r"\D", "", regex=True) == cnpj_clean
        fund_df = df[mask]
        if fund_df.empty:
            continue

        row = fund_df.iloc[-1]
        nav_val = _safe_float(row, ["VL_QUOTA", "VL_COTA", "vl_quota"])
        net_val = _safe_float(row, ["VL_PATRIM_LIQ", "vl_patrim_liq"])
        dt_col = next((c for c in df.columns if "DT_COMPTC" in c.upper() or "DATA" in c.upper()), None)
        dt = pd.to_datetime(row[dt_col]).date() if dt_col else ref

        rows.append({"date": dt, "nav": nav_val, "net_assets": net_val})

    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values("date")


def _safe_float(row: pd.Series, candidates: list[str]) -> float | None:
    for col in candidates:
        if col in row.index and pd.notna(row[col]):
            try:
                return float(str(row[col]).replace(",", "."))
            except ValueError:
                pass
    return None
