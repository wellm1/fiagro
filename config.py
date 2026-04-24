import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./fiagro.db")
NEWS_API_KEY = os.getenv("NEWS_API_KEY", "")
SCHEDULER_ENABLED = os.getenv("SCHEDULER_ENABLED", "true").lower() == "true"
SCHEDULER_HOUR = int(os.getenv("SCHEDULER_HOUR", "7"))
SCHEDULER_MINUTE = int(os.getenv("SCHEDULER_MINUTE", "0"))

BCB_CDI_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.12/dados"
BCB_SELIC_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.11/dados"
CVM_FII_BASE = "https://dados.cvm.gov.br/dados/FII/DOC/INF_MENSAL/DADOS"
CVM_CAD_URL = "https://dados.cvm.gov.br/dados/FII/CAD/DADOS/cad_fii.csv"
GOOGLE_NEWS_RSS = "https://news.google.com/rss/search?q={query}&hl=pt-BR&gl=BR&ceid=BR:pt-419"

FIAGROS = [
    {"ticker": "RURA11", "name": "Kinea Rural FIAGRO", "cnpj": ""},
    {"ticker": "RZAG11", "name": "Riza Agro FIAGRO", "cnpj": ""},
    {"ticker": "KNAG11", "name": "Kinea Agro FIAGRO", "cnpj": ""},
    {"ticker": "BTAG11", "name": "BTG Pactual Agro FIAGRO", "cnpj": ""},
    {"ticker": "XPAG11", "name": "XP Agro FIAGRO", "cnpj": ""},
    {"ticker": "VGIA11", "name": "Valora GI Agro FIAGRO", "cnpj": ""},
    {"ticker": "MCHF11", "name": "Mauá Capital FIAGRO", "cnpj": ""},
    {"ticker": "SNAG11", "name": "Santander Agro FIAGRO", "cnpj": ""},
    {"ticker": "FIAG11", "name": "FIAG11 FIAGRO", "cnpj": ""},
    {"ticker": "PGRC11", "name": "Porto Real Agro FIAGRO", "cnpj": ""},
    {"ticker": "HFOF11", "name": "Hedge Agro FIAGRO", "cnpj": ""},
    {"ticker": "ZAGH11", "name": "Itaú Agro FIAGRO", "cnpj": ""},
]

# Keywords for alert classification
ALERT_KEYWORDS = {
    "recuperacao_judicial": {
        "terms": ["recuperação judicial", "recuperacao judicial", "rj pedido", "judicial recovery"],
        "impact": "alto",
        "label": "Recuperação Judicial",
    },
    "inadimplencia": {
        "terms": ["inadimplência", "inadimplencia", "default", "calote", "não pagou", "nao pagou", "inadimplente"],
        "impact": "alto",
        "label": "Inadimplência",
    },
    "reestruturacao": {
        "terms": ["reestruturação", "reestruturacao", "renegociação", "renegociacao", "renegociar", "carência", "carencia"],
        "impact": "medio",
        "label": "Reestruturação de Dívida",
    },
    "falencia": {
        "terms": ["falência", "falencia", "liquidação judicial", "liquidacao judicial", "insolvência"],
        "impact": "alto",
        "label": "Falência/Liquidação",
    },
    "evento_climatico": {
        "terms": ["seca", "geada", "enchente", "inundação", "inundacao", "estiagem", "perda de safra"],
        "impact": "medio",
        "label": "Evento Climático",
    },
    "crise_financeira": {
        "terms": ["crise financeira", "dificuldade financeira", "dívida vencida", "divida vencida", "fluxo de caixa negativo"],
        "impact": "medio",
        "label": "Crise Financeira",
    },
}

# Generic agro sector search terms
AGRO_SECTOR_TERMS = [
    "FIAGRO",
    "CRA agronegócio",
    "FIDC agro",
    "recuperação judicial agronegócio",
    "default CRA",
]
