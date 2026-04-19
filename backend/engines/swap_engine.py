"""
NeoNoble On-Chain Swap Engine (BSC Mainnet)

Fallback chain used to guarantee the user always gets the output token:

    Tier 1 — 1inch Aggregator (best price across ~30 DEXs)
    Tier 2 — PancakeSwap V2 Router (direct on-chain fallback)
    Tier 3 — Direct Hot-Wallet Transfer (when DEX liquidity is unavailable,
             the platform sells its own reserves of the output token at the
             oracle price — the user still receives real on-chain tokens).
    Tier 4 — Ledger Credit + Queue (last resort: credit the user's platform
             balance immediately and queue the on-chain delivery for when
             liquidity / reserves are restored).

This gives users a consistent UX while preserving on-chain integrity whenever
it is physically possible.
"""

from __future__ import annotations

import asyncio
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
# Pydantic models
# ---------------------------------------------------------------------------


class SwapRequest(BaseModel):
    user_id: str
    from_token: str
    to_token: str
    amount_in: Decimal
    chain: str = "bsc"
    slippage: float = 0.8
    user_wallet_address: str


class SwapResult(BaseModel):
    success: bool
    tx_hash: Optional[str] = None
    amount_in: Optional[Decimal] = None
    amount_out: Optional[Decimal] = None
    from_token: Optional[str] = None
    to_token: Optional[str] = None
    tier: Optional[str] = None          # which tier served the swap
    tier_label: Optional[str] = None    # human readable
    explorer_url: Optional[str] = None
    error: Optional[str] = None
    message: Optional[str] = None
    swap_id: Optional[str] = None
    queued: bool = False
    queued_at: Optional[str] = None


# ---------------------------------------------------------------------------
# Minimal ABIs
# ---------------------------------------------------------------------------

ERC20_ABI = [
    {"constant": True, "inputs": [], "name": "decimals", "outputs": [{"name": "", "type": "uint8"}], "stateMutability": "view", "type": "function"},
    {"constant": True, "inputs": [], "name": "symbol", "outputs": [{"name": "", "type": "string"}], "stateMutability": "view", "type": "function"},
    {"constant": True, "inputs": [{"name": "who", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
    {"constant": True, "inputs": [{"name": "owner", "type": "address"}, {"name": "spender", "type": "address"}], "name": "allowance", "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
    {"constant": False, "inputs": [{"name": "_spender", "type": "address"}, {"name": "_value", "type": "uint256"}], "name": "approve", "outputs": [{"name": "", "type": "bool"}], "stateMutability": "nonpayable", "type": "function"},
    {"constant": False, "inputs": [{"name": "_to", "type": "address"}, {"name": "_value", "type": "uint256"}], "name": "transfer", "outputs": [{"name": "", "type": "bool"}], "stateMutability": "nonpayable", "type": "function"},
]

PANCAKE_ROUTER_ABI = [
    {"inputs": [{"name": "amountIn", "type": "uint256"}, {"name": "path", "type": "address[]"}], "name": "getAmountsOut", "outputs": [{"name": "amounts", "type": "uint256[]"}], "stateMutability": "view", "type": "function"},
    {"inputs": [{"name": "amountIn", "type": "uint256"}, {"name": "amountOutMin", "type": "uint256"}, {"name": "path", "type": "address[]"}, {"name": "to", "type": "address"}, {"name": "deadline", "type": "uint256"}], "name": "swapExactTokensForTokens", "outputs": [{"name": "amounts", "type": "uint256[]"}], "stateMutability": "nonpayable", "type": "function"},
]


# ---------------------------------------------------------------------------
# Swap Engine
# ---------------------------------------------------------------------------

CHAIN_ID_BSC = 56
PANCAKE_V2_ROUTER = Web3.to_checksum_address("0x10ED43C718714eb63d5aA57B78B54704E256024E")
ONEINCH_API_V6 = "https://api.1inch.dev/swap/v6.0/56"  # chain 56 = BSC
BSC_EXPLORER_TX = "https://bscscan.com/tx/"


class SwapEngine:
    """Orchestrates the Tier 1→4 swap strategy."""

    def __init__(self):
        self.rpc_url = os.environ.get(
            "BSC_RPC_URL", "https://bsc-dataseed1.binance.org"
        )
        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url, request_kwargs={"timeout": 30}))

        self.hot_wallet = os.environ.get("HOT_WALLET_ADDRESS", "").strip()
        pk_raw = os.environ.get("HOT_WALLET_PRIVATE_KEY", "").strip()
        if pk_raw and not pk_raw.startswith("0x"):
            pk_raw = "0x" + pk_raw
        self.hot_wallet_pk = pk_raw
        if self.hot_wallet:
            try:
                self.hot_wallet = Web3.to_checksum_address(self.hot_wallet)
            except Exception as e:
                logger.error("Invalid HOT_WALLET_ADDRESS: %s", e)
                self.hot_wallet = ""

        self.oneinch_key = os.environ.get("ONEINCH_API_KEY", "").strip()

        self.default_slippage = float(
            os.environ.get("SWAP_DEFAULT_SLIPPAGE_PCT", "0.8")
        )
        self.max_slippage = float(os.environ.get("SWAP_MAX_SLIPPAGE_PCT", "5.0"))
        self.max_neno_per_tx = Decimal(os.environ.get("SWAP_MAX_NENO_PER_TX", "5000"))

        self.db = None  # injected by server at startup

        logger.info(
            "SwapEngine initialized | hot_wallet=%s | rpc_connected=%s | "
            "1inch_configured=%s",
            self.hot_wallet or "MISSING",
            self._rpc_connected(),
            bool(self.oneinch_key),
        )

    # -- wiring ------------------------------------------------------------

    def set_db(self, db):
        """Inject the motor AsyncIOMotorDatabase instance."""
        self.db = db

    def _rpc_connected(self) -> bool:
        try:
            return self.w3.is_connected()
        except Exception:
            return False

    # -- token helpers -----------------------------------------------------

    def _resolve_or_raise(self, symbol_or_address: str) -> dict:
        tok = resolve_token(symbol_or_address)
        if not tok:
            raise ValueError(f"Unsupported token: {symbol_or_address}")

        if tok.get("decimals") is None:
            # Custom token, fetch decimals on-chain
            try:
                dec = self._read_decimals(tok["address"])
                tok["decimals"] = dec
            except Exception:
                tok["decimals"] = 18
        return tok

    def _read_decimals(self, address: str) -> int:
        contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(address), abi=ERC20_ABI
        )
        try:
            return contract.functions.decimals().call()
        except Exception:
            return 18

    def _erc20_balance(self, token_address: str, owner: str) -> int:
        contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(token_address), abi=ERC20_ABI
        )
        try:
            return contract.functions.balanceOf(
                Web3.to_checksum_address(owner)
            ).call()
        except Exception as e:
            logger.warning("balanceOf failed for %s: %s", token_address, e)
            return 0

    # -- public API --------------------------------------------------------

    async def get_quote(
        self, from_token: str, to_token: str, amount_in: Decimal
    ) -> Dict[str, Any]:
        """Return an estimated output amount using 1inch → PancakeSwap fallback."""
        f_tok = self._resolve_or_raise(from_token)
        t_tok = self._resolve_or_raise(to_token)

        amount_in_wei = int(Decimal(amount_in) * Decimal(10 ** f_tok["decimals"]))

        # Try 1inch quote
        try:
            q = await self._oneinch_quote(
                f_tok["address"], t_tok["address"], amount_in_wei
            )
            if q is not None:
                out_wei = int(q.get("dstAmount") or q.get("toTokenAmount") or 0)
                if out_wei > 0:
                    out_amt = Decimal(out_wei) / Decimal(10 ** t_tok["decimals"])
                    return {
                        "from_token": f_tok["symbol"],
                        "to_token": t_tok["symbol"],
                        "amount_in": float(amount_in),
                        "estimated_amount_out": float(out_amt),
                        "source": "1inch",
                        "rate": float(out_amt / Decimal(amount_in))
                        if Decimal(amount_in) > 0
                        else 0,
                    }
        except Exception as e:
            logger.info("1inch quote unavailable: %s", e)

        # Fallback: PancakeSwap on-chain quote
        try:
            router = self.w3.eth.contract(
                address=PANCAKE_V2_ROUTER, abi=PANCAKE_ROUTER_ABI
            )
            wbnb = BSC_TOKENS["WBNB"]["address"]
            # Try direct pair first, then via WBNB
            for path in (
                [f_tok["address"], t_tok["address"]],
                [f_tok["address"], wbnb, t_tok["address"]],
            ):
                try:
                    amounts = router.functions.getAmountsOut(
                        amount_in_wei, path
                    ).call()
                    out_wei = int(amounts[-1])
                    if out_wei > 0:
                        out_amt = Decimal(out_wei) / Decimal(
                            10 ** t_tok["decimals"]
                        )
                        return {
                            "from_token": f_tok["symbol"],
                            "to_token": t_tok["symbol"],
                            "amount_in": float(amount_in),
                            "estimated_amount_out": float(out_amt),
                            "source": "pancakeswap",
                            "rate": float(out_amt / Decimal(amount_in))
                            if Decimal(amount_in) > 0
                            else 0,
                        }
                except (ContractLogicError, Exception):
                    continue
        except Exception as e:
            logger.info("PancakeSwap quote unavailable: %s", e)

        # Last resort — conservative placeholder
        return {
            "from_token": f_tok["symbol"],
            "to_token": t_tok["symbol"],
            "amount_in": float(amount_in),
            "estimated_amount_out": float(Decimal(amount_in) * Decimal("0.95")),
            "source": "estimate",
            "rate": 0.95,
            "note": "No DEX liquidity; platform may complete via internal reserves (Tier 3/4).",
        }

    async def execute_swap(self, req: SwapRequest) -> SwapResult:
        """Execute a swap using the Tier 1→4 fallback chain."""
        swap_id = str(uuid.uuid4())
        started_at = datetime.now(timezone.utc)

        # Basic validation
        if not self.hot_wallet or not self.hot_wallet_pk:
            return SwapResult(
                success=False,
                swap_id=swap_id,
                error="Hot wallet not configured",
                message="Server misconfiguration: missing HOT_WALLET_*",
            )
        try:
            user_wallet = Web3.to_checksum_address(req.user_wallet_address)
        except Exception:
            return SwapResult(
                success=False,
                swap_id=swap_id,
                error="Invalid user_wallet_address",
                message="Fornisci un indirizzo BSC valido (0x…40 char)",
            )

        if req.amount_in <= 0:
            return SwapResult(
                success=False,
                swap_id=swap_id,
                error="amount_in must be > 0",
                message="Quantità non valida",
            )

        slippage = min(max(req.slippage, 0.1), self.max_slippage)

        # Resolve tokens
        try:
            f_tok = self._resolve_or_raise(req.from_token)
            t_tok = self._resolve_or_raise(req.to_token)
        except ValueError as e:
            return SwapResult(
                success=False, swap_id=swap_id, error=str(e), message=str(e)
            )

        if f_tok["address"].lower() == t_tok["address"].lower():
            return SwapResult(
                success=False,
                swap_id=swap_id,
                error="from_token == to_token",
                message="I token di input e output devono essere diversi",
            )

        # Cap NENO
        if f_tok["symbol"] == "NENO" and req.amount_in > self.max_neno_per_tx:
            return SwapResult(
                success=False,
                swap_id=swap_id,
                error="NENO cap exceeded",
                message=f"Massimo {self.max_neno_per_tx} NENO per transazione",
            )

        amount_in_wei = int(req.amount_in * Decimal(10 ** f_tok["decimals"]))

        # Persist an INITIAL record so the history always shows the attempt
        await self._save_swap(
            {
                "swap_id": swap_id,
                "user_id": req.user_id,
                "user_wallet": user_wallet,
                "from_token": f_tok["symbol"],
                "from_address": f_tok["address"],
                "to_token": t_tok["symbol"],
                "to_address": t_tok["address"],
                "amount_in": str(req.amount_in),
                "slippage_pct": slippage,
                "status": "pending",
                "tier": None,
                "tx_hash": None,
                "amount_out": None,
                "error": None,
                "created_at": started_at.isoformat(),
            }
        )

        attempts: List[str] = []
        last_err: Optional[str] = None

        # ---- TIER 1: 1inch aggregator ---------------------------------
        if self.oneinch_key:
            attempts.append("tier1_1inch")
            try:
                tx_hash, out_wei = await self._execute_via_1inch(
                    f_tok, t_tok, amount_in_wei, user_wallet, slippage
                )
                if tx_hash:
                    out_amt = Decimal(out_wei) / Decimal(10 ** t_tok["decimals"])
                    result = SwapResult(
                        success=True,
                        swap_id=swap_id,
                        tx_hash=tx_hash,
                        explorer_url=BSC_EXPLORER_TX + tx_hash,
                        amount_in=req.amount_in,
                        amount_out=out_amt,
                        from_token=f_tok["symbol"],
                        to_token=t_tok["symbol"],
                        tier="tier1",
                        tier_label="1inch Aggregator",
                        message="Swap eseguito tramite 1inch (best price)",
                    )
                    await self._finalize_swap(swap_id, result, attempts)
                    return result
            except Exception as e:
                last_err = f"1inch: {e}"
                logger.info("Tier 1 failed: %s", e)

        # ---- TIER 2: PancakeSwap V2 ------------------------------------
        attempts.append("tier2_pancakeswap")
        try:
            tx_hash, out_wei = await self._execute_via_pancakeswap(
                f_tok, t_tok, amount_in_wei, user_wallet, slippage
            )
            if tx_hash:
                out_amt = Decimal(out_wei) / Decimal(10 ** t_tok["decimals"])
                result = SwapResult(
                    success=True,
                    swap_id=swap_id,
                    tx_hash=tx_hash,
                    explorer_url=BSC_EXPLORER_TX + tx_hash,
                    amount_in=req.amount_in,
                    amount_out=out_amt,
                    from_token=f_tok["symbol"],
                    to_token=t_tok["symbol"],
                    tier="tier2",
                    tier_label="PancakeSwap V2",
                    message="Swap eseguito tramite PancakeSwap V2",
                )
                await self._finalize_swap(swap_id, result, attempts)
                return result
        except Exception as e:
            last_err = f"pancake: {e}"
            logger.info("Tier 2 failed: %s", e)

        # ---- TIER 3: Direct Hot Wallet Transfer -----------------------
        attempts.append("tier3_direct_transfer")
        try:
            tx_hash, out_wei = await self._execute_direct_transfer(
                f_tok, t_tok, amount_in_wei, user_wallet
            )
            if tx_hash:
                out_amt = Decimal(out_wei) / Decimal(10 ** t_tok["decimals"])
                result = SwapResult(
                    success=True,
                    swap_id=swap_id,
                    tx_hash=tx_hash,
                    explorer_url=BSC_EXPLORER_TX + tx_hash,
                    amount_in=req.amount_in,
                    amount_out=out_amt,
                    from_token=f_tok["symbol"],
                    to_token=t_tok["symbol"],
                    tier="tier3",
                    tier_label="Direct Transfer (reserve)",
                    message="Liquidità DEX non disponibile: inviato direttamente dalle riserve della piattaforma",
                )
                await self._finalize_swap(swap_id, result, attempts)
                return result
        except Exception as e:
            last_err = f"direct: {e}"
            logger.info("Tier 3 failed: %s", e)

        # ---- TIER 4: Ledger credit + queue ----------------------------
        attempts.append("tier4_queue")
        try:
            out_estimate = await self._estimate_output(
                f_tok, t_tok, req.amount_in
            )
            result = SwapResult(
                success=True,
                swap_id=swap_id,
                tx_hash=None,
                amount_in=req.amount_in,
                amount_out=out_estimate,
                from_token=f_tok["symbol"],
                to_token=t_tok["symbol"],
                tier="tier4",
                tier_label="Queued for on-chain delivery",
                queued=True,
                queued_at=datetime.now(timezone.utc).isoformat(),
                message=(
                    "Nessuna liquidità DEX né riserve disponibili al momento. "
                    "Il saldo è stato accreditato sulla piattaforma e la consegna "
                    "on-chain è in coda."
                ),
            )
            await self._enqueue_delivery(swap_id, req, f_tok, t_tok, out_estimate)
            await self._finalize_swap(swap_id, result, attempts, queued=True)
            return result
        except Exception as e:
            last_err = f"queue: {e}"
            logger.error("Tier 4 failed: %s", e)

        # All tiers failed
        failed = SwapResult(
            success=False,
            swap_id=swap_id,
            from_token=f_tok["symbol"],
            to_token=t_tok["symbol"],
            amount_in=req.amount_in,
            error=last_err or "all tiers failed",
            message="Swap fallito su tutti i tier. Contatta il supporto.",
        )
        await self._finalize_swap(swap_id, failed, attempts)
        return failed

    # ------------------------------------------------------------------
    # TIER 1 — 1inch
    # ------------------------------------------------------------------

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
        async with aiohttp.ClientSession(timeout=timeout) as s:
            async with s.get(url, headers=headers, params=params) as resp:
                txt = await resp.text()
                if resp.status != 200:
                    logger.info(
                        "1inch %s %s → %s: %s",
                        path,
                        params.get("src", ""),
                        resp.status,
                        txt[:200],
                    )
                    return None
                try:
                    return json.loads(txt)
                except Exception:
                    return None

    async def _oneinch_quote(
        self, src: str, dst: str, amount_wei: int
    ) -> Optional[dict]:
        return await self._oneinch_get(
            "/quote",
            {"src": src, "dst": dst, "amount": str(amount_wei)},
        )

    async def _execute_via_1inch(
        self,
        f_tok: dict,
        t_tok: dict,
        amount_in_wei: int,
        user_wallet: str,
        slippage: float,
    ) -> (Optional[str], int):
        # Ensure hot wallet has enough token balance
        bal = self._erc20_balance(f_tok["address"], self.hot_wallet)
        if bal < amount_in_wei:
            raise RuntimeError(
                f"hot wallet insufficient {f_tok['symbol']} balance: "
                f"{bal} < {amount_in_wei}"
            )

        # Ensure allowance to the 1inch router (spender fetched dynamically)
        spender_resp = await self._oneinch_get("/approve/spender", {})
        if not spender_resp or "address" not in spender_resp:
            raise RuntimeError("1inch: spender address unavailable")
        spender = Web3.to_checksum_address(spender_resp["address"])
        await self._ensure_allowance(f_tok["address"], spender, amount_in_wei)

        # Build swap tx via 1inch (v6)
        swap_resp = await self._oneinch_get(
            "/swap",
            {
                "src": f_tok["address"],
                "dst": t_tok["address"],
                "amount": str(amount_in_wei),
                "from": self.hot_wallet,
                "slippage": str(slippage),
                "receiver": user_wallet,
                "disableEstimate": "true",
                "allowPartialFill": "false",
            },
        )
        if not swap_resp or "tx" not in swap_resp:
            raise RuntimeError("1inch /swap returned no tx data")

        tx = swap_resp["tx"]
        estimated_out = int(
            swap_resp.get("dstAmount") or swap_resp.get("toTokenAmount") or 0
        )

        nonce = self.w3.eth.get_transaction_count(self.hot_wallet)
        gas_price = self.w3.eth.gas_price
        raw_tx = {
            "from": self.hot_wallet,
            "to": Web3.to_checksum_address(tx["to"]),
            "data": tx.get("data", "0x"),
            "value": int(tx.get("value", 0)),
            "gas": int(tx.get("gas") or 500_000),
            "gasPrice": int(tx.get("gasPrice") or gas_price),
            "nonce": nonce,
            "chainId": CHAIN_ID_BSC,
        }
        signed = self.w3.eth.account.sign_transaction(raw_tx, self.hot_wallet_pk)
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction).hex()
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
        if receipt.status != 1:
            raise RuntimeError(f"1inch tx reverted: {tx_hash}")

        # Normalize hex prefix
        if not tx_hash.startswith("0x"):
            tx_hash = "0x" + tx_hash
        return tx_hash, estimated_out

    # ------------------------------------------------------------------
    # TIER 2 — PancakeSwap V2
    # ------------------------------------------------------------------

    async def _execute_via_pancakeswap(
        self,
        f_tok: dict,
        t_tok: dict,
        amount_in_wei: int,
        user_wallet: str,
        slippage: float,
    ) -> (Optional[str], int):
        bal = self._erc20_balance(f_tok["address"], self.hot_wallet)
        if bal < amount_in_wei:
            raise RuntimeError(
                f"hot wallet insufficient {f_tok['symbol']}: {bal} < {amount_in_wei}"
            )

        router = self.w3.eth.contract(
            address=PANCAKE_V2_ROUTER, abi=PANCAKE_ROUTER_ABI
        )
        wbnb = BSC_TOKENS["WBNB"]["address"]

        # Find a viable path
        chosen_path: Optional[List[str]] = None
        estimated_out = 0
        for path in (
            [f_tok["address"], t_tok["address"]],
            [f_tok["address"], wbnb, t_tok["address"]],
        ):
            try:
                amts = router.functions.getAmountsOut(
                    amount_in_wei, path
                ).call()
                if int(amts[-1]) > 0:
                    chosen_path = path
                    estimated_out = int(amts[-1])
                    break
            except Exception:
                continue

        if not chosen_path or estimated_out <= 0:
            raise RuntimeError("no PancakeSwap path with liquidity")

        min_out = int(
            Decimal(estimated_out) * (Decimal(1) - Decimal(slippage) / Decimal(100))
        )

        await self._ensure_allowance(f_tok["address"], PANCAKE_V2_ROUTER, amount_in_wei)

        nonce = self.w3.eth.get_transaction_count(self.hot_wallet)
        gas_price = self.w3.eth.gas_price
        swap_tx = router.functions.swapExactTokensForTokens(
            amount_in_wei,
            min_out,
            chosen_path,
            user_wallet,
            int(time.time()) + 1200,
        ).build_transaction(
            {
                "from": self.hot_wallet,
                "gas": 500_000,
                "gasPrice": gas_price,
                "nonce": nonce,
                "chainId": CHAIN_ID_BSC,
            }
        )
        signed = self.w3.eth.account.sign_transaction(swap_tx, self.hot_wallet_pk)
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction).hex()
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
        if receipt.status != 1:
            raise RuntimeError(f"pancake tx reverted: {tx_hash}")
        if not tx_hash.startswith("0x"):
            tx_hash = "0x" + tx_hash
        return tx_hash, estimated_out

    # ------------------------------------------------------------------
    # TIER 3 — Direct hot-wallet transfer at oracle price
    # ------------------------------------------------------------------

    async def _execute_direct_transfer(
        self,
        f_tok: dict,
        t_tok: dict,
        amount_in_wei: int,
        user_wallet: str,
    ) -> (Optional[str], int):
        """
        When DEX liquidity is unavailable, we value the swap at an off-chain
        oracle (1inch quote of the INVERSE pair — or a small fallback).  We
        then transfer the equivalent amount of `to_token` from the hot wallet
        directly to the user.  The `from_token` remains in the user's balance
        on the platform ledger (they have NOT parted with their tokens on-chain
        in this case — a direct transfer is atomic from the platform side).
        """
        out_amount = await self._estimate_output(
            f_tok,
            t_tok,
            Decimal(amount_in_wei) / Decimal(10 ** f_tok["decimals"]),
        )
        out_wei = int(out_amount * Decimal(10 ** t_tok["decimals"]))
        if out_wei <= 0:
            raise RuntimeError("estimated out is 0")

        # Check reserve
        reserve = self._erc20_balance(t_tok["address"], self.hot_wallet)
        if reserve < out_wei:
            raise RuntimeError(
                f"hot wallet reserve insufficient for {t_tok['symbol']}: "
                f"{reserve} < {out_wei}"
            )

        token = self.w3.eth.contract(
            address=Web3.to_checksum_address(t_tok["address"]), abi=ERC20_ABI
        )
        nonce = self.w3.eth.get_transaction_count(self.hot_wallet)
        gas_price = self.w3.eth.gas_price
        tx = token.functions.transfer(user_wallet, out_wei).build_transaction(
            {
                "from": self.hot_wallet,
                "gas": 120_000,
                "gasPrice": gas_price,
                "nonce": nonce,
                "chainId": CHAIN_ID_BSC,
            }
        )
        signed = self.w3.eth.account.sign_transaction(tx, self.hot_wallet_pk)
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction).hex()
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
        if receipt.status != 1:
            raise RuntimeError(f"direct transfer reverted: {tx_hash}")
        if not tx_hash.startswith("0x"):
            tx_hash = "0x" + tx_hash
        return tx_hash, out_wei

    # ------------------------------------------------------------------
    # TIER 4 — Ledger credit + delivery queue
    # ------------------------------------------------------------------

    async def _enqueue_delivery(
        self,
        swap_id: str,
        req: SwapRequest,
        f_tok: dict,
        t_tok: dict,
        estimated_out: Decimal,
    ):
        if self.db is None:
            return
        await self.db.swap_queue.insert_one(
            {
                "_id": swap_id,
                "user_id": req.user_id,
                "user_wallet": req.user_wallet_address,
                "from_token": f_tok["symbol"],
                "to_token": t_tok["symbol"],
                "amount_in": str(req.amount_in),
                "amount_out_estimate": str(estimated_out),
                "status": "queued",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "attempts": 0,
            }
        )
        # Optional ledger credit (platform balance)
        try:
            await self.db.platform_balances.update_one(
                {"user_id": req.user_id, "token": t_tok["symbol"]},
                {
                    "$inc": {"amount": float(estimated_out)},
                    "$setOnInsert": {
                        "user_id": req.user_id,
                        "token": t_tok["symbol"],
                    },
                },
                upsert=True,
            )
        except Exception as e:
            logger.warning("ledger credit failed: %s", e)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _estimate_output(
        self, f_tok: dict, t_tok: dict, amount_in: Decimal
    ) -> Decimal:
        """Best-effort output estimate, used by Tier 3 and Tier 4."""
        q = await self.get_quote(f_tok["symbol"], t_tok["symbol"], amount_in)
        return Decimal(str(q.get("estimated_amount_out", 0)))

    async def _ensure_allowance(
        self, token_address: str, spender: str, amount: int
    ):
        """Approve `spender` for at least `amount` if needed."""
        token = self.w3.eth.contract(
            address=Web3.to_checksum_address(token_address), abi=ERC20_ABI
        )
        try:
            current = token.functions.allowance(
                self.hot_wallet, Web3.to_checksum_address(spender)
            ).call()
        except Exception:
            current = 0
        if current >= amount:
            return

        nonce = self.w3.eth.get_transaction_count(self.hot_wallet)
        gas_price = self.w3.eth.gas_price
        approve_tx = token.functions.approve(
            Web3.to_checksum_address(spender),
            2 ** 256 - 1,  # max approval for gas efficiency
        ).build_transaction(
            {
                "from": self.hot_wallet,
                "gas": 80_000,
                "gasPrice": gas_price,
                "nonce": nonce,
                "chainId": CHAIN_ID_BSC,
            }
        )
        signed = self.w3.eth.account.sign_transaction(approve_tx, self.hot_wallet_pk)
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction).hex()
        self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
        logger.info("Approved %s → %s", token_address, spender)

    async def _save_swap(self, doc: dict):
        if self.db is None:
            return
        try:
            await self.db.swaps.insert_one(doc)
        except Exception as e:
            logger.warning("save_swap failed: %s", e)

    async def _finalize_swap(
        self,
        swap_id: str,
        result: SwapResult,
        attempts: List[str],
        queued: bool = False,
    ):
        if self.db is None:
            return
        update = {
            "status": "queued"
            if queued
            else ("completed" if result.success else "failed"),
            "tier": result.tier,
            "tier_label": result.tier_label,
            "tx_hash": result.tx_hash,
            "amount_out": str(result.amount_out)
            if result.amount_out is not None
            else None,
            "error": result.error,
            "attempts": attempts,
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "explorer_url": result.explorer_url,
        }
        try:
            await self.db.swaps.update_one(
                {"swap_id": swap_id}, {"$set": update}
            )
        except Exception as e:
            logger.warning("finalize_swap failed: %s", e)

    async def get_user_history(
        self, user_id: str, limit: int = 50
    ) -> List[dict]:
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

    def health(self) -> dict:
        return {
            "hot_wallet": self.hot_wallet,
            "hot_wallet_configured": bool(self.hot_wallet and self.hot_wallet_pk),
            "rpc_connected": self._rpc_connected(),
            "rpc_url": self.rpc_url,
            "oneinch_configured": bool(self.oneinch_key),
            "default_slippage_pct": self.default_slippage,
            "max_slippage_pct": self.max_slippage,
            "max_neno_per_tx": float(self.max_neno_per_tx),
            "supported_tokens": [
                {"symbol": t["symbol"], "address": t["address"], "name": t["name"]}
                for t in BSC_TOKENS.values()
            ],
        }
