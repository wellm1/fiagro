"""
seed_demo.py — popula o banco com dados simulados realistas para demonstração.
Gera preços históricos, CDI, carteiras e notícias/alertas de exemplo.
"""
import random
import math
from datetime import date, timedelta, datetime

random.seed(42)

# ── dados dos fundos ──────────────────────────────────────────────────────────
FUND_PROFILES = [
    {"ticker": "RURA11", "name": "Kinea Rural FIAGRO",       "manager": "Kinea",      "admin_fee": 0.0100, "inception": date(2022,  3, 10), "base_price": 97.50,  "annual_ret": 0.133, "vol": 0.028},
    {"ticker": "RZAG11", "name": "Riza Agro FIAGRO",          "manager": "Riza Asset", "admin_fee": 0.0120, "inception": date(2022,  5, 20), "base_price": 103.20, "annual_ret": 0.118, "vol": 0.035},
    {"ticker": "KNAG11", "name": "Kinea Agro FIAGRO",         "manager": "Kinea",      "admin_fee": 0.0090, "inception": date(2022,  8,  5), "base_price": 99.00,  "annual_ret": 0.125, "vol": 0.031},
    {"ticker": "BTAG11", "name": "BTG Pactual Agro FIAGRO",   "manager": "BTG Pactual","admin_fee": 0.0080, "inception": date(2022,  6, 15), "base_price": 101.50, "annual_ret": 0.141, "vol": 0.022},
    {"ticker": "XPAG11", "name": "XP Agro FIAGRO",            "manager": "XP Asset",   "admin_fee": 0.0110, "inception": date(2022,  9, 12), "base_price": 96.80,  "annual_ret": 0.109, "vol": 0.042},
    {"ticker": "VGIA11", "name": "Valora GI Agro FIAGRO",     "manager": "Valora",     "admin_fee": 0.0150, "inception": date(2022, 11,  3), "base_price": 95.00,  "annual_ret": 0.096, "vol": 0.055},
    {"ticker": "MCHF11", "name": "Mauá Capital FIAGRO",       "manager": "Mauá Capital","admin_fee": 0.0095,"inception": date(2023,  2, 20), "base_price": 100.00, "annual_ret": 0.122, "vol": 0.030},
    {"ticker": "SNAG11", "name": "Santander Agro FIAGRO",     "manager": "Santander",  "admin_fee": 0.0085, "inception": date(2022,  7,  8), "base_price": 102.00, "annual_ret": 0.130, "vol": 0.025},
    {"ticker": "FIAG11", "name": "FIAG11 FIAGRO",             "manager": "Genial",     "admin_fee": 0.0130, "inception": date(2023,  4, 17), "base_price": 98.50,  "annual_ret": 0.115, "vol": 0.038},
    {"ticker": "PGRC11", "name": "Porto Real Agro FIAGRO",    "manager": "Porto Real", "admin_fee": 0.0140, "inception": date(2023,  1, 10), "base_price": 94.00,  "annual_ret": 0.088, "vol": 0.060},
    {"ticker": "HFOF11", "name": "Hedge Agro FIAGRO",         "manager": "Hedge Inv.", "admin_fee": 0.0100, "inception": date(2022,  4, 25), "base_price": 100.50, "annual_ret": 0.127, "vol": 0.032},
    {"ticker": "ZAGH11", "name": "Itaú Agro FIAGRO",          "manager": "Itaú Asset", "admin_fee": 0.0075, "inception": date(2022,  2, 14), "base_price": 105.00, "annual_ret": 0.138, "vol": 0.020},
]

ISSUERS_BY_FUND = {
    "RURA11": ["Amaggi Exportação", "JBS S.A.", "Copersucar", "BrasilAgro", "SLC Agrícola"],
    "RZAG11": ["Raízen S.A.", "Adecoagro", "Cocamar", "Bom Futuro", "Minerva Foods"],
    "KNAG11": ["Amaggi Exportação", "Três Tentos", "Tereos", "Cutrale", "Aprosoja"],
    "BTAG11": ["JBS S.A.", "Marfrig", "BRF", "Agrogalaxy", "Terra Nova"],
    "XPAG11": ["Copersucar", "São Martinho", "Jalles Machado", "Biosev", "Colombo"],
    "VGIA11": ["Bom Futuro", "Fiagril", "SLC Agrícola", "Cerrado Agropecuária", "Agrex"],
    "MCHF11": ["Raízen S.A.", "Copersucar", "Amaggi Exportação", "Marfrig", "JBS S.A."],
    "SNAG11": ["Terra Santa Agro", "Agrogalaxy", "BrasilAgro", "Cocamar", "Cutrale"],
    "FIAG11": ["Boa Safra", "Três Tentos", "SLC Agrícola", "Jalles Machado", "Minerva Foods"],
    "PGRC11": ["Fiagril", "Bom Futuro", "Cerrado Agropecuária", "Adecoagro", "Colombo"],
    "HFOF11": ["JBS S.A.", "Marfrig", "Raízen S.A.", "Amaggi Exportação", "Tereos"],
    "ZAGH11": ["BRF", "JBS S.A.", "SLC Agrícola", "São Martinho", "BrasilAgro"],
}

ASSET_TYPES = ["CRA", "CRA", "CRA", "FIDC", "FIDC", "LCA", "Outros"]

NEWS_SAMPLES = [
    {
        "title": "Bom Futuro enfrenta dificuldades financeiras após quebra de safra no MT",
        "source": "Valor Econômico",
        "summary": "A trading Bom Futuro, uma das maiores do país, reportou dificuldades no pagamento de CRAs emitidos em 2023 após perdas na safra de soja no Mato Grosso.",
        "issuers": ["Bom Futuro"],
        "alert_type": "Inadimplência",
        "impact": "alto",
        "keywords": "inadimplencia",
    },
    {
        "title": "Fiagril pede recuperação judicial após endividamento de R$ 2 bi",
        "source": "InfoMoney",
        "summary": "A Fiagril, distribuidora de insumos agrícolas e emissora de CRAs, entrou com pedido de recuperação judicial no Tribunal de Justiça de Mato Grosso.",
        "issuers": ["Fiagril"],
        "alert_type": "Recuperação Judicial",
        "impact": "alto",
        "keywords": "recuperacao_judicial",
    },
    {
        "title": "Estiagem prolongada no RS afeta produção de soja e perspectivas de CRAs agrícolas",
        "source": "Agência Reuters",
        "summary": "A pior seca dos últimos 40 anos no Rio Grande do Sul prejudica produtores ligados a CRAs emitidos em 2022 e 2023, aumentando risco de inadimplência.",
        "issuers": ["Boa Safra", "Três Tentos"],
        "alert_type": "Evento Climático",
        "impact": "medio",
        "keywords": "evento_climatico",
    },
    {
        "title": "JBS S.A. negocia reperfilamento de dívida com credores internacionais",
        "source": "Exame",
        "summary": "JBS iniciou conversas com detentores de bonds para estender prazo de dívidas, sem impacto imediato nos CRAs domésticos, mas gerando cautela no mercado.",
        "issuers": ["JBS S.A."],
        "alert_type": "Reestruturação de Dívida",
        "impact": "medio",
        "keywords": "reestruturacao",
    },
    {
        "title": "Agrogalaxy convoca assembleia de credores para reestruturar passivo de R$ 1,8 bi",
        "source": "Pipeline Value",
        "summary": "A distribuidora de insumos Agrogalaxy, com CRAs em vencimento em 2024 e 2025, propõe carência de 18 meses e redução de juros para evitar inadimplência.",
        "issuers": ["Agrogalaxy"],
        "alert_type": "Reestruturação de Dívida",
        "impact": "medio",
        "keywords": "reestruturacao",
    },
    {
        "title": "FIAGRO: setor registra captação recorde de R$ 12 bi em 2025",
        "source": "Broadcast Agro",
        "summary": "Os fundos de investimento do agronegócio (FIAGROs) captaram R$ 12 bilhões nos primeiros quatro meses de 2025, crescimento de 35% ante igual período de 2024.",
        "issuers": [],
        "alert_type": None,
        "impact": "baixo",
        "keywords": "",
    },
    {
        "title": "Cerrado Agropecuária atrasa pagamento de CRA de R$ 180 milhões",
        "source": "Valor Econômico",
        "summary": "A Cerrado Agropecuária comunicou ao mercado atraso de 30 dias no pagamento de juros de CRA emitido em 2022, alegando problemas operacionais temporários.",
        "issuers": ["Cerrado Agropecuária"],
        "alert_type": "Inadimplência",
        "impact": "alto",
        "keywords": "inadimplencia",
    },
]


def _generate_prices(profile: dict) -> list[dict]:
    """Simulate daily prices with GBM + mean reversion."""
    inception = profile["inception"]
    daily_ret = profile["annual_ret"] / 252
    daily_vol = profile["vol"] / math.sqrt(252)
    price = profile["base_price"]
    nav = price * random.uniform(0.97, 1.03)

    rows = []
    cur = inception
    today = date.today()
    while cur <= today:
        if cur.weekday() < 5:  # mon–fri only
            ret = random.gauss(daily_ret, daily_vol)
            price = max(price * (1 + ret), 1.0)
            nav = nav * (1 + daily_ret * 0.7 + random.gauss(0, daily_vol * 0.3))
            pvp = price / nav
            volume = random.randint(50_000, 2_000_000)
            rows.append({
                "date": cur,
                "close": round(price, 2),
                "open": round(price * random.uniform(0.998, 1.002), 2),
                "high": round(price * random.uniform(1.001, 1.008), 2),
                "low": round(price * random.uniform(0.992, 0.999), 2),
                "volume": volume,
                "nav": round(nav, 4),
                "net_assets": round(nav * random.uniform(500_000, 5_000_000), 0),
                "pvp": round(pvp, 4),
            })
        cur += timedelta(days=1)
    return rows


def _generate_cdi(start: date, end: date) -> list[dict]:
    """Simulate CDI daily rates around 10.50% a.a. (declining over time)."""
    rows = []
    # Selic trajectory: ~13.75% in 2022, declining to ~10.5% in 2024-2025
    annualized_start = 0.1375
    annualized_end = 0.1050
    cur = start
    total_days = (end - start).days or 1
    day_num = 0
    while cur <= end:
        if cur.weekday() < 5:
            progress = day_num / total_days
            ann = annualized_start + (annualized_end - annualized_start) * progress
            ann += random.gauss(0, 0.0005)
            daily = (1 + ann) ** (1 / 252) - 1
            rows.append({"date": cur, "daily_rate": daily, "annualized": ann})
        cur += timedelta(days=1)
        day_num += 1
    return rows


def _generate_portfolio(fiagro_id: int, ticker: str, ref_date: date) -> list[dict]:
    issuers = ISSUERS_BY_FUND.get(ticker, ["Emissor Genérico"])
    weights = [random.uniform(5, 35) for _ in issuers]
    total = sum(weights)
    # Normalize and add "Caixa/LFT" residual
    holdings = []
    allocated = 0.0
    for i, issuer in enumerate(issuers):
        pct = round(weights[i] / total * 85, 2)  # 85% allocated, 15% caixa
        allocated += pct
        asset_type = random.choice(ASSET_TYPES)
        holdings.append({
            "fiagro_id": fiagro_id,
            "reference_date": ref_date,
            "asset_name": f"CRA {issuer} {ref_date.year}/{random.randint(1,3):02d}",
            "asset_type": asset_type,
            "issuer": issuer,
            "percentage": pct,
            "value": None,
        })
    # Cash / LFT
    holdings.append({
        "fiagro_id": fiagro_id,
        "reference_date": ref_date,
        "asset_name": "Caixa e Equivalentes (LFT)",
        "asset_type": "Outros",
        "issuer": "Tesouro Nacional",
        "percentage": round(100 - allocated, 2),
        "value": None,
    })
    return holdings


def main():
    from database import init_db, SessionLocal
    from models import Fiagro, DailyPrice, CdiRate, PortfolioHolding, NewsArticle, Alert
    from config import FIAGROS

    print("Initialising database …")
    init_db()
    db = SessionLocal()

    # 1. Upsert FIAGRO records
    for prof in FUND_PROFILES:
        f = db.query(Fiagro).filter_by(ticker=prof["ticker"]).first()
        if not f:
            f = Fiagro(ticker=prof["ticker"])
            db.add(f)
        f.name = prof["name"]
        f.manager = prof["manager"]
        f.admin_fee = prof["admin_fee"]
        f.inception_date = prof["inception"]
    db.commit()
    print(f"  {db.query(Fiagro).count()} fundos")

    # 2. Price history
    print("Gerando preços históricos …")
    fiagros = {f.ticker: f for f in db.query(Fiagro).all()}
    for prof in FUND_PROFILES:
        ticker = prof["ticker"]
        fiagro = fiagros[ticker]
        if db.query(DailyPrice).filter_by(fiagro_id=fiagro.id).count() > 50:
            print(f"  {ticker}: já tem dados, pulando")
            continue
        rows = _generate_prices(prof)
        for r in rows:
            if not db.query(DailyPrice).filter_by(fiagro_id=fiagro.id, date=r["date"]).first():
                db.add(DailyPrice(
                    fiagro_id=fiagro.id, date=r["date"],
                    close_price=r["close"], open_price=r["open"],
                    high_price=r["high"], low_price=r["low"],
                    volume=r["volume"], nav=r["nav"],
                    net_assets=r["net_assets"], pvp=r["pvp"],
                ))
        db.commit()
        print(f"  {ticker}: {len(rows)} dias de preço")

    # 3. CDI
    print("Gerando taxas CDI …")
    if db.query(CdiRate).count() < 100:
        start = date(2022, 1, 1)
        end = date.today()
        cdi_rows = _generate_cdi(start, end)
        for r in cdi_rows:
            if not db.query(CdiRate).filter_by(date=r["date"]).first():
                db.add(CdiRate(date=r["date"], daily_rate=r["daily_rate"], annualized=r["annualized"]))
        db.commit()
        print(f"  {len(cdi_rows)} dias de CDI")
    else:
        print("  CDI: já tem dados, pulando")

    # 4. Portfolio holdings
    print("Gerando carteiras …")
    ref_date = date.today().replace(day=1) - timedelta(days=1)
    ref_date = ref_date.replace(day=1)
    for ticker, fiagro in fiagros.items():
        if db.query(PortfolioHolding).filter_by(fiagro_id=fiagro.id).count() > 3:
            continue
        holdings = _generate_portfolio(fiagro.id, ticker, ref_date)
        for h in holdings:
            db.add(PortfolioHolding(**h))
        db.commit()
        print(f"  {ticker}: {len(holdings)} ativos na carteira")

    # 5. News & alerts
    print("Inserindo notícias e alertas de exemplo …")
    for sample in NEWS_SAMPLES:
        existing = db.query(NewsArticle).filter_by(title=sample["title"]).first()
        if existing:
            article = existing
        else:
            article = NewsArticle(
                title=sample["title"],
                url=f"https://exemplo.com/noticias/{abs(hash(sample['title'])) % 100000}",
                source=sample["source"],
                published_date=datetime.now() - timedelta(days=random.randint(0, 7)),
                summary=sample["summary"],
                keywords_matched=sample.get("keywords", ""),
            )
            db.add(article)
            db.flush()

        if not sample.get("alert_type"):
            continue

        for ticker, fiagro in fiagros.items():
            fund_issuers = ISSUERS_BY_FUND.get(ticker, [])
            for issuer in sample["issuers"]:
                if issuer in fund_issuers:
                    exists = db.query(Alert).filter_by(
                        fiagro_id=fiagro.id, article_id=article.id, alert_type=sample["alert_type"]
                    ).first()
                    if not exists:
                        db.add(Alert(
                            fiagro_id=fiagro.id,
                            article_id=article.id,
                            asset_name=f"CRA {issuer}",
                            issuer=issuer,
                            alert_type=sample["alert_type"],
                            impact_level=sample["impact"],
                            summary=(
                                f"[{sample['alert_type']}] {ticker}: {sample['title']}. "
                                f"Emissor afetado: {issuer}. Impacto estimado: {sample['impact'].upper()}."
                            ),
                        ))
    db.commit()

    alerts = db.query(Alert).count()
    articles = db.query(NewsArticle).count()
    print(f"  {articles} notícias, {alerts} alertas")

    db.close()
    print("\n✅ Dados de demonstração prontos!")


if __name__ == "__main__":
    main()
