"""Página 4 — Alertas: monitoramento de notícias e alertas automáticos."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Alertas — FIAGRO Monitor", page_icon="🚨", layout="wide")
st.title("🚨 Alertas e Monitoramento de Notícias")

IMPACT_COLORS = {"alto": "🔴", "medio": "🟡", "baixo": "🟢"}
IMPACT_LABELS = {"alto": "Alto", "medio": "Médio", "baixo": "Baixo"}


@st.cache_data(ttl=300)
def load_alerts(show_read: bool = False):
    from database import SessionLocal
    from models import Alert, Fiagro, NewsArticle
    db = SessionLocal()
    try:
        q = db.query(Alert, Fiagro, NewsArticle).join(
            Fiagro, Alert.fiagro_id == Fiagro.id
        ).outerjoin(NewsArticle, Alert.article_id == NewsArticle.id)
        if not show_read:
            q = q.filter(Alert.is_read == False)
        q = q.order_by(Alert.created_at.desc()).limit(200)
        rows = []
        for alert, fund, article in q.all():
            rows.append({
                "_id": alert.id,
                "FIAGRO": fund.ticker,
                "Emissor": alert.issuer or "—",
                "Ativo": alert.asset_name or "—",
                "Tipo de Evento": alert.alert_type,
                "Impacto": IMPACT_COLORS.get(alert.impact_level, "⚪") + " " + IMPACT_LABELS.get(alert.impact_level, alert.impact_level),
                "_impact_raw": alert.impact_level,
                "Data": alert.created_at,
                "Resumo": alert.summary or "—",
                "Fonte": article.url if article else None,
                "Título notícia": article.title if article else "—",
                "Lido": alert.is_read,
            })
        return pd.DataFrame(rows)
    finally:
        db.close()


@st.cache_data(ttl=300)
def load_recent_articles():
    from database import SessionLocal
    from models import NewsArticle
    db = SessionLocal()
    try:
        articles = db.query(NewsArticle).order_by(NewsArticle.created_at.desc()).limit(50).all()
        return pd.DataFrame([{
            "Título": a.title,
            "Fonte": a.source,
            "Data": a.published_date,
            "URL": a.url,
            "Keywords": a.keywords_matched or "",
        } for a in articles])
    finally:
        db.close()


def mark_all_read():
    from database import SessionLocal
    from models import Alert
    db = SessionLocal()
    try:
        db.query(Alert).filter_by(is_read=False).update({"is_read": True})
        db.commit()
    finally:
        db.close()


# Controls
ctrl1, ctrl2, ctrl3 = st.columns([2, 2, 2])
show_read = ctrl1.checkbox("Mostrar alertas já lidos", value=False)
if ctrl2.button("✅ Marcar todos como lidos"):
    mark_all_read()
    st.cache_data.clear()
    st.rerun()

if ctrl3.button("🔄 Buscar notícias agora"):
    with st.spinner("Buscando notícias…"):
        from scheduler import _update_news_and_alerts
        from database import SessionLocal
        db = SessionLocal()
        try:
            _update_news_and_alerts(db)
        finally:
            db.close()
    st.cache_data.clear()
    st.rerun()

# Alerts table
df = load_alerts(show_read)

if df.empty:
    st.success("✅ Nenhum alerta pendente.")
else:
    # Impact filter
    impact_filter = st.multiselect(
        "Filtrar por impacto",
        options=["alto", "medio", "baixo"],
        default=["alto", "medio"],
        format_func=lambda x: IMPACT_LABELS.get(x, x),
    )
    filtered = df[df["_impact_raw"].isin(impact_filter)] if impact_filter else df

    st.markdown(f"**{len(filtered)} alerta(s)**")

    for _, row in filtered.iterrows():
        impact_raw = row["_impact_raw"]
        border_color = {"alto": "#f44336", "medio": "#ff9800", "baixo": "#4caf50"}.get(impact_raw, "#ccc")

        with st.expander(
            f"{IMPACT_COLORS.get(impact_raw, '⚪')} **{row['FIAGRO']}** — {row['Tipo de Evento']} — {row['Emissor']}",
            expanded=(impact_raw == "alto"),
        ):
            c1, c2, c3 = st.columns(3)
            c1.markdown(f"**FIAGRO:** {row['FIAGRO']}")
            c2.markdown(f"**Emissor:** {row['Emissor']}")
            c3.markdown(f"**Ativo:** {row['Ativo']}")

            c4, c5 = st.columns(2)
            c4.markdown(f"**Tipo de evento:** {row['Tipo de Evento']}")
            c5.markdown(f"**Impacto estimado:** {row['Impacto']}")

            st.markdown(f"**Resumo:** {row['Resumo']}")
            if row.get("Título notícia") and row["Título notícia"] != "—":
                st.markdown(f"**Notícia:** {row['Título notícia']}")
            if row.get("Fonte"):
                st.markdown(f"[🔗 Ler notícia completa]({row['Fonte']})")
            st.caption(f"Criado em: {row['Data']}")

st.divider()

# Recent articles section
st.subheader("📰 Notícias recentes monitoradas")
articles_df = load_recent_articles()
if articles_df.empty:
    st.info("Nenhuma notícia coletada ainda.")
else:
    # Search filter
    art_search = st.text_input("🔍 Filtrar notícias", "")
    if art_search:
        articles_df = articles_df[
            articles_df["Título"].str.contains(art_search, case=False, na=False)
        ]
    for _, art in articles_df.iterrows():
        date_str = art["Data"].strftime("%d/%m/%Y %H:%M") if pd.notna(art["Data"]) else "—"
        kw = f" • 🏷️ `{art['Keywords']}`" if art["Keywords"] else ""
        if art.get("URL"):
            st.markdown(f"- [{art['Título']}]({art['URL']}) — {art['Fonte']} • {date_str}{kw}")
        else:
            st.markdown(f"- **{art['Título']}** — {art['Fonte']} • {date_str}{kw}")
