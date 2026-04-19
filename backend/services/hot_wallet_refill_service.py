"""
Hot Wallet Auto-Refill Service
Automatically refills hot wallet from CEX when balance is low
"""
import os
import logging
from decimal import Decimal
from typing import Dict, Optional
import asyncio

logger = logging.getLogger(__name__)

try:
    import ccxt
    CCXT_AVAILABLE = True
except ImportError:
    CCXT_AVAILABLE = False
    logger.warning("ccxt not installed")


class HotWalletRefillService:
    """
    Monitors hot wallet balance and automatically refills from CEX
    """
    
    def __init__(self):
        self.enabled = False
        self.hot_wallet_address = os.getenv('HOT_WALLET_ADDRESS')
        self.refill_threshold = {}  # token -> threshold
        self.refill_amount = {}  # token -> amount
        
        # Default thresholds
        self.refill_threshold = {
            'USDT': Decimal('500'),  # Refill when < 500 USDT
            'USDC': Decimal('500'),
            'BNB': Decimal('0.05'),
        }
        
        self.refill_amount = {
            'USDT': Decimal('2000'),  # Refill with 2000 USDT
            'USDC': Decimal('2000'),
            'BNB': Decimal('0.2'),
        }
        
        if CCXT_AVAILABLE:
            self.initialize_cex()
    
    def initialize_cex(self):
        """Initialize CEX connections"""
        self.exchanges = {}
        
        # Binance
        binance_key = os.getenv('BINANCE_API_KEY')
        binance_secret = os.getenv('BINANCE_API_SECRET')
        
        if binance_key and binance_secret:
            try:
                self.exchanges['binance'] = ccxt.binance({
                    'apiKey': binance_key,
                    'secret': binance_secret,
                    'enableRateLimit': True,
                })
                logger.info("✅ Binance connected for hot wallet refill")
                self.enabled = True
            except Exception as e:
                logger.error(f"Binance connection failed: {e}")
        
        # MEXC
        mexc_key = os.getenv('MEXC_API_KEY')
        mexc_secret = os.getenv('MEXC_API_SECRET')
        
        if mexc_key and mexc_secret:
            try:
                self.exchanges['mexc'] = ccxt.mexc({
                    'apiKey': mexc_key,
                    'secret': mexc_secret,
                    'enableRateLimit': True,
                })
                logger.info("✅ MEXC connected for hot wallet refill")
                self.enabled = True
            except Exception as e:
                logger.error(f"MEXC connection failed: {e}")
        
        if not self.enabled:
            logger.warning("⚠️  Hot Wallet Auto-Refill disabled (no CEX API keys)")
    
    async def check_and_refill(self, token: str, current_balance: Decimal) -> Dict:
        """
        Check if refill is needed and execute
        
        Args:
            token: Token symbol (USDT, BNB, etc)
            current_balance: Current hot wallet balance
            
        Returns:
            Dict with refill status
        """
        if not self.enabled:
            return {
                "needed": False,
                "reason": "Auto-refill not configured"
            }
        
        threshold = self.refill_threshold.get(token, Decimal('0'))
        
        if current_balance >= threshold:
            return {
                "needed": False,
                "current_balance": float(current_balance),
                "threshold": float(threshold)
            }
        
        # Balance is low, trigger refill
        logger.warning(f"🔄 Hot wallet {token} balance low: {current_balance} < {threshold}")
        
        refill_result = await self.execute_refill(token)
        
        return {
            "needed": True,
            "current_balance": float(current_balance),
            "threshold": float(threshold),
            "refill": refill_result
        }
    
    async def execute_refill(self, token: str) -> Dict:
        """
        Execute refill from CEX to hot wallet
        
        Strategy:
        1. Try Binance first
        2. Fallback to MEXC
        3. Return status
        """
        if not self.hot_wallet_address:
            return {
                "success": False,
                "error": "HOT_WALLET_ADDRESS not configured"
            }
        
        refill_amount = self.refill_amount.get(token, Decimal('1000'))
        
        # Try each exchange
        for exchange_name, exchange in self.exchanges.items():
            try:
                logger.info(f"Attempting refill from {exchange_name}: {refill_amount} {token}")
                
                # Check exchange balance
                balance = exchange.fetch_balance()
                available = balance.get(token, {}).get('free', 0)
                
                if available < float(refill_amount):
                    logger.warning(f"{exchange_name} insufficient balance: {available} {token}")
                    continue
                
                # Network mapping
                network_map = {
                    'USDT': 'BSC',  # BEP20
                    'USDC': 'BSC',
                    'BNB': 'BSC',
                    'BTCB': 'BSC',
                }
                
                network = network_map.get(token, 'BSC')
                
                # Execute withdrawal
                withdrawal = exchange.withdraw(
                    code=token,
                    amount=float(refill_amount),
                    address=self.hot_wallet_address,
                    params={'network': network}
                )
                
                logger.info(f"✅ Refill initiated from {exchange_name}")
                logger.info(f"📝 Withdrawal ID: {withdrawal.get('id')}")
                logger.info(f"💰 Amount: {refill_amount} {token}")
                logger.info(f"⏱️  ETA: 5-30 minutes")
                
                return {
                    "success": True,
                    "exchange": exchange_name,
                    "amount": float(refill_amount),
                    "token": token,
                    "withdrawal_id": withdrawal.get('id'),
                    "status": withdrawal.get('status'),
                    "note": f"Refill initiated. Hot wallet will receive {refill_amount} {token} in 5-30 min."
                }
                
            except Exception as e:
                logger.error(f"{exchange_name} refill failed: {e}")
                continue
        
        # All exchanges failed
        return {
            "success": False,
            "error": "All CEX refill attempts failed",
            "note": "Check CEX API keys, balances, and withdrawal permissions"
        }
    
    async def get_cex_balances(self) -> Dict:
        """Get current balances on all connected CEXs"""
        balances = {}
        
        for exchange_name, exchange in self.exchanges.items():
            try:
                balance = exchange.fetch_balance()
                balances[exchange_name] = {
                    'USDT': balance.get('USDT', {}).get('free', 0),
                    'USDC': balance.get('USDC', {}).get('free', 0),
                    'BNB': balance.get('BNB', {}).get('free', 0),
                }
            except Exception as e:
                logger.error(f"Failed to fetch {exchange_name} balance: {e}")
                balances[exchange_name] = {"error": str(e)}
        
        return balances
    
    def get_status(self) -> Dict:
        """Get service status"""
        return {
            "enabled": self.enabled,
            "hot_wallet": self.hot_wallet_address,
            "exchanges_connected": list(self.exchanges.keys()),
            "refill_thresholds": {k: float(v) for k, v in self.refill_threshold.items()},
            "refill_amounts": {k: float(v) for k, v in self.refill_amount.items()},
        }
