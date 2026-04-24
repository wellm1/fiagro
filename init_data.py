"""
Bootstrap script — run once to:
  1. Create DB tables
  2. Insert FIAGRO records
  3. Load historical prices (2022-present)
  4. Load historical CDI
  5. Discover CNPJs from CVM and load portfolio data
  6. Run first news scan

Usage:
    python init_data.py
"""
import logging
import sys
from datetime import date

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def main():
    from database import init_db, SessionLocal
    from config import FIAGROS
    from models import Fiagro, DailyPrice, CdiRate
    from scrapers.market_data import fetch_price_history, fetch_cdi_rates
    from scrapers.cvm_data import find_cnpjs_by_tickers, fetch_nav_data
    from scrapers.news_scraper import search_sector_news
    from analytics.alert_engine import process_articles
    from config import AGRO_SECTOR_TERMS

    logger.info("Initialising database …")
    init_db()
    db = SessionLocal()

    # --- 1. Insert FIAGRO records ---
    for fund_cfg in FIAGROS:
        existing = db.query(Fiagro).filter_by(ticker=fund_cfg["ticker"]).first()
        if not existing:
            db.add(Fiagro(
                ticker=fund_cfg["ticker"],
                name=fund_cfg["name"],
                cnpj=fund_cfg.get("cnpj", ""),
            ))
    db.commit()
    logger.info("Fund records ready")

    # --- 2. Discover CNPJs from CVM ---
    tickers = [f["ticker"] for f in FIAGROS]
    logger.info("Fetching CVM catalog to discover CNPJs …")
    cnpj_map = find_cnpjs_by_tickers(tickers)
    for ticker, cnpj in cnpj_map.items():
        db.query(Fiagro).filter_by(ticker=ticker).update({"cnpj": cnpj})
    db.commit()
    logger.info("CNPJs discovered: %s", cnpj_map)

    # --- 3. Load price history ---
    start = date(2022, 1, 1)
    fiagros = db.query(Fiagro).all()
    for fiagro in fiagros:
        logger.info("Loading prices for %s …", fiagro.ticker)
        df = fetch_price_history(fiagro.ticker, start)
        if df.empty:
            logger.warning("  No price data for %s", fiagro.ticker)
            continue
        for _, row in df.iterrows():
            if not db.query(DailyPrice).filter_by(fiagro_id=fiagro.id, date=row["date"]).first():
                db.add(DailyPrice(
                    fiagro_id=fiagro.id,
                    date=row["date"],
                    close_price=row.get("close"),
                    open_price=row.get("open"),
                    high_price=row.get("high"),
                    low_price=row.get("low"),
                    volume=row.get("volume"),
                ))
        db.commit()
        logger.info("  Saved %d price rows for %s", len(df), fiagro.ticker)

    # --- 4. Load CDI history ---
    logger.info("Loading CDI rates from BCB …")
    cdi_df = fetch_cdi_rates(start)
    if not cdi_df.empty:
        for _, row in cdi_df.iterrows():
            if not db.query(CdiRate).filter_by(date=row["date"]).first():
                db.add(CdiRate(date=row["date"], daily_rate=row["daily_rate"], annualized=row["annualized"]))
        db.commit()
        logger.info("Saved %d CDI rows", len(cdi_df))
    else:
        logger.warning("No CDI data retrieved")

    # --- 5. Load NAV from CVM for funds with known CNPJs ---
    from models import DailyPrice as DP
    for fiagro in db.query(Fiagro).filter(Fiagro.cnpj != "").all():
        logger.info("Loading NAV for %s (CNPJ %s) …", fiagro.ticker, fiagro.cnpj)
        nav_df = fetch_nav_data(fiagro.cnpj, months=30)
        if nav_df.empty:
            continue
        for _, row in nav_df.iterrows():
            dp = db.query(DP).filter_by(fiagro_id=fiagro.id, date=row["date"]).first()
            if dp:
                dp.nav = row.get("nav")
                dp.net_assets = row.get("net_assets")
                if dp.close_price and dp.nav and dp.nav > 0:
                    dp.pvp = dp.close_price / dp.nav
        db.commit()
        logger.info("  NAV data saved for %s", fiagro.ticker)

    # --- 6. Initial news scan ---
    logger.info("Running initial news scan …")
    articles = search_sector_news(AGRO_SECTOR_TERMS)
    if articles:
        n = process_articles(articles, db)
        logger.info("Initial news scan: %d articles processed, alerts generated", n)

    db.close()
    logger.info("Initialisation complete!")


if __name__ == "__main__":
    main()
