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
from engines.swap_tokens import list_tokens
from middleware.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/swap", tags=["Swap"])

_engine: Optional[SwapEngineV2] = None


def get_engine() -> SwapEngineV2:
    global _engine
    if _engine is None:
        _engine = SwapEngineV2()
    return _engine


def set_swap_db(db):
    """Called from server.py at startup to wire the DB."""
    get_engine().set_db(db)


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
