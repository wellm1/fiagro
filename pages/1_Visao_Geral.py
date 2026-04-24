"""Página 1 — Visão Geral: tabela comparativa de todos os FIAGROs."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Visão Geral — FIAGRO Monitor", page_icon="📊", layout="wide")
st.title("📊 Visão Geral")


@st.cache_data(ttl=3600)
def load_overview():
    from database import SessionLocal
    from models import Fiagro, DailyPrice, CdiRate
    from analytics.performance import calculate_returns, calculate_sharpe, risk_score
    import numpy as np

    db = SessionLocal()
    try:
        fiagros = db.query(Fiagro).all()
        cdi_rows = db.query(CdiRate).order_by(CdiRate.date).all()
        cdi_df = pd.DataFrame(
            [{"date": r.date, "daily_rate": r.daily_rate} for r in cdi_rows]
        )

        rows = []
        for f in fiagros:
            price_rows = (
                db.query(DailyPrice)
                .filter_by(fiagro_id=f.id)
                .order_by(DailyPrice.date)
                .all()
            )
            if not price_rows:
                continue
            price_df = pd.DataFrame([{
                "date": p.date, "close": p.close_price,
                "nav": p.nav, "pvp": p.pvp, "net_assets": p.net_assets,
            } for p in price_rows])
            price_df = price_df.dropna(subset=["close"])

            ret = calculate_returns(price_df, cdi_df)
            sharpe = calculate_sharpe(price_df, cdi_df)
            last = price_df.iloc[-1]

            nav_val = price_df["nav"].dropna().iloc[-1] if price_df["nav"].dropna().any() else None
            pvp_val = price_df["pvp"].dropna().iloc[-1] if price_df["pvp"].dropna().any() else None
            net_val = price_df["net_assets"].dropna().iloc[-1] if price_df["net_assets"].dropna().any() else None

            ann_vol = price_df["close"].pct_change().std() * np.sqrt(252)
            risk = risk_score(sharpe, ann_vol, pvp_val)

            rows.append({
                "Ticker": f.ticker,
                "Nome": f.name or f.ticker,
                "Preço": last["close"],
                "P/VP": pvp_val,
                "PL (R$ mi)": round(net_val / 1e6, 1) if net_val else None,
                "MTD %": _pct(ret.get("mtd")),
                "YTD %": _pct(ret.get("ytd")),
                "12M %": _pct(ret.get("twelve_m")),
                "Desde Início %": _pct(ret.get("inception")),
                "CDI+ 12M %": _pct(ret.get("cdi_plus_12m")),
                "Sharpe": round(sharpe, 2) if sharpe else None,
                "Risco": risk,
                "Início": ret.get("first_date"),
            })
        return pd.DataFrame(rows)
    finally:
        db.close()


def _pct(v):
    return round(v * 100, 2) if v is not None else None


def _color_pct(val):
    if val is None:
        return ""
    color = "green" if val > 0 else "red"
    return f"color: {color}"


with st.spinner("Carregando dados…"):
    df = load_overview()

if df.empty:
    st.warning("Nenhum dado disponível. Execute `python init_data.py` primeiro.")
    st.stop()

# Summary metrics
col1, col2, col3, col4 = st.columns(4)
col1.metric("FIAGROs com dados", len(df))
col2.metric("Melhor 12M", f"{df['12M %'].max():.2f}%" if df["12M %"].notna().any() else "—")
col3.metric("Maior Sharpe", f"{df['Sharpe'].max():.2f}" if df["Sharpe"].notna().any() else "—")
col4.metric("Maior PL", f"R$ {df['PL (R$ mi)'].max():.0f} mi" if df["PL (R$ mi)"].notna().any() else "—")

st.divider()

# Filters
col_f1, col_f2 = st.columns([3, 1])
search = col_f1.text_input("🔍 Filtrar por ticker ou nome", "")
risk_filter = col_f2.selectbox("Risco", ["Todos", "Baixo", "Moderado", "Alto"])

filtered = df.copy()
if search:
    mask = (
        filtered["Ticker"].str.contains(search, case=False, na=False) |
        filtered["Nome"].str.contains(search, case=False, na=False)
    )
    filtered = filtered[mask]
if risk_filter != "Todos":
    filtered = filtered[filtered["Risco"] == risk_filter]

# Styled table
pct_cols = ["MTD %", "YTD %", "12M %", "Desde Início %", "CDI+ 12M %"]
styled = (
    filtered.style
    .format({
        "Preço": "R$ {:.2f}",
        "P/VP": "{:.2f}",
        "PL (R$ mi)": "R$ {:.1f}",
        **{c: "{:.2f}%" for c in pct_cols if c in filtered.columns},
        "Sharpe": "{:.2f}",
    }, na_rep="—")
    .applymap(_color_pct, subset=[c for c in pct_cols if c in filtered.columns])
)

st.dataframe(styled, use_container_width=True, height=500)
st.caption(f"Exibindo {len(filtered)} de {len(df)} fundos • Atualizado em {pd.Timestamp.now().strftime('%d/%m/%Y %H:%M')}")

# Quick chart: 12M returns bar
st.subheader("Retorno 12 meses (%)")
chart_df = df[df["12M %"].notna()].sort_values("12M %", ascending=True)
if not chart_df.empty:
    import plotly.express as px
    fig = px.bar(
        chart_df, x="12M %", y="Ticker", orientation="h",
        color="12M %", color_continuous_scale=["red", "lightyellow", "green"],
        text="12M %",
    )
    fig.update_traces(texttemplate="%{text:.2f}%", textposition="outside")
    fig.update_layout(height=400, showlegend=False, coloraxis_showscale=False,
                      margin=dict(l=0, r=0, t=10, b=0))
    st.plotly_chart(fig, use_container_width=True)
