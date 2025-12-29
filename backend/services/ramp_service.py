from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import Optional, List
from datetime import datetime, timezone, timedelta
import logging
import uuid

from models.transaction import (
    Transaction,
    TransactionCreate,
    TransactionResponse,
    TransactionType,
    TransactionStatus
)
from models.quote import QuoteRequest, QuoteResponse, RampRequest, RampResponse
from services.pricing_service import pricing_service

logger = logging.getLogger(__name__)

# Quote validity duration
QUOTE_VALIDITY_MINUTES = 5

# In-memory quote cache (in production, use Redis)
_quote_cache = {}


class RampService:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db.transactions
    
    async def create_onramp_quote(self, fiat_amount: float, crypto_currency: str) -> QuoteResponse:
        """Create an onramp quote (Fiat -> Crypto)."""
        quote_data = await pricing_service.calculate_onramp_quote(
            fiat_amount=fiat_amount,
            crypto=crypto_currency
        )
        
        quote_id = f"quote_{uuid.uuid4().hex[:16]}"
        valid_until = datetime.now(timezone.utc) + timedelta(minutes=QUOTE_VALIDITY_MINUTES)
        
        quote = QuoteResponse(
            quote_id=quote_id,
            direction="onramp",
            valid_until=valid_until,
            **quote_data
        )
        
        # Cache the quote
        _quote_cache[quote_id] = {
            "quote": quote,
            "expires_at": valid_until
        }
        
        logger.info(f"Created onramp quote: {quote_id} - {fiat_amount} EUR -> {quote.crypto_amount} {crypto_currency}")
        return quote
    
    async def create_offramp_quote(self, crypto_amount: float, crypto_currency: str) -> QuoteResponse:
        """Create an offramp quote (Crypto -> Fiat)."""
        quote_data = await pricing_service.calculate_offramp_quote(
            crypto_amount=crypto_amount,
            crypto=crypto_currency
        )
        
        quote_id = f"quote_{uuid.uuid4().hex[:16]}"
        valid_until = datetime.now(timezone.utc) + timedelta(minutes=QUOTE_VALIDITY_MINUTES)
        
        quote = QuoteResponse(
            quote_id=quote_id,
            direction="offramp",
            valid_until=valid_until,
            **quote_data
        )
        
        # Cache the quote
        _quote_cache[quote_id] = {
            "quote": quote,
            "expires_at": valid_until
        }
        
        logger.info(f"Created offramp quote: {quote_id} - {crypto_amount} {crypto_currency} -> {quote.fiat_amount} EUR")
        return quote
    
    async def execute_onramp(
        self,
        quote_id: str,
        wallet_address: str,
        user_id: Optional[str] = None,
        api_key_id: Optional[str] = None
    ) -> tuple[Optional[RampResponse], Optional[str]]:
        """Execute an onramp transaction."""
        # Validate quote
        cached = _quote_cache.get(quote_id)
        if not cached:
            return None, "Quote not found or expired"
        
        quote: QuoteResponse = cached["quote"]
        if datetime.now(timezone.utc) > cached["expires_at"]:
            del _quote_cache[quote_id]
            return None, "Quote has expired"
        
        if quote.direction != "onramp":
            return None, "Invalid quote type for onramp"
        
        if not wallet_address:
            return None, "Wallet address is required for onramp"
        
        # Create transaction
        transaction = Transaction(
            user_id=user_id,
            api_key_id=api_key_id,
            type=TransactionType.ONRAMP,
            fiat_currency=quote.fiat_currency,
            fiat_amount=quote.fiat_amount,
            crypto_currency=quote.crypto_currency,
            crypto_amount=quote.crypto_amount,
            exchange_rate=quote.exchange_rate,
            fee_amount=quote.fee_amount,
            fee_currency=quote.fee_currency,
            wallet_address=wallet_address,
            status=TransactionStatus.PROCESSING,
            metadata={"quote_id": quote_id}
        )
        
        # Save to database
        tx_dict = transaction.model_dump()
        for field in ['created_at', 'updated_at', 'completed_at']:
            if tx_dict.get(field):
                tx_dict[field] = tx_dict[field].isoformat()
        await self.collection.insert_one(tx_dict)
        
        # Remove used quote
        del _quote_cache[quote_id]
        
        # In a real system, this would trigger payment processing
        # For now, we'll simulate a successful transaction
        await self._complete_transaction(transaction.id)
        
        logger.info(f"Executed onramp: {transaction.reference} - {quote.total_fiat} EUR -> {quote.crypto_amount} {quote.crypto_currency}")
        
        return RampResponse(
            transaction_id=transaction.id,
            reference=transaction.reference,
            status=TransactionStatus.PROCESSING.value,
            direction="onramp",
            fiat_currency=quote.fiat_currency,
            fiat_amount=quote.fiat_amount,
            crypto_currency=quote.crypto_currency,
            crypto_amount=quote.crypto_amount,
            exchange_rate=quote.exchange_rate,
            fee_amount=quote.fee_amount,
            total_fiat=quote.total_fiat,
            wallet_address=wallet_address,
            bank_account=None,
            created_at=transaction.created_at,
            message="Transaction initiated. Crypto will be sent to your wallet once payment is confirmed."
        ), None
    
    async def execute_offramp(
        self,
        quote_id: str,
        bank_account: str,
        user_id: Optional[str] = None,
        api_key_id: Optional[str] = None
    ) -> tuple[Optional[RampResponse], Optional[str]]:
        """Execute an offramp transaction."""
        # Validate quote
        cached = _quote_cache.get(quote_id)
        if not cached:
            return None, "Quote not found or expired"
        
        quote: QuoteResponse = cached["quote"]
        if datetime.now(timezone.utc) > cached["expires_at"]:
            del _quote_cache[quote_id]
            return None, "Quote has expired"
        
        if quote.direction != "offramp":
            return None, "Invalid quote type for offramp"
        
        if not bank_account:
            return None, "Bank account is required for offramp"
        
        # Create transaction
        transaction = Transaction(
            user_id=user_id,
            api_key_id=api_key_id,
            type=TransactionType.OFFRAMP,
            fiat_currency=quote.fiat_currency,
            fiat_amount=quote.fiat_amount,
            crypto_currency=quote.crypto_currency,
            crypto_amount=quote.crypto_amount,
            exchange_rate=quote.exchange_rate,
            fee_amount=quote.fee_amount,
            fee_currency=quote.fee_currency,
            bank_account=bank_account,
            status=TransactionStatus.PROCESSING,
            metadata={"quote_id": quote_id}
        )
        
        # Save to database
        tx_dict = transaction.model_dump()
        for field in ['created_at', 'updated_at', 'completed_at']:
            if tx_dict.get(field):
                tx_dict[field] = tx_dict[field].isoformat()
        await self.collection.insert_one(tx_dict)
        
        # Remove used quote
        del _quote_cache[quote_id]
        
        # Simulate processing
        await self._complete_transaction(transaction.id)
        
        logger.info(f"Executed offramp: {transaction.reference} - {quote.crypto_amount} {quote.crypto_currency} -> {quote.total_fiat} EUR")
        
        return RampResponse(
            transaction_id=transaction.id,
            reference=transaction.reference,
            status=TransactionStatus.PROCESSING.value,
            direction="offramp",
            fiat_currency=quote.fiat_currency,
            fiat_amount=quote.fiat_amount,
            crypto_currency=quote.crypto_currency,
            crypto_amount=quote.crypto_amount,
            exchange_rate=quote.exchange_rate,
            fee_amount=quote.fee_amount,
            total_fiat=quote.total_fiat,
            wallet_address=None,
            bank_account=bank_account,
            created_at=transaction.created_at,
            message="Transaction initiated. Funds will be sent to your bank account once crypto is received."
        ), None
    
    async def _complete_transaction(self, transaction_id: str):
        """Mark a transaction as completed (simulation)."""
        await self.collection.update_one(
            {"id": transaction_id},
            {
                "$set": {
                    "status": TransactionStatus.COMPLETED.value,
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
            }
        )
    
    async def get_user_transactions(
        self,
        user_id: str,
        limit: int = 50
    ) -> List[TransactionResponse]:
        """Get transactions for a user."""
        transactions = []
        cursor = self.collection.find(
            {"user_id": user_id}
        ).sort("created_at", -1).limit(limit)
        
        async for doc in cursor:
            tx = self._doc_to_response(doc)
            transactions.append(tx)
        
        return transactions
    
    def _doc_to_response(self, doc: dict) -> TransactionResponse:
        """Convert MongoDB document to TransactionResponse."""
        for field in ['created_at', 'updated_at', 'completed_at']:
            if doc.get(field) and isinstance(doc[field], str):
                doc[field] = datetime.fromisoformat(doc[field])
        
        return TransactionResponse(
            id=doc['id'],
            type=doc['type'],
            fiat_currency=doc['fiat_currency'],
            fiat_amount=doc['fiat_amount'],
            crypto_currency=doc['crypto_currency'],
            crypto_amount=doc['crypto_amount'],
            exchange_rate=doc['exchange_rate'],
            fee_amount=doc['fee_amount'],
            status=doc['status'],
            reference=doc['reference'],
            created_at=doc['created_at'],
            completed_at=doc.get('completed_at')
        )
