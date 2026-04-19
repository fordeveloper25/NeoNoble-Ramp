"""
Hybrid Swap Engine Extension for NeoNoble Ramp
Extends swap_engine_v2.py with Market Maker + CEX fallback support
"""
import logging
import os
from typing import Dict, List, Optional, Tuple
from decimal import Decimal

from engines.swap_engine_v2 import SwapEngineV2
from engines.market_maker import MarketMaker
from engines.chain_router import ChainRouter
from services.exchanges.binance_connector import BinanceConnector
from services.exchanges.mexc_connector import MexcConnector
from services.exchanges.kraken_connector import KrakenConnector
from services.exchanges.coinbase_connector import CoinbaseConnector

logger = logging.getLogger(__name__)


class HybridSwapEngine:
    """
    Hybrid Swap Engine that combines:
    1. DEX routing (1inch → PancakeSwap → other DEX)
    2. Market Maker for NENO and custom tokens
    3. CEX fallback for high liquidity needs
    """
    
    def __init__(self, db):
        self.db = db
        
        # Initialize core swap engine (DEX routing)
        self.swap_engine = SwapEngineV2()
        if db:
            self.swap_engine.set_db(db)
        
        # Initialize market maker for NENO/custom tokens
        self.market_maker = MarketMaker(db)
        
        # Initialize multi-chain router
        self.chain_router = ChainRouter()
        
        # Initialize CEX connectors
        self.cex_enabled = os.getenv("CEX_FALLBACK_ENABLED", "true").lower() == "true"
        self.cex_connectors = {}
        
        if self.cex_enabled:
            try:
                self.cex_connectors["binance"] = BinanceConnector()
                logger.info("✅ Binance connector initialized")
            except Exception as e:
                logger.warning(f"Binance connector failed: {e}")
            
            try:
                self.cex_connectors["mexc"] = MexcConnector()
                logger.info("✅ MEXC connector initialized")
            except Exception as e:
                logger.warning(f"MEXC connector failed: {e}")
            
            try:
                self.cex_connectors["kraken"] = KrakenConnector()
                logger.info("✅ Kraken connector initialized")
            except Exception as e:
                logger.warning(f"Kraken connector failed: {e}")
            
            try:
                self.cex_connectors["coinbase"] = CoinbaseConnector()
                logger.info("✅ Coinbase connector initialized")
            except Exception as e:
                logger.warning(f"Coinbase connector failed: {e}")
        
        logger.info(f"HybridSwapEngine initialized with {len(self.cex_connectors)} CEX connectors")
    
    async def get_quote(
        self,
        from_token: str,
        to_token: str,
        amount_in: float,
        chain_id: int = 56
    ) -> Optional[Dict]:
        """
        Get best quote using hybrid routing:
        1. Try DEX (1inch → PancakeSwap)
        2. Try Market Maker (if NENO involved)
        3. Try CEX (if enabled)
        
        Returns the best available quote
        """
        quotes = []
        
        # 1. Try DEX routing (existing swap_engine_v2 logic)
        try:
            dex_quote = await self.swap_engine.get_quote(from_token, to_token, amount_in)
            if dex_quote and dex_quote.get("estimated_amount_out", 0) > 0:
                quotes.append({
                    "source": dex_quote.get("source", "dex"),
                    "amount_out": dex_quote["estimated_amount_out"],
                    "rate": dex_quote["rate"],
                    "quote": dex_quote,
                    "execution_mode": "user_signed"
                })
                logger.info(f"DEX quote: {from_token}→{to_token} = {dex_quote['estimated_amount_out']}")
        except Exception as e:
            logger.error(f"DEX quote failed: {e}")
        
        # 2. Try Market Maker (for NENO and custom tokens)
        try:
            mm_quote = await self.market_maker.get_price(from_token, to_token, amount_in)
            if mm_quote:
                quotes.append({
                    "source": "market_maker",
                    "amount_out": mm_quote["amount_out"],
                    "rate": mm_quote["rate"],
                    "quote": mm_quote,
                    "execution_mode": "platform"
                })
                logger.info(f"Market Maker quote: {from_token}→{to_token} = {mm_quote['amount_out']}")
        except Exception as e:
            logger.error(f"Market Maker quote failed: {e}")
        
        # 3. Try CEX liquidity (if enabled and no good DEX quote)
        if self.cex_enabled and (not quotes or max(q["amount_out"] for q in quotes) == 0):
            cex_quote = await self._get_best_cex_quote(from_token, to_token, amount_in)
            if cex_quote:
                quotes.append(cex_quote)
                logger.info(f"CEX quote from {cex_quote['source']}: {from_token}→{to_token} = {cex_quote['amount_out']}")
        
        # Return best quote (highest output)
        if quotes:
            best_quote = max(quotes, key=lambda q: q["amount_out"])
            logger.info(f"Best quote: {best_quote['source']} with {best_quote['amount_out']} {to_token}")
            return best_quote["quote"]
        
        logger.warning(f"No quotes available for {from_token}→{to_token}")
        return None
    
    async def _get_best_cex_quote(
        self,
        from_token: str,
        to_token: str,
        amount_in: float
    ) -> Optional[Dict]:
        """
        Query all CEX connectors and return best quote
        """
        cex_quotes = []
        
        for exchange_name, connector in self.cex_connectors.items():
            try:
                # Normalize symbol for the exchange
                symbol = connector.normalize_symbol(from_token, to_token)
                
                # Get ticker price
                ticker = await connector.get_ticker(symbol)
                if ticker:
                    # Estimate output (simplified - assumes selling from_token)
                    estimated_out = amount_in * ticker["bid"]
                    
                    cex_quotes.append({
                        "source": f"cex_{exchange_name}",
                        "amount_out": estimated_out,
                        "rate": ticker["bid"],
                        "quote": {
                            "from_token": from_token,
                            "to_token": to_token,
                            "amount_in": amount_in,
                            "estimated_amount_out": estimated_out,
                            "rate": ticker["bid"],
                            "source": f"cex_{exchange_name}",
                            "exchange": exchange_name,
                            "note": "CEX liquidity fallback"
                        },
                        "execution_mode": "platform_cex"
                    })
            except Exception as e:
                logger.error(f"CEX quote from {exchange_name} failed: {e}")
        
        if cex_quotes:
            return max(cex_quotes, key=lambda q: q["amount_out"])
        
        return None
    
    async def build_swap(
        self,
        from_token: str,
        to_token: str,
        amount_in: float,
        user_wallet: str,
        slippage_pct: float = 0.8,
        chain_id: int = 56
    ) -> Optional[Dict]:
        """
        Build swap transaction based on best available route
        
        Returns swap details with execution mode:
        - "user_signed": User signs DEX transaction in MetaMask
        - "platform": Platform executes via Market Maker
        - "platform_cex": Platform executes via CEX
        """
        # Get best quote
        quote = await self.get_quote(from_token, to_token, amount_in, chain_id)
        
        if not quote:
            return None
        
        source = quote.get("source", "")
        
        # Route 1: DEX (user-signed mode)
        if source in ["1inch", "pancakeswap", "dex"]:
            logger.info(f"Building DEX swap via {source}")
            return await self.swap_engine.build_swap(
                from_token, to_token, amount_in, user_wallet, slippage_pct
            )
        
        # Route 2: Market Maker (platform execution)
        elif source == "market_maker":
            logger.info("Building Market Maker swap")
            return {
                "execution_mode": "platform",
                "source": "market_maker",
                "from_token": from_token,
                "to_token": to_token,
                "amount_in": amount_in,
                "estimated_amount_out": quote["amount_out"],
                "user_wallet": user_wallet,
                "status": "pending_platform_execution",
                "note": f"Platform will execute swap at {quote.get('price_eur', 0)}€ per NENO"
            }
        
        # Route 3: CEX (platform execution)
        elif source.startswith("cex_"):
            exchange = source.replace("cex_", "")
            logger.info(f"Building CEX swap via {exchange}")
            return {
                "execution_mode": "platform_cex",
                "source": source,
                "exchange": exchange,
                "from_token": from_token,
                "to_token": to_token,
                "amount_in": amount_in,
                "estimated_amount_out": quote["amount_out"],
                "user_wallet": user_wallet,
                "status": "pending_cex_execution",
                "note": f"Platform will execute on {exchange} CEX"
            }
        
        return None
    
    async def execute_hybrid_swap(
        self,
        swap_build: Dict,
        user_id: str
    ) -> Tuple[bool, Optional[str], Optional[Dict]]:
        """
        Execute swap based on execution mode
        
        Returns:
            (success, tx_hash, details)
        """
        execution_mode = swap_build.get("execution_mode")
        
        # User-signed mode: User executes in their wallet
        if execution_mode == "user_signed":
            # For user-signed, we just return the calldata
            # The actual execution happens when user signs in MetaMask
            return True, None, {
                "status": "awaiting_user_signature",
                "note": "User must sign transaction in MetaMask"
            }
        
        # Platform Market Maker execution
        elif execution_mode == "platform":
            success, swap_id, details = await self.market_maker.execute_swap(
                swap_build["from_token"],
                swap_build["to_token"],
                swap_build["amount_in"],
                swap_build["user_wallet"],
                user_id
            )
            return success, swap_id, details
        
        # CEX execution
        elif execution_mode == "platform_cex":
            exchange_name = swap_build.get("exchange")
            connector = self.cex_connectors.get(exchange_name)
            
            if not connector:
                return False, None, {"error": f"CEX connector {exchange_name} not available"}
            
            result = await connector.execute_swap(
                swap_build["from_token"],
                swap_build["to_token"],
                swap_build["amount_in"]
            )
            
            if result and result.get("success"):
                return True, result.get("order_id"), result
            else:
                return False, None, {"error": "CEX swap execution failed"}
        
        return False, None, {"error": f"Unknown execution mode: {execution_mode}"}
    
    async def track_swap(
        self,
        swap_id: str,
        tx_hash: str
    ) -> Optional[Dict]:
        """
        Track swap status (delegates to swap_engine_v2 for DEX swaps)
        """
        return await self.swap_engine.track_swap(swap_id, tx_hash)
    
    async def get_health(self) -> Dict:
        """
        Get health status of hybrid swap system
        """
        base_health = self.swap_engine.health()  # Not async
        
        return {
            **base_health,
            "mode": "hybrid",
            "market_maker_enabled": self.market_maker.enabled,
            "cex_fallback_enabled": self.cex_enabled,
            "cex_connectors_available": list(self.cex_connectors.keys()),
            "supported_chains": [56, 1, 137, 42161, 8453],
            "neno_price_eur": float(self.market_maker.neno_price_eur)
        }
