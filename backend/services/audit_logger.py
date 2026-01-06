"""
Audit Logger Service for PoR Engine.

Provides comprehensive audit logging for:
- Transaction lifecycle events
- Settlement processing traces
- Compliance status changes
- System health monitoring

All logs are structured JSON for easy parsing and analysis.
"""

import os
import logging
import json
from typing import Dict, Optional, Any
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorDatabase
from enum import Enum

# Configure structured logging
logger = logging.getLogger("por.audit")


class AuditEventType(str, Enum):
    """Audit event types."""
    # Transaction lifecycle
    QUOTE_CREATED = "quote.created"
    QUOTE_ACCEPTED = "quote.accepted"
    QUOTE_EXPIRED = "quote.expired"
    QUOTE_CANCELLED = "quote.cancelled"
    
    # Deposit events
    DEPOSIT_PENDING = "deposit.pending"
    DEPOSIT_DETECTED = "deposit.detected"
    DEPOSIT_CONFIRMED = "deposit.confirmed"
    DEPOSIT_FAILED = "deposit.failed"
    
    # Settlement events
    SETTLEMENT_INITIATED = "settlement.initiated"
    SETTLEMENT_PROCESSING = "settlement.processing"
    SETTLEMENT_COMPLETED = "settlement.completed"
    SETTLEMENT_FAILED = "settlement.failed"
    
    # Payout events
    PAYOUT_INITIATED = "payout.initiated"
    PAYOUT_COMPLETED = "payout.completed"
    PAYOUT_FAILED = "payout.failed"
    
    # Compliance events
    KYC_STATUS_CHANGE = "compliance.kyc_status_change"
    AML_STATUS_CHANGE = "compliance.aml_status_change"
    RISK_ASSESSMENT = "compliance.risk_assessment"
    
    # System events
    SYSTEM_STARTUP = "system.startup"
    SYSTEM_SHUTDOWN = "system.shutdown"
    SYSTEM_ERROR = "system.error"
    RATE_LIMIT_HIT = "system.rate_limit"


class AuditLogger:
    """
    Structured audit logger for PoR engine.
    
    Logs to both console (structured JSON) and MongoDB for persistence.
    """
    
    def __init__(self, db: Optional[AsyncIOMotorDatabase] = None):
        self.db = db
        self.audit_collection = db.audit_logs if db is not None else None
        self._enabled = True
        self._log_to_db = db is not None
    
    async def initialize(self):
        """Initialize audit logger."""
        if self.audit_collection:
            await self.audit_collection.create_index("timestamp")
            await self.audit_collection.create_index("event_type")
            await self.audit_collection.create_index("quote_id")
            await self.audit_collection.create_index("settlement_id")
            logger.info("Audit logger initialized with MongoDB persistence")
        else:
            logger.info("Audit logger initialized (console only)")
    
    def _format_log(self, event_type: AuditEventType, data: Dict) -> str:
        """Format log entry as structured JSON."""
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type.value,
            "service": "por_engine",
            **data
        }
        return json.dumps(log_entry)
    
    async def log(
        self,
        event_type: AuditEventType,
        quote_id: Optional[str] = None,
        settlement_id: Optional[str] = None,
        user_id: Optional[str] = None,
        api_key_id: Optional[str] = None,
        details: Optional[Dict] = None,
        error: Optional[str] = None
    ):
        """Log an audit event."""
        if not self._enabled:
            return
        
        data = {
            "quote_id": quote_id,
            "settlement_id": settlement_id,
            "user_id": user_id,
            "api_key_id": api_key_id,
            "details": details or {},
            "error": error
        }
        
        # Remove None values
        data = {k: v for k, v in data.items() if v is not None}
        
        # Log to console (structured JSON)
        log_message = self._format_log(event_type, data)
        
        if error:
            logger.error(log_message)
        else:
            logger.info(log_message)
        
        # Log to MongoDB if enabled
        if self._log_to_db and self.audit_collection:
            try:
                doc = {
                    "timestamp": datetime.now(timezone.utc),
                    "event_type": event_type.value,
                    **data
                }
                await self.audit_collection.insert_one(doc)
            except Exception as e:
                logger.error(f"Failed to persist audit log: {e}")
    
    async def log_transaction_event(
        self,
        event_type: AuditEventType,
        quote_id: str,
        state: str,
        crypto_amount: Optional[float] = None,
        crypto_currency: Optional[str] = None,
        fiat_amount: Optional[float] = None,
        details: Optional[Dict] = None
    ):
        """Log a transaction lifecycle event."""
        await self.log(
            event_type=event_type,
            quote_id=quote_id,
            details={
                "state": state,
                "crypto_amount": crypto_amount,
                "crypto_currency": crypto_currency,
                "fiat_amount": fiat_amount,
                **(details or {})
            }
        )
    
    async def log_settlement_event(
        self,
        event_type: AuditEventType,
        quote_id: str,
        settlement_id: str,
        amount_eur: float,
        payout_reference: Optional[str] = None,
        bank_account: Optional[str] = None,
        details: Optional[Dict] = None
    ):
        """Log a settlement processing event."""
        await self.log(
            event_type=event_type,
            quote_id=quote_id,
            settlement_id=settlement_id,
            details={
                "amount_eur": amount_eur,
                "payout_reference": payout_reference,
                "bank_account_masked": bank_account[:8] + "..." if bank_account else None,
                **(details or {})
            }
        )
    
    async def log_compliance_event(
        self,
        event_type: AuditEventType,
        quote_id: str,
        status_field: str,
        old_status: Optional[str] = None,
        new_status: str = None,
        provider: str = "internal_por",
        details: Optional[Dict] = None
    ):
        """Log a compliance status change."""
        await self.log(
            event_type=event_type,
            quote_id=quote_id,
            details={
                "status_field": status_field,
                "old_status": old_status,
                "new_status": new_status,
                "provider": provider,
                **(details or {})
            }
        )
    
    async def log_system_event(
        self,
        event_type: AuditEventType,
        component: str,
        message: str,
        details: Optional[Dict] = None,
        error: Optional[str] = None
    ):
        """Log a system event."""
        await self.log(
            event_type=event_type,
            details={
                "component": component,
                "message": message,
                **(details or {})
            },
            error=error
        )
    
    async def get_audit_trail(self, quote_id: str) -> list:
        """Get complete audit trail for a quote."""
        if not self.audit_collection:
            return []
        
        cursor = self.audit_collection.find(
            {"quote_id": quote_id}
        ).sort("timestamp", 1)
        
        docs = await cursor.to_list(length=1000)
        for doc in docs:
            doc.pop("_id", None)
            doc["timestamp"] = doc["timestamp"].isoformat() if hasattr(doc["timestamp"], "isoformat") else str(doc["timestamp"])
        
        return docs
    
    async def get_recent_events(
        self,
        event_type: Optional[AuditEventType] = None,
        limit: int = 100
    ) -> list:
        """Get recent audit events."""
        if not self.audit_collection:
            return []
        
        query = {}
        if event_type:
            query["event_type"] = event_type.value
        
        cursor = self.audit_collection.find(query).sort("timestamp", -1).limit(limit)
        
        docs = await cursor.to_list(length=limit)
        for doc in docs:
            doc.pop("_id", None)
            doc["timestamp"] = doc["timestamp"].isoformat() if hasattr(doc["timestamp"], "isoformat") else str(doc["timestamp"])
        
        return docs


# Global audit logger instance
audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    """Get the global audit logger instance."""
    global audit_logger
    if audit_logger is None:
        audit_logger = AuditLogger()
    return audit_logger


def set_audit_logger(logger: AuditLogger):
    """Set the global audit logger instance."""
    global audit_logger
    audit_logger = logger
