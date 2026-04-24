"""News monitoring via Google News RSS and optional NewsAPI."""
import logging
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import quote_plus

import requests

from config import GOOGLE_NEWS_RSS, NEWS_API_KEY

logger = logging.getLogger(__name__)


def fetch_google_news(query: str, max_results: int = 20) -> list[dict]:
    """Fetch articles from Google News RSS using requests + stdlib XML (no feedparser)."""
    url = GOOGLE_NEWS_RSS.format(query=quote_plus(query))
    headers = {"User-Agent": "Mozilla/5.0 (compatible; FiagroMonitor/1.0)"}
    try:
        resp = requests.get(url, headers=headers, timeout=20)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
        channel = root.find("channel")
        if channel is None:
            return []
        articles = []
        for item in channel.findall("item")[:max_results]:
            title = item.findtext("title", "")
            link = item.findtext("link", "")
            pub_raw = item.findtext("pubDate", "")
            summary = _strip_html(item.findtext("description", ""))
            source_el = item.find("source")
            source = source_el.text if source_el is not None else "Google News"

            published = None
            if pub_raw:
                try:
                    published = parsedate_to_datetime(pub_raw)
                except Exception:
                    pass

            articles.append({
                "title": title,
                "url": link,
                "source": source,
                "published_date": published,
                "summary": summary,
            })
        return articles
    except Exception as e:
        logger.warning("Google News RSS failed for '%s': %s", query, e)
        return []


def fetch_newsapi(query: str, max_results: int = 20) -> list[dict]:
    """Fetch articles from NewsAPI.org (requires API key)."""
    if not NEWS_API_KEY:
        return []
    try:
        resp = requests.get(
            "https://newsapi.org/v2/everything",
            params={
                "q": query,
                "language": "pt",
                "sortBy": "publishedAt",
                "pageSize": max_results,
                "apiKey": NEWS_API_KEY,
            },
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
        articles = []
        for item in data.get("articles", []):
            published = None
            if item.get("publishedAt"):
                try:
                    published = datetime.fromisoformat(item["publishedAt"].replace("Z", "+00:00"))
                except ValueError:
                    pass
            articles.append({
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "source": item.get("source", {}).get("name", ""),
                "published_date": published,
                "summary": item.get("description", "") or "",
            })
        return articles
    except Exception as e:
        logger.warning("NewsAPI failed for '%s': %s", query, e)
        return []


def search_issuer_news(issuers: list[str]) -> list[dict]:
    """Search news for each issuer name; de-duplicate by URL."""
    seen_urls: set[str] = set()
    all_articles: list[dict] = []

    for issuer in issuers:
        query = f'"{issuer}" agronegócio OR CRA OR FIDC OR "recuperação judicial"'
        articles = fetch_newsapi(query) or fetch_google_news(query, max_results=10)
        for art in articles:
            if art["url"] and art["url"] not in seen_urls:
                seen_urls.add(art["url"])
                art["searched_issuer"] = issuer
                all_articles.append(art)

    return all_articles


def search_sector_news(terms: list[str]) -> list[dict]:
    """Search generic agro sector news."""
    seen_urls: set[str] = set()
    all_articles: list[dict] = []
    for term in terms:
        articles = fetch_newsapi(term) or fetch_google_news(term, max_results=10)
        for art in articles:
            if art["url"] and art["url"] not in seen_urls:
                seen_urls.add(art["url"])
                art["searched_issuer"] = None
                all_articles.append(art)
    return all_articles


def _strip_html(text: str) -> str:
    import re
    return re.sub(r"<[^>]+>", "", text).strip()
