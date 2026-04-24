"""Cross-reference news articles with portfolio issuers and generate alerts."""
import logging
from datetime import datetime

from sqlalchemy.orm import Session

from config import ALERT_KEYWORDS
from models import Alert, Fiagro, NewsArticle, PortfolioHolding

logger = logging.getLogger(__name__)


def _classify_article(title: str, summary: str) -> list[dict]:
    """Return list of {alert_type, impact, label} matches for an article."""
    text = (title + " " + summary).lower()
    matches = []
    for key, cfg in ALERT_KEYWORDS.items():
        for term in cfg["terms"]:
            if term.lower() in text:
                matches.append({
                    "alert_type": cfg["label"],
                    "impact": cfg["impact"],
                    "key": key,
                })
                break
    return matches


def _get_active_issuers(db: Session) -> dict[int, list[str]]:
    """Return {fiagro_id: [issuer, ...]} from the latest portfolio data."""
    # Get the most recent reference date per fiagro
    from sqlalchemy import func
    subq = (
        db.query(
            PortfolioHolding.fiagro_id,
            func.max(PortfolioHolding.reference_date).label("max_date"),
        )
        .group_by(PortfolioHolding.fiagro_id)
        .subquery()
    )
    holdings = (
        db.query(PortfolioHolding)
        .join(subq, (PortfolioHolding.fiagro_id == subq.c.fiagro_id) &
              (PortfolioHolding.reference_date == subq.c.max_date))
        .all()
    )
    result: dict[int, list[str]] = {}
    for h in holdings:
        result.setdefault(h.fiagro_id, [])
        if h.issuer and h.issuer not in result[h.fiagro_id]:
            result[h.fiagro_id].append(h.issuer)
    return result


def process_articles(articles: list[dict], db: Session) -> int:
    """
    Persist new articles and generate alerts when issuers match fund portfolios.
    Returns number of new alerts created.
    """
    fiagros = {f.id: f for f in db.query(Fiagro).all()}
    active_issuers = _get_active_issuers(db)
    new_alerts = 0

    for art_data in articles:
        url = art_data.get("url", "")
        if not url:
            continue

        # Upsert article
        article = db.query(NewsArticle).filter_by(url=url).first()
        if not article:
            article = NewsArticle(
                title=art_data.get("title", "")[:600],
                url=url,
                source=art_data.get("source", ""),
                published_date=art_data.get("published_date"),
                summary=(art_data.get("summary", "") or "")[:2000],
            )
            db.add(article)
            db.flush()

        # Classify article for alert keywords
        matches = _classify_article(article.title, article.summary or "")
        if not matches:
            continue

        article.keywords_matched = ",".join(m["key"] for m in matches)
        searched_issuer = art_data.get("searched_issuer")

        for fiagro_id, issuers in active_issuers.items():
            matched_issuer = None
            matched_asset = None

            if searched_issuer:
                # Check if the searched issuer belongs to this fund
                for issuer in issuers:
                    if _names_overlap(searched_issuer, issuer):
                        matched_issuer = issuer
                        # Find associated asset
                        holding = (
                            db.query(PortfolioHolding)
                            .filter_by(fiagro_id=fiagro_id, issuer=issuer)
                            .order_by(PortfolioHolding.reference_date.desc())
                            .first()
                        )
                        matched_asset = holding.asset_name if holding else issuer
                        break
            else:
                # Sector news: check if any word from title matches an issuer
                title_lower = article.title.lower()
                for issuer in issuers:
                    if _names_overlap(title_lower, issuer.lower()):
                        matched_issuer = issuer
                        break

            if not matched_issuer:
                continue

            # Create alert for each match
            for match in matches:
                existing = (
                    db.query(Alert)
                    .filter_by(
                        fiagro_id=fiagro_id,
                        article_id=article.id,
                        alert_type=match["alert_type"],
                    )
                    .first()
                )
                if existing:
                    continue

                alert = Alert(
                    fiagro_id=fiagro_id,
                    article_id=article.id,
                    asset_name=matched_asset or matched_issuer,
                    issuer=matched_issuer,
                    alert_type=match["alert_type"],
                    impact_level=match["impact"],
                    summary=_build_alert_summary(article, match, fiagros.get(fiagro_id)),
                )
                db.add(alert)
                new_alerts += 1

    db.commit()
    logger.info("Generated %d new alerts", new_alerts)
    return new_alerts


def _names_overlap(a: str, b: str, min_len: int = 5) -> bool:
    """True if any word of length >= min_len from a appears in b."""
    words = [w for w in a.lower().split() if len(w) >= min_len]
    b_lower = b.lower()
    return any(w in b_lower for w in words)


def _build_alert_summary(article: NewsArticle, match: dict, fiagro: Fiagro | None) -> str:
    fund_name = fiagro.ticker if fiagro else "Fundo"
    return (
        f"[{match['alert_type']}] {fund_name}: "
        f"{article.title}. "
        f"Impacto estimado: {match['impact'].upper()}."
    )
