"""Página 2 — Detalhes do Fundo: performance individual e gráfico base-100 vs CDI."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Detalhes do Fundo — FIAGRO Monitor", page_icon="📈", layout="wide")
st.title("📈 Detalhes do Fundo")


@st.cache_data(ttl=3600)
def get_tickers():
    from database import SessionLocal
    from models import Fiagro, DailyPrice
    db = SessionLocal()
    try:
        return [
            f.ticker for f in db.query(Fiagro).all()
            if db.query(DailyPrice).filter_by(fiagro_id=f.id).count() > 0
        ]
    finally:
        db.close()


@st.cache_data(ttl=3600)
def load_fund_data(ticker: str):
    from database import SessionLocal
    from models import Fiagro, DailyPrice, CdiRate
    from analytics.performance import calculate_returns, calculate_sharpe, build_base100, risk_score
    import numpy as np

    db = SessionLocal()
    try:
        f = db.query(Fiagro).filter_by(ticker=ticker).first()
        if not f:
            return None, None, None, None

        price_rows = (
            db.query(DailyPrice).filter_by(fiagro_id=f.id)
            .order_by(DailyPrice.date).all()
        )
        cdi_rows = db.query(CdiRate).order_by(CdiRate.date).all()

        price_df = pd.DataFrame([{
            "date": p.date, "close": p.close_price, "volume": p.volume,
            "nav": p.nav, "pvp": p.pvp, "net_assets": p.net_assets,
        } for p in price_rows]).dropna(subset=["close"])

        cdi_df = pd.DataFrame([{"date": r.date, "daily_rate": r.daily_rate} for r in cdi_rows])

        ret = calculate_returns(price_df, cdi_df)
        sharpe = calculate_sharpe(price_df, cdi_df)
        base100 = build_base100(price_df, cdi_df)
        ann_vol = price_df["close"].pct_change().std() * np.sqrt(252)
        risk = risk_score(sharpe, ann_vol,
                          price_df["pvp"].dropna().iloc[-1] if price_df["pvp"].dropna().any() else None)

        info = {
            "ticker": f.ticker,
            "name": f.name,
            "cnpj": f.cnpj,
            "manager": f.manager,
            "admin_fee": f.admin_fee,
            "inception_date": f.inception_date,
            "last_price": price_df["close"].iloc[-1],
            "last_date": price_df["date"].iloc[-1],
            "nav": price_df["nav"].dropna().iloc[-1] if price_df["nav"].dropna().any() else None,
            "pvp": price_df["pvp"].dropna().iloc[-1] if price_df["pvp"].dropna().any() else None,
            "net_assets": price_df["net_assets"].dropna().iloc[-1] if price_df["net_assets"].dropna().any() else None,
            "volume_avg": price_df["volume"].tail(21).mean(),
            "risk": risk,
            "ann_vol": ann_vol,
        }

        return info, ret, base100, sharpe

    finally:
        db.close()


tickers = get_tickers()
if not tickers:
    st.warning("Nenhum dado disponível. Execute `python init_data.py` primeiro.")
    st.stop()

selected = st.selectbox("Selecione o FIAGRO", tickers)
info, ret, base100, sharpe = load_fund_data(selected)

if info is None:
    st.error("Falha ao carregar dados do fundo.")
    st.stop()

# Header
st.subheader(f"{info['ticker']} — {info['name'] or ''}")
col_a, col_b, col_c, col_d = st.columns(4)
col_a.metric("Preço", f"R$ {info['last_price']:.2f}")
col_b.metric("P/VP", f"{info['pvp']:.2f}" if info["pvp"] else "—")
col_c.metric("PL", f"R$ {info['net_assets']/1e6:.1f} mi" if info["net_assets"] else "—")
col_d.metric("Risco", info["risk"])

st.divider()

# Performance grid
st.subheader("Performance")
cols = st.columns(6)

def _m(col, label, val, is_pct=True):
    if val is None:
        col.metric(label, "—")
    elif is_pct:
        col.metric(label, f"{val*100:.2f}%", delta=f"{val*100:.2f}%",
                   delta_color="normal" if val >= 0 else "inverse")
    else:
        col.metric(label, f"{val:.2f}")

_m(cols[0], "MTD", ret.get("mtd"))
_m(cols[1], "YTD", ret.get("ytd"))
_m(cols[2], "12 meses", ret.get("twelve_m"))
_m(cols[3], "Desde início", ret.get("inception"))
_m(cols[4], "CDI+ 12M", ret.get("cdi_plus_12m"))
_m(cols[5], "Sharpe", sharpe, is_pct=False)

st.divider()

# Base-100 chart
st.subheader("Evolução da cota vs CDI (base 100)")
period_options = {"6 meses": 180, "1 ano": 365, "2 anos": 730, "Desde início": 0}
period_label = st.radio("Período", list(period_options.keys()), horizontal=True, index=1)
days = period_options[period_label]

if not base100.empty:
    chart_df = base100.copy()
    chart_df["date"] = pd.to_datetime(chart_df["date"])
    if days > 0:
        cutoff = chart_df["date"].max() - pd.Timedelta(days=days)
        chart_df = chart_df[chart_df["date"] >= cutoff]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=chart_df["date"], y=chart_df["fund_base100"],
        name=selected, line=dict(color="#2196F3", width=2),
    ))
    if "cdi_base100" in chart_df.columns:
        fig.add_trace(go.Scatter(
            x=chart_df["date"], y=chart_df["cdi_base100"],
            name="CDI", line=dict(color="#FF9800", width=2, dash="dash"),
        ))
    fig.update_layout(
        height=420, hovermode="x unified",
        xaxis_title="Data", yaxis_title="Base 100",
        legend=dict(orientation="h", y=-0.15),
        margin=dict(l=0, r=0, t=10, b=0),
    )
    st.plotly_chart(fig, use_container_width=True)

    # Diff area (fund - CDI)
    if "cdi_base100" in chart_df.columns:
        chart_df["diff"] = chart_df["fund_base100"] - chart_df["cdi_base100"]
        fig2 = go.Figure()
        colors = ["green" if v >= 0 else "red" for v in chart_df["diff"]]
        fig2.add_trace(go.Bar(
            x=chart_df["date"], y=chart_df["diff"],
            marker_color=colors, name="Fundo − CDI",
        ))
        fig2.update_layout(
            height=200, hovermode="x unified",
            xaxis_title="", yaxis_title="Diferença",
            margin=dict(l=0, r=0, t=5, b=0),
        )
        st.plotly_chart(fig2, use_container_width=True)

st.divider()

# Fund info
st.subheader("Informações gerais")
info_cols = st.columns(3)
info_cols[0].markdown(f"**CNPJ:** {info['cnpj'] or '—'}")
info_cols[1].markdown(f"**Gestor:** {info['manager'] or '—'}")
info_cols[2].markdown(f"**Taxa de adm.:** {f\"{info['admin_fee']*100:.2f}% a.a.\" if info['admin_fee'] else '—'}")
info_cols[0].markdown(f"**Início:** {info['inception_date'] or ret.get('first_date') or '—'}")
info_cols[1].markdown(f"**Vol. médio 21d:** {f\"R$ {info['volume_avg']/1e3:.0f} mil\" if info['volume_avg'] else '—'}")
info_cols[2].markdown(f"**Volatilidade (a.a.):** {f\"{info['ann_vol']*100:.2f}%\" if info['ann_vol'] else '—'}")
