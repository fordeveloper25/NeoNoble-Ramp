"""
Developer Ramp API Routes - HMAC-protected endpoints for NeoNoble Ramp.

Provides full off-ramp functionality powered by the PoR engine.
Developers can access via API Keys with HMAC authentication.

Authentication:
- X-API-KEY: Your API key
- X-TIMESTAMP: Unix timestamp in seconds  
- X-SIGNATURE: HMAC-SHA256(timestamp + bodyJson, apiSecret)
"""

from fastapi import APIRouter, HTTPException, Request, Query
from pydantic import BaseModel, Field
from typing import Optional
import logging

from models.quote import QuoteResponse, RampResponse
from services.ramp_service import RampService
from services.por_engine import InternalPoRProvider
from services.pricing_service import pricing_service, SUPPORTED_CRYPTOS, NENO_PRICE_EUR
from middleware.auth import HMACAuthMiddleware
from services.api_key_service import PlatformApiKeyService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Developer Ramp API"])

# Services will be set by main app
ramp_service: RampService = None
por_engine: InternalPoRProvider = None
hmac_middleware: HMACAuthMiddleware = None


def set_services(ramp: RampService, api_key_service: PlatformApiKeyService):
    global ramp_service, hmac_middleware
    ramp_service = ramp
    hmac_middleware = HMACAuthMiddleware(api_key_service)


def set_por_engine(engine: InternalPoRProvider):
    global por_engine
    por_engine = engine


# ========================
# Request Models
# ========================

class OnrampQuoteRequest(BaseModel):
    fiat_amount: float = Field(..., gt=0, description="Amount in EUR to convert")
    crypto_currency: str = Field(..., description="Target cryptocurrency (BTC, ETH, NENO, etc.)")


class OfframpQuoteRequest(BaseModel):
    crypto_amount: float = Field(..., gt=0, description="Amount of crypto to convert")
    crypto_currency: str = Field(..., description="Source cryptocurrency (BTC, ETH, NENO, etc.)")
    bank_account: Optional[str] = Field(None, description="IBAN for payout (optional at quote)")


class OnrampExecuteRequest(BaseModel):
    quote_id: str = Field(..., description="Quote ID from onramp-quote endpoint")
    wallet_address: str = Field(..., description="Wallet address to receive crypto")


class OfframpExecuteRequest(BaseModel):
    quote_id: str = Field(..., description="Quote ID from offramp-quote endpoint")
    bank_account: str = Field(..., description="Bank account IBAN to receive fiat")


class DepositProcessRequest(BaseModel):
    quote_id: str = Field(..., description="Quote ID")
    tx_hash: str = Field(..., description="Blockchain transaction hash")
    amount: float = Field(..., description="Amount received")


class PoROnrampQuoteRequest(BaseModel):
    """PoR-powered on-ramp quote request."""
    fiat_amount: float = Field(..., gt=0, description="Amount in EUR to spend")
    crypto_currency: str = Field(default="NENO", description="Cryptocurrency to receive")
    wallet_address: Optional[str] = Field(None, description="Wallet address for crypto delivery")


class PoROnrampExecuteRequest(BaseModel):
    """PoR-powered on-ramp execute request."""
    quote_id: str = Field(..., description="Quote ID to execute")
    wallet_address: str = Field(..., description="Wallet address to receive crypto")


class PoRPaymentProcessRequest(BaseModel):
    """PoR on-ramp payment processing request."""
    quote_id: str = Field(..., description="Quote ID")
    payment_ref: str = Field(..., description="Payment reference")
    amount_paid: float = Field(..., description="Amount paid in EUR")


# ========================
# Helper Functions
# ========================

def por_quote_to_response(quote) -> dict:
    """Convert PoR quote to API response."""
    response = {
        "quote_id": quote.quote_id,
        "provider": quote.provider.value,
        "direction": getattr(quote, 'direction', 'offramp'),
        "crypto_amount": quote.crypto_amount,
        "crypto_currency": quote.crypto_currency,
        "fiat_amount": quote.fiat_amount,
        "fiat_currency": quote.fiat_currency,
        "exchange_rate": quote.exchange_rate,
        "fee_amount": quote.fee_amount,
        "fee_percentage": quote.fee_percentage,
        "net_payout": quote.net_payout,
        "deposit_address": quote.deposit_address,
        "wallet_address": getattr(quote, 'wallet_address', None),
        "payment_reference": getattr(quote, 'payment_reference', None),
        "payment_amount": getattr(quote, 'payment_amount', None),
        "expires_at": quote.expires_at,
        "created_at": quote.created_at,
        "state": quote.state.value,
        "compliance": {
            "kyc_status": quote.compliance.kyc_status.value,
            "kyc_provider": quote.compliance.kyc_provider,
            "aml_status": quote.compliance.aml_status.value,
            "aml_provider": quote.compliance.aml_provider,
            "por_responsible": quote.compliance.por_responsible
        },
        "timeline": [
            {
                "timestamp": e.timestamp,
                "state": e.state.value,
                "message": e.message,
                "details": e.details,
                "provider": e.provider
            }
            for e in quote.timeline
        ],
        "metadata": quote.metadata
    }
    return response


# ========================
# Public Endpoints (No Auth Required)
# ========================

@router.get("/ramp-api-health")
async def ramp_health():
    """Health check for the Ramp API."""
    por_status = "available" if por_engine and por_engine.is_available() else "unavailable"
    return {
        "status": "healthy",
        "service": "NeoNoble Ramp API",
        "version": "2.0.0",
        "por_engine": por_status,
        "supported_cryptos": SUPPORTED_CRYPTOS,
        "neno_price_eur": NENO_PRICE_EUR
    }


@router.get("/ramp-api-cache-status")
async def get_cache_status():
    """Get pricing cache status for monitoring."""
    return pricing_service.get_cache_status()


@router.get("/ramp-api-prices")
async def get_prices():
    """Get current prices for all supported cryptocurrencies."""
    try:
        prices = await pricing_service.get_all_prices_eur()
        return {
            "success": True,
            "currency": "EUR",
            "prices": prices,
            "neno_note": "NENO is fixed at 10,000 EUR per token"
        }
    except Exception as e:
        logger.error(f"Failed to fetch prices: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch prices")


@router.get("/ramp-api-por-status")
async def get_por_status():
    """Get PoR engine status (public endpoint)."""
    if not por_engine:
        return {"available": False, "error": "PoR engine not initialized"}
    
    config = por_engine.get_config()
    liquidity = await por_engine.get_liquidity_status()
    
    return {
        "available": por_engine.is_available(),
        "provider": config.name,
        "settlement_mode": config.settlement_mode.value,
        "fee_percentage": config.fee_percentage,
        "supported_cryptos": config.supported_cryptos,
        "neno_price_eur": NENO_PRICE_EUR,
        "liquidity_unlimited": liquidity.get("unlimited_mode", True)
    }


# ========================
# Legacy On-Ramp Endpoints (HMAC Protected)
# ========================

@router.post("/ramp-api-onramp-quote", response_model=QuoteResponse)
async def create_onramp_quote(request: OnrampQuoteRequest, http_request: Request):
    """
    Get a quote for onramp (Fiat -> Crypto).
    
    **HMAC Authentication Required**
    """
    await hmac_middleware.authenticate(http_request)
    
    if request.crypto_currency.upper() not in SUPPORTED_CRYPTOS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported cryptocurrency. Supported: {SUPPORTED_CRYPTOS}"
        )
    
    try:
        quote = await ramp_service.create_onramp_quote(
            fiat_amount=request.fiat_amount,
            crypto_currency=request.crypto_currency.upper()
        )
        return quote
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/ramp-api-onramp", response_model=RampResponse)
async def execute_onramp(request: OnrampExecuteRequest, http_request: Request):
    """
    Execute an onramp transaction (Fiat -> Crypto).
    
    **HMAC Authentication Required**
    """
    auth_info = await hmac_middleware.authenticate(http_request)
    
    result, error = await ramp_service.execute_onramp(
        quote_id=request.quote_id,
        wallet_address=request.wallet_address,
        api_key_id=auth_info["api_key_id"]
    )
    
    if error:
        raise HTTPException(status_code=400, detail=error)
    
    return result


# ========================
# PoR-Powered Off-Ramp Endpoints (HMAC Protected)
# ========================

@router.post("/ramp-api-offramp-quote")
async def create_offramp_quote_por(request: OfframpQuoteRequest, http_request: Request):
    """
    Get a quote for offramp (Crypto -> Fiat) via PoR engine.
    
    **HMAC Authentication Required**
    
    Returns enterprise-grade quote with:
    - Deposit address for crypto
    - NENO fixed at €10,000
    - 1.5% fee
    - Full compliance info
    - Transaction timeline
    """
    auth_info = await hmac_middleware.authenticate(http_request)
    
    if not por_engine:
        raise HTTPException(status_code=503, detail="PoR engine not available")
    
    if request.crypto_currency.upper() not in SUPPORTED_CRYPTOS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported cryptocurrency. Supported: {SUPPORTED_CRYPTOS}"
        )
    
    quote, error = await por_engine.create_quote(
        crypto_amount=request.crypto_amount,
        crypto_currency=request.crypto_currency.upper(),
        fiat_currency="EUR",
        user_id=None,  # API key based
        bank_account=request.bank_account
    )
    
    if error:
        raise HTTPException(status_code=400, detail=error)
    
    # Add API key info to metadata
    quote.metadata["api_key_id"] = auth_info["api_key_id"]
    
    return por_quote_to_response(quote)


@router.post("/ramp-api-offramp")
async def execute_offramp_por(request: OfframpExecuteRequest, http_request: Request):
    """
    Execute an offramp transaction via PoR engine.
    
    **HMAC Authentication Required**
    
    Accepts the quote and transitions to DEPOSIT_PENDING.
    User must then send crypto to the deposit address.
    """
    auth_info = await hmac_middleware.authenticate(http_request)
    
    if not por_engine:
        raise HTTPException(status_code=503, detail="PoR engine not available")
    
    quote, error = await por_engine.accept_quote(
        quote_id=request.quote_id,
        bank_account=request.bank_account
    )
    
    if error:
        raise HTTPException(status_code=400, detail=error)
    
    response = por_quote_to_response(quote)
    response["message"] = f"Please send {quote.crypto_amount} {quote.crypto_currency} to {quote.deposit_address}"
    response["api_key_id"] = auth_info["api_key_id"]
    
    return response


@router.post("/ramp-api-deposit-process")
async def process_deposit_por(request: DepositProcessRequest, http_request: Request):
    """
    Process a confirmed crypto deposit via PoR engine.
    
    **HMAC Authentication Required**
    
    In instant settlement mode, this completes the entire
    off-ramp flow automatically.
    """
    await hmac_middleware.authenticate(http_request)
    
    if not por_engine:
        raise HTTPException(status_code=503, detail="PoR engine not available")
    
    quote, error = await por_engine.process_deposit(
        quote_id=request.quote_id,
        tx_hash=request.tx_hash,
        amount=request.amount
    )
    
    if error:
        raise HTTPException(status_code=400, detail=error)
    
    return por_quote_to_response(quote)


@router.get("/ramp-api-transaction/{quote_id}")
async def get_transaction_por(quote_id: str, http_request: Request):
    """
    Get transaction details by quote ID via PoR engine.
    
    **HMAC Authentication Required**
    
    Returns full transaction data including:
    - Current state
    - Compliance info (KYC/AML)
    - Timeline of all events
    - Settlement details
    """
    await hmac_middleware.authenticate(http_request)
    
    if not por_engine:
        raise HTTPException(status_code=503, detail="PoR engine not available")
    
    quote = await por_engine.get_transaction(quote_id)
    
    if not quote:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    return por_quote_to_response(quote)


@router.get("/ramp-api-transaction/{quote_id}/timeline")
async def get_transaction_timeline_por(quote_id: str, http_request: Request):
    """
    Get transaction timeline via PoR engine.
    
    **HMAC Authentication Required**
    
    Returns detailed event log with all state transitions.
    """
    await hmac_middleware.authenticate(http_request)
    
    if not por_engine:
        raise HTTPException(status_code=503, detail="PoR engine not available")
    
    timeline = await por_engine.get_timeline(quote_id)
    
    if not timeline:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    return {
        "quote_id": quote_id,
        "event_count": len(timeline),
        "events": [
            {
                "timestamp": e.timestamp,
                "state": e.state.value,
                "message": e.message,
                "details": e.details,
                "provider": e.provider
            }
            for e in timeline
        ]
    }


@router.get("/ramp-api-transactions")
async def list_transactions_por(
    http_request: Request,
    state: Optional[str] = Query(None, description="Filter by state"),
    limit: int = Query(50, ge=1, le=100)
):
    """
    List transactions via PoR engine.
    
    **HMAC Authentication Required**
    """
    await hmac_middleware.authenticate(http_request)
    
    if not por_engine:
        raise HTTPException(status_code=503, detail="PoR engine not available")
    
    from services.provider_interface import TransactionState
    
    state_filter = TransactionState(state) if state else None
    
    transactions = await por_engine.list_transactions(
        state=state_filter,
        limit=limit
    )
    
    return {
        "count": len(transactions),
        "transactions": [por_quote_to_response(q) for q in transactions]
    }


# ========================
# PoR-Powered On-Ramp Endpoints (HMAC Protected)
# ========================

@router.post("/ramp-api-onramp-quote-por")
async def create_onramp_quote_por(request: PoROnrampQuoteRequest, http_request: Request):
    """
    Get a quote for on-ramp (Fiat -> Crypto) via PoR engine.
    
    **HMAC Authentication Required**
    
    Returns enterprise-grade quote with:
    - Payment reference for fiat transfer
    - NENO fixed at €10,000
    - 1.5% fee
    - Full compliance info
    - Transaction timeline
    """
    auth_info = await hmac_middleware.authenticate(http_request)
    
    if not por_engine:
        raise HTTPException(status_code=503, detail="PoR engine not available")
    
    if request.crypto_currency.upper() not in SUPPORTED_CRYPTOS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported cryptocurrency. Supported: {SUPPORTED_CRYPTOS}"
        )
    
    quote, error = await por_engine.create_onramp_quote(
        fiat_amount=request.fiat_amount,
        crypto_currency=request.crypto_currency.upper(),
        fiat_currency="EUR",
        user_id=None,  # API key based
        wallet_address=request.wallet_address
    )
    
    if error:
        raise HTTPException(status_code=400, detail=error)
    
    # Add API key info to metadata
    quote.metadata["api_key_id"] = auth_info["api_key_id"]
    
    return por_quote_to_response(quote)


@router.post("/ramp-api-onramp-por")
async def execute_onramp_por(request: PoROnrampExecuteRequest, http_request: Request):
    """
    Execute an on-ramp transaction via PoR engine.
    
    **HMAC Authentication Required**
    
    Accepts the quote and transitions to PAYMENT_PENDING.
    User must then send fiat payment using the payment reference.
    """
    auth_info = await hmac_middleware.authenticate(http_request)
    
    if not por_engine:
        raise HTTPException(status_code=503, detail="PoR engine not available")
    
    quote, error = await por_engine.accept_onramp_quote(
        quote_id=request.quote_id,
        wallet_address=request.wallet_address
    )
    
    if error:
        raise HTTPException(status_code=400, detail=error)
    
    response = por_quote_to_response(quote)
    response["message"] = f"Please send €{quote.payment_amount} using reference: {quote.payment_reference}"
    response["api_key_id"] = auth_info["api_key_id"]
    
    return response


@router.post("/ramp-api-payment-process-por")
async def process_payment_por(request: PoRPaymentProcessRequest, http_request: Request):
    """
    Process a confirmed fiat payment via PoR engine.
    
    **HMAC Authentication Required**
    
    In instant settlement mode, this completes the entire
    on-ramp flow automatically, delivering crypto to the wallet.
    """
    await hmac_middleware.authenticate(http_request)
    
    if not por_engine:
        raise HTTPException(status_code=503, detail="PoR engine not available")
    
    quote, error = await por_engine.process_onramp_payment(
        quote_id=request.quote_id,
        payment_ref=request.payment_ref,
        amount_paid=request.amount_paid
    )
    
    if error:
        raise HTTPException(status_code=400, detail=error)
    
    return por_quote_to_response(quote)


@router.get("/ramp-api-onramp-transaction/{quote_id}")
async def get_onramp_transaction_por(quote_id: str, http_request: Request):
    """
    Get on-ramp transaction details by quote ID via PoR engine.
    
    **HMAC Authentication Required**
    
    Returns full transaction data including:
    - Current state
    - Compliance info (KYC/AML)
    - Timeline of all events
    - Crypto delivery details
    """
    await hmac_middleware.authenticate(http_request)
    
    if not por_engine:
        raise HTTPException(status_code=503, detail="PoR engine not available")
    
    quote = await por_engine.get_transaction(quote_id)
    
    if not quote:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    return por_quote_to_response(quote)


@router.get("/ramp-api-onramp-transaction/{quote_id}/timeline")
async def get_onramp_timeline_por(quote_id: str, http_request: Request):
    """
    Get on-ramp transaction timeline via PoR engine.
    
    **HMAC Authentication Required**
    
    Returns detailed event log with all state transitions.
    """
    await hmac_middleware.authenticate(http_request)
    
    if not por_engine:
        raise HTTPException(status_code=503, detail="PoR engine not available")
    
    timeline = await por_engine.get_timeline(quote_id)
    
    if not timeline:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    return {
        "quote_id": quote_id,
        "event_count": len(timeline),
        "events": [
            {
                "timestamp": e.timestamp,
                "state": e.state.value,
                "message": e.message,
                "details": e.details,
                "provider": e.provider
            }
            for e in timeline
        ]
    }
