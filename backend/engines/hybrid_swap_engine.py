"""
Hybrid Swap Engine - Simplified with CEX Liquidity Integration
Handles NENO Market Maker @ 10,000€ with real token delivery
"""
import logging
from decimal import Decimal
from typing import Dict, Optional

from services.cex.cex_liquidity_provider import CexLiquidityProvider

logger = logging.getLogger(__name__)


class HybridSwapEngine:
    """
    Hybrid Swap Engine for NENO Market Maker with CEX liquidity
    """
    
    def __init__(self):
        self.market_maker_enabled = True
        self.cex_fallback_enabled = True
        self.neno_price_eur = Decimal("10000.0")
        
        # Initialize CEX liquidity provider
        self.cex_provider = CexLiquidityProvider()
        
        logger.info(f"✅ HybridSwapEngine initialized (NENO @ {self.neno_price_eur}€) with CEX liquidity")
    
    async def get_quote(
        self,
        from_token: str,
        to_token: str,
        amount_in: float
    ) -> Optional[Dict]:
        """Get quote for swap"""
        try:
            # Market Maker for NENO
            if from_token.upper() == "NENO":
                # EUR per NENO = 10,000
                # Approximate EUR/USDT rate = 1.05
                eur_value = Decimal(str(amount_in)) * self.neno_price_eur
                
                # Convert EUR to target token (simplified)
                if to_token.upper() in ["USDT", "USDC", "BUSD"]:
                    amount_out = float(eur_value / Decimal("0.95"))  # 1 EUR ≈ 1.05 USD
                elif to_token.upper() in ["BTCB", "BTC"]:
                    amount_out = float(eur_value / Decimal("90000"))  # 1 BTC ≈ 90k EUR
                elif to_token.upper() in ["BNB", "WBNB"]:
                    amount_out = float(eur_value / Decimal("550"))  # 1 BNB ≈ 550 EUR
                elif to_token.upper() in ["ETH"]:
                    amount_out = float(eur_value / Decimal("3000"))  # 1 ETH ≈ 3k EUR
                else:
                    amount_out = float(eur_value)  # Default 1:1
                
                return {
                    "source": "market_maker",
                    "from_token": from_token,
                    "to_token": to_token,
                    "amount_in": amount_in,
                    "estimated_amount_out": amount_out,
                    "rate": amount_out / amount_in,
                    "price_eur": float(self.neno_price_eur),
                    "note": f"Platform market maker (NENO={self.neno_price_eur}€)"
                }
            
            # No quote available for non-NENO tokens yet
            return None
            
        except Exception as e:
            logger.error(f"HybridSwapEngine.get_quote error: {e}")
            return None
    
    async def build_swap(
        self,
        from_token: str,
        to_token: str,
        amount_in: float,
        user_wallet: str,
        slippage_pct: float = 0.8
    ) -> Optional[Dict]:
        """Build swap transaction"""
        try:
            quote = await self.get_quote(from_token, to_token, amount_in)
            
            if not quote:
                return None
            
            # For Market Maker swaps, return platform execution mode
            if quote["source"] == "market_maker":
                return {
                    "execution_mode": "platform",
                    "source": "market_maker",
                    "from_token": from_token,
                    "to_token": to_token,
                    "amount_in": amount_in,
                    "estimated_amount_out": quote["estimated_amount_out"],
                    "user_wallet": user_wallet,
                    "status": "ready_for_execution",
                    "note": f"Platform will execute swap at {quote['price_eur']}€ per NENO"
                }
            
            return None
            
        except Exception as e:
            logger.error(f"HybridSwapEngine.build_swap error: {e}")
            return None
    
    async def execute_swap(
        self,
        from_token: str,
        to_token: str,
        amount_in: float,
        user_wallet: str,
        user_id: str
    ) -> tuple[bool, Optional[str], Optional[Dict]]:
        """
        Execute Market Maker swap with real CEX liquidity delivery
        Returns: (success, swap_id, details)
        """
        try:
            # Generate swap ID
            import uuid
            swap_id = str(uuid.uuid4())
            
            logger.info(f"Executing Market Maker swap {swap_id}: {amount_in} {from_token} → {to_token}")
            
            # Process swap with CEX liquidity provider
            result = await self.cex_provider.process_market_maker_swap(
                amount_in=Decimal(str(amount_in)),
                from_token=from_token,
                to_token=to_token,
                user_wallet=user_wallet,
                chain="BSC"
            )
            
            if not result["success"]:
                return False, None, {"error": result.get("error", "Swap execution failed")}
            
            logger.info(
                f"✅ Market Maker swap {swap_id} completed: "
                f"{amount_in} {from_token} → {result['amount_out']:.4f} {to_token} "
                f"(mode: {result.get('mode', 'unknown')})"
            )
            
            return True, swap_id, {
                "swap_id": swap_id,
                "status": "completed" if result.get("mode") == "real" else "simulated",
                "amount_out": result["amount_out"],
                "tx_hash": result.get("tx_hash"),
                "mode": result.get("mode", "unknown"),
                "note": result.get("note", "Swap processed"),
                "execution_eta_minutes": 0 if result.get("mode") == "mock" else 30
            }
            
        except Exception as e:
            logger.error(f"HybridSwapEngine.execute_swap error: {e}")
            return False, None, {"error": str(e)}
    
    async def get_health(self) -> Dict:
        """Get health status"""
        return {
            "mode": "hybrid_simplified",
            "market_maker_enabled": self.market_maker_enabled,
            "cex_fallback_enabled": self.cex_fallback_enabled,
            "neno_price_eur": float(self.neno_price_eur),
            "status": "operational"
        }

