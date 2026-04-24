"""Página 5 — Ranking: comparativo por Sharpe, retorno e score de risco."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Ranking — FIAGRO Monitor", page_icon="🏆", layout="wide")
st.title("🏆 Ranking de FIAGROs")


@st.cache_data(ttl=3600)
def load_ranking_data():
    from database import SessionLocal
    from models import Fiagro, DailyPrice, CdiRate
    from analytics.performance import calculate_returns, calculate_sharpe, risk_score
    import numpy as np

    db = SessionLocal()
    try:
        fiagros = db.query(Fiagro).all()
        cdi_rows = db.query(CdiRate).order_by(CdiRate.date).all()
        cdi_df = pd.DataFrame([{"date": r.date, "daily_rate": r.daily_rate} for r in cdi_rows])

        rows = []
        for f in fiagros:
            price_rows = (
                db.query(DailyPrice).filter_by(fiagro_id=f.id)
                .order_by(DailyPrice.date).all()
            )
            if len(price_rows) < 30:
                continue
            price_df = pd.DataFrame([{
                "date": p.date, "close": p.close_price,
                "nav": p.nav, "pvp": p.pvp, "net_assets": p.net_assets,
            } for p in price_rows]).dropna(subset=["close"])

            ret = calculate_returns(price_df, cdi_df)
            sharpe = calculate_sharpe(price_df, cdi_df)
            ann_vol = price_df["close"].pct_change().std() * np.sqrt(252)
            pvp = price_df["pvp"].dropna().iloc[-1] if price_df["pvp"].dropna().any() else None
            risk = risk_score(sharpe, ann_vol, pvp)

            rows.append({
                "Ticker": f.ticker,
                "Nome": (f.name or f.ticker)[:40],
                "MTD %": _pct(ret.get("mtd")),
                "YTD %": _pct(ret.get("ytd")),
                "12M %": _pct(ret.get("twelve_m")),
                "Desde Início %": _pct(ret.get("inception")),
                "CDI+ 12M %": _pct(ret.get("cdi_plus_12m")),
                "Sharpe": round(sharpe, 3) if sharpe is not None else None,
                "Vol a.a. %": round(ann_vol * 100, 2) if ann_vol else None,
                "P/VP": round(pvp, 2) if pvp else None,
                "Risco": risk,
            })
        return pd.DataFrame(rows)
    finally:
        db.close()


def _pct(v):
    return round(v * 100, 2) if v is not None else None


df = load_ranking_data()

if df.empty:
    st.warning("Dados insuficientes para ranking. Execute `python init_data.py` primeiro.")
    st.stop()

tab1, tab2, tab3 = st.tabs(["📊 Ranking por Sharpe", "📈 Ranking por Retorno", "⚠️ Score de Risco"])

with tab1:
    st.subheader("Ranking por Índice de Sharpe")
    rank_df = df[df["Sharpe"].notna()].sort_values("Sharpe", ascending=False).reset_index(drop=True)
    rank_df.index += 1
    rank_df.insert(0, "Posição", rank_df.index)

    # Bar chart
    fig = px.bar(
        rank_df, x="Sharpe", y="Ticker", orientation="h",
        color="Sharpe", color_continuous_scale=["red", "#fff176", "green"],
        text="Sharpe", title="Sharpe — maior = melhor risco/retorno",
    )
    fig.update_traces(texttemplate="%{text:.2f}", textposition="outside")
    fig.update_layout(height=400, coloraxis_showscale=False, margin=dict(l=0, r=0, t=40, b=0))
    st.plotly_chart(fig, use_container_width=True)

    # Table
    show_cols = ["Posição", "Ticker", "Nome", "Sharpe", "12M %", "Vol a.a. %", "Risco"]
    st.dataframe(
        rank_df[show_cols].style.format({
            "Sharpe": "{:.3f}",
            "12M %": "{:.2f}%",
            "Vol a.a. %": "{:.2f}%",
        }, na_rep="—"),
        use_container_width=True,
    )

with tab2:
    st.subheader("Ranking por Retorno")
    period = st.radio("Período", ["MTD %", "YTD %", "12M %", "Desde Início %"], horizontal=True)
    rank_ret = df[df[period].notna()].sort_values(period, ascending=False).reset_index(drop=True)
    rank_ret.index += 1
    rank_ret.insert(0, "Posição", rank_ret.index)

    fig2 = px.bar(
        rank_ret, x=period, y="Ticker", orientation="h",
        color=period, color_continuous_scale=["red", "#fff176", "green"],
        text=period,
    )
    fig2.update_traces(texttemplate="%{text:.2f}%", textposition="outside")
    fig2.update_layout(height=400, coloraxis_showscale=False, margin=dict(l=0, r=0, t=10, b=0))
    st.plotly_chart(fig2, use_container_width=True)

    show_cols2 = ["Posição", "Ticker", "Nome", period, "Sharpe", "P/VP", "Risco"]
    st.dataframe(
        rank_ret[[c for c in show_cols2 if c in rank_ret.columns]]
        .style.format({
            period: "{:.2f}%",
            "Sharpe": "{:.3f}",
            "P/VP": "{:.2f}",
        }, na_rep="—"),
        use_container_width=True,
    )

with tab3:
    st.subheader("Score de Risco por Fundo")
    st.markdown(
        "O score de risco é calculado com base em 3 fatores: "
        "**Sharpe** (qualidade do retorno ajustado), "
        "**Volatilidade anualizada** e **P/VP** (desconto/prêmio)."
    )

    risk_order = {"Baixo": 1, "Moderado": 2, "Alto": 3}
    risk_df = df.copy()
    risk_df["_risk_order"] = risk_df["Risco"].map(risk_order)
    risk_df = risk_df.sort_values("_risk_order").reset_index(drop=True)

    risk_colors = {"Baixo": "#4caf50", "Moderado": "#ff9800", "Alto": "#f44336"}
    risk_df["Cor"] = risk_df["Risco"].map(risk_colors)

    fig3 = go.Figure()
    for risk_level in ["Baixo", "Moderado", "Alto"]:
        sub = risk_df[risk_df["Risco"] == risk_level]
        if sub.empty:
            continue
        fig3.add_trace(go.Bar(
            x=sub["Ticker"], y=sub["Vol a.a. %"],
            name=risk_level,
            marker_color=risk_colors[risk_level],
            text=sub["Vol a.a. %"].apply(lambda v: f"{v:.1f}%" if pd.notna(v) else "—"),
            textposition="outside",
        ))
    fig3.update_layout(
        height=400, barmode="group",
        xaxis_title="FIAGRO", yaxis_title="Volatilidade a.a. (%)",
        legend_title="Risco",
        margin=dict(l=0, r=0, t=10, b=0),
    )
    st.plotly_chart(fig3, use_container_width=True)

    # Risk table
    show_risk = ["Ticker", "Nome", "Sharpe", "Vol a.a. %", "P/VP", "Risco", "12M %"]
    st.dataframe(
        risk_df[[c for c in show_risk if c in risk_df.columns]]
        .style.format({
            "Sharpe": "{:.3f}",
            "Vol a.a. %": "{:.2f}%",
            "P/VP": "{:.2f}",
            "12M %": "{:.2f}%",
        }, na_rep="—")
        .applymap(
            lambda v: f"background-color: {risk_colors.get(v, '')}22; color: {risk_colors.get(v, 'black')}; font-weight: bold",
            subset=["Risco"],
        ),
        use_container_width=True,
    )

st.divider()

# Scatter: Retorno 12M vs Volatilidade
st.subheader("Retorno 12M × Volatilidade (mapa risco-retorno)")
scatter_df = df[df["12M %"].notna() & df["Vol a.a. %"].notna()].copy()
if not scatter_df.empty:
    fig4 = px.scatter(
        scatter_df, x="Vol a.a. %", y="12M %",
        text="Ticker", color="Risco",
        color_discrete_map={"Baixo": "#4caf50", "Moderado": "#ff9800", "Alto": "#f44336"},
        size_max=20,
        labels={"Vol a.a. %": "Volatilidade a.a. (%)", "12M %": "Retorno 12M (%)"},
        title="Maior y e menor x = melhor",
    )
    fig4.update_traces(textposition="top center")
    fig4.update_layout(height=450, margin=dict(l=0, r=0, t=40, b=0))
    st.plotly_chart(fig4, use_container_width=True)
