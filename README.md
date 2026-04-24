# 🌾 FIAGRO Monitor

Plataforma de monitoramento diário de **Fundos de Investimento nas Cadeias Agroindustriais (FIAGROs)** listados na B3.

## Funcionalidades

| Módulo | Descrição |
|--------|-----------|
| **Visão Geral** | Tabela comparativa com MTD, YTD, 12M, Sharpe, P/VP de todos os fundos |
| **Detalhes do Fundo** | Gráfico base-100 vs CDI, métricas de performance, informações cadastrais |
| **Carteira** | Composição por tipo de ativo (CRA, FIDC, Outros) e por emissor |
| **Alertas** | Monitoramento automático de notícias com cruzamento de emissores da carteira |
| **Ranking** | Ranking por Sharpe, retorno e mapa risco-retorno interativo |

## Fontes de dados

| Dado | Fonte |
|------|-------|
| Preços diários | yfinance (B3 via Yahoo Finance) |
| CDI histórico | BCB (Banco Central do Brasil) — série 12 |
| NAV / PL / VPC | CVM dados abertos (relatórios mensais FII) |
| Carteira | CVM dados abertos (INF_MENSAL) |
| Notícias | Google News RSS + NewsAPI (opcional) |

## Instalação rápida (sem Docker)

```bash
# 1. Clone e crie virtualenv
python -m venv .venv && source .venv/bin/activate

# 2. Instale dependências
pip install -r requirements.txt

# 3. Configure variáveis (opcional)
cp .env.example .env
# edite .env se quiser PostgreSQL ou NewsAPI key

# 4. Carregue dados históricos (demora ~5 min na primeira vez)
python init_data.py

# 5. Inicie o dashboard
streamlit run app.py
```

Acesse: http://localhost:8501

## Instalação com Docker

```bash
cp .env.example .env
# opcionalmente, adicione NEWS_API_KEY=sua_chave no .env

docker compose up --build
```

Acesse: http://localhost:8501

## Configuração

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `DATABASE_URL` | `sqlite:///./fiagro.db` | URL de conexão com o banco |
| `NEWS_API_KEY` | *(vazio)* | Chave da [NewsAPI.org](https://newsapi.org) (opcional) |
| `SCHEDULER_ENABLED` | `true` | Habilita atualização automática diária |
| `SCHEDULER_HOUR` | `7` | Horário da atualização (hora, fuso BRT) |
| `SCHEDULER_MINUTE` | `0` | Minuto da atualização |

## Arquitetura

```
fiagro/
├── app.py               # Streamlit — página inicial
├── pages/               # Streamlit multi-page
│   ├── 1_Visao_Geral.py
│   ├── 2_Detalhes_Fundo.py
│   ├── 3_Carteira.py
│   ├── 4_Alertas.py
│   └── 5_Ranking.py
├── scrapers/
│   ├── market_data.py   # yfinance + BCB API
│   ├── cvm_data.py      # CVM dados abertos
│   └── news_scraper.py  # Google News RSS + NewsAPI
├── analytics/
│   ├── performance.py   # MTD/YTD/12M/Sharpe/CDI+
│   └── alert_engine.py  # Cruzamento notícias × carteira
├── scheduler.py         # APScheduler (atualização diária)
├── init_data.py         # Bootstrap inicial de dados
├── models.py            # SQLAlchemy ORM
├── database.py          # Conexão com banco
└── config.py            # Configurações e lista de FIAGROs
```

## FIAGROs monitorados

- RURA11 — Kinea Rural
- RZAG11 — Riza Agro
- KNAG11 — Kinea Agro
- BTAG11 — BTG Pactual Agro
- XPAG11 — XP Agro
- VGIA11 — Valora GI Agro
- MCHF11 — Mauá Capital
- SNAG11 — Santander Agro
- FIAG11
- PGRC11 — Porto Real Agro
- HFOF11 — Hedge Agro
- ZAGH11 — Itaú Agro

Para adicionar/remover fundos, edite a lista `FIAGROS` em `config.py`.

## Sistema de alertas

O monitor busca notícias diariamente e cruza com os emissores das carteiras. Alertas são gerados automaticamente para eventos como:

- 🔴 **Alto impacto**: recuperação judicial, falência, inadimplência
- 🟡 **Médio impacto**: reestruturação de dívida, crise financeira, eventos climáticos
- 🟢 **Baixo impacto**: outros eventos relevantes

Cada alerta exibe: FIAGRO impactado, ativo/emissor afetado, tipo de evento, resumo e link para a notícia.
