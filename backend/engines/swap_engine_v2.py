"""
NeoNoble On-Chain Swap Engine — USER-SIGNED VERSION (BSC Mainnet)

Architecture
------------

This engine does NOT execute swaps on behalf of the user.  It provides:

    * quote:   best-price estimate (1inch → PancakeSwap fallback)
    * build:   unsigned transaction calldata for the user to sign in MetaMask
    * approve: ERC-20 approve calldata for the same router spender
    * track:   verify a user-submitted tx hash and record it to the ledger

The user's own wallet holds the input token AND pays the gas.  This means
the backend never needs a private key for swap execution, and the platform
has no exposure to hot-wallet token reserves.

(A legacy "hot-wallet" execution mode is still available through the old
 SwapEngine implementation, but is disabled by default.  See swap_routes.py.)
"""

from __future__ import annotations

import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

import aiohttp
from pydantic import BaseModel
from web3 import Web3
from web3.exceptions import ContractLogicError

from engines.swap_tokens import BSC_TOKENS, resolve_token

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CHAIN_ID_BSC = 56
PANCAKE_V2_ROUTER = Web3.to_checksum_address(
    "0x10ED43C718714eb63d5aA57B78B54704E256024E"
)
ONEINCH_API_V6 = "https://api.1inch.dev/swap/v6.0/56"  # BSC
BSC_EXPLORER_TX = "https://bscscan.com/tx/"

# Minimal ERC-20 + Router ABIs
ERC20_ABI = [
    {"constant": True, "inputs": [], "name": "decimals",
     "outputs": [{"name": "", "type": "uint8"}],
     "stateMutability": "view", "type": "function"},
    {"constant": True, "inputs": [{"name": "owner", "type": "address"},
                                   {"name": "spender", "type": "address"}],
     "name": "allowance",
     "outputs": [{"name": "", "type": "uint256"}],
     "stateMutability": "view", "type": "function"},
    {"constant": True, "inputs": [{"name": "who", "type": "address"}],
     "name": "balanceOf",
     "outputs": [{"name": "", "type": "uint256"}],
     "stateMutability": "view", "type": "function"},
]

PANCAKE_ROUTER_ABI = [
    {"inputs": [{"name": "amountIn", "type": "uint256"},
                {"name": "path", "type": "address[]"}],
     "name": "getAmountsOut",
     "outputs": [{"name": "amounts", "type": "uint256[]"}],
     "stateMutability": "view", "type": "function"},
]

# ERC20 approve(address,uint256) selector + ABI-encoded args
APPROVE_SELECTOR = "0x095ea7b3"
MAX_UINT256 = (1 << 256) - 1


def _encode_approve(spender: str, amount: int) -> str:
    """Return the calldata hex string for ERC20.approve(spender, amount)."""
    spender_hex = spender.lower().replace("0x", "").rjust(64, "0")
    amount_hex = hex(amount)[2:].rjust(64, "0")
    return APPROVE_SELECTOR + spender_hex + amount_hex


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class QuoteResult(BaseModel):
    from_token: str
    to_token: str
    amount_in: float
    estimated_amount_out: float
    rate: float
    source: str                 # '1inch' | 'pancakeswap' | 'estimate'
    note: Optional[str] = None


class BuildResult(BaseModel):
    swap_id: str
    source: str                 # '1inch' | 'pancakeswap'
    to: str
    data: str
    value: str                  # hex-encoded wei
    gas: Optional[str] = None
    gas_price: Optional[str] = None
    estimated_amount_out: str   # wei string
    estimated_amount_out_human: float
    chain_id: int = CHAIN_ID_BSC
    spender: Optional[str] = None
    needs_approve: bool = False
    approve_calldata: Optional[Dict[str, str]] = None
    from_token: str
    to_token: str
    amount_in: str              # wei string
    amount_in_human: float
    user_wallet: str
    slippage_pct: float


class TrackResult(BaseModel):
    swap_id: str
    tx_hash: str
    status: str                 # 'pending' | 'success' | 'failed'
    block_number: Optional[int] = None
    gas_used: Optional[int] = None
    explorer_url: str


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------


class SwapEngineV2:
    """
    Stateless helper that orchestrates 1inch & PancakeSwap calls and exposes a
    clean interface for the REST layer.
    """

    def __init__(self):
        self.rpc_url = os.environ.get(
            "BSC_RPC_URL", "https://bsc-dataseed1.binance.org"
        )
        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url, request_kwargs={"timeout": 30}))
        self.oneinch_key = os.environ.get("ONEINCH_API_KEY", "").strip()
        self.default_slippage = float(
            os.environ.get("SWAP_DEFAULT_SLIPPAGE_PCT", "0.8")
        )
        self.max_slippage = float(os.environ.get("SWAP_MAX_SLIPPAGE_PCT", "5.0"))
        self.max_neno_per_tx = Decimal(os.environ.get("SWAP_MAX_NENO_PER_TX", "5000"))
        self.db = None

        logger.info(
            "SwapEngineV2 | rpc=%s connected=%s 1inch=%s",
            self.rpc_url, self._rpc_connected(), bool(self.oneinch_key),
        )

    def set_db(self, db):
        self.db = db

    # ---------- helpers ---------------------------------------------------

    def _rpc_connected(self) -> bool:
        try:
            return self.w3.is_connected()
        except Exception:
            return False

    def _resolve_or_raise(self, sym_or_addr: str) -> dict:
        tok = resolve_token(sym_or_addr)
        if not tok:
            raise ValueError(f"Unsupported token: {sym_or_addr}")
        if tok.get("decimals") is None:
            tok["decimals"] = self._read_decimals(tok["address"])
        return tok

    def _read_decimals(self, addr: str) -> int:
        try:
            c = self.w3.eth.contract(
                address=Web3.to_checksum_address(addr), abi=ERC20_ABI
            )
            return c.functions.decimals().call()
        except Exception:
            return 18

    def _read_allowance(self, token: str, owner: str, spender: str) -> int:
        try:
            c = self.w3.eth.contract(
                address=Web3.to_checksum_address(token), abi=ERC20_ABI
            )
            return c.functions.allowance(
                Web3.to_checksum_address(owner),
                Web3.to_checksum_address(spender),
            ).call()
        except Exception:
            return 0

    # ---------- 1inch HTTP ------------------------------------------------

    async def _oneinch_get(
        self, path: str, params: dict
    ) -> Optional[dict]:
        if not self.oneinch_key:
            return None
        headers = {
            "Authorization": f"Bearer {self.oneinch_key}",
            "Accept": "application/json",
        }
        url = f"{ONEINCH_API_V6}{path}"
        timeout = aiohttp.ClientTimeout(total=25)
        try:
            async with aiohttp.ClientSession(timeout=timeout) as s:
                async with s.get(url, headers=headers, params=params) as r:
                    txt = await r.text()
                    if r.status != 200:
                        logger.info("1inch %s → %s: %s", path, r.status, txt[:200])
                        return None
                    try:
                        return json.loads(txt)
                    except Exception:
                        return None
        except Exception as e:
            logger.info("1inch net error: %s", e)
            return None

    async def _oneinch_spender(self) -> Optional[str]:
        resp = await self._oneinch_get("/approve/spender", {})
        if resp and "address" in resp:
            return Web3.to_checksum_address(resp["address"])
        return None

    # ---------- quote -----------------------------------------------------

    async def get_quote(
        self, from_token: str, to_token: str, amount_in: Decimal
    ) -> QuoteResult:
        f = self._resolve_or_raise(from_token)
        t = self._resolve_or_raise(to_token)

        amount_wei = int(Decimal(amount_in) * Decimal(10 ** f["decimals"]))

        # Try 1inch
        q = await self._oneinch_get(
            "/quote", {"src": f["address"], "dst": t["address"], "amount": str(amount_wei)}
        )
        if q:
            out_wei = int(q.get("dstAmount") or q.get("toTokenAmount") or 0)
            if out_wei > 0:
                out = Decimal(out_wei) / Decimal(10 ** t["decimals"])
                return QuoteResult(
                    from_token=f["symbol"], to_token=t["symbol"],
                    amount_in=float(amount_in),
                    estimated_amount_out=float(out),
                    rate=float(out / Decimal(amount_in)) if Decimal(amount_in) > 0 else 0,
                    source="1inch",
                )

        # Fallback: PancakeSwap
        try:
            router = self.w3.eth.contract(
                address=PANCAKE_V2_ROUTER, abi=PANCAKE_ROUTER_ABI
            )
            wbnb = BSC_TOKENS["WBNB"]["address"]
            for path in (
                [f["address"], t["address"]],
                [f["address"], wbnb, t["address"]],
            ):
                try:
                    amts = router.functions.getAmountsOut(amount_wei, path).call()
                    if int(amts[-1]) > 0:
                        out_wei = int(amts[-1])
                        out = Decimal(out_wei) / Decimal(10 ** t["decimals"])
                        return QuoteResult(
                            from_token=f["symbol"], to_token=t["symbol"],
                            amount_in=float(amount_in),
                            estimated_amount_out=float(out),
                            rate=float(out / Decimal(amount_in)) if Decimal(amount_in) > 0 else 0,
                            source="pancakeswap",
                        )
                except (ContractLogicError, Exception):
                    continue
        except Exception as e:
            logger.info("pancake quote error: %s", e)

        # No liquidity found
        return QuoteResult(
            from_token=f["symbol"], to_token=t["symbol"],
            amount_in=float(amount_in),
            estimated_amount_out=0.0,
            rate=0.0,
            source="estimate",
            note="Nessuna liquidità DEX trovata per questa coppia.",
        )

    # ---------- build (tx calldata for the user to sign) ------------------

    async def build_swap_tx(
        self,
        user_id: str,
        from_token: str,
        to_token: str,
        amount_in: Decimal,
        user_wallet: str,
        slippage: float,
    ) -> BuildResult:
        # Validate inputs
        try:
            user_wallet = Web3.to_checksum_address(user_wallet)
        except Exception:
            raise ValueError("Invalid user_wallet address")

        f = self._resolve_or_raise(from_token)
        t = self._resolve_or_raise(to_token)
        if f["address"].lower() == t["address"].lower():
            raise ValueError("from_token == to_token")
        if f["symbol"] == "NENO" and Decimal(amount_in) > self.max_neno_per_tx:
            raise ValueError(f"Max {self.max_neno_per_tx} NENO per tx")

        slippage = min(max(float(slippage), 0.1), self.max_slippage)
        amount_wei = int(Decimal(amount_in) * Decimal(10 ** f["decimals"]))

        swap_id = str(uuid.uuid4())

        # === Try 1inch first ===
        if self.oneinch_key:
            built = await self._build_via_1inch(
                f, t, amount_wei, user_wallet, slippage, amount_in, swap_id
            )
            if built is not None:
                await self._save_build(built, user_id)
                return built

        # === Fallback PancakeSwap ===
        built = await self._build_via_pancake(
            f, t, amount_wei, user_wallet, slippage, amount_in, swap_id
        )
        if built is not None:
            await self._save_build(built, user_id)
            return built

        raise RuntimeError(
            "No liquidity found on 1inch or PancakeSwap for this pair. "
            "The token may be unlisted or have no routing path."
        )

    async def _build_via_1inch(
        self, f, t, amount_wei, user_wallet, slippage, amount_in, swap_id
    ) -> Optional[BuildResult]:
        spender = await self._oneinch_spender()
        if not spender:
            return None

        swap = await self._oneinch_get(
            "/swap",
            {
                "src": f["address"],
                "dst": t["address"],
                "amount": str(amount_wei),
                "from": user_wallet,
                "slippage": str(slippage),
                "disableEstimate": "true",
                "allowPartialFill": "false",
            },
        )
        if not swap or "tx" not in swap:
            return None

        tx = swap["tx"]
        est_out_wei = int(swap.get("dstAmount") or swap.get("toTokenAmount") or 0)
        est_out = Decimal(est_out_wei) / Decimal(10 ** t["decimals"])

        # Allowance check
        current_allowance = self._read_allowance(f["address"], user_wallet, spender)
        needs_approve = current_allowance < amount_wei
        approve_cd = None
        if needs_approve:
            approve_cd = {
                "to": f["address"],
                "data": _encode_approve(spender, MAX_UINT256),
                "value": "0x0",
            }

        return BuildResult(
            swap_id=swap_id,
            source="1inch",
            to=Web3.to_checksum_address(tx["to"]),
            data=tx.get("data", "0x"),
            value=hex(int(tx.get("value", 0))),
            gas=hex(int(tx["gas"])) if tx.get("gas") else None,
            gas_price=hex(int(tx["gasPrice"])) if tx.get("gasPrice") else None,
            estimated_amount_out=str(est_out_wei),
            estimated_amount_out_human=float(est_out),
            chain_id=CHAIN_ID_BSC,
            spender=spender,
            needs_approve=needs_approve,
            approve_calldata=approve_cd,
            from_token=f["symbol"],
            to_token=t["symbol"],
            amount_in=str(amount_wei),
            amount_in_human=float(amount_in),
            user_wallet=user_wallet,
            slippage_pct=slippage,
        )

    async def _build_via_pancake(
        self, f, t, amount_wei, user_wallet, slippage, amount_in, swap_id
    ) -> Optional[BuildResult]:
        router = self.w3.eth.contract(
            address=PANCAKE_V2_ROUTER, abi=PANCAKE_ROUTER_ABI + [
                {"inputs": [
                    {"name": "amountIn", "type": "uint256"},
                    {"name": "amountOutMin", "type": "uint256"},
                    {"name": "path", "type": "address[]"},
                    {"name": "to", "type": "address"},
                    {"name": "deadline", "type": "uint256"}],
                 "name": "swapExactTokensForTokens",
                 "outputs": [{"name": "amounts", "type": "uint256[]"}],
                 "stateMutability": "nonpayable", "type": "function"},
            ]
        )
        wbnb = BSC_TOKENS["WBNB"]["address"]
        chosen_path = None
        est_out_wei = 0
        for path in (
            [f["address"], t["address"]],
            [f["address"], wbnb, t["address"]],
        ):
            try:
                amts = router.functions.getAmountsOut(amount_wei, path).call()
                if int(amts[-1]) > 0:
                    chosen_path = path
                    est_out_wei = int(amts[-1])
                    break
            except Exception:
                continue

        if not chosen_path or est_out_wei <= 0:
            return None

        min_out = int(
            Decimal(est_out_wei) * (Decimal(1) - Decimal(slippage) / Decimal(100))
        )
        deadline = int(time.time()) + 1200

        # Build calldata without sending
        tx = router.functions.swapExactTokensForTokens(
            amount_wei, min_out, chosen_path, user_wallet, deadline
        ).build_transaction(
            {
                "from": user_wallet,
                "chainId": CHAIN_ID_BSC,
                "gas": 500_000,
                "gasPrice": self.w3.eth.gas_price,
                "nonce": 0,  # client replaces it
                "value": 0,
            }
        )

        est_out = Decimal(est_out_wei) / Decimal(10 ** t["decimals"])
        current_allowance = self._read_allowance(
            f["address"], user_wallet, PANCAKE_V2_ROUTER
        )
        needs_approve = current_allowance < amount_wei
        approve_cd = None
        if needs_approve:
            approve_cd = {
                "to": f["address"],
                "data": _encode_approve(PANCAKE_V2_ROUTER, MAX_UINT256),
                "value": "0x0",
            }

        return BuildResult(
            swap_id=swap_id,
            source="pancakeswap",
            to=PANCAKE_V2_ROUTER,
            data=tx["data"],
            value=hex(0),
            gas=hex(int(tx.get("gas", 500_000))),
            gas_price=hex(int(tx.get("gasPrice", 5_000_000_000))),
            estimated_amount_out=str(est_out_wei),
            estimated_amount_out_human=float(est_out),
            chain_id=CHAIN_ID_BSC,
            spender=PANCAKE_V2_ROUTER,
            needs_approve=needs_approve,
            approve_calldata=approve_cd,
            from_token=f["symbol"],
            to_token=t["symbol"],
            amount_in=str(amount_wei),
            amount_in_human=float(amount_in),
            user_wallet=user_wallet,
            slippage_pct=slippage,
        )

    # ---------- track -----------------------------------------------------

    async def track_tx(
        self, swap_id: str, tx_hash: str, user_id: str
    ) -> TrackResult:
        if not tx_hash.startswith("0x"):
            tx_hash = "0x" + tx_hash

        status = "pending"
        block_number = None
        gas_used = None

        try:
            receipt = self.w3.eth.get_transaction_receipt(tx_hash)
            if receipt:
                status = "success" if receipt.status == 1 else "failed"
                block_number = receipt.blockNumber
                gas_used = receipt.gasUsed
        except Exception:
            # still pending or unknown
            status = "pending"

        # Persist
        if self.db is not None:
            try:
                await self.db.swaps.update_one(
                    {"swap_id": swap_id},
                    {
                        "$set": {
                            "tx_hash": tx_hash,
                            "status": status,
                            "block_number": block_number,
                            "gas_used": gas_used,
                            "user_id": user_id,
                            "completed_at": datetime.now(timezone.utc).isoformat()
                            if status != "pending" else None,
                            "explorer_url": BSC_EXPLORER_TX + tx_hash,
                        }
                    },
                    upsert=True,
                )
            except Exception as e:
                logger.warning("track persist failed: %s", e)

        return TrackResult(
            swap_id=swap_id,
            tx_hash=tx_hash,
            status=status,
            block_number=block_number,
            gas_used=gas_used,
            explorer_url=BSC_EXPLORER_TX + tx_hash,
        )

    async def _save_build(self, built: BuildResult, user_id: str):
        if self.db is None:
            return
        try:
            await self.db.swaps.insert_one(
                {
                    "swap_id": built.swap_id,
                    "user_id": user_id,
                    "user_wallet": built.user_wallet,
                    "from_token": built.from_token,
                    "to_token": built.to_token,
                    "amount_in": built.amount_in_human,
                    "amount_out_estimate": built.estimated_amount_out_human,
                    "source": built.source,
                    "slippage_pct": built.slippage_pct,
                    "status": "built",
                    "tx_hash": None,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "mode": "user_signed",
                }
            )
        except Exception as e:
            logger.warning("save build failed: %s", e)

    # ---------- history ---------------------------------------------------

    async def get_user_history(self, user_id: str, limit: int = 50) -> List[dict]:
        if self.db is None:
            return []
        cursor = (
            self.db.swaps.find({"user_id": user_id})
            .sort("created_at", -1)
            .limit(limit)
        )
        rows = []
        async for doc in cursor:
            doc.pop("_id", None)
            rows.append(doc)
        return rows

    # ---------- health ----------------------------------------------------

    def health(self) -> dict:
        return {
            "mode": "user_signed",
            "rpc_connected": self._rpc_connected(),
            "rpc_url": self.rpc_url,
            "oneinch_configured": bool(self.oneinch_key),
            "default_slippage_pct": self.default_slippage,
            "max_slippage_pct": self.max_slippage,
            "max_neno_per_tx": float(self.max_neno_per_tx),
            "chain_id": CHAIN_ID_BSC,
            "supported_tokens": [
                {"symbol": v["symbol"], "address": v["address"], "name": v["name"]}
                for v in BSC_TOKENS.values()
            ],
        }
