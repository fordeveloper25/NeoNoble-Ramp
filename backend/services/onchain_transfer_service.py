"""
Real On-Chain Token Transfer Service
Handles actual token transfers from hot wallet to user wallets
"""
import os
import logging
from decimal import Decimal
from typing import Dict, Optional
import asyncio

logger = logging.getLogger(__name__)

# Try to import Web3
try:
    from web3 import Web3
    from web3.middleware import geth_poa_middleware
    WEB3_AVAILABLE = True
except ImportError:
    WEB3_AVAILABLE = False
    logger.warning("Web3.py not installed. Real transfers disabled.")


class OnChainTransferService:
    """
    Handles real on-chain token transfers for Market Maker swaps
    """
    
    def __init__(self):
        self.enabled = False
        self.w3 = None
        self.hot_wallet_address = None
        self.hot_wallet_private_key = None
        
        if WEB3_AVAILABLE:
            self.initialize_web3()
    
    def initialize_web3(self):
        """Initialize Web3 connection to BSC"""
        try:
            rpc_url = os.getenv('BSC_RPC_URL', 'https://bsc-dataseed.binance.org/')
            self.w3 = Web3(Web3.HTTPProvider(rpc_url))
            self.w3.middleware_onion.inject(geth_poa_middleware, layer=0)
            
            # Check connection
            if not self.w3.is_connected():
                logger.error("Failed to connect to BSC RPC")
                return
            
            # Load hot wallet credentials
            self.hot_wallet_private_key = os.getenv('HOT_WALLET_PRIVATE_KEY')
            
            if self.hot_wallet_private_key:
                # Derive address from private key
                account = self.w3.eth.account.from_key(self.hot_wallet_private_key)
                self.hot_wallet_address = account.address
                self.enabled = True
                
                balance = self.w3.eth.get_balance(self.hot_wallet_address)
                balance_bnb = self.w3.from_wei(balance, 'ether')
                
                logger.info(f"✅ On-Chain Transfer Service initialized")
                logger.info(f"📍 Hot Wallet: {self.hot_wallet_address}")
                logger.info(f"💰 Balance: {balance_bnb} BNB")
            else:
                logger.warning("HOT_WALLET_PRIVATE_KEY not set. Real transfers disabled.")
                
        except Exception as e:
            logger.error(f"Failed to initialize Web3: {e}")
            self.enabled = False
    
    async def transfer_tokens(
        self,
        token_symbol: str,
        amount: Decimal,
        to_address: str,
        token_address: Optional[str] = None
    ) -> Dict:
        """
        Transfer tokens from hot wallet to user
        
        Args:
            token_symbol: Symbol of token (USDT, BNB, etc)
            amount: Amount to transfer
            to_address: Recipient address
            token_address: Contract address (for ERC20)
        
        Returns:
            Dict with success status and tx_hash
        """
        if not self.enabled:
            return await self._transfer_mock(token_symbol, amount, to_address)
        
        try:
            # BSC Token addresses (BEP-20)
            token_contracts = {
                'USDT': '0x55d398326f99059fF775485246999027B3197955',
                'USDC': '0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d',
                'BUSD': '0xe9e7CEA3DedcA5984780Bafc599bD69ADd087D56',
                'BTCB': '0x7130d2A12B9BCbFAe4f2634d864A1Ee1Ce3Ead9c',
                'ETH': '0x2170Ed0880ac9A755fd29B2688956BD959F933F8',
                'WBNB': '0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c',
            }
            
            if token_symbol == 'BNB':
                # Native BNB transfer
                return await self._transfer_bnb(amount, to_address)
            
            # ERC-20 token transfer
            contract_address = token_address or token_contracts.get(token_symbol.upper())
            
            if not contract_address:
                logger.error(f"Unknown token: {token_symbol}")
                return await self._transfer_mock(token_symbol, amount, to_address)
            
            return await self._transfer_erc20(
                contract_address,
                token_symbol,
                amount,
                to_address
            )
            
        except Exception as e:
            logger.error(f"Transfer failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "mode": "failed"
            }
    
    async def _transfer_bnb(self, amount: Decimal, to_address: str) -> Dict:
        """Transfer native BNB"""
        try:
            # Get nonce
            nonce = self.w3.eth.get_transaction_count(self.hot_wallet_address)
            
            # Build transaction
            tx = {
                'nonce': nonce,
                'to': Web3.to_checksum_address(to_address),
                'value': self.w3.to_wei(float(amount), 'ether'),
                'gas': 21000,
                'gasPrice': self.w3.eth.gas_price,
                'chainId': 56  # BSC Mainnet
            }
            
            # Sign transaction
            signed_tx = self.w3.eth.account.sign_transaction(tx, self.hot_wallet_private_key)
            
            # Send transaction
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            tx_hash_hex = self.w3.to_hex(tx_hash)
            
            logger.info(f"✅ BNB transfer sent: {amount} BNB → {to_address}")
            logger.info(f"📝 TX: https://bscscan.com/tx/{tx_hash_hex}")
            
            return {
                "success": True,
                "tx_hash": tx_hash_hex,
                "amount_delivered": float(amount),
                "mode": "real",
                "note": f"Transferred {amount} BNB to {to_address}. Check BscScan for confirmation."
            }
            
        except Exception as e:
            logger.error(f"BNB transfer error: {e}")
            raise
    
    async def _transfer_erc20(
        self,
        contract_address: str,
        token_symbol: str,
        amount: Decimal,
        to_address: str
    ) -> Dict:
        """Transfer ERC-20 token"""
        try:
            # ERC-20 ABI (transfer function only)
            erc20_abi = [
                {
                    "constant": False,
                    "inputs": [
                        {"name": "_to", "type": "address"},
                        {"name": "_value", "type": "uint256"}
                    ],
                    "name": "transfer",
                    "outputs": [{"name": "", "type": "bool"}],
                    "type": "function"
                },
                {
                    "constant": True,
                    "inputs": [],
                    "name": "decimals",
                    "outputs": [{"name": "", "type": "uint8"}],
                    "type": "function"
                }
            ]
            
            # Create contract instance
            contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(contract_address),
                abi=erc20_abi
            )
            
            # Get token decimals
            decimals = contract.functions.decimals().call()
            
            # Convert amount to token units
            amount_units = int(float(amount) * (10 ** decimals))
            
            # Get nonce
            nonce = self.w3.eth.get_transaction_count(self.hot_wallet_address)
            
            # Build transaction
            tx = contract.functions.transfer(
                Web3.to_checksum_address(to_address),
                amount_units
            ).build_transaction({
                'chainId': 56,
                'gas': 100000,
                'gasPrice': self.w3.eth.gas_price,
                'nonce': nonce,
            })
            
            # Sign transaction
            signed_tx = self.w3.eth.account.sign_transaction(tx, self.hot_wallet_private_key)
            
            # Send transaction
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            tx_hash_hex = self.w3.to_hex(tx_hash)
            
            logger.info(f"✅ {token_symbol} transfer sent: {amount} → {to_address}")
            logger.info(f"📝 TX: https://bscscan.com/tx/{tx_hash_hex}")
            
            return {
                "success": True,
                "tx_hash": tx_hash_hex,
                "amount_delivered": float(amount),
                "mode": "real",
                "note": f"Transferred {amount} {token_symbol} to {to_address}. Confirm on BscScan (1-2 min)."
            }
            
        except Exception as e:
            logger.error(f"{token_symbol} transfer error: {e}")
            raise
    
    async def _transfer_mock(self, token_symbol: str, amount: Decimal, to_address: str) -> Dict:
        """Mock transfer for demo/testing"""
        await asyncio.sleep(0.5)
        
        mock_tx_hash = f"0x{'mock' * 16}"
        
        logger.info(f"🔄 MOCK: Would transfer {amount} {token_symbol} to {to_address}")
        
        return {
            "success": True,
            "tx_hash": mock_tx_hash,
            "amount_delivered": float(amount),
            "mode": "mock",
            "note": f"DEMO MODE: In production, {amount} {token_symbol} would be transferred to {to_address}. Enable real transfers by setting HOT_WALLET_PRIVATE_KEY environment variable."
        }
    
    def get_status(self) -> Dict:
        """Get service status"""
        return {
            "enabled": self.enabled,
            "hot_wallet": self.hot_wallet_address if self.enabled else None,
            "web3_available": WEB3_AVAILABLE,
            "connected": self.w3.is_connected() if self.w3 else False
        }
