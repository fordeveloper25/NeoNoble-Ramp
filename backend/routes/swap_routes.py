"""
NeoNoble Swap API — USER-SIGNED mode.

All routes are mounted under /api (the parent APIRouter has prefix='/api'),
so this router uses prefix='/swap' to yield the final paths:

    GET    /api/swap/health
    GET    /api/swap/tokens
    POST   /api/swap/quote
    POST   /api/swap/build           ← returns calldata for MetaMask to sign
    POST   /api/swap/track            ← record the user-submitted tx hash
    GET    /api/swap/history          ← JWT-protected

The legacy server-side execution endpoint (/api/swap/execute) is intentionally
NOT exposed in user-signed mode — swaps are performed exclusively by the
user's own wallet.
"""

from __future__ import annotations

import logging
import os
import time
from collections import defaultdict, deque
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from engines.swap_engine_v2 import SwapEngineV2, BuildResult, QuoteResult, TrackResult
from engines.hybrid_swap_engine import HybridSwapEngine
from engines.swap_tokens import list_tokens
from middleware.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/swap", tags=["Swap"])

_engine: Optional[SwapEngineV2] = None
_hybrid_engine: Optional[HybridSwapEngine] = None


def get_engine() -> SwapEngineV2:
    global _engine
    if _engine is None:
        _engine = SwapEngineV2()
    return _engine


def get_hybrid_engine() -> HybridSwapEngine:
    global _hybrid_engine
    if _hybrid_engine is None:
        # Share the same SwapEngineV2 instance so DB/history are unified
        _hybrid_engine = HybridSwapEngine(v2=get_engine())
    return _hybrid_engine


def set_swap_db(db):
    """Called from server.py at startup to wire the DB."""
    global _engine, _hybrid_engine
    if _engine is None:
        _engine = SwapEngineV2()
    _engine.set_db(db)
    # Rebuild hybrid engine on the DB-wired v2
    _hybrid_engine = HybridSwapEngine(v2=_engine)
    logger.info("✅ Swap engine DB configured (v2 + hybrid)")


# ---------------------------------------------------------------------------
# In-memory rate limiter
# ---------------------------------------------------------------------------

_rate_bucket: dict = defaultdict(deque)
_RATE_LIMIT = int(os.environ.get("SWAP_RATE_LIMIT_PER_MIN", "100"))


def _rate_check(user_id: str):
    now = time.time()
    q = _rate_bucket[user_id]
    while q and now - q[0] > 60.0:
        q.popleft()
    if len(q) >= _RATE_LIMIT:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded ({_RATE_LIMIT}/min)",
        )
    q.append(now)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class QuoteRequest(BaseModel):
    from_token: str
    to_token: str
    amount_in: Decimal = Field(..., gt=0)


class BuildRequest(BaseModel):
    from_token: str
    to_token: str
    amount_in: Decimal = Field(..., gt=0)
    user_wallet_address: str
    slippage: Optional[float] = Field(default=None, ge=0.1, le=5.0)


class TrackRequest(BaseModel):
    swap_id: str
    tx_hash: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/health")
async def swap_health():
    return get_engine().health()


@router.get("/tokens")
async def swap_tokens():
    return {"chain": "bsc", "tokens": list_tokens()}


@router.post("/quote", response_model=QuoteResult)
async def swap_quote(body: QuoteRequest):
    try:
        return await get_engine().get_quote(
            body.from_token, body.to_token, body.amount_in
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("swap_quote failed")
        raise HTTPException(status_code=500, detail=f"quote error: {e}")


@router.post("/build", response_model=BuildResult)
async def swap_build(
    body: BuildRequest,
    current_user: dict = Depends(get_current_user),
):
    """Return calldata that the user's wallet (MetaMask) must sign."""
    user_id = current_user.get("user_id") or "unknown"
    _rate_check(user_id)
    engine = get_engine()
    slippage = body.slippage if body.slippage is not None else engine.default_slippage
    try:
        return await engine.build_swap_tx(
            user_id=user_id,
            from_token=body.from_token,
            to_token=body.to_token,
            amount_in=body.amount_in,
            user_wallet=body.user_wallet_address,
            slippage=slippage,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.exception("swap_build failed")
        raise HTTPException(status_code=500, detail=f"build error: {e}")


@router.post("/track", response_model=TrackResult)
async def swap_track(
    body: TrackRequest,
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user.get("user_id") or "unknown"
    try:
        return await get_engine().track_tx(body.swap_id, body.tx_hash, user_id)
    except Exception as e:
        logger.exception("swap_track failed")
        raise HTTPException(status_code=500, detail=f"track error: {e}")


@router.get("/history")
async def swap_history(
    limit: int = 50,
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user.get("user_id") or "unknown"
    rows = await get_engine().get_user_history(user_id, limit=limit)
    return {"user_id": user_id, "count": len(rows), "history": rows}


# ---------------------------------------------------------------------------
# HYBRID SWAP ENDPOINTS (DEX + Market Maker + CEX Fallback)
# ---------------------------------------------------------------------------

@router.get("/hybrid/health")
async def hybrid_swap_health():
    """Health check for hybrid swap engine (DEX + Market Maker + CEX)"""
    try:
        engine = get_hybrid_engine()
        health_data = await engine.get_health()
        return {
            "status": "healthy",
            "service": "hybrid_swap_engine",
            **health_data
        }
    except Exception as e:
        logger.warning(f"Hybrid engine healthcheck warning: {e}")
        # Return healthy even if engine has issues (optional modules may be missing)
        return {
            "status": "healthy",
            "service": "hybrid_swap_engine",
            "mode": "degraded",
            "note": "Core service operational, optional features may be unavailable"
        }


@router.post("/hybrid/quote")
async def hybrid_swap_quote(body: QuoteRequest):
    """
    Get best DEX route (user-signed). Tries 1inch aggregator first
    (which spans PancakeSwap V2/V3, Biswap, ApeSwap, MDEX, etc.) and
    falls back to a direct PancakeSwap V2 router quote.

    The platform deposits zero capital; liquidity is provided by public
    on-chain pools.
    """
    try:
        result = await get_hybrid_engine().get_quote(
            body.from_token,
            body.to_token,
            float(body.amount_in)
        )
        if not result:
            raise HTTPException(
                status_code=404,
                detail="No liquidity available for this pair across DEX, Market Maker, or CEX"
            )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("hybrid_swap_quote failed")
        raise HTTPException(status_code=500, detail=f"quote error: {e}")


@router.post("/hybrid/build")
async def hybrid_swap_build(
    body: BuildRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Build a user-signed DEX swap. Always returns unsigned calldata
    (execution_mode='on-chain') ready to be submitted by MetaMask.
    The platform never executes swaps on behalf of the user.
    """
    user_id = current_user.get("user_id") or "unknown"
    _rate_check(user_id)
    
    slippage = body.slippage if body.slippage is not None else 0.8
    
    try:
        result = await get_hybrid_engine().build_swap(
            from_token=body.from_token,
            to_token=body.to_token,
            amount_in=float(body.amount_in),
            user_wallet=body.user_wallet_address,
            slippage_pct=slippage,
            user_id=user_id,
        )

        if not result:
            raise HTTPException(
                status_code=404,
                detail="Unable to build swap - no liquidity available"
            )

        return result
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.exception("hybrid_swap_build failed")
        raise HTTPException(status_code=500, detail=f"build error: {e}")


@router.post("/hybrid/execute")
async def hybrid_swap_execute(
    body: dict,
    current_user: dict = Depends(get_current_user),
):
    """
    DISABLED: In the user-signed DEX model, swaps are submitted by the
    user's own wallet. There is no server-side execution path because the
    platform holds no capital.

    Frontend clients should sign `build.data` in MetaMask and then call
    POST /api/swap/track with the resulting tx hash.
    """
    raise HTTPException(
        status_code=410,
        detail=(
            "Server-side execution is disabled. Sign the transaction returned "
            "by /api/swap/hybrid/build with your wallet, then POST the tx hash "
            "to /api/swap/track."
        ),
    )
