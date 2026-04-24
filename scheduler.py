"""Daily update scheduler — runs data collection tasks at configured time."""
import logging
from datetime import date, timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from config import FIAGROS, SCHEDULER_HOUR, SCHEDULER_MINUTE, AGRO_SECTOR_TERMS

logger = logging.getLogger(__name__)
_scheduler: BackgroundScheduler | None = None


def run_daily_update():
    """Full daily pipeline: prices → CDI → NAV → news → alerts."""
    logger.info("=== Daily update started ===")
    from database import SessionLocal, init_db
    from scrapers.market_data import fetch_all_prices, fetch_cdi_rates
    from scrapers.news_scraper import search_issuer_news, search_sector_news
    from analytics.alert_engine import process_articles
    from models import Fiagro, DailyPrice, CdiRate, PortfolioHolding

    init_db()
    db = SessionLocal()
    try:
        _update_prices(db)
        _update_cdi(db)
        _update_news_and_alerts(db)
    finally:
        db.close()
    logger.info("=== Daily update finished ===")


def _update_prices(db):
    from scrapers.market_data import fetch_price_history
    from models import Fiagro, DailyPrice

    for fund_cfg in FIAGROS:
        ticker = fund_cfg["ticker"]
        fiagro = db.query(Fiagro).filter_by(ticker=ticker).first()
        if not fiagro:
            continue

        # Find the last price date we have
        latest = (
            db.query(DailyPrice)
            .filter_by(fiagro_id=fiagro.id)
            .order_by(DailyPrice.date.desc())
            .first()
        )
        start = latest.date + timedelta(days=1) if latest else date(2022, 1, 1)
        if start > date.today():
            continue

        df = fetch_price_history(ticker, start)
        if df.empty:
            continue

        for _, row in df.iterrows():
            existing = db.query(DailyPrice).filter_by(
                fiagro_id=fiagro.id, date=row["date"]
            ).first()
            if existing:
                continue
            dp = DailyPrice(
                fiagro_id=fiagro.id,
                date=row["date"],
                close_price=row.get("close"),
                open_price=row.get("open"),
                high_price=row.get("high"),
                low_price=row.get("low"),
                volume=row.get("volume"),
            )
            db.add(dp)
        db.commit()
        logger.info("Updated prices for %s", ticker)


def _update_cdi(db):
    from scrapers.market_data import fetch_cdi_rates
    from models import CdiRate

    latest = db.query(CdiRate).order_by(CdiRate.date.desc()).first()
    start = latest.date + timedelta(days=1) if latest else date(2022, 1, 1)
    if start > date.today():
        return

    df = fetch_cdi_rates(start)
    if df.empty:
        return
    for _, row in df.iterrows():
        if not db.query(CdiRate).filter_by(date=row["date"]).first():
            db.add(CdiRate(date=row["date"], daily_rate=row["daily_rate"], annualized=row["annualized"]))
    db.commit()
    logger.info("Updated CDI rates up to %s", df["date"].max())


def _update_news_and_alerts(db):
    from scrapers.news_scraper import search_issuer_news, search_sector_news
    from analytics.alert_engine import process_articles
    from models import PortfolioHolding

    # Gather all unique issuers from portfolios
    issuers = [
        h.issuer for h in db.query(PortfolioHolding.issuer).distinct()
        if h.issuer
    ]
    articles = []
    if issuers:
        articles += search_issuer_news(issuers)
    articles += search_sector_news(AGRO_SECTOR_TERMS)

    if articles:
        n = process_articles(articles, db)
        logger.info("Processed %d articles, generated alerts", n)


def start_scheduler():
    global _scheduler
    if _scheduler and _scheduler.running:
        return
    _scheduler = BackgroundScheduler(timezone="America/Sao_Paulo")
    _scheduler.add_job(
        run_daily_update,
        CronTrigger(hour=SCHEDULER_HOUR, minute=SCHEDULER_MINUTE),
        id="daily_update",
        replace_existing=True,
    )
    _scheduler.start()
    logger.info("Scheduler started — daily update at %02d:%02d BRT", SCHEDULER_HOUR, SCHEDULER_MINUTE)


def stop_scheduler():
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
