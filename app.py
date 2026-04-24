"""
FIAGRO Monitor — main Streamlit entry point.
Run with: streamlit run app.py
"""
import logging
import sys
import os

import streamlit as st

# Add project root to path so pages/ can import backend modules
sys.path.insert(0, os.path.dirname(__file__))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

st.set_page_config(
    page_title="FIAGRO Monitor",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialise DB and scheduler once per process
@st.cache_resource
def _bootstrap():
    from database import init_db
    from config import SCHEDULER_ENABLED
    init_db()
    if SCHEDULER_ENABLED:
        from scheduler import start_scheduler
        start_scheduler()
    return True

_bootstrap()

# ---------- sidebar ----------
st.sidebar.title("🌾 FIAGRO Monitor")
st.sidebar.markdown("Monitoramento diário de FIAGROs listados na B3")
st.sidebar.divider()

with st.sidebar:
    if st.button("🔄 Atualizar dados agora", use_container_width=True):
        with st.spinner("Atualizando…"):
            from scheduler import run_daily_update
            run_daily_update()
        st.success("Dados atualizados!")

st.sidebar.divider()
st.sidebar.caption("Dados: B3 / CVM / BCB • Notícias: Google News")

# ---------- home page ----------
st.title("🌾 FIAGRO Monitor")
st.markdown(
    "Plataforma de monitoramento diário de **Fundos de Investimento nas Cadeias Agroindustriais** "
    "listados na B3."
)

from database import SessionLocal
from models import Fiagro, DailyPrice, Alert

db = SessionLocal()
try:
    total_funds = db.query(Fiagro).count()
    total_prices = db.query(DailyPrice).count()
    unread_alerts = db.query(Alert).filter_by(is_read=False).count()
finally:
    db.close()

col1, col2, col3 = st.columns(3)
col1.metric("FIAGROs monitorados", total_funds)
col2.metric("Registros de preço", f"{total_prices:,}")
col3.metric("Alertas não lidos", unread_alerts, delta_color="inverse")

st.divider()
st.markdown("""
### Navegação

| Página | Descrição |
|--------|-----------|
| **1 Visão Geral** | Tabela comparativa de todos os FIAGROs com métricas-chave |
| **2 Detalhes do Fundo** | Performance individual, gráfico base-100 vs CDI, informações |
| **3 Carteira** | Composição por tipo de ativo e emissor |
| **4 Alertas** | Monitoramento de notícias e alertas automáticos |
| **5 Ranking** | Ranking por Sharpe, retorno e score de risco |

Use o menu lateral para navegar entre as páginas.

---
**Primeira vez?** Clique em **Atualizar dados agora** na barra lateral ou execute:
```bash
python init_data.py
```
""")

if total_prices == 0:
    st.warning(
        "⚠️ Nenhum dado carregado ainda. Execute `python init_data.py` "
        "ou clique em **Atualizar dados agora** para carregar os dados históricos."
    )
