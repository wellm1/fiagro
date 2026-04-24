from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Date, DateTime,
    Boolean, Text, ForeignKey, UniqueConstraint,
)
from sqlalchemy.orm import relationship
from database import Base


class Fiagro(Base):
    __tablename__ = "fiagros"

    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String(10), unique=True, nullable=False, index=True)
    name = Column(String(200))
    cnpj = Column(String(20))
    manager = Column(String(200))
    admin_fee = Column(Float)           # % ao ano
    inception_date = Column(Date)
    last_updated = Column(DateTime, default=datetime.utcnow)

    prices = relationship("DailyPrice", back_populates="fiagro", cascade="all, delete-orphan")
    holdings = relationship("PortfolioHolding", back_populates="fiagro", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="fiagro", cascade="all, delete-orphan")


class DailyPrice(Base):
    __tablename__ = "daily_prices"
    __table_args__ = (UniqueConstraint("fiagro_id", "date"),)

    id = Column(Integer, primary_key=True, index=True)
    fiagro_id = Column(Integer, ForeignKey("fiagros.id"), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    close_price = Column(Float)
    open_price = Column(Float)
    high_price = Column(Float)
    low_price = Column(Float)
    volume = Column(Float)
    nav = Column(Float)         # Valor Patrimonial por Cota (VPC)
    net_assets = Column(Float)  # Patrimônio Líquido
    pvp = Column(Float)         # Preço / Valor Patrimonial

    fiagro = relationship("Fiagro", back_populates="prices")


class CdiRate(Base):
    __tablename__ = "cdi_rates"

    date = Column(Date, primary_key=True)
    daily_rate = Column(Float, nullable=False)   # taxa diária em decimal (0.000432...)
    annualized = Column(Float)                    # taxa anualizada em %


class PortfolioHolding(Base):
    __tablename__ = "portfolio_holdings"
    __table_args__ = (UniqueConstraint("fiagro_id", "reference_date", "asset_name"),)

    id = Column(Integer, primary_key=True, index=True)
    fiagro_id = Column(Integer, ForeignKey("fiagros.id"), nullable=False, index=True)
    reference_date = Column(Date, nullable=False)
    asset_name = Column(String(500))
    asset_type = Column(String(50))     # CRA, FIDC, LCA, LCI, Outros
    issuer = Column(String(300))
    percentage = Column(Float)          # % da carteira
    value = Column(Float)               # R$ valor

    fiagro = relationship("Fiagro", back_populates="holdings")


class NewsArticle(Base):
    __tablename__ = "news_articles"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(600), nullable=False)
    url = Column(Text, unique=True)
    source = Column(String(150))
    published_date = Column(DateTime)
    summary = Column(Text)
    keywords_matched = Column(Text)     # comma-separated
    created_at = Column(DateTime, default=datetime.utcnow)

    alerts = relationship("Alert", back_populates="article", cascade="all, delete-orphan")


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    fiagro_id = Column(Integer, ForeignKey("fiagros.id"), nullable=False, index=True)
    article_id = Column(Integer, ForeignKey("news_articles.id"), nullable=True)
    asset_name = Column(String(300))
    issuer = Column(String(300))
    alert_type = Column(String(100))
    impact_level = Column(String(20))   # alto, medio, baixo
    summary = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    is_read = Column(Boolean, default=False)

    fiagro = relationship("Fiagro", back_populates="alerts")
    article = relationship("NewsArticle", back_populates="alerts")
