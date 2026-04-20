"""
Hybrid Swap Engine — USER-SIGNED DEX MODE (ZERO PLATFORM CAPITAL)

This engine is now a thin wrapper around SwapEngineV2. All swaps are
executed on-chain by the USER's own wallet (MetaMask) via:

    1) 1inch Aggregator (BSC) — aggregates PancakeSwap, Biswap, BakerySwap,
       ApeSwap, MDEX, Uniswap V3 BSC, etc. → best available route.
    2) PancakeSwap V2 fallback — direct router quote for simple pairs.

Liquidity sources
-----------------
Public DEX pools provided by anonymous LPs on chain. The platform owner
does NOT need to provide any capital or seed liquidity. If no DEX route
exists anywhere on BSC for a pair, we return a clean "no liquidity" error
(swapping a token with zero on-chain liquidity is physically impossible
without counter-party capital — this is an economic reality, not a bug).

The legacy CEX / Market-Maker fallback has been intentionally removed
because it required platform-held capital.
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Dict, Optional

from engines.swap_engine_v2 import SwapEngineV2

logger = logging.getLogger(__name__)


class HybridSwapEngine:
    """User-signed DEX aggregator wrapper."""

    def __init__(self, v2: Optional[SwapEngineV2] = None):
        # Share the singleton SwapEngineV2 so DB wiring in server.py
        # applies to both `/swap/*` and `/swap/hybrid/*` routes.
        self.v2 = v2 or SwapEngineV2()
        logger.info("✅ HybridSwapEngine → user-signed DEX mode (1inch + PancakeSwap)")

    # ---------- quote ------------------------------------------------------

    async def get_quote(
        self,
        from_token: str,
        to_token: str,
        amount_in: float,
    ) -> Optional[Dict]:
        """
        Return a dict compatible with the existing /hybrid/quote response
        schema used by the frontend.
        """
        try:
            q = await self.v2.get_quote(
                from_token, to_token, Decimal(str(amount_in))
            )
            # Convert Pydantic model to plain dict expected by the UI
            out = q.model_dump()

            # If no route found, signal clearly
            if out.get("estimated_amount_out", 0) <= 0 or out.get("source") == "estimate":
                return {
                    **out,
                    "source": out.get("source") or "estimate",
                    "note": out.get("note")
                    or "Nessuna liquidità DEX disponibile per questa coppia su BSC "
                       "(PancakeSwap / 1inch). La piattaforma non deposita capitale: "
                       "lo swap è possibile solo se esiste un pool pubblico per la coppia.",
                }
            return out
        except ValueError as e:
            logger.warning("hybrid.get_quote value error: %s", e)
            return {
                "from_token": from_token,
                "to_token": to_token,
                "amount_in": amount_in,
                "estimated_amount_out": 0,
                "rate": 0,
                "source": "error",
                "note": str(e),
            }
        except Exception as e:
            logger.exception("hybrid.get_quote failed")
            return {
                "from_token": from_token,
                "to_token": to_token,
                "amount_in": amount_in,
                "estimated_amount_out": 0,
                "rate": 0,
                "source": "error",
                "note": f"quote error: {e}",
            }

    # ---------- build ------------------------------------------------------

    async def build_swap(
        self,
        from_token: str,
        to_token: str,
        amount_in: float,
        user_wallet: str,
        slippage_pct: float = 0.8,
        user_id: str = "unknown",
    ) -> Optional[Dict]:
        """
        Build an unsigned transaction for the user's MetaMask to sign.
        Always returns execution_mode = "on-chain" so the frontend knows
        to request a signature (never a server-side execution).
        """
        try:
            built = await self.v2.build_swap_tx(
                user_id=user_id,
                from_token=from_token,
                to_token=to_token,
                amount_in=Decimal(str(amount_in)),
                user_wallet=user_wallet,
                slippage=slippage_pct,
            )
            payload = built.model_dump()
            # Force on-chain / user-signed mode so the UI always triggers
            # a MetaMask prompt — never a platform-executed swap.
            payload["execution_mode"] = "on-chain"
            return payload
        except ValueError as e:
            logger.warning("hybrid.build_swap value error: %s", e)
            raise
        except RuntimeError as e:
            # No liquidity found → let the route return 422
            logger.info("hybrid.build_swap: no liquidity — %s", e)
            raise
        except Exception:
            logger.exception("hybrid.build_swap failed")
            raise

    # ---------- execute (DISABLED in user-signed mode) ---------------------

    async def execute_swap(self, *args, **kwargs):
        """
        User-signed mode: the platform never executes swaps on-chain.
        Kept only to avoid AttributeError from stale callers.
        """
        return False, None, {
            "error": "Server-side execution is disabled. "
                     "Swaps are signed and submitted by the user's own wallet."
        }

    # ---------- health -----------------------------------------------------

    async def get_health(self) -> Dict:
        h = self.v2.health()
        return {
            "mode": "user_signed_dex",
            "capital_required": False,
            "rpc_connected": h.get("rpc_connected"),
            "oneinch_configured": h.get("oneinch_configured"),
            "chain_id": h.get("chain_id"),
            "default_slippage_pct": h.get("default_slippage_pct"),
            "max_slippage_pct": h.get("max_slippage_pct"),
            "supported_tokens_count": len(h.get("supported_tokens", [])),
            "note": "All swaps are executed by the user's wallet via DEX aggregators. "
                    "The platform does not deposit any capital.",
            "status": "operational",
        }
