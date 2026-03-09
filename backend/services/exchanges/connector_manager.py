"""
Connector Manager - Manages multiple exchange connectors.

Provides:
- Unified interface for multiple exchanges
- Automatic failover between venues
- Order routing and execution
- Balance aggregation
- NENO virtual exchange integration
"""

import os
import logging
from typing import Optional, Dict, List, Tuple
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorDatabase

from .base_connector import (
    ExchangeConnector,
    OrderSide,
    OrderType,
    OrderStatus,
    ExchangeOrder,
    ExchangeBalance,
    MarketTicker
)
from .binance_connector import BinanceConnector
from .kraken_connector import KrakenConnector
from .coinbase_connector import CoinbaseConnector
from .neno_virtual_exchange import get_neno_exchange, NenoVirtualExchange

logger = logging.getLogger(__name__)


class ConnectorManager:
    """
    Manages multiple exchange connectors with automatic failover.
    
    Features:
    - Multi-venue order routing
    - Automatic failover on errors
    - Balance aggregation
    - Best price selection
    """
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.orders_collection = db.exchange_orders
        self.config_collection = db.exchange_config
        
        self._initialized = False
        self._connectors: Dict[str, ExchangeConnector] = {}
        self._primary_venue = "binance"
        self._fallback_venue = "kraken"
        self._enabled = False
        self._shadow_mode = True  # Start in shadow mode
        
        # NENO Virtual Exchange
        self._neno_exchange: NenoVirtualExchange = get_neno_exchange()
    
    async def initialize(self):
        """Initialize the connector manager."""
        if self._initialized:
            return
        
        # Create indexes
        await self.orders_collection.create_index("order_id", unique=True)
        await self.orders_collection.create_index("exchange_order_id")
        await self.orders_collection.create_index("exchange")
        await self.orders_collection.create_index("status")
        await self.orders_collection.create_index("created_at")
        
        # Load configuration
        config = await self.config_collection.find_one({"config_type": "exchanges"})
        
        if config:
            self._enabled = config.get("enabled", False)
            self._shadow_mode = config.get("shadow_mode", True)
            self._primary_venue = config.get("primary_venue", "binance")
            self._fallback_venue = config.get("fallback_venue", "kraken")
        else:
            # Create default config
            await self.config_collection.insert_one({
                "config_type": "exchanges",
                "enabled": False,
                "shadow_mode": True,
                "primary_venue": "binance",
                "fallback_venue": "kraken",
                "created_at": datetime.now(timezone.utc).isoformat()
            })
        
        # Initialize connectors (without credentials yet)
        self._connectors["binance"] = BinanceConnector()
        self._connectors["kraken"] = KrakenConnector()
        self._connectors["coinbase"] = CoinbaseConnector()
        
        # Load and initialize credentials from environment
        await self._load_credentials()
        
        self._initialized = True
        logger.info(
            f"Connector Manager initialized:\n"
            f"  Enabled: {self._enabled}\n"
            f"  Shadow Mode: {self._shadow_mode}\n"
            f"  Primary: {self._primary_venue}\n"
            f"  Fallback: {self._fallback_venue}"
        )
    
    async def _load_credentials(self):
        """Load exchange credentials from environment."""
        # Binance
        binance_key = os.environ.get("BINANCE_API_KEY")
        binance_secret = os.environ.get("BINANCE_API_SECRET")
        binance_testnet = os.environ.get("BINANCE_TESTNET", "false").lower() == "true"
        
        if binance_key and binance_secret:
            await self._connectors["binance"].initialize(
                api_key=binance_key,
                api_secret=binance_secret,
                testnet=binance_testnet
            )
            await self._connectors["binance"].connect()
            logger.info("[CONNECTORS] Binance connector configured")
        else:
            logger.warning("[CONNECTORS] Binance credentials not configured")
        
        # Kraken
        kraken_key = os.environ.get("KRAKEN_API_KEY")
        kraken_secret = os.environ.get("KRAKEN_API_SECRET")
        
        if kraken_key and kraken_secret:
            await self._connectors["kraken"].initialize(
                api_key=kraken_key,
                api_secret=kraken_secret
            )
            await self._connectors["kraken"].connect()
            logger.info("[CONNECTORS] Kraken connector configured")
        else:
            logger.warning("[CONNECTORS] Kraken credentials not configured")
        
        # Coinbase
        coinbase_key = os.environ.get("COINBASE_API_KEY")
        coinbase_secret = os.environ.get("COINBASE_API_SECRET")
        
        if coinbase_key and coinbase_secret:
            await self._connectors["coinbase"].initialize(
                api_key=coinbase_key,
                api_secret=coinbase_secret
            )
            await self._connectors["coinbase"].connect()
            logger.info("[CONNECTORS] Coinbase connector configured")
        else:
            logger.warning("[CONNECTORS] Coinbase credentials not configured")
    
    def is_enabled(self) -> bool:
        """Check if exchange trading is enabled."""
        return self._enabled and not self._shadow_mode
    
    def is_shadow_mode(self) -> bool:
        """Check if in shadow mode (simulated trades)."""
        return self._shadow_mode
    
    def get_connector(self, exchange: str) -> Optional[ExchangeConnector]:
        """Get a specific exchange connector."""
        return self._connectors.get(exchange)
    
    async def get_best_price(self, symbol: str) -> Tuple[Optional[MarketTicker], str]:
        """Get best price across all connected venues."""
        best_ticker = None
        best_venue = ""
        
        for name, connector in self._connectors.items():
            if not connector.is_connected():
                continue
            
            ticker = await connector.get_ticker(symbol)
            if ticker:
                if best_ticker is None or ticker.ask < best_ticker.ask:
                    best_ticker = ticker
                    best_venue = name
        
        return best_ticker, best_venue
    
    async def get_all_balances(self) -> Dict[str, List[ExchangeBalance]]:
        """Get balances from all connected venues."""
        all_balances = {}
        
        for name, connector in self._connectors.items():
            if connector.is_connected():
                balances = await connector.get_balances()
                all_balances[name] = balances
        
        return all_balances
    
    async def get_aggregated_balance(self, currency: str) -> Dict[str, float]:
        """Get aggregated balance for a currency across all venues."""
        result = {
            "total": 0,
            "available": 0,
            "locked": 0,
            "by_venue": {}
        }
        
        for name, connector in self._connectors.items():
            if connector.is_connected():
                balance = await connector.get_balance(currency)
                if balance:
                    result["total"] += balance.total
                    result["available"] += balance.available
                    result["locked"] += balance.locked
                    result["by_venue"][name] = balance.to_dict()
        
        return result
    
    async def execute_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: float,
        order_type: OrderType = OrderType.MARKET,
        price: Optional[float] = None,
        venue: Optional[str] = None,
        client_order_id: Optional[str] = None
    ) -> Tuple[ExchangeOrder, Optional[str]]:
        """
        Execute an order on the best venue or specified venue.
        
        Returns:
            Tuple of (ExchangeOrder, error_message)
        """
        now = datetime.now(timezone.utc)
        
        # Check if trading is enabled
        if not self._enabled:
            return self._create_shadow_order(
                symbol, side, quantity, order_type, price,
                "trading_disabled", "Exchange trading is disabled"
            ), "Exchange trading is disabled"
        
        if self._shadow_mode:
            return self._create_shadow_order(
                symbol, side, quantity, order_type, price,
                "shadow_mode", "Operating in shadow mode"
            ), None
        
        # Select venue
        target_venue = venue or self._primary_venue
        connector = self._connectors.get(target_venue)
        
        if not connector or not connector.is_connected():
            # Try fallback
            target_venue = self._fallback_venue
            connector = self._connectors.get(target_venue)
            
            if not connector or not connector.is_connected():
                return self._create_shadow_order(
                    symbol, side, quantity, order_type, price,
                    "no_venue", "No connected venues available"
                ), "No connected venues available"
        
        # Execute order
        try:
            if order_type == OrderType.MARKET:
                order = await connector.place_market_order(
                    symbol=symbol,
                    side=side,
                    quantity=quantity,
                    client_order_id=client_order_id
                )
            else:
                if price is None:
                    return self._create_shadow_order(
                        symbol, side, quantity, order_type, price,
                        "no_price", "Price required for limit orders"
                    ), "Price required for limit orders"
                
                order = await connector.place_limit_order(
                    symbol=symbol,
                    side=side,
                    quantity=quantity,
                    price=price,
                    client_order_id=client_order_id
                )
            
            # Store order
            await self.orders_collection.insert_one({
                **order.to_dict(),
                "is_shadow": False,
                "stored_at": now.isoformat()
            })
            
            return order, None
            
        except Exception as e:
            logger.error(f"[CONNECTORS] Order execution error: {e}")
            
            # Try fallback venue
            if target_venue == self._primary_venue:
                fallback_connector = self._connectors.get(self._fallback_venue)
                if fallback_connector and fallback_connector.is_connected():
                    logger.info(f"[CONNECTORS] Failing over to {self._fallback_venue}")
                    return await self.execute_order(
                        symbol, side, quantity, order_type, price,
                        self._fallback_venue, client_order_id
                    )
            
            return self._create_shadow_order(
                symbol, side, quantity, order_type, price,
                "execution_error", str(e)
            ), str(e)
    
    def _create_shadow_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: float,
        order_type: OrderType,
        price: Optional[float],
        reason: str,
        message: str
    ) -> ExchangeOrder:
        """Create a shadow (simulated) order for logging."""
        from uuid import uuid4
        
        return ExchangeOrder(
            order_id=f"shadow_{uuid4().hex[:12]}",
            exchange="shadow",
            symbol=symbol,
            side=side,
            order_type=order_type,
            status=OrderStatus.PENDING,
            quantity=quantity,
            price=price,
            client_order_id=f"shadow_{reason}"
        )
    
    async def enable_live_trading(self, user_id: str = None):
        """Enable live trading (disable shadow mode)."""
        self._shadow_mode = False
        self._enabled = True
        
        await self.config_collection.update_one(
            {"config_type": "exchanges"},
            {
                "$set": {
                    "enabled": True,
                    "shadow_mode": False,
                    "enabled_at": datetime.now(timezone.utc).isoformat(),
                    "enabled_by": user_id
                }
            }
        )
        
        logger.info(f"[CONNECTORS] LIVE TRADING ENABLED by {user_id}")
    
    async def disable_live_trading(self, reason: str = None):
        """Disable live trading (enable shadow mode)."""
        self._shadow_mode = True
        
        await self.config_collection.update_one(
            {"config_type": "exchanges"},
            {
                "$set": {
                    "shadow_mode": True,
                    "disabled_at": datetime.now(timezone.utc).isoformat(),
                    "disabled_reason": reason
                }
            }
        )
        
        logger.warning(f"[CONNECTORS] LIVE TRADING DISABLED: {reason}")
    
    async def get_status(self) -> Dict:
        """Get connector manager status."""
        venues = {}
        
        for name, connector in self._connectors.items():
            venues[name] = {
                "initialized": connector.is_initialized(),
                "connected": connector.is_connected()
            }
        
        return {
            "enabled": self._enabled,
            "shadow_mode": self._shadow_mode,
            "primary_venue": self._primary_venue,
            "fallback_venue": self._fallback_venue,
            "venues": venues
        }


# Global instance
_connector_manager: Optional[ConnectorManager] = None


def get_connector_manager() -> Optional[ConnectorManager]:
    return _connector_manager


def set_connector_manager(manager: ConnectorManager):
    global _connector_manager
    _connector_manager = manager
