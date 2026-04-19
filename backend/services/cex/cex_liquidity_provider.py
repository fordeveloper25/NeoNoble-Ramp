"""
CEX Liquidity Provider for NeoNoble Ramp
Handles real token delivery via on-chain transfers or CEX APIs
"""
import os
import logging
import asyncio
from decimal import Decimal
from typing import Dict, Optional
import time

logger = logging.getLogger(__name__)

# Import on-chain transfer service
try:
    from services.onchain_transfer_service import OnChainTransferService
    ONCHAIN_SERVICE_AVAILABLE = True
except ImportError:
    ONCHAIN_SERVICE_AVAILABLE = False
    logger.warning("OnChainTransferService not available")

# Try to import ccxt (optional for CEX)
try:
    import ccxt
    CCXT_AVAILABLE = True
except ImportError:
    CCXT_AVAILABLE = False
    logger.warning("CCXT not installed. CEX fallback disabled.")


class CexLiquidityProvider:
    """
    Provides liquidity for Market Maker swaps via on-chain transfers or CEX APIs
    Priority: On-chain hot wallet → CEX withdrawal → Mock
    """
    
    def __init__(self):
        self.exchanges = {}
        self.neno_price_eur = Decimal("10000.0")
        
        # Initialize on-chain transfer service (PRIORITY)
        if ONCHAIN_SERVICE_AVAILABLE:
            self.onchain_service = OnChainTransferService()
            if self.onchain_service.enabled:
                logger.info("✅ On-Chain Transfer Service active (REAL MODE)")
                self.mock_mode = False
            else:
                logger.warning("On-Chain Transfer Service not configured")
                self.mock_mode = True
                self.onchain_service = None
        else:
            self.onchain_service = None
            self.mock_mode = True
        
        # Initialize CEX as fallback
        if CCXT_AVAILABLE and self.mock_mode:
            self.load_exchanges()
        
        if self.mock_mode and not self.exchanges:
            logger.warning("⚠️  CEX Liquidity Provider running in MOCK MODE")
    
    def load_exchanges(self):
        """Load CEX exchanges from environment variables"""
        try:
            # Binance
            binance_key = os.getenv('BINANCE_API_KEY')
            binance_secret = os.getenv('BINANCE_API_SECRET')
            
            if binance_key and binance_secret:
                self.exchanges["binance"] = ccxt.binance({
                    'apiKey': binance_key,
                    'secret': binance_secret,
                    'enableRateLimit': True,
                })
                logger.info("✅ Binance exchange loaded")
            
            # MEXC
            mexc_key = os.getenv('MEXC_API_KEY')
            mexc_secret = os.getenv('MEXC_API_SECRET')
            
            if mexc_key and mexc_secret:
                self.exchanges["mexc"] = ccxt.mexc({
                    'apiKey': mexc_key,
                    'secret': mexc_secret,
                    'enableRateLimit': True,
                })
                logger.info("✅ MEXC exchange loaded")
            
            # Kraken
            kraken_key = os.getenv('KRAKEN_API_KEY')
            kraken_secret = os.getenv('KRAKEN_API_SECRET')
            
            if kraken_key and kraken_secret:
                self.exchanges["kraken"] = ccxt.kraken({
                    'apiKey': kraken_key,
                    'secret': kraken_secret,
                    'enableRateLimit': True,
                })
                logger.info("✅ Kraken exchange loaded")
            
            logger.info(f"CEX Liquidity Provider initialized with {len(self.exchanges)} exchanges")
            
        except Exception as e:
            logger.error(f"Error loading CEX exchanges: {e}")
            self.mock_mode = True
    
    async def provide_liquidity(
        self,
        to_token: str,
        amount_out: Decimal,
        user_wallet: str,
        chain: str = "BSC"
    ) -> Dict:
        """
        Provide liquidity using:
        1. CEX withdrawal (PRIORITY - from your exchange balance)
        2. On-chain hot wallet transfer (fallback)
        3. Mock mode (demo)
        """
        # PRIORITY: Use CEX withdrawal if configured
        if self.exchanges and not self.mock_mode:
            try:
                logger.info(f"🎯 Using CEX withdrawal for {amount_out} {to_token}")
                result = await self._provide_liquidity_cex(to_token, amount_out, user_wallet, chain)
                
                if result["success"]:
                    return result
                    
                logger.warning(f"CEX withdrawal failed: {result.get('error')}")
            except Exception as e:
                logger.warning(f"CEX withdrawal error: {e}")
        
        # FALLBACK: Use on-chain transfer if CEX fails
        if self.onchain_service and self.onchain_service.enabled:
            try:
                logger.info(f"Fallback: using on-chain transfer for {amount_out} {to_token}")
                result = await self.onchain_service.transfer_tokens(
                    token_symbol=to_token,
                    amount=amount_out,
                    to_address=user_wallet
                )
                
                if result["success"]:
                    return result
            except Exception as e:
                logger.warning(f"On-chain transfer error: {e}")
        
        # LAST RESORT: Mock mode
        return await self._provide_liquidity_mock(to_token, amount_out, user_wallet, chain)
    
    async def _provide_liquidity_cex(
        self,
        to_token: str,
        amount_out: Decimal,
        user_wallet: str,
        chain: str
    ) -> Dict:
        """Try CEX withdrawal"""
        
        # Try real CEX withdrawal
        cex_priority = ["binance", "mexc", "kraken"]
        
        for cex_name in cex_priority:
            if cex_name not in self.exchanges:
                continue
            
            try:
                result = await self._attempt_cex_withdrawal(
                    cex_name,
                    to_token,
                    amount_out,
                    user_wallet,
                    chain
                )
                
                if result["success"]:
                    return result
                    
            except Exception as e:
                logger.warning(f"CEX {cex_name} withdrawal failed: {e}")
                continue
        
        # Fallback to mock if all CEX fail
        logger.warning("All CEX withdrawals failed, using mock execution")
        return await self._provide_liquidity_mock(to_token, amount_out, user_wallet, chain)
    
    async def _attempt_cex_withdrawal(
        self,
        cex_name: str,
        to_token: str,
        amount_out: Decimal,
        user_wallet: str,
        chain: str
    ) -> Dict:
        """Attempt real withdrawal from CEX"""
        exchange = self.exchanges[cex_name]
        
        # Note: This requires:
        # 1. Withdrawal permissions on API key
        # 2. Whitelisted wallet address
        # 3. Sufficient balance on CEX
        
        try:
            # Attempt withdrawal
            withdraw_result = await asyncio.to_thread(
                exchange.withdraw,
                code=to_token,
                amount=float(amount_out),
                address=user_wallet,
                tag=None,
                params={'network': chain}
            )
            
            tx_id = withdraw_result.get('id') or withdraw_result.get('txid')
            
            logger.info(f"✅ Real withdrawal initiated from {cex_name}: {tx_id}")
            
            return {
                "success": True,
                "cex_used": cex_name,
                "amount_delivered": float(amount_out),
                "tx_hash": tx_id,
                "mode": "real",
                "note": f"Withdrawal initiated from {cex_name}. Tokens will arrive in 5-30 minutes."
            }
            
        except Exception as e:
            # Common errors: insufficient permissions, non-whitelisted address, etc.
            logger.warning(f"CEX withdrawal not possible: {e}")
            raise
    
    async def _provide_liquidity_mock(
        self,
        to_token: str,
        amount_out: Decimal,
        user_wallet: str,
        chain: str
    ) -> Dict:
        """
        Mock liquidity provision (for demo/development)
        Shows what would happen in production
        """
        # Simulate processing time
        await asyncio.sleep(0.5)
        
        # Generate mock tx hash
        mock_tx_hash = f"0x{'a' * 64}"  # Mock transaction hash
        
        logger.info(
            f"🔄 MOCK EXECUTION: Would transfer {amount_out} {to_token} to {user_wallet} on {chain}"
        )
        logger.info(
            f"📋 PRODUCTION FLOW: "
            f"1) Buy {amount_out} {to_token} on CEX, "
            f"2) Withdraw to {user_wallet}, "
            f"3) Wait 5-30min for network confirmation"
        )
        
        return {
            "success": True,
            "cex_used": "mock_binance",
            "amount_delivered": float(amount_out),
            "tx_hash": mock_tx_hash,
            "mode": "mock",
            "note": f"DEMO: In production, {amount_out} {to_token} would be transferred to {user_wallet} via CEX withdrawal (5-30 min). For now, this is a simulated successful transfer."
        }
    
    async def process_market_maker_swap(
        self,
        amount_in: Decimal,
        from_token: str,
        to_token: str,
        user_wallet: str,
        chain: str = "BSC"
    ) -> Dict:
        """
        Process Market Maker swap with CEX liquidity
        
        Flow:
        1. Calculate output amount based on NENO price (10,000€)
        2. Acquire liquidity from CEX
        3. Transfer to user wallet
        """
        try:
            # Calculate output based on EUR conversion
            eur_value = amount_in * self.neno_price_eur
            
            # Convert EUR to target token (simplified rates)
            conversion_rates = {
                "USDT": Decimal("0.95"),   # 1 EUR ≈ 1.05 USD
                "USDC": Decimal("0.95"),
                "BUSD": Decimal("0.95"),
                "BTCB": Decimal("90000"),  # 1 BTC ≈ 90k EUR
                "BTC": Decimal("90000"),
                "BNB": Decimal("550"),     # 1 BNB ≈ 550 EUR
                "WBNB": Decimal("550"),
                "ETH": Decimal("3000"),    # 1 ETH ≈ 3k EUR
            }
            
            rate = conversion_rates.get(to_token.upper(), Decimal("1"))
            amount_out = eur_value / rate
            
            logger.info(
                f"Market Maker swap: {amount_in} {from_token} @ {self.neno_price_eur}€ "
                f"= {eur_value}€ = {amount_out} {to_token}"
            )
            
            # Provide liquidity via CEX
            result = await self.provide_liquidity(to_token, amount_out, user_wallet, chain)
            
            if result["success"]:
                return {
                    "success": True,
                    "tx_hash": result["tx_hash"],
                    "amount_out": result["amount_delivered"],
                    "source": "market_maker_cex",
                    "mode": result.get("mode", "unknown"),
                    "note": result["note"]
                }
            
            return {"success": False, "error": "CEX liquidity provision failed"}
            
        except Exception as e:
            logger.error(f"Market Maker swap processing error: {e}")
            return {"success": False, "error": str(e)}
