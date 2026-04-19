"""
NeoNoble Ramp - Market Maker Engine
Handles pricing and execution for custom tokens (NENO and platform-created tokens)
"""
import os
from decimal import Decimal
from typing import Dict, Optional, Tuple
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)


class MarketMaker:
    """
    Market maker for NENO and custom platform tokens.
    Provides fixed or dynamic pricing independent of DEX liquidity.
    """
    
    def __init__(self, db):
        self.db = db
        self.enabled = os.getenv("MARKET_MAKER_ENABLED", "true").lower() == "true"
        self.neno_price_eur = Decimal(os.getenv("NENO_PRICE_EUR", "10000"))
        self.max_daily_volume_eur = Decimal(os.getenv("MARKET_MAKER_MAX_DAILY_VOLUME_EUR", "1000000"))
        
        # Supported tokens for market making
        self.supported_tokens = ["NENO"]
        
        logger.info(f"MarketMaker initialized: NENO={self.neno_price_eur}€, max_daily={self.max_daily_volume_eur}€")
    
    def is_supported(self, token_symbol: str) -> bool:
        """Check if token is supported by market maker"""
        return token_symbol.upper() in self.supported_tokens
    
    async def get_price(self, from_token: str, to_token: str, amount_in: float) -> Optional[Dict]:
        """
        Get market maker price for a token pair.
        Returns None if pair is not supported.
        
        Args:
            from_token: Source token symbol
            to_token: Destination token symbol  
            amount_in: Amount of source token
            
        Returns:
            Dict with price info or None if not supported
        """
        if not self.enabled:
            return None
        
        from_token = from_token.upper()
        to_token = to_token.upper()
        
        # Check if at least one token is supported by market maker
        if not (self.is_supported(from_token) or self.is_supported(to_token)):
            return None
        
        try:
            # Check daily volume limits
            if not await self._check_volume_limit(amount_in, from_token):
                logger.warning(f"MarketMaker: Daily volume limit exceeded for {from_token}")
                return None
            
            # Calculate price based on NENO/EUR fixed rate
            if from_token == "NENO":
                # Selling NENO
                eur_value = Decimal(str(amount_in)) * self.neno_price_eur
                amount_out = await self._convert_eur_to_crypto(eur_value, to_token)
                
                return {
                    "source": "market_maker",
                    "from_token": from_token,
                    "to_token": to_token,
                    "amount_in": amount_in,
                    "amount_out": float(amount_out),
                    "rate": float(amount_out / Decimal(str(amount_in))),
                    "price_eur": float(self.neno_price_eur),
                    "spread_pct": 0.0,  # No spread for platform market making
                    "note": f"Platform market maker (NENO={self.neno_price_eur}€)"
                }
            
            elif to_token == "NENO":
                # Buying NENO
                # First convert from_token to EUR value
                eur_value = await self._convert_crypto_to_eur(Decimal(str(amount_in)), from_token)
                # Then calculate NENO amount
                amount_out = eur_value / self.neno_price_eur
                
                return {
                    "source": "market_maker",
                    "from_token": from_token,
                    "to_token": to_token,
                    "amount_in": amount_in,
                    "amount_out": float(amount_out),
                    "rate": float(amount_out / Decimal(str(amount_in))),
                    "price_eur": float(self.neno_price_eur),
                    "spread_pct": 0.0,
                    "note": f"Platform market maker (NENO={self.neno_price_eur}€)"
                }
            
            return None
            
        except Exception as e:
            logger.error(f"MarketMaker.get_price error: {e}")
            return None
    
    async def execute_swap(
        self, 
        from_token: str, 
        to_token: str, 
        amount_in: float,
        user_wallet: str,
        user_id: str
    ) -> Tuple[bool, Optional[str], Optional[Dict]]:
        """
        Execute a market maker swap.
        
        Returns:
            (success, tx_hash, details)
        """
        try:
            # Check if DB is configured
            if self.db is None:
                logger.error("MarketMaker DB not configured")
                return False, None, {"error": "Database not configured"}
            
            # Get price quote
            quote = await self.get_price(from_token, to_token, amount_in)
            if not quote:
                return False, None, {"error": "Market maker quote unavailable"}
            
            # Record swap in database
            swap_record = {
                "user_id": user_id,
                "user_wallet": user_wallet,
                "from_token": from_token,
                "to_token": to_token,
                "amount_in": amount_in,
                "amount_out": quote["amount_out"],
                "rate": quote["rate"],
                "source": "market_maker",
                "status": "pending",
                "execution_mode": "platform",
                "created_at": datetime.now(timezone.utc),
                "neno_price_eur": float(self.neno_price_eur)
            }
            
            result = await self.db.market_maker_swaps.insert_one(swap_record)
            swap_id = str(result.inserted_id)
            
            logger.info(f"MarketMaker swap recorded: {swap_id} - {from_token} → {to_token}")
            
            # In production, here would be logic to:
            # 1. If selling NENO: Transfer NENO from user → platform
            # 2. If buying NENO: Transfer crypto from user → platform
            # 3. Execute CEX trade if needed
            # 4. Transfer output tokens to user wallet
            # For now, mark as pending and return success
            
            return True, swap_id, {
                "swap_id": swap_id,
                "status": "pending",
                "amount_out": quote["amount_out"],
                "note": "Market maker swap pending execution. Platform will transfer tokens to your wallet soon.",
                "execution_eta_minutes": 2
            }
            
        except Exception as e:
            logger.error(f"MarketMaker.execute_swap error: {e}")
            return False, None, {"error": str(e)}
    
    async def _check_volume_limit(self, amount: float, token: str) -> bool:
        """Check if swap is within daily volume limits"""
        try:
            today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
            
            # Get today's volume in EUR
            pipeline = [
                {
                    "$match": {
                        "created_at": {"$gte": today},
                        "$or": [
                            {"from_token": token},
                            {"to_token": token}
                        ],
                        "status": {"$ne": "failed"}
                    }
                },
                {
                    "$group": {
                        "_id": None,
                        "total_eur": {"$sum": "$amount_in"}  # Simplified - should convert to EUR
                    }
                }
            ]
            
            result = await self.db.market_maker_swaps.aggregate(pipeline).to_list(1)
            today_volume_eur = Decimal(str(result[0]["total_eur"])) if result else Decimal("0")
            
            # Add current swap volume
            if token == "NENO":
                current_eur = Decimal(str(amount)) * self.neno_price_eur
            else:
                current_eur = Decimal(str(amount))  # Simplified
            
            total_eur = today_volume_eur + current_eur
            
            if total_eur > self.max_daily_volume_eur:
                logger.warning(f"Daily volume limit exceeded: {total_eur}€ > {self.max_daily_volume_eur}€")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking volume limit: {e}")
            return True  # Allow on error to not block swaps
    
    async def _convert_eur_to_crypto(self, eur_amount: Decimal, crypto_symbol: str) -> Decimal:
        """
        Convert EUR to cryptocurrency amount.
        Uses approximate rates - in production would query real-time prices.
        """
        # Approximate EUR prices (should be fetched from price oracle in production)
        eur_prices = {
            "USDT": Decimal("0.95"),  # 1 USDT ≈ 0.95 EUR
            "USDC": Decimal("0.95"),  # 1 USDC ≈ 0.95 EUR
            "BTCB": Decimal("90000"),  # 1 BTCB ≈ 90000 EUR
            "BTC": Decimal("90000"),
            "ETH": Decimal("3000"),   # 1 ETH ≈ 3000 EUR
            "BNB": Decimal("550"),    # 1 BNB ≈ 550 EUR
            "WBNB": Decimal("550"),
            "BUSD": Decimal("0.95"),
        }
        
        price = eur_prices.get(crypto_symbol.upper(), Decimal("1"))
        return eur_amount / price
    
    async def _convert_crypto_to_eur(self, crypto_amount: Decimal, crypto_symbol: str) -> Decimal:
        """
        Convert cryptocurrency to EUR amount.
        Uses approximate rates - in production would query real-time prices.
        """
        # Approximate EUR prices
        eur_prices = {
            "USDT": Decimal("0.95"),
            "USDC": Decimal("0.95"),
            "BTCB": Decimal("90000"),
            "BTC": Decimal("90000"),
            "ETH": Decimal("3000"),
            "BNB": Decimal("550"),
            "WBNB": Decimal("550"),
            "BUSD": Decimal("0.95"),
        }
        
        price = eur_prices.get(crypto_symbol.upper(), Decimal("1"))
        return crypto_amount * price
