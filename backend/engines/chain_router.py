"""
Multi-Chain Router for NeoNoble Ramp Hybrid Swap Engine
Handles routing and DEX discovery across multiple blockchains
"""
import os
from typing import Dict, List, Optional
from web3 import Web3
import logging

logger = logging.getLogger(__name__)


class ChainRouter:
    """
    Multi-chain routing for swaps across BSC, Ethereum, Polygon, Arbitrum, Base
    """
    
    # Chain IDs
    BSC_CHAIN_ID = 56
    ETHEREUM_CHAIN_ID = 1
    POLYGON_CHAIN_ID = 137
    ARBITRUM_CHAIN_ID = 42161
    BASE_CHAIN_ID = 8453
    
    # DEX Routers per chain
    DEX_ROUTERS = {
        56: {  # BSC
            "pancakeswap_v2": "0x10ED43C718714eb63d5aA57B78B54704E256024E",
            "biswap": "0x3a6d8cA21D1CF76F653A67577FA0D27453350dD8",
            "apeswap": "0xcF0feBd3f17CEf5b47b0cD257aCf6025c5BFf3b7",
            "mdex": "0x7DAe51BD3E3376B8c7c4900E9107f12Be3AF1bA8",
        },
        1: {  # Ethereum
            "uniswap_v2": "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D",
            "uniswap_v3": "0xE592427A0AEce92De3Edee1F18E0157C05861564",
            "sushiswap": "0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F",
        },
        137: {  # Polygon
            "quickswap": "0xa5E0829CaCEd8fFDD4De3c43696c57F7D7A678ff",
            "sushiswap": "0x1b02dA8Cb0d097eB8D57A175b88c7D8b47997506",
        },
        42161: {  # Arbitrum
            "uniswap_v3": "0xE592427A0AEce92De3Edee1F18E0157C05861564",
            "sushiswap": "0x1b02dA8Cb0d097eB8D57A175b88c7D8b47997506",
            "camelot": "0xc873fEcbd354f5A56E00E710B90EF4201db2448d",
        },
        8453: {  # Base
            "uniswap": "0x4752ba5DBc23f44D87826276BF6Fd6b1C372aD24",
            "aerodrome": "0xcF77a3Ba9A5CA399B7c97c74d54e5b1Beb874E43",
        }
    }
    
    def __init__(self):
        self.rpcs = {
            self.BSC_CHAIN_ID: os.getenv("BSC_RPC_URL", "https://bsc-dataseed1.binance.org"),
            self.ETHEREUM_CHAIN_ID: os.getenv("ETHEREUM_RPC_URL", ""),
            self.POLYGON_CHAIN_ID: os.getenv("POLYGON_RPC_URL", ""),
            self.ARBITRUM_CHAIN_ID: os.getenv("ARBITRUM_RPC_URL", ""),
            self.BASE_CHAIN_ID: os.getenv("BASE_RPC_URL", ""),
        }
        
        # Initialize Web3 instances
        self.web3_instances = {}
        for chain_id, rpc in self.rpcs.items():
            if rpc:
                try:
                    self.web3_instances[chain_id] = Web3(Web3.HTTPProvider(rpc))
                    logger.info(f"ChainRouter: Initialized chain {chain_id}")
                except Exception as e:
                    logger.error(f"ChainRouter: Failed to initialize chain {chain_id}: {e}")
    
    def get_chain_name(self, chain_id: int) -> str:
        """Get human-readable chain name"""
        names = {
            56: "BSC",
            1: "Ethereum",
            137: "Polygon",
            42161: "Arbitrum",
            8453: "Base"
        }
        return names.get(chain_id, f"Chain{chain_id}")
    
    def is_chain_supported(self, chain_id: int) -> bool:
        """Check if chain is supported"""
        return chain_id in self.web3_instances
    
    def get_web3(self, chain_id: int) -> Optional[Web3]:
        """Get Web3 instance for chain"""
        return self.web3_instances.get(chain_id)
    
    def get_dex_routers(self, chain_id: int) -> Dict[str, str]:
        """Get available DEX routers for chain"""
        return self.DEX_ROUTERS.get(chain_id, {})
    
    def get_native_token(self, chain_id: int) -> str:
        """Get native token symbol for chain"""
        native_tokens = {
            56: "BNB",
            1: "ETH",
            137: "MATIC",
            42161: "ETH",
            8453: "ETH"
        }
        return native_tokens.get(chain_id, "ETH")
    
    def get_wrapped_native(self, chain_id: int) -> str:
        """Get wrapped native token address for chain"""
        wrapped_addresses = {
            56: "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c",  # WBNB
            1: "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",   # WETH
            137: "0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270", # WMATIC
            42161: "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1", # WETH (Arbitrum)
            8453: "0x4200000000000000000000000000000000000006"  # WETH (Base)
        }
        return wrapped_addresses.get(chain_id, "")
    
    def supports_1inch(self, chain_id: int) -> bool:
        """Check if 1inch supports this chain"""
        # 1inch supports: Ethereum, BSC, Polygon, Arbitrum, Optimism, Avalanche, Gnosis, Fantom, Klaytn, Aurora, ZkSync
        supported_chains = [1, 56, 137, 42161]
        return chain_id in supported_chains
    
    async def estimate_gas(self, chain_id: int, tx_data: Dict) -> Optional[int]:
        """Estimate gas for a transaction on specific chain"""
        try:
            web3 = self.get_web3(chain_id)
            if not web3:
                return None
            
            gas_estimate = web3.eth.estimate_gas(tx_data)
            return gas_estimate
            
        except Exception as e:
            logger.error(f"ChainRouter.estimate_gas error on chain {chain_id}: {e}")
            return None
    
    def get_explorer_url(self, chain_id: int) -> str:
        """Get block explorer URL for chain"""
        explorers = {
            56: "https://bscscan.com",
            1: "https://etherscan.io",
            137: "https://polygonscan.com",
            42161: "https://arbiscan.io",
            8453: "https://basescan.org"
        }
        return explorers.get(chain_id, "")
    
    def format_explorer_tx_url(self, chain_id: int, tx_hash: str) -> str:
        """Format transaction URL for explorer"""
        base_url = self.get_explorer_url(chain_id)
        return f"{base_url}/tx/{tx_hash}" if base_url else ""


# Global instance
chain_router = ChainRouter()
