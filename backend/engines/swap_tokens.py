"""
Token registry for NeoNoble Swap Engine (BSC Mainnet).

Each token has:
- symbol: uppercase ticker used in the UI and API
- address: BSC mainnet contract address (checksum)
- decimals: ERC-20 decimals
- name: human readable name
- logo: emoji or URL (used by the frontend)
"""

from typing import Dict, Optional
from web3 import Web3


def _cs(addr: str) -> str:
    """Return checksum address."""
    return Web3.to_checksum_address(addr)


# BSC Mainnet token list
BSC_TOKENS: Dict[str, dict] = {
    "NENO": {
        "symbol": "NENO",
        "address": _cs("0xeF3F5C1892A8d7A3304E4A15959E124402d69974"),
        "decimals": 18,
        "name": "NeoNoble Token",
        "logo": "🟣",
    },
    "USDT": {
        "symbol": "USDT",
        "address": _cs("0x55d398326f99059fF775485246999027B3197955"),
        "decimals": 18,  # BEP-20 USDT on BSC is 18 decimals (unusual but true)
        "name": "Tether USD (BEP-20)",
        "logo": "💵",
    },
    "BTCB": {
        "symbol": "BTCB",
        "address": _cs("0x7130d2A12B9BCbFAe4f2634d864A1Ee1Ce3Ead9c"),
        "decimals": 18,
        "name": "Bitcoin BEP-20",
        "logo": "🟠",
    },
    "BUSD": {
        "symbol": "BUSD",
        "address": _cs("0xe9e7CEA3DedcA5984780Bafc599bD69ADd087D56"),
        "decimals": 18,
        "name": "Binance USD",
        "logo": "💲",
    },
    "WBNB": {
        "symbol": "WBNB",
        "address": _cs("0xbb4CdB9CBd36B01bD1c0A0C9b3F4F6F2F5A1F5A1"),
        "decimals": 18,
        "name": "Wrapped BNB",
        "logo": "🟡",
    },
    "USDC": {
        "symbol": "USDC",
        "address": _cs("0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d"),
        "decimals": 18,
        "name": "USD Coin (BEP-20)",
        "logo": "🔵",
    },
    "CAKE": {
        "symbol": "CAKE",
        "address": _cs("0x0E09FaBB73Bd3Ade0a17ECC321fD13a19e81cE82"),
        "decimals": 18,
        "name": "PancakeSwap Token",
        "logo": "🥞",
    },
    "ETH": {
        "symbol": "ETH",
        "address": _cs("0x2170Ed0880ac9A755fd29B2688956BD959F933F8"),
        "decimals": 18,
        "name": "Ethereum (BEP-20)",
        "logo": "🔷",
    },
}


def resolve_token(symbol_or_address: str) -> Optional[dict]:
    """
    Resolve a token by symbol (NENO, USDT, etc.) or by contract address.
    Returns the token dict or None.
    """
    if not symbol_or_address:
        return None

    s = symbol_or_address.strip()

    # Try symbol lookup (case-insensitive)
    if s.upper() in BSC_TOKENS:
        return BSC_TOKENS[s.upper()]

    # Try address lookup
    if s.startswith("0x") and len(s) == 42:
        try:
            checksum = _cs(s)
            for t in BSC_TOKENS.values():
                if t["address"] == checksum:
                    return t
            # Unknown token but valid address — return a minimal dict.
            # The engine will try to fetch decimals on-chain.
            return {
                "symbol": checksum[:6].upper(),
                "address": checksum,
                "decimals": None,  # to be discovered
                "name": "Custom token",
                "logo": "🪙",
                "custom": True,
            }
        except Exception:
            return None

    return None


def list_tokens() -> list:
    """Return the token registry as a list (for the UI dropdown)."""
    return list(BSC_TOKENS.values())
