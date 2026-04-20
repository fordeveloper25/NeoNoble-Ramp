"""
NeoNoble BTC native bridge — scaffold MVP.

Modello: deposit-only bridge (user invia BTC → minta equivalente in BTCB su BSC).

Architettura:
 * Genera indirizzo BTC univoco per utente (derivato da HD seed platform via BIP-32).
 * Polla una blockchain indexer (es. Blockstream Esplora API, mempool.space) per
   detectare depositi in arrivo.
 * Dopo N conferme (6 default), il backend dispone un mint equivalente di BTCB
   ERC-20 sul wallet dell'utente via tesoreria BSC.
 * Withdrawal inverso (BTCB → BTC nativo) richiede che la tesoreria detenga BTC
   reale disponibile — gestito off-chain (MANUALE in v1, da automatizzare v2).

Limiti v1:
 * Solo deposit (BTC → BTCB). Withdrawal BTCB → BTC nativo e` manuale.
 * Nessun Lightning support (solo on-chain BTC).
 * HD seed platform va custodito in KMS (AWS KMS / HashiCorp Vault) — v1
   legge da `BTC_BRIDGE_SEED_HEX` env per sviluppo.

Endpoints:
    GET    /api/btc/health
    POST   /api/btc/deposit-address       # genera address univoco per user
    GET    /api/btc/deposit-status        # stato deposito (pending/confirmed/minted)
    GET    /api/btc/history               # storico bridge dell'utente
"""
from __future__ import annotations

import hashlib
import logging
import os
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from middleware.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/btc", tags=["BTC Native Bridge"])

ESPLORA_BASE = os.environ.get("BTC_ESPLORA_API", "https://blockstream.info/api")
MIN_CONFIRMATIONS = int(os.environ.get("BTC_MIN_CONFIRMATIONS", "6"))
SEED_HEX = os.environ.get("BTC_BRIDGE_SEED_HEX", "").strip()


def _derive_address(user_id: str) -> Optional[str]:
    """
    DEV scaffold: deriva un address deterministico da user_id + seed.
    In produzione v2 usare python-bitcoinlib + BIP-32 HD derivation (m/84'/0'/0'/0/N
    per bech32 P2WPKH). Per v1 torniamo None se seed non settato.
    """
    if not SEED_HEX:
        return None
    # Stub: hash-based (NON usare in prod — placeholder)
    h = hashlib.sha256((SEED_HEX + user_id).encode()).hexdigest()
    # finto indirizzo bech32 per scaffold
    return f"bc1q{h[:39]}"


class DepositAddrIn(BaseModel):
    label: Optional[str] = Field(default=None, max_length=80)


class _State:
    def __init__(self):
        self.db = None

    def set_db(self, db):
        self.db = db


_state: Optional[_State] = None


def get_state() -> _State:
    global _state
    if _state is None:
        _state = _State()
    return _state


def set_btc_db(db):
    get_state().set_db(db)


@router.get("/health")
async def btc_health():
    return {
        "status": "scaffold" if not SEED_HEX else "operational",
        "network": "bitcoin-mainnet",
        "esplora_api": ESPLORA_BASE,
        "min_confirmations": MIN_CONFIRMATIONS,
        "seed_configured": bool(SEED_HEX),
        "note": (
            "Native BTC bridge scaffold MVP. Withdrawals (BTCB -> BTC native) are "
            "manual in v1. For production set BTC_BRIDGE_SEED_HEX (custodied in KMS) "
            "and enable the HD derivation + Esplora poller."
        ),
    }


@router.post("/deposit-address")
async def get_deposit_address(
    body: DepositAddrIn,
    user: dict = Depends(get_current_user),
):
    s = get_state()
    if s.db is None:
        raise HTTPException(503, "db not ready")
    uid = user.get("user_id") or user.get("email")
    if not uid:
        raise HTTPException(401, "no user id")

    # lookup esistente
    existing = await s.db.btc_deposit_addresses.find_one({"user_id": uid}, {"_id": 0})
    if existing:
        return existing

    addr = _derive_address(uid)
    if not addr:
        raise HTTPException(
            503,
            "BTC bridge seed non configurato (dev). Impostare BTC_BRIDGE_SEED_HEX "
            "in ambiente produzione (custodito in KMS).",
        )
    doc = {
        "user_id": uid,
        "address": addr,
        "label": body.label,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "min_confirmations": MIN_CONFIRMATIONS,
    }
    await s.db.btc_deposit_addresses.insert_one(doc)
    doc.pop("_id", None)
    return doc


@router.get("/deposit-status")
async def deposit_status(
    address: str = Query(..., min_length=10),
    user: dict = Depends(get_current_user),
):
    """
    Check dello stato deposito. In v1 ritorna info da Esplora API se l'address
    e` registrato. In v2: trigger mint automatico BTCB dopo N conferme.
    """
    import httpx
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(f"{ESPLORA_BASE}/address/{address}")
            if r.status_code == 404:
                return {"address": address, "status": "no_transactions", "balance_btc": 0}
            r.raise_for_status()
            data = r.json()
    except Exception as e:
        logger.warning("esplora fetch failed: %s", e)
        raise HTTPException(502, f"esplora: {e}")

    funded = data.get("chain_stats", {}).get("funded_txo_sum", 0)
    spent = data.get("chain_stats", {}).get("spent_txo_sum", 0)
    balance_sats = funded - spent
    balance_btc = balance_sats / 1e8

    # mempool
    mempool_funded = data.get("mempool_stats", {}).get("funded_txo_sum", 0)
    mempool_btc = mempool_funded / 1e8

    return {
        "address": address,
        "status": "confirmed" if balance_btc > 0 else ("pending" if mempool_btc > 0 else "no_transactions"),
        "balance_btc": balance_btc,
        "pending_mempool_btc": mempool_btc,
        "tx_count": data.get("chain_stats", {}).get("tx_count", 0),
        "min_confirmations_required": MIN_CONFIRMATIONS,
        "explorer_url": f"https://mempool.space/address/{address}",
    }


@router.get("/history")
async def history(user: dict = Depends(get_current_user)):
    s = get_state()
    if s.db is None:
        return {"items": []}
    uid = user.get("user_id") or user.get("email")
    items = []
    async for d in s.db.btc_bridge_events.find({"user_id": uid}, {"_id": 0}).sort("created_at", -1).limit(100):
        items.append(d)
    return {"items": items}
