"""
NeoNoble Internal Exchange — $NENO On/Off-Ramp.

Fully independent conversion engine for $NENO at fixed price of EUR 10,000.
No external providers. All conversions happen on-platform with wallet credit.

Supports:
- Buy NENO with: BNB, ETH, USDT, BTC, USDC, MATIC, EUR, USD
- Sell NENO for:  BNB, ETH, USDT, BTC, USDC, MATIC, EUR, USD
- Off-ramp to card (NIUM) or bank account (SEPA)
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timezone
import uuid

from database.mongodb import get_database
from routes.auth import get_current_user

router = APIRouter(prefix="/neno-exchange", tags=["NENO Exchange"])

# ── Fixed NENO price ──
NENO_EUR_PRICE = 10_000.0

# ── Market reference prices (EUR) — synced with settlement engine ──
MARKET_PRICES_EUR = {
    "BTC": 60787.0,
    "ETH": 1769.0,
    "BNB": 555.36,
    "USDT": 0.92,
    "USDC": 0.92,
    "MATIC": 0.55,
    "SOL": 74.72,
    "XRP": 1.21,
    "ADA": 0.38,
    "DOGE": 0.082,
    "EUR": 1.0,
    "USD": 0.92,
}

PLATFORM_FEE = 0.003  # 0.3%
SUPPORTED_ASSETS = list(MARKET_PRICES_EUR.keys())


def _neno_rate(asset: str) -> float:
    """How many units of `asset` equal 1 NENO."""
    price_eur = MARKET_PRICES_EUR.get(asset.upper())
    if price_eur is None or price_eur <= 0:
        raise ValueError(f"Asset non supportato: {asset}")
    return NENO_EUR_PRICE / price_eur


class BuyNenoRequest(BaseModel):
    pay_asset: str = Field(description="Asset used to pay (BNB, ETH, EUR ...)")
    neno_amount: float = Field(gt=0, description="How many NENO to buy")


class SellNenoRequest(BaseModel):
    receive_asset: str = Field(description="Asset to receive (BNB, ETH, EUR ...)")
    neno_amount: float = Field(gt=0, description="How many NENO to sell")


class OfframpRequest(BaseModel):
    neno_amount: float = Field(gt=0)
    destination: str = Field(description="'card' or 'bank'")
    card_id: Optional[str] = None
    destination_iban: Optional[str] = None
    beneficiary_name: Optional[str] = None


# ── helpers ──

async def _get_balance(db, user_id: str, asset: str) -> float:
    w = await db.wallets.find_one({"user_id": user_id, "asset": asset.upper()})
    return w.get("balance", 0) if w else 0


async def _credit(db, user_id: str, asset: str, amount: float):
    await db.wallets.update_one(
        {"user_id": user_id, "asset": asset.upper()},
        {"$inc": {"balance": amount}, "$setOnInsert": {"user_id": user_id, "asset": asset.upper()}},
        upsert=True,
    )


async def _debit(db, user_id: str, asset: str, amount: float):
    await db.wallets.update_one(
        {"user_id": user_id, "asset": asset.upper()},
        {"$inc": {"balance": -amount}},
    )


async def _log_tx(db, tx: dict):
    await db.neno_transactions.insert_one({**tx, "_id": tx["id"]})


# ── Quote ──

@router.get("/quote")
async def get_quote(
    direction: str = "buy",
    asset: str = "EUR",
    neno_amount: float = 1.0,
):
    """Get a live quote for buying or selling NENO."""
    asset = asset.upper()
    if asset not in MARKET_PRICES_EUR:
        raise HTTPException(status_code=400, detail=f"Asset non supportato: {asset}")

    rate = _neno_rate(asset)
    gross = round(neno_amount * rate, 8)
    fee = round(gross * PLATFORM_FEE, 8)

    if direction == "buy":
        total_cost = round(gross + fee, 8)
        return {
            "direction": "buy",
            "neno_amount": neno_amount,
            "pay_asset": asset,
            "rate": round(rate, 8),
            "neno_eur_price": NENO_EUR_PRICE,
            "gross_cost": gross,
            "fee": fee,
            "fee_percent": PLATFORM_FEE * 100,
            "total_cost": total_cost,
            "summary": f"Per acquistare {neno_amount} NENO servono {total_cost} {asset} (fee {PLATFORM_FEE*100}%)",
        }
    else:
        net_receive = round(gross - fee, 8)
        return {
            "direction": "sell",
            "neno_amount": neno_amount,
            "receive_asset": asset,
            "rate": round(rate, 8),
            "neno_eur_price": NENO_EUR_PRICE,
            "gross_value": gross,
            "fee": fee,
            "fee_percent": PLATFORM_FEE * 100,
            "net_receive": net_receive,
            "summary": f"Vendendo {neno_amount} NENO ricevi {net_receive} {asset} (fee {PLATFORM_FEE*100}%)",
        }


# ── Buy NENO ──

@router.post("/buy")
async def buy_neno(req: BuyNenoRequest, current_user: dict = Depends(get_current_user)):
    """Buy NENO paying with any supported asset. Credits NENO to wallet."""
    db = get_database()
    uid = current_user["user_id"]
    asset = req.pay_asset.upper()

    if asset not in MARKET_PRICES_EUR:
        raise HTTPException(status_code=400, detail=f"Asset non supportato: {asset}")

    rate = _neno_rate(asset)
    gross_cost = round(req.neno_amount * rate, 8)
    fee = round(gross_cost * PLATFORM_FEE, 8)
    total_cost = round(gross_cost + fee, 8)

    balance = await _get_balance(db, uid, asset)
    if balance < total_cost:
        raise HTTPException(
            status_code=400,
            detail=f"Saldo {asset} insufficiente: {balance:.8g} disponibile, {total_cost:.8g} necessario",
        )

    # Execute
    await _debit(db, uid, asset, total_cost)
    await _credit(db, uid, "NENO", req.neno_amount)

    tx = {
        "id": str(uuid.uuid4()),
        "user_id": uid,
        "type": "buy_neno",
        "neno_amount": req.neno_amount,
        "pay_asset": asset,
        "pay_amount": total_cost,
        "rate": rate,
        "neno_eur_price": NENO_EUR_PRICE,
        "fee": fee,
        "fee_asset": asset,
        "status": "completed",
        "created_at": datetime.now(timezone.utc),
    }
    await _log_tx(db, tx)

    new_neno = await _get_balance(db, uid, "NENO")
    new_pay = await _get_balance(db, uid, asset)

    tx["created_at"] = tx["created_at"].isoformat()
    return {
        "message": f"Acquistati {req.neno_amount} NENO per {total_cost} {asset}",
        "transaction": tx,
        "balances": {"NENO": round(new_neno, 8), asset: round(new_pay, 8)},
    }


# ── Sell NENO ──

@router.post("/sell")
async def sell_neno(req: SellNenoRequest, current_user: dict = Depends(get_current_user)):
    """Sell NENO and receive any supported asset in wallet."""
    db = get_database()
    uid = current_user["user_id"]
    asset = req.receive_asset.upper()

    if asset not in MARKET_PRICES_EUR:
        raise HTTPException(status_code=400, detail=f"Asset non supportato: {asset}")

    neno_balance = await _get_balance(db, uid, "NENO")
    if neno_balance < req.neno_amount:
        raise HTTPException(
            status_code=400,
            detail=f"Saldo NENO insufficiente: {neno_balance:.8g} disponibile",
        )

    rate = _neno_rate(asset)
    gross = round(req.neno_amount * rate, 8)
    fee = round(gross * PLATFORM_FEE, 8)
    net = round(gross - fee, 8)

    # Execute
    await _debit(db, uid, "NENO", req.neno_amount)
    await _credit(db, uid, asset, net)

    tx = {
        "id": str(uuid.uuid4()),
        "user_id": uid,
        "type": "sell_neno",
        "neno_amount": req.neno_amount,
        "receive_asset": asset,
        "receive_amount": net,
        "rate": rate,
        "neno_eur_price": NENO_EUR_PRICE,
        "fee": fee,
        "fee_asset": asset,
        "status": "completed",
        "created_at": datetime.now(timezone.utc),
    }
    await _log_tx(db, tx)

    new_neno = await _get_balance(db, uid, "NENO")
    new_asset = await _get_balance(db, uid, asset)

    tx["created_at"] = tx["created_at"].isoformat()
    return {
        "message": f"Venduti {req.neno_amount} NENO per {net} {asset}",
        "transaction": tx,
        "balances": {"NENO": round(new_neno, 8), asset: round(new_asset, 8)},
    }


# ── Off-Ramp: NENO → EUR → Card or Bank ──

@router.post("/offramp")
async def offramp_neno(req: OfframpRequest, current_user: dict = Depends(get_current_user)):
    """Sell NENO and send EUR directly to card or bank account."""
    db = get_database()
    uid = current_user["user_id"]

    neno_balance = await _get_balance(db, uid, "NENO")
    if neno_balance < req.neno_amount:
        raise HTTPException(status_code=400, detail=f"Saldo NENO insufficiente: {neno_balance:.8g}")

    eur_gross = round(req.neno_amount * NENO_EUR_PRICE, 2)
    fee = round(eur_gross * PLATFORM_FEE, 2)
    eur_net = round(eur_gross - fee, 2)

    # Debit NENO
    await _debit(db, uid, "NENO", req.neno_amount)

    if req.destination == "card":
        if not req.card_id:
            raise HTTPException(status_code=400, detail="card_id richiesto per off-ramp su carta")
        card = await db.cards.find_one({"id": req.card_id, "user_id": uid})
        if not card:
            raise HTTPException(status_code=404, detail="Carta non trovata")

        await db.cards.update_one({"id": req.card_id}, {"$inc": {"balance": eur_net}})
        dest_info = f"Carta {card.get('card_number_masked', '****')}"

    elif req.destination == "bank":
        if not req.destination_iban:
            raise HTTPException(status_code=400, detail="IBAN richiesto per off-ramp su conto")

        withdrawal_fee = max(round(eur_net * 0.001, 2), 0.50)
        eur_after_bank = round(eur_net - withdrawal_fee, 2)

        bank_tx = {
            "id": str(uuid.uuid4()),
            "user_id": uid,
            "type": "sepa_withdrawal",
            "amount": eur_net,
            "fee": withdrawal_fee,
            "net_amount": eur_after_bank,
            "currency": "EUR",
            "destination_iban": req.destination_iban,
            "beneficiary_name": req.beneficiary_name or "NeoNoble User",
            "reference": f"NENO-OFFRAMP-{uuid.uuid4().hex[:8].upper()}",
            "status": "processing",
            "estimated_arrival": "1-2 giorni lavorativi",
            "created_at": datetime.now(timezone.utc),
        }
        await db.banking_transactions.insert_one({**bank_tx, "_id": bank_tx["id"]})
        eur_net = eur_after_bank
        dest_info = f"IBAN {req.destination_iban[-4:]}"
    else:
        raise HTTPException(status_code=400, detail="destination deve essere 'card' o 'bank'")

    tx = {
        "id": str(uuid.uuid4()),
        "user_id": uid,
        "type": "neno_offramp",
        "neno_amount": req.neno_amount,
        "eur_gross": eur_gross,
        "fee": fee,
        "eur_net": eur_net,
        "destination": req.destination,
        "destination_info": dest_info,
        "status": "completed" if req.destination == "card" else "processing",
        "created_at": datetime.now(timezone.utc),
    }
    await _log_tx(db, tx)
    tx["created_at"] = tx["created_at"].isoformat()

    return {
        "message": f"{req.neno_amount} NENO → EUR {eur_net:.2f} → {dest_info}",
        "transaction": tx,
        "neno_balance": round(await _get_balance(db, uid, "NENO"), 8),
    }


# ── Transaction History ──

@router.get("/transactions")
async def get_neno_transactions(current_user: dict = Depends(get_current_user)):
    """Get NENO exchange transaction history."""
    db = get_database()
    txs = await db.neno_transactions.find(
        {"user_id": current_user["user_id"]}, {"_id": 0}
    ).sort("created_at", -1).limit(50).to_list(50)
    for t in txs:
        if "created_at" in t and hasattr(t["created_at"], "isoformat"):
            t["created_at"] = t["created_at"].isoformat()
    return {"transactions": txs, "total": len(txs)}


# ── Market Info ──

@router.get("/market")
async def neno_market_info():
    """Get $NENO market info and all conversion rates."""
    pairs = {}
    for asset, eur_price in MARKET_PRICES_EUR.items():
        rate = NENO_EUR_PRICE / eur_price
        pairs[f"NENO/{asset}"] = {
            "rate": round(rate, 8),
            "asset_eur_price": eur_price,
            "neno_eur_price": NENO_EUR_PRICE,
        }
    return {
        "neno_eur_price": NENO_EUR_PRICE,
        "neno_usd_price": NENO_EUR_PRICE * 1.087,
        "fee_percent": PLATFORM_FEE * 100,
        "supported_assets": SUPPORTED_ASSETS,
        "pairs": pairs,
    }
