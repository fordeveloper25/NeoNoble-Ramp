"""
NeoNoble Launchpad — Bonding Curve Token Factory (BSC Mainnet)

Architettura
------------
Il creator (utente qualunque) deploy un ERC20 con bonding curve progressiva
pagando solo una deploy fee (~0.05 BNB). NESSUN collateral richiesto.

La liquidita` viene interamente dai buyer: ogni BUY aumenta realBnbReserve,
ogni SELL preleva da realBnbReserve. Prezzo segue una curva costante-prodotto
virtuale (x*y=k) con reserve iniziali che bootstrapano il prezzo di partenza.

Endpoints
---------
    GET    /api/launchpad/health
    GET    /api/launchpad/config
    GET    /api/launchpad/tokens           ?limit=50&offset=0
    GET    /api/launchpad/tokens/{address}
    POST   /api/launchpad/build-create     (user_signed_tx creator)
    POST   /api/launchpad/build-buy        (user_signed_tx buyer)
    POST   /api/launchpad/build-sell       (user_signed_tx seller)
    GET    /api/launchpad/quote-buy        ?token=...&bnb_in=0.1
    GET    /api/launchpad/quote-sell       ?token=...&tokens_in=1000

Config
------
Richiede su ENV:
    BSC_RPC_URL                    (es. https://bsc-dataseed1.binance.org)
    LAUNCHPAD_FACTORY_ADDRESS      (indirizzo factory BSC — impostato dopo deploy)

Se LAUNCHPAD_FACTORY_ADDRESS non e` settato, gli endpoint ritornano 503
con istruzioni di deploy (vedi /app/contracts/DEPLOY.md).
"""
from __future__ import annotations

import json
import logging
import os
from decimal import Decimal
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from web3 import Web3
from web3.exceptions import ContractLogicError

from middleware.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/launchpad", tags=["Launchpad"])

BSC_CHAIN_ID = 56
BSC_EXPLORER = "https://bscscan.com"

_ABI_DIR = Path(__file__).parent.parent / "abis"
with open(_ABI_DIR / "launchpad_abi.json") as f:
    FACTORY_ABI = json.load(f)
with open(_ABI_DIR / "bonding_curve_abi.json") as f:
    TOKEN_ABI = json.load(f)


class _LaunchpadState:
    def __init__(self):
        self.rpc_url = os.environ.get("BSC_RPC_URL", "https://bsc-dataseed1.binance.org")
        self.factory_address = os.environ.get("LAUNCHPAD_FACTORY_ADDRESS", "").strip()
        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url, request_kwargs={"timeout": 30}))

    @property
    def deployed(self) -> bool:
        return bool(self.factory_address) and Web3.is_address(self.factory_address)

    @property
    def factory(self):
        if not self.deployed:
            return None
        return self.w3.eth.contract(
            address=Web3.to_checksum_address(self.factory_address),
            abi=FACTORY_ABI,
        )

    def token(self, addr: str):
        return self.w3.eth.contract(
            address=Web3.to_checksum_address(addr), abi=TOKEN_ABI
        )


_state: Optional[_LaunchpadState] = None


def get_state() -> _LaunchpadState:
    global _state
    if _state is None:
        _state = _LaunchpadState()
    return _state


def require_deployed(state: _LaunchpadState):
    if not state.deployed:
        raise HTTPException(
            status_code=503,
            detail=(
                "Launchpad factory non ancora deployato. "
                "Deploy dei contract in /app/contracts/ su BSC, poi imposta "
                "LAUNCHPAD_FACTORY_ADDRESS nelle variabili d'ambiente. "
                "Vedi /app/contracts/DEPLOY.md."
            ),
        )


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class CreateTokenRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    symbol: str = Field(..., min_length=1, max_length=12)
    metadata_uri: str = Field(default="", max_length=500)
    user_wallet_address: str


class BuyRequest(BaseModel):
    token_address: str
    bnb_in: Decimal = Field(..., gt=0, description="BNB amount to spend (human units)")
    user_wallet_address: str
    slippage_pct: float = Field(default=3.0, ge=0.1, le=50.0)


class SellRequest(BaseModel):
    token_address: str
    tokens_in: Decimal = Field(..., gt=0, description="Token amount to sell (human units)")
    user_wallet_address: str
    slippage_pct: float = Field(default=3.0, ge=0.1, le=50.0)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _format_token_info(state: _LaunchpadState, token_addr: str) -> dict:
    c = state.token(token_addr)
    try:
        name = c.functions.name().call()
        symbol = c.functions.symbol().call()
        total_supply = c.functions.totalSupply().call()
        creator = c.functions.creator().call()
        metadata_uri = c.functions.metadataURI().call()
        graduated = c.functions.graduated().call()
        v_bnb = c.functions.virtualBnbReserve().call()
        v_tok = c.functions.virtualTokenReserve().call()
        r_bnb = c.functions.realBnbReserve().call()
        r_tok = c.functions.realTokenReserve().call()
        price_wei = c.functions.currentPriceWei().call()
        mcap_wei = c.functions.marketCapWei().call()
        grad_bnb = c.functions.GRADUATION_BNB().call()
    except Exception as e:
        logger.warning("token info failed %s: %s", token_addr, e)
        return {"address": token_addr, "error": str(e)}

    return {
        "address": Web3.to_checksum_address(token_addr),
        "name": name,
        "symbol": symbol,
        "total_supply": str(total_supply),
        "total_supply_human": float(Decimal(total_supply) / Decimal(10**18)),
        "creator": creator,
        "metadata_uri": metadata_uri,
        "graduated": graduated,
        "price_bnb": float(Decimal(price_wei) / Decimal(10**18)),
        "market_cap_bnb": float(Decimal(mcap_wei) / Decimal(10**18)),
        "virtual_bnb_reserve": str(v_bnb),
        "virtual_token_reserve": str(v_tok),
        "real_bnb_reserve": str(r_bnb),
        "real_bnb_reserve_human": float(Decimal(r_bnb) / Decimal(10**18)),
        "real_token_reserve": str(r_tok),
        "graduation_bnb": float(Decimal(grad_bnb) / Decimal(10**18)),
        "graduation_progress_pct": (float(r_bnb) / float(grad_bnb) * 100) if grad_bnb > 0 else 0,
        "explorer_url": f"{BSC_EXPLORER}/token/{Web3.to_checksum_address(token_addr)}",
    }


# ---------------------------------------------------------------------------
# Endpoints: read
# ---------------------------------------------------------------------------

@router.get("/health")
async def health():
    state = get_state()
    return {
        "status": "operational" if state.deployed else "awaiting_deploy",
        "rpc_connected": state.w3.is_connected(),
        "chain_id": BSC_CHAIN_ID,
        "factory_deployed": state.deployed,
        "factory_address": state.factory_address or None,
        "model": "virtual_constant_product_amm",
        "capital_required_from_platform": False,
        "capital_required_from_creator": "only deploy fee (~0.05 BNB)",
    }


@router.get("/config")
async def config():
    state = get_state()
    require_deployed(state)
    try:
        deploy_fee = state.factory.functions.deployFee().call()
        recipient = state.factory.functions.platformFeeRecipient().call()
        owner = state.factory.functions.owner().call()
        total = state.factory.functions.allTokensLength().call()
    except Exception as e:
        raise HTTPException(500, f"factory read error: {e}")
    return {
        "factory_address": state.factory_address,
        "deploy_fee_wei": str(deploy_fee),
        "deploy_fee_bnb": float(Decimal(deploy_fee) / Decimal(10**18)),
        "platform_fee_recipient": recipient,
        "owner": owner,
        "total_tokens": total,
        "platform_fee_bps": 100,   # hardcoded in contract
        "creator_fee_bps": 100,    # hardcoded in contract
        "graduation_bnb": 85.0,
        "tokens_on_curve": 800_000_000,
        "tokens_for_lp": 200_000_000,
    }


@router.get("/tokens")
async def list_tokens(limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0)):
    state = get_state()
    require_deployed(state)
    try:
        total = state.factory.functions.allTokensLength().call()
    except Exception as e:
        raise HTTPException(500, f"factory read error: {e}")

    end = min(offset + limit, total)
    addrs: List[str] = []
    for i in range(offset, end):
        try:
            addrs.append(state.factory.functions.allTokens(i).call())
        except Exception as e:
            logger.warning("allTokens(%d) failed: %s", i, e)

    items = [_format_token_info(state, a) for a in addrs]
    return {"total": total, "offset": offset, "limit": limit, "tokens": items}


@router.get("/tokens/{address}")
async def token_detail(address: str):
    state = get_state()
    require_deployed(state)
    if not Web3.is_address(address):
        raise HTTPException(400, "bad address")
    return _format_token_info(state, address)


@router.get("/quote-buy")
async def quote_buy(
    token: str = Query(...),
    bnb_in: float = Query(..., gt=0),
):
    state = get_state()
    require_deployed(state)
    if not Web3.is_address(token):
        raise HTTPException(400, "bad token")
    wei_in = int(Decimal(str(bnb_in)) * Decimal(10**18))
    try:
        tokens_out, bnb_after_fees = state.token(token).functions.getTokensOut(wei_in).call()
    except (ContractLogicError, Exception) as e:
        raise HTTPException(422, f"quote failed: {e}")
    return {
        "token_address": Web3.to_checksum_address(token),
        "bnb_in": bnb_in,
        "bnb_in_wei": str(wei_in),
        "bnb_after_fees": str(bnb_after_fees),
        "bnb_after_fees_human": float(Decimal(bnb_after_fees) / Decimal(10**18)),
        "tokens_out_wei": str(tokens_out),
        "tokens_out_human": float(Decimal(tokens_out) / Decimal(10**18)),
        "effective_price_bnb_per_token": (bnb_in / float(Decimal(tokens_out) / Decimal(10**18)))
            if tokens_out > 0 else 0,
    }


@router.get("/quote-sell")
async def quote_sell(
    token: str = Query(...),
    tokens_in: float = Query(..., gt=0),
):
    state = get_state()
    require_deployed(state)
    if not Web3.is_address(token):
        raise HTTPException(400, "bad token")
    wei_in = int(Decimal(str(tokens_in)) * Decimal(10**18))
    try:
        bnb_out, user_receives = state.token(token).functions.getBnbOut(wei_in).call()
    except (ContractLogicError, Exception) as e:
        raise HTTPException(422, f"quote failed: {e}")
    return {
        "token_address": Web3.to_checksum_address(token),
        "tokens_in": tokens_in,
        "tokens_in_wei": str(wei_in),
        "bnb_out_gross_wei": str(bnb_out),
        "bnb_out_gross_human": float(Decimal(bnb_out) / Decimal(10**18)),
        "user_receives_wei": str(user_receives),
        "user_receives_human": float(Decimal(user_receives) / Decimal(10**18)),
    }


# ---------------------------------------------------------------------------
# Endpoints: build (unsigned tx for MetaMask)
# ---------------------------------------------------------------------------

@router.post("/build-create")
async def build_create(
    body: CreateTokenRequest,
    current_user: dict = Depends(get_current_user),
):
    state = get_state()
    require_deployed(state)
    if not Web3.is_address(body.user_wallet_address):
        raise HTTPException(400, "bad wallet")

    try:
        deploy_fee = state.factory.functions.deployFee().call()
        tx = state.factory.functions.createToken(
            body.name, body.symbol, body.metadata_uri or ""
        ).build_transaction({
            "from": Web3.to_checksum_address(body.user_wallet_address),
            "value": deploy_fee,
            "chainId": BSC_CHAIN_ID,
            "gas": 3_500_000,
            "gasPrice": state.w3.eth.gas_price,
            "nonce": 0,  # frontend replaces
        })
    except Exception as e:
        logger.exception("build_create failed")
        raise HTTPException(500, f"build error: {e}")

    return {
        "to": tx["to"],
        "data": tx["data"],
        "value": hex(int(tx["value"])),
        "gas": hex(int(tx["gas"])),
        "gas_price": hex(int(tx["gasPrice"])),
        "chain_id": BSC_CHAIN_ID,
        "deploy_fee_bnb": float(Decimal(deploy_fee) / Decimal(10**18)),
    }


@router.post("/build-buy")
async def build_buy(
    body: BuyRequest,
    current_user: dict = Depends(get_current_user),
):
    state = get_state()
    require_deployed(state)
    if not Web3.is_address(body.user_wallet_address):
        raise HTTPException(400, "bad wallet")
    if not Web3.is_address(body.token_address):
        raise HTTPException(400, "bad token")

    wei_in = int(body.bnb_in * Decimal(10**18))
    token = state.token(body.token_address)
    try:
        tokens_out, _ = token.functions.getTokensOut(wei_in).call()
    except Exception as e:
        raise HTTPException(422, f"quote failed: {e}")

    min_out = int(Decimal(tokens_out) * (Decimal(1) - Decimal(body.slippage_pct) / Decimal(100)))

    try:
        tx = token.functions.buy(min_out).build_transaction({
            "from": Web3.to_checksum_address(body.user_wallet_address),
            "value": wei_in,
            "chainId": BSC_CHAIN_ID,
            "gas": 400_000,
            "gasPrice": state.w3.eth.gas_price,
            "nonce": 0,
        })
    except Exception as e:
        logger.exception("build_buy failed")
        raise HTTPException(500, f"build error: {e}")

    return {
        "to": tx["to"],
        "data": tx["data"],
        "value": hex(int(tx["value"])),
        "gas": hex(int(tx["gas"])),
        "gas_price": hex(int(tx["gasPrice"])),
        "chain_id": BSC_CHAIN_ID,
        "tokens_out_estimate": str(tokens_out),
        "tokens_out_estimate_human": float(Decimal(tokens_out) / Decimal(10**18)),
        "min_tokens_out": str(min_out),
        "slippage_pct": body.slippage_pct,
    }


@router.post("/build-sell")
async def build_sell(
    body: SellRequest,
    current_user: dict = Depends(get_current_user),
):
    state = get_state()
    require_deployed(state)
    if not Web3.is_address(body.user_wallet_address):
        raise HTTPException(400, "bad wallet")
    if not Web3.is_address(body.token_address):
        raise HTTPException(400, "bad token")

    wei_tokens = int(body.tokens_in * Decimal(10**18))
    token = state.token(body.token_address)
    try:
        _, user_receives = token.functions.getBnbOut(wei_tokens).call()
    except Exception as e:
        raise HTTPException(422, f"quote failed: {e}")

    min_bnb = int(Decimal(user_receives) * (Decimal(1) - Decimal(body.slippage_pct) / Decimal(100)))

    try:
        tx = token.functions.sell(wei_tokens, min_bnb).build_transaction({
            "from": Web3.to_checksum_address(body.user_wallet_address),
            "value": 0,
            "chainId": BSC_CHAIN_ID,
            "gas": 300_000,
            "gasPrice": state.w3.eth.gas_price,
            "nonce": 0,
        })
    except Exception as e:
        logger.exception("build_sell failed")
        raise HTTPException(500, f"build error: {e}")

    return {
        "to": tx["to"],
        "data": tx["data"],
        "value": "0x0",
        "gas": hex(int(tx["gas"])),
        "gas_price": hex(int(tx["gasPrice"])),
        "chain_id": BSC_CHAIN_ID,
        "bnb_out_estimate": str(user_receives),
        "bnb_out_estimate_human": float(Decimal(user_receives) / Decimal(10**18)),
        "min_bnb_out": str(min_bnb),
        "slippage_pct": body.slippage_pct,
    }
