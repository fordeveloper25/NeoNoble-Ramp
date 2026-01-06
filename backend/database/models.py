"""
SQLAlchemy Models for PostgreSQL.

Defines all database tables for the NeoNoble Ramp platform.
"""

from datetime import datetime, timezone
from typing import Optional, List
from uuid import uuid4
import json

from sqlalchemy import (
    Column, String, Float, Boolean, DateTime, Text, Integer,
    ForeignKey, Enum as SQLEnum, JSON, Index
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

from database.config import Base


def generate_uuid():
    return str(uuid4())


def utc_now():
    return datetime.now(timezone.utc)


# ========================
# User Models
# ========================

class User(Base):
    """User account model."""
    __tablename__ = "users"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), default="user")  # user, developer, admin
    company_name = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
    
    # Relationships
    api_keys = relationship("PlatformApiKey", back_populates="user")
    transactions = relationship("Transaction", back_populates="user")


# ========================
# API Key Models
# ========================

class PlatformApiKey(Base):
    """Platform API key for developer access."""
    __tablename__ = "platform_api_keys"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    api_key = Column(String(255), unique=True, nullable=False, index=True)
    encrypted_api_secret = Column(Text, nullable=False)
    status = Column(String(50), default="active")  # active, revoked
    created_at = Column(DateTime(timezone=True), default=utc_now)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="api_keys")
    webhooks = relationship("Webhook", back_populates="api_key")


# ========================
# Transaction Models
# ========================

class Transaction(Base):
    """PoR transaction model."""
    __tablename__ = "transactions"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    quote_id = Column(String(50), unique=True, nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)
    api_key_id = Column(String(36), ForeignKey("platform_api_keys.id"), nullable=True)
    
    # Direction and type
    direction = Column(String(20), nullable=False, index=True)  # onramp, offramp
    provider = Column(String(50), default="internal_por")
    
    # Amounts
    crypto_amount = Column(Float, nullable=False)
    crypto_currency = Column(String(20), nullable=False, index=True)
    fiat_amount = Column(Float, nullable=False)
    fiat_currency = Column(String(10), default="EUR")
    exchange_rate = Column(Float, nullable=False)
    fee_amount = Column(Float, nullable=False)
    fee_percentage = Column(Float, default=1.5)
    net_payout = Column(Float, nullable=False)
    
    # Addresses and references
    deposit_address = Column(String(255), nullable=True)  # For off-ramp
    wallet_address = Column(String(255), nullable=True)   # For on-ramp
    payment_reference = Column(String(50), nullable=True)  # For on-ramp
    payment_amount = Column(Float, nullable=True)          # For on-ramp
    bank_account = Column(String(50), nullable=True)       # For off-ramp
    
    # State
    state = Column(String(50), nullable=False, index=True)
    
    # Compliance
    kyc_status = Column(String(50), default="not_required")
    kyc_provider = Column(String(50), default="internal_por")
    kyc_verified_at = Column(DateTime(timezone=True), nullable=True)
    aml_status = Column(String(50), default="not_required")
    aml_provider = Column(String(50), default="internal_por")
    aml_cleared_at = Column(DateTime(timezone=True), nullable=True)
    risk_score = Column(Float, nullable=True)
    risk_level = Column(String(20), default="low")
    por_responsible = Column(Boolean, default=True)
    
    # Timestamps
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Extra data (JSON) - renamed from metadata to avoid SQLAlchemy conflict
    extra_data = Column(JSONB, default=dict)
    
    # Relationships
    user = relationship("User", back_populates="transactions")
    timeline_events = relationship("TimelineEvent", back_populates="transaction", order_by="TimelineEvent.created_at")
    settlement = relationship("Settlement", back_populates="transaction", uselist=False)
    
    # Indexes
    __table_args__ = (
        Index("ix_transactions_state_direction", "state", "direction"),
        Index("ix_transactions_created_at", "created_at"),
    )


class TimelineEvent(Base):
    """Transaction timeline event."""
    __tablename__ = "timeline_events"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    transaction_id = Column(String(36), ForeignKey("transactions.id"), nullable=False, index=True)
    
    state = Column(String(50), nullable=False)
    message = Column(Text, nullable=False)
    provider = Column(String(50), default="internal_por")
    details = Column(JSONB, default=dict)
    
    created_at = Column(DateTime(timezone=True), default=utc_now)
    
    # Relationships
    transaction = relationship("Transaction", back_populates="timeline_events")


# ========================
# Settlement Models
# ========================

class Settlement(Base):
    """Settlement record."""
    __tablename__ = "settlements"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    settlement_id = Column(String(50), unique=True, nullable=False, index=True)
    transaction_id = Column(String(36), ForeignKey("transactions.id"), nullable=False, index=True)
    
    amount = Column(Float, nullable=False)
    currency = Column(String(10), default="EUR")
    status = Column(String(50), nullable=False, index=True)
    
    payout_reference = Column(String(100), nullable=True)
    payout_method = Column(String(50), default="internal_por")
    
    created_at = Column(DateTime(timezone=True), default=utc_now)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    extra_data = Column(JSONB, default=dict)
    
    # Relationships
    transaction = relationship("Transaction", back_populates="settlement")


# ========================
# Webhook Models
# ========================

class Webhook(Base):
    """Webhook subscription."""
    __tablename__ = "webhooks"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    webhook_id = Column(String(50), unique=True, nullable=False, index=True)
    api_key_id = Column(String(36), ForeignKey("platform_api_keys.id"), nullable=True, index=True)
    
    url = Column(String(500), nullable=False)
    secret = Column(String(255), nullable=False)
    events = Column(JSONB, default=list)  # List of event patterns
    enabled = Column(Boolean, default=True)
    
    max_retries = Column(Integer, default=5)
    retry_delays = Column(JSONB, default=lambda: [30, 60, 300, 900, 3600])
    
    created_at = Column(DateTime(timezone=True), default=utc_now)
    
    # Relationships
    api_key = relationship("PlatformApiKey", back_populates="webhooks")
    deliveries = relationship("WebhookDelivery", back_populates="webhook")


class WebhookDelivery(Base):
    """Webhook delivery record."""
    __tablename__ = "webhook_deliveries"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    delivery_id = Column(String(50), unique=True, nullable=False, index=True)
    webhook_id = Column(String(50), ForeignKey("webhooks.webhook_id"), nullable=False, index=True)
    event_id = Column(String(50), nullable=False, index=True)
    event_type = Column(String(100), nullable=False, index=True)
    
    payload = Column(JSONB, nullable=False)
    status = Column(String(50), nullable=False, index=True)  # pending, delivered, failed, retrying
    
    attempt = Column(Integer, default=0)
    response_status = Column(Integer, nullable=True)
    response_body = Column(Text, nullable=True)
    last_error = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=utc_now)
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    next_retry_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    webhook = relationship("Webhook", back_populates="deliveries")


# ========================
# Audit Models
# ========================

class AuditLog(Base):
    """Audit log entry."""
    __tablename__ = "audit_logs"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    
    event_type = Column(String(100), nullable=False, index=True)
    quote_id = Column(String(50), nullable=True, index=True)
    settlement_id = Column(String(50), nullable=True, index=True)
    
    state = Column(String(50), nullable=True)
    crypto_amount = Column(Float, nullable=True)
    crypto_currency = Column(String(20), nullable=True)
    fiat_amount = Column(Float, nullable=True)
    
    extra_details = Column(JSONB, default=dict)
    
    created_at = Column(DateTime(timezone=True), default=utc_now, index=True)
    
    __table_args__ = (
        Index("ix_audit_logs_quote_created", "quote_id", "created_at"),
    )


# ========================
# Wallet Models
# ========================

class DepositAddress(Base):
    """Generated deposit address."""
    __tablename__ = "deposit_addresses"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    
    quote_id = Column(String(50), nullable=False, index=True)
    address = Column(String(255), nullable=False, unique=True, index=True)
    derivation_path = Column(String(50), nullable=True)
    
    crypto_currency = Column(String(20), nullable=False)
    network = Column(String(50), default="bsc")
    
    status = Column(String(50), default="active")  # active, used, expired
    
    created_at = Column(DateTime(timezone=True), default=utc_now)
    used_at = Column(DateTime(timezone=True), nullable=True)


# ========================
# Blockchain Models
# ========================

class BlockchainEvent(Base):
    """Blockchain transfer event."""
    __tablename__ = "blockchain_events"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    
    transaction_hash = Column(String(100), unique=True, nullable=False, index=True)
    block_number = Column(Integer, nullable=False)
    
    from_address = Column(String(255), nullable=False)
    to_address = Column(String(255), nullable=False, index=True)
    amount = Column(String(100), nullable=False)  # Store as string for precision
    
    token_address = Column(String(255), nullable=True)
    token_symbol = Column(String(20), nullable=True)
    
    status = Column(String(50), default="pending", index=True)  # pending, processed, failed
    
    created_at = Column(DateTime(timezone=True), default=utc_now)
    processed_at = Column(DateTime(timezone=True), nullable=True)
    
    metadata = Column(JSONB, default=dict)


# ========================
# Liquidity Pool Models
# ========================

class LiquidityPool(Base):
    """PoR liquidity pool status."""
    __tablename__ = "liquidity_pools"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    
    pool_name = Column(String(50), unique=True, nullable=False, default="default")
    
    available_eur = Column(Float, default=100000000.0)  # €100M
    reserved_eur = Column(Float, default=0.0)
    
    unlimited = Column(Boolean, default=True)
    
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
