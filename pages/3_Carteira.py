"""Página 3 — Carteira: composição por tipo de ativo e por emissor."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Carteira — FIAGRO Monitor", page_icon="🗂️", layout="wide")
st.title("🗂️ Composição da Carteira")


@st.cache_data(ttl=3600)
def get_tickers_with_portfolio():
    from database import SessionLocal
    from models import Fiagro, PortfolioHolding
    db = SessionLocal()
    try:
        ids = {h.fiagro_id for h in db.query(PortfolioHolding).all()}
        return [f.ticker for f in db.query(Fiagro).filter(Fiagro.id.in_(ids)).all()]
    finally:
        db.close()


@st.cache_data(ttl=3600)
def load_portfolio(ticker: str):
    from database import SessionLocal
    from models import Fiagro, PortfolioHolding
    from sqlalchemy import func

    db = SessionLocal()
    try:
        f = db.query(Fiagro).filter_by(ticker=ticker).first()
        if not f:
            return pd.DataFrame(), None

        # Latest reference date
        latest_date = (
            db.query(func.max(PortfolioHolding.reference_date))
            .filter_by(fiagro_id=f.id)
            .scalar()
        )
        if not latest_date:
            return pd.DataFrame(), None

        holdings = (
            db.query(PortfolioHolding)
            .filter_by(fiagro_id=f.id, reference_date=latest_date)
            .all()
        )
        df = pd.DataFrame([{
            "Ativo": h.asset_name,
            "Tipo": h.asset_type or "Outros",
            "Emissor": h.issuer or "—",
            "Participação %": h.percentage,
            "Valor (R$)": h.value,
        } for h in holdings])
        return df, latest_date
    finally:
        db.close()


all_tickers = get_tickers_with_portfolio()

if not all_tickers:
    st.info(
        "Dados de carteira não disponíveis ainda.\n\n"
        "Os dados de carteira vêm dos relatórios mensais da CVM e são carregados "
        "automaticamente após o `python init_data.py` para fundos com CNPJ identificado."
    )

    # Show demo layout with placeholder data
    st.subheader("Exemplo de visualização (dados fictícios)")
    demo = pd.DataFrame({
        "Tipo": ["CRA", "CRA", "FIDC", "FIDC", "Outros"],
        "Participação %": [35.0, 25.0, 20.0, 12.0, 8.0],
        "Emissor": ["Empresa A", "Empresa B", "FIDC Agro X", "FIDC Rural Y", "Caixa"],
    })
    col1, col2 = st.columns(2)
    fig = px.pie(demo, names="Tipo", values="Participação %", title="Por tipo de ativo",
                 color_discrete_sequence=px.colors.qualitative.Set2)
    col1.plotly_chart(fig, use_container_width=True)

    fig2 = px.bar(demo.sort_values("Participação %"), x="Participação %", y="Emissor",
                  orientation="h", title="Por emissor", color="Tipo",
                  color_discrete_sequence=px.colors.qualitative.Set2)
    col2.plotly_chart(fig2, use_container_width=True)
    st.stop()

selected = st.selectbox("Selecione o FIAGRO", all_tickers)
df, ref_date = load_portfolio(selected)

if df.empty:
    st.warning(f"Nenhum dado de carteira para {selected}.")
    st.stop()

st.caption(f"Data de referência: {ref_date}")

# Summary metrics
col1, col2, col3 = st.columns(3)
col1.metric("Ativos na carteira", len(df))
col2.metric("Tipos de ativo", df["Tipo"].nunique())
col3.metric("Emissores únicos", df["Emissor"].nunique())

st.divider()

# Charts row
chart_col1, chart_col2 = st.columns(2)

# By asset type
type_df = df.groupby("Tipo")["Participação %"].sum().reset_index().sort_values("Participação %", ascending=False)
fig_type = px.pie(
    type_df, names="Tipo", values="Participação %",
    title="Alocação por tipo de produto",
    color_discrete_sequence=px.colors.qualitative.Set2,
    hole=0.4,
)
fig_type.update_traces(textposition="outside", textinfo="percent+label")
chart_col1.plotly_chart(fig_type, use_container_width=True)

# By issuer (top 15)
issuer_df = (
    df.groupby("Emissor")["Participação %"].sum()
    .reset_index()
    .sort_values("Participação %", ascending=False)
    .head(15)
)
fig_issuer = px.bar(
    issuer_df.sort_values("Participação %"),
    x="Participação %", y="Emissor", orientation="h",
    title="Top 15 emissores",
    color="Participação %",
    color_continuous_scale=["#e8f5e9", "#1b5e20"],
    text="Participação %",
)
fig_issuer.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
fig_issuer.update_layout(coloraxis_showscale=False, margin=dict(l=0, r=0, t=40, b=0))
chart_col2.plotly_chart(fig_issuer, use_container_width=True)

st.divider()

# Concentration analysis
st.subheader("Concentração da carteira")
sorted_df = df.sort_values("Participação %", ascending=False).reset_index(drop=True)
top5 = sorted_df.head(5)["Participação %"].sum()
top10 = sorted_df.head(10)["Participação %"].sum()

conc_col1, conc_col2 = st.columns(2)
conc_col1.metric("Top 5 ativos", f"{top5:.1f}%")
conc_col2.metric("Top 10 ativos", f"{top10:.1f}%")

# Full holdings table
st.subheader("Detalhamento completo")
disp = df.sort_values("Participação %", ascending=False).reset_index(drop=True)
disp.index += 1
st.dataframe(
    disp.style.format({
        "Participação %": "{:.2f}%",
        "Valor (R$)": "R$ {:,.0f}",
    }, na_rep="—"),
    use_container_width=True,
    height=500,
)
