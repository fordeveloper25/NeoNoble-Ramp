"""
Connector Manager — minimal, boot-safe implementation.

The previous version of this file had multiple overlapping class bodies and
syntax errors that prevented the backend from booting.  The NeoNoble on-chain
Swap feature doesn't depend on real CEX order execution, so we keep this file
import-safe with graceful fallbacks while preserving the public API the rest
of the codebase expects:

    ConnectorManager(db=None)
    manager.initialize()
    manager.enable_live_trading(user_id="system")
    manager.execute(...)
    manager.execute_order(symbol, side, quantity, user_id="system")
    manager.get_ticker(symbol)
    manager.get_best_price(symbol)
    manager.get_aggregated_balance(currency)
    get_connector_manager()
    set_connector_manager(manager)
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Optional imports — all failures are swallowed so the backend can still boot
# ---------------------------------------------------------------------------

try:
    from .binance_connector import BinanceConnector  # noqa: F401
except Exception as _e:  # pragma: no cover
    BinanceConnector = None
    logger.warning("BinanceConnector unavailable: %s", _e)

try:
    from .kraken_connector import KrakenConnector  # noqa: F401
except Exception as _e:  # pragma: no cover
    KrakenConnector = None
    logger.warning("KrakenConnector unavailable: %s", _e)

try:
    from .coinbase_connector import CoinbaseConnector  # noqa: F401
except Exception as _e:  # pragma: no cover
    CoinbaseConnector = None
    logger.warning("CoinbaseConnector unavailable: %s", _e)

try:
    from .mexc_connector import MexcConnector  # noqa: F401
except Exception as _e:  # pragma: no cover
    MexcConnector = None
    logger.warning("MexcConnector unavailable: %s", _e)

try:
    from .neno_virtual_exchange import (
        get_neno_exchange,
        NenoVirtualExchange,
    )
except Exception as _e:  # pragma: no cover
    NenoVirtualExchange = None

    def get_neno_exchange():
        return None

    logger.warning("NenoVirtualExchange unavailable: %s", _e)


# ---------------------------------------------------------------------------
# ConnectorManager
# ---------------------------------------------------------------------------


class ConnectorManager:
    """Minimal boot-safe connector manager."""

    def __init__(self, db: Any = None):
        self.db = db
        self._enabled = False
        self._shadow_mode = True
        self._connectors: Dict[str, Any] = {}
        self._primary_venue = "binance"

        # Try to construct a real Binance connector (optional).
        self.binance = None
        if BinanceConnector is not None:
            try:
                self.binance = BinanceConnector()
                self._connectors["binance"] = self.binance
            except Exception as e:
                logger.warning("BinanceConnector init failed: %s", e)

        # Resolve NENO virtual exchange (for $NENO internal orders).
        try:
            self._neno_exchange = get_neno_exchange()
        except Exception:
            self._neno_exchange = None

    # -- lifecycle ----------------------------------------------------------

    async def initialize(self):
        """Async init — no-op for safety."""
        logger.info(
            "ConnectorManager initialized (connectors=%s)",
            list(self._connectors.keys()),
        )
        return True

    async def enable_live_trading(self, user_id: str = "system"):
        """Flip out of shadow mode."""
        self._enabled = True
        self._shadow_mode = False
        logger.info("ConnectorManager: live trading enabled by %s", user_id)

    def is_enabled(self) -> bool:
        return self._enabled

    # -- helpers ------------------------------------------------------------

    @staticmethod
    def _is_internal_symbol(symbol: str) -> bool:
        up = (symbol or "").upper()
        return "NENO" in up or up.startswith("TKN")

    # -- order execution ----------------------------------------------------

    async def execute(self, *args, **kwargs) -> Tuple[Optional[Any], Optional[str]]:
        """Generic execute — forwards to execute_order."""
        symbol = kwargs.get("symbol") or (args[0] if args else None)
        side = kwargs.get("side") or (args[1] if len(args) > 1 else "buy")
        quantity = kwargs.get("quantity") or (args[2] if len(args) > 2 else 0)
        user_id = kwargs.get("user_id", "system")
        return await self.execute_order(symbol, side, quantity, user_id)

    async def execute_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        user_id: str = "system",
    ) -> Tuple[Optional[Any], Optional[str]]:
        if not self._enabled:
            return None, "Trading not enabled (shadow mode)"

        # Internal NENO / custom token
        if self._is_internal_symbol(symbol) and self._neno_exchange is not None:
            try:
                order = await self._neno_exchange.place_market_order(
                    user_id=user_id,
                    symbol=symbol,
                    side=side,
                    quantity=quantity,
                )
                return order, None
            except Exception as e:
                return None, f"NENO exchange error: {e}"

        # External CEX (Binance only for now)
        if self.binance is not None:
            try:
                return await self.binance.place_market_order(
                    symbol, side, quantity
                ), None
            except Exception as e:
                return None, f"Binance order error: {e}"

        return None, "No connector available"

    # -- market data --------------------------------------------------------

    async def get_ticker(self, symbol: str):
        if self._is_internal_symbol(symbol) and self._neno_exchange is not None:
            try:
                return await self._neno_exchange.get_ticker(symbol)
            except Exception:
                return None
        if self.binance is not None:
            try:
                result = await self.binance.get_ticker(symbol)
                # Some connectors return (ticker, venue); normalize
                if isinstance(result, tuple):
                    return result[0]
                return result
            except Exception:
                return None
        return None

    async def get_best_price(self, symbol: str):
        if self._is_internal_symbol(symbol) and self._neno_exchange is not None:
            try:
                return await self._neno_exchange.get_ticker(symbol), "neno_exchange"
            except Exception:
                return None, None
        if self.binance is not None:
            try:
                result = await self.binance.get_ticker(symbol)
                if isinstance(result, tuple):
                    return result
                return result, "binance"
            except Exception:
                return None, None
        return None, None

    async def get_aggregated_balance(self, currency: str):
        currency_up = (currency or "").upper()
        if currency_up == "NENO" and self._neno_exchange is not None:
            try:
                return await self._neno_exchange.get_balance(currency_up)
            except Exception:
                return 0
        if self.binance is not None:
            try:
                return await self.binance.get_balance(currency_up)
            except Exception:
                return 0
        return 0


# ---------------------------------------------------------------------------
# Module-level singleton management
# ---------------------------------------------------------------------------

_manager_singleton: Optional[ConnectorManager] = None


def set_connector_manager(mgr: ConnectorManager) -> None:
    global _manager_singleton
    _manager_singleton = mgr


def get_connector_manager() -> ConnectorManager:
    global _manager_singleton
    if _manager_singleton is None:
        _manager_singleton = ConnectorManager()
    return _manager_singleton


__all__ = [
    "ConnectorManager",
    "get_connector_manager",
    "set_connector_manager",
]
