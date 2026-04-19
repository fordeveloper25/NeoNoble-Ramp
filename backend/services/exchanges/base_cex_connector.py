"""
Base CEX Connector for NeoNoble Ramp Hybrid Swap Engine
"""
from abc import ABC, abstractmethod
from typing import Dict, Optional, List
import logging

logger = logging.getLogger(__name__)


class BaseCEXConnector(ABC):
    """Abstract base class for CEX connectors"""
    
    def __init__(self, api_key: str, api_secret: str, testnet: bool = False):
        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet
        self.exchange_name = self.__class__.__name__.replace("Connector", "")
    
    @abstractmethod
    async def get_ticker(self, symbol: str) -> Optional[Dict]:
        """
        Get current price for a trading pair
        
        Args:
            symbol: Trading pair (e.g., 'BTCUSDT')
            
        Returns:
            {"bid": float, "ask": float, "last": float} or None
        """
        pass
    
    @abstractmethod
    async def get_orderbook(self, symbol: str, limit: int = 10) -> Optional[Dict]:
        """
        Get order book depth
        
        Returns:
            {"bids": [[price, quantity], ...], "asks": [[price, quantity], ...]}
        """
        pass
    
    @abstractmethod
    async def create_market_order(
        self, 
        symbol: str, 
        side: str, 
        quantity: float
    ) -> Optional[Dict]:
        """
        Create a market order
        
        Args:
            symbol: Trading pair
            side: 'BUY' or 'SELL'
            quantity: Amount to trade
            
        Returns:
            Order details or None on failure
        """
        pass
    
    @abstractmethod
    async def get_balance(self, asset: str) -> Optional[float]:
        """Get available balance for an asset"""
        pass
    
    @abstractmethod
    async def get_account_info(self) -> Optional[Dict]:
        """Get account information"""
        pass
    
    @abstractmethod
    def normalize_symbol(self, base: str, quote: str) -> str:
        """
        Normalize trading pair to exchange format
        
        Args:
            base: Base currency (e.g., 'BTC')
            quote: Quote currency (e.g., 'USDT')
            
        Returns:
            Exchange-specific symbol format
        """
        pass
    
    async def estimate_liquidity(self, symbol: str, quantity: float, side: str) -> Optional[Dict]:
        """
        Estimate if CEX has enough liquidity for a trade
        
        Returns:
            {"available": bool, "estimated_slippage_pct": float, "estimated_price": float}
        """
        try:
            orderbook = await self.get_orderbook(symbol, limit=50)
            if not orderbook:
                return None
            
            # Calculate if there's enough liquidity
            orders = orderbook["asks"] if side == "BUY" else orderbook["bids"]
            
            total_quantity = 0
            total_cost = 0
            
            for price, qty in orders:
                if total_quantity >= quantity:
                    break
                available_qty = min(qty, quantity - total_quantity)
                total_quantity += available_qty
                total_cost += price * available_qty
            
            if total_quantity < quantity:
                return {
                    "available": False,
                    "reason": f"Insufficient liquidity: {total_quantity}/{quantity}"
                }
            
            avg_price = total_cost / total_quantity
            ticker = await self.get_ticker(symbol)
            mid_price = (ticker["bid"] + ticker["ask"]) / 2 if ticker else avg_price
            
            slippage_pct = abs((avg_price - mid_price) / mid_price * 100)
            
            return {
                "available": True,
                "estimated_slippage_pct": slippage_pct,
                "estimated_price": avg_price,
                "total_quantity": total_quantity,
                "exchange": self.exchange_name
            }
            
        except Exception as e:
            logger.error(f"{self.exchange_name}.estimate_liquidity error: {e}")
            return None
    
    async def execute_swap(
        self,
        from_token: str,
        to_token: str,
        amount_in: float,
        slippage_tolerance: float = 3.0
    ) -> Optional[Dict]:
        """
        Execute a swap on the CEX
        
        Returns:
            Swap result with transaction details
        """
        try:
            # Determine trading pair and side
            # This is simplified - production would handle more complex routing
            symbol = self.normalize_symbol(from_token, to_token)
            side = "SELL"  # Selling from_token for to_token
            
            # Check liquidity
            liquidity = await self.estimate_liquidity(symbol, amount_in, side)
            if not liquidity or not liquidity.get("available"):
                return None
            
            if liquidity["estimated_slippage_pct"] > slippage_tolerance:
                logger.warning(f"{self.exchange_name}: Slippage too high {liquidity['estimated_slippage_pct']}%")
                return None
            
            # Execute market order
            order = await self.create_market_order(symbol, side, amount_in)
            
            if order:
                return {
                    "success": True,
                    "exchange": self.exchange_name,
                    "order_id": order.get("orderId") or order.get("id"),
                    "from_token": from_token,
                    "to_token": to_token,
                    "amount_in": amount_in,
                    "amount_out": order.get("executedQty") or order.get("filled"),
                    "avg_price": order.get("avgPrice") or order.get("price"),
                    "status": order.get("status"),
                    "slippage_pct": liquidity["estimated_slippage_pct"]
                }
            
            return None
            
        except Exception as e:
            logger.error(f"{self.exchange_name}.execute_swap error: {e}")
            return None
