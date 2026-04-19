"""
NeoNoble Swap API routes.

Mounted under /api (api_router has prefix='/api'), so this router uses
prefix='/swap' to produce the final paths:

    GET    /api/swap/health
    GET    /api/swap/tokens
    POST   /api/swap/quote
    POST   /api/swap/execute
    GET    /api/swap/history
"""

from __future__ import annotations

import logging
import time
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from engines.swap_engine import SwapEngine, SwapRequest, SwapResult
from engines.swap_tokens import list_tokens
from middleware.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/swap", tags=["Swap"])

# Single module-level engine (initialised lazily to read env at runtime)
_engine: Optional[SwapEngine] = None


def get_engine() -> SwapEngine:
    global _engine
    if _engine is None:
        _engine = SwapEngine()
    return _engine


def set_swap_db(db):
    """Call this from server.py during startup to wire the DB."""
    get_engine().set_db(db)


# ---------------------------------------------------------------------------
# Very small in-memory rate limiter (per-user, per-minute) — env configurable.
# ---------------------------------------------------------------------------

import os
from collections import defaultdict, deque

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
            detail=f"Rate limit exceeded ({_RATE_LIMIT}/min). Riprova tra poco.",
        )
    q.append(now)


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class QuoteRequest(BaseModel):
    from_token: str = Field(..., description="Symbol (NENO, USDT…) or contract address")
    to_token: str
    amount_in: Decimal = Field(..., gt=0)


class ExecuteRequest(BaseModel):
    from_token: str
    to_token: str
    amount_in: Decimal = Field(..., gt=0)
    user_wallet_address: str = Field(..., description="BSC address that will receive the tokens")
    slippage: Optional[float] = Field(
        default=None,
        ge=0.1,
        le=5.0,
        description="Slippage percentage (0.1–5.0)",
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/health")
async def swap_health():
    """Report engine configuration (no secrets)."""
    return get_engine().health()


@router.get("/tokens")
async def swap_tokens():
    """List of supported tokens for the UI dropdown."""
    return {"chain": "bsc", "tokens": list_tokens()}


@router.post("/quote")
async def swap_quote(body: QuoteRequest):
    """Estimate output amount without executing."""
    try:
        return await get_engine().get_quote(
            body.from_token, body.to_token, body.amount_in
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("swap_quote failed")
        raise HTTPException(status_code=500, detail=f"quote error: {e}")


@router.post("/execute", response_model=SwapResult)
async def swap_execute(
    body: ExecuteRequest,
    current_user: dict = Depends(get_current_user),
):
    """Execute a real on-chain swap (JWT required)."""
    user_id = current_user.get("user_id") or "unknown"
    _rate_check(user_id)

    engine = get_engine()
    slippage = body.slippage if body.slippage is not None else engine.default_slippage

    req = SwapRequest(
        user_id=user_id,
        from_token=body.from_token,
        to_token=body.to_token,
        amount_in=body.amount_in,
        chain="bsc",
        slippage=slippage,
        user_wallet_address=body.user_wallet_address,
    )
    return await engine.execute_swap(req)


@router.get("/history")
async def swap_history(
    limit: int = 50,
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user.get("user_id") or "unknown"
    rows = await get_engine().get_user_history(user_id, limit=limit)
    return {"user_id": user_id, "count": len(rows), "history": rows}


# --- Backward-compat: the old frontend called POST /api/swap (root) -------
@router.post("", response_model=SwapResult)
async def swap_execute_legacy(
    body: ExecuteRequest,
    current_user: dict = Depends(get_current_user),
):
    return await swap_execute(body, current_user)
