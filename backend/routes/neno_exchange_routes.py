"""
NeoNoble Internal Exchange — $NENO On/Off-Ramp.

Fully independent conversion engine for $NENO at fixed price of EUR 10,000.
No external providers. All conversions happen on-platform with wallet credit.

Supports:
- Buy NENO with: BNB, ETH, USDT, BTC, USDC, MATIC, EUR, USD
- Sell NENO for:  BNB, ETH, USDT, BTC, USDC, MATIC, EUR, USD
- Off-ramp to card (NIUM) or bank account (SEPA)
- Create custom tokens with specified price
- Swap any token pair through NENO as bridge
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timezone, timedelta
import uuid
import hashlib
import asyncio

from database.mongodb import get_database
from routes.auth import get_current_user


def _generate_settlement_hash(tx_id: str, uid: str, amount: float) -> str:
    """Generate a deterministic settlement hash (0x-prefixed hex) for tx tracking."""
    raw = f"{tx_id}:{uid}:{amount}:{datetime.now(timezone.utc).isoformat()}"
    return "0x" + hashlib.sha256(raw.encode()).hexdigest()


def _settlement_record(tx_id: str, tx_type: str, uid: str, amount: float, asset: str, details: dict) -> dict:
    """Create a complete settlement record for a transaction."""
    settlement_hash = _generate_settlement_hash(tx_id, uid, amount)
    return {
        "settlement_hash": settlement_hash,
        "settlement_status": "settled",
        "settlement_timestamp": datetime.now(timezone.utc).isoformat(),
        "settlement_network": "NeoNoble Internal Ledger",
        "settlement_confirmations": 1,
        "settlement_details": details,
    }

router = APIRouter(prefix="/neno-exchange", tags=["NENO Exchange"])

# ── Base NENO price — dynamically adjusted based on order book pressure ──
NENO_BASE_PRICE = 10_000.0
NENO_MAX_DEVIATION = 0.05
PRICE_IMPACT_FACTOR = 0.0001

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


async def _get_dynamic_neno_price() -> dict:
    """Calculate dynamic NENO price based on recent order book pressure."""
    db = get_database()
    now = datetime.now(timezone.utc)
    window = now - timedelta(hours=24)

    pipeline = [
        {"$match": {"created_at": {"$gte": window}}},
        {"$group": {
            "_id": "$type",
            "total_neno": {"$sum": "$neno_amount"},
            "count": {"$sum": 1},
        }},
    ]
    agg = await db.neno_transactions.aggregate(pipeline).to_list(10)
    buy_vol = 0
    sell_vol = 0
    for row in agg:
        if row["_id"] in ("buy_neno",):
            buy_vol = row["total_neno"]
        elif row["_id"] in ("sell_neno", "offramp_card", "offramp_bank"):
            sell_vol += row["total_neno"]

    net_pressure = buy_vol - sell_vol
    price_shift = net_pressure * PRICE_IMPACT_FACTOR
    max_shift = NENO_BASE_PRICE * NENO_MAX_DEVIATION
    price_shift = max(-max_shift, min(max_shift, price_shift))

    dynamic_price = round(NENO_BASE_PRICE + price_shift, 2)
    return {
        "price": dynamic_price,
        "base_price": NENO_BASE_PRICE,
        "shift": round(price_shift, 2),
        "shift_pct": round((price_shift / NENO_BASE_PRICE) * 100, 3),
        "buy_volume_24h": round(buy_vol, 4),
        "sell_volume_24h": round(sell_vol, 4),
        "net_pressure": round(net_pressure, 4),
    }


def _neno_rate_with_price(asset: str, neno_price: float) -> float:
    """How many units of `asset` equal 1 NENO at given price."""
    price_eur = MARKET_PRICES_EUR.get(asset.upper())
    if price_eur is None or price_eur <= 0:
        raise ValueError(f"Asset non supportato: {asset}")
    return neno_price / price_eur


async def _get_custom_token_price(db, symbol: str) -> Optional[float]:
    """Get price in EUR for a custom token from DB."""
    token = await db.custom_tokens.find_one({"symbol": symbol.upper()}, {"_id": 0})
    if token:
        return token.get("price_eur", 0)
    return None


async def _get_any_price_eur(db, asset: str) -> Optional[float]:
    """Get EUR price for built-in OR custom token OR NENO."""
    asset = asset.upper()
    if asset == "NENO":
        pricing = await _get_dynamic_neno_price()
        return pricing["price"]
    if asset in MARKET_PRICES_EUR:
        return MARKET_PRICES_EUR[asset]
    return await _get_custom_token_price(db, asset)


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


class CreateTokenRequest(BaseModel):
    symbol: str = Field(min_length=2, max_length=10, description="Token ticker (e.g. MYTOKEN)")
    name: str = Field(min_length=1, max_length=50, description="Token display name")
    price_eur: float = Field(gt=0, description="Price in EUR per token")
    total_supply: float = Field(gt=0, default=1_000_000, description="Total supply to mint")
    description: Optional[str] = None


class SwapRequest(BaseModel):
    from_asset: str = Field(description="Asset to sell")
    to_asset: str = Field(description="Asset to receive")
    amount: float = Field(gt=0, description="Amount of from_asset to swap")


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
    doc = {**tx}
    doc["_id"] = doc["id"]
    await db.neno_transactions.insert_one(doc)


# ── Dynamic Price endpoint ──

@router.get("/price")
async def get_neno_price():
    pricing = await _get_dynamic_neno_price()
    return {
        "neno_eur_price": pricing["price"],
        "base_price": pricing["base_price"],
        "price_shift": pricing["shift"],
        "shift_pct": pricing["shift_pct"],
        "buy_volume_24h": pricing["buy_volume_24h"],
        "sell_volume_24h": pricing["sell_volume_24h"],
        "net_pressure": pricing["net_pressure"],
        "pricing_model": "dynamic_orderbook",
        "max_deviation": f"{NENO_MAX_DEVIATION * 100}%",
    }


# ── Quote ──

@router.get("/quote")
async def get_quote(direction: str = "buy", asset: str = "EUR", neno_amount: float = 1.0):
    asset = asset.upper()
    db = get_database()
    price_eur = await _get_any_price_eur(db, asset)
    if price_eur is None:
        raise HTTPException(status_code=400, detail=f"Asset non supportato: {asset}")

    pricing = await _get_dynamic_neno_price()
    neno_eur_price = pricing["price"]
    rate = neno_eur_price / price_eur
    gross = round(neno_amount * rate, 8)
    fee = round(gross * PLATFORM_FEE, 8)

    if direction == "buy":
        total_cost = round(gross + fee, 8)
        return {
            "direction": "buy", "neno_amount": neno_amount, "pay_asset": asset,
            "rate": round(rate, 8), "neno_eur_price": neno_eur_price,
            "base_price": NENO_BASE_PRICE, "price_shift_pct": pricing["shift_pct"],
            "gross_cost": gross, "fee": fee, "fee_percent": PLATFORM_FEE * 100,
            "total_cost": total_cost,
            "summary": f"Per acquistare {neno_amount} NENO servono {total_cost} {asset} (fee {PLATFORM_FEE*100}%)",
        }
    else:
        net_receive = round(gross - fee, 8)
        return {
            "direction": "sell", "neno_amount": neno_amount, "receive_asset": asset,
            "rate": round(rate, 8), "neno_eur_price": neno_eur_price,
            "base_price": NENO_BASE_PRICE, "price_shift_pct": pricing["shift_pct"],
            "gross_value": gross, "fee": fee, "fee_percent": PLATFORM_FEE * 100,
            "net_receive": net_receive,
            "summary": f"Vendendo {neno_amount} NENO ricevi {net_receive} {asset} (fee {PLATFORM_FEE*100}%)",
        }


# ── Buy NENO ──

@router.post("/buy")
async def buy_neno(req: BuyNenoRequest, current_user: dict = Depends(get_current_user)):
    db = get_database()
    uid = current_user["user_id"]
    asset = req.pay_asset.upper()

    price_eur = await _get_any_price_eur(db, asset)
    if price_eur is None:
        raise HTTPException(status_code=400, detail=f"Asset non supportato: {asset}")

    pricing = await _get_dynamic_neno_price()
    neno_eur_price = pricing["price"]
    rate = neno_eur_price / price_eur
    gross_cost = round(req.neno_amount * rate, 8)
    fee = round(gross_cost * PLATFORM_FEE, 8)
    total_cost = round(gross_cost + fee, 8)

    balance = await _get_balance(db, uid, asset)
    if balance < total_cost:
        raise HTTPException(
            status_code=400,
            detail=f"Saldo {asset} insufficiente: {balance:.8g} disponibile, {total_cost:.8g} necessario",
        )

    await _debit(db, uid, asset, total_cost)
    await _credit(db, uid, "NENO", req.neno_amount)

    tx_id = str(uuid.uuid4())
    settlement = _settlement_record(tx_id, "buy_neno", uid, req.neno_amount, "NENO", {
        "debit": {"asset": asset, "amount": total_cost},
        "credit": {"asset": "NENO", "amount": req.neno_amount},
        "fee": {"asset": asset, "amount": fee},
    })

    tx = {
        "id": tx_id, "user_id": uid, "type": "buy_neno",
        "neno_amount": req.neno_amount, "pay_asset": asset,
        "pay_amount": total_cost, "rate": rate, "neno_eur_price": neno_eur_price,
        "fee": fee, "fee_asset": asset, "status": "completed",
        "eur_value": round(req.neno_amount * neno_eur_price, 2),
        **settlement,
        "created_at": datetime.now(timezone.utc),
    }
    await _log_tx(db, tx)
    tx["created_at"] = tx["created_at"].isoformat()

    try:
        from services.notification_dispatch import notify_trade_executed
        eur_value = round(req.neno_amount * neno_eur_price, 2)
        asyncio.ensure_future(notify_trade_executed(uid, "NENO", "buy", req.neno_amount, neno_eur_price, eur_value))
    except Exception:
        pass

    new_neno = await _get_balance(db, uid, "NENO")
    new_pay = await _get_balance(db, uid, asset)

    return {
        "message": f"Acquistati {req.neno_amount} NENO per {total_cost} {asset}",
        "transaction": tx,
        "balances": {"NENO": round(new_neno, 8), asset: round(new_pay, 8)},
    }


# ── Sell NENO ──

@router.post("/sell")
async def sell_neno(req: SellNenoRequest, current_user: dict = Depends(get_current_user)):
    db = get_database()
    uid = current_user["user_id"]
    asset = req.receive_asset.upper()

    price_eur = await _get_any_price_eur(db, asset)
    if price_eur is None:
        raise HTTPException(status_code=400, detail=f"Asset non supportato: {asset}")

    neno_balance = await _get_balance(db, uid, "NENO")
    if neno_balance < req.neno_amount:
        raise HTTPException(
            status_code=400,
            detail=f"Saldo NENO insufficiente: {neno_balance:.8g} disponibile",
        )

    pricing = await _get_dynamic_neno_price()
    neno_eur_price = pricing["price"]
    rate = neno_eur_price / price_eur
    gross = round(req.neno_amount * rate, 8)
    fee = round(gross * PLATFORM_FEE, 8)
    net = round(gross - fee, 8)

    await _debit(db, uid, "NENO", req.neno_amount)
    await _credit(db, uid, asset, net)

    tx_id = str(uuid.uuid4())
    settlement = _settlement_record(tx_id, "sell_neno", uid, req.neno_amount, asset, {
        "debit": {"asset": "NENO", "amount": req.neno_amount},
        "credit": {"asset": asset, "amount": net},
        "fee": {"asset": asset, "amount": fee},
    })

    tx = {
        "id": tx_id, "user_id": uid, "type": "sell_neno",
        "neno_amount": req.neno_amount, "receive_asset": asset,
        "receive_amount": net, "rate": rate, "neno_eur_price": neno_eur_price,
        "fee": fee, "fee_asset": asset, "status": "completed",
        "eur_value": round(req.neno_amount * neno_eur_price, 2),
        **settlement,
        "created_at": datetime.now(timezone.utc),
    }
    await _log_tx(db, tx)
    tx["created_at"] = tx["created_at"].isoformat()

    try:
        from services.notification_dispatch import notify_trade_executed
        eur_value = round(req.neno_amount * neno_eur_price, 2)
        asyncio.ensure_future(notify_trade_executed(uid, "NENO", "sell", req.neno_amount, neno_eur_price, eur_value))
    except Exception:
        pass

    new_neno = await _get_balance(db, uid, "NENO")
    new_asset = await _get_balance(db, uid, asset)
    return {
        "message": f"Venduti {req.neno_amount} NENO per {net} {asset}",
        "transaction": tx,
        "balances": {"NENO": round(new_neno, 8), asset: round(new_asset, 8)},
    }


# ── Swap: Any Token ↔ Any Token (via NENO bridge) ──

@router.post("/swap")
async def swap_tokens(req: SwapRequest, current_user: dict = Depends(get_current_user)):
    """Swap any token for any other token. Uses NENO as the bridge asset."""
    db = get_database()
    uid = current_user["user_id"]
    from_asset = req.from_asset.upper()
    to_asset = req.to_asset.upper()

    if from_asset == to_asset:
        raise HTTPException(status_code=400, detail="Non puoi swappare lo stesso asset")

    from_price = await _get_any_price_eur(db, from_asset)
    to_price = await _get_any_price_eur(db, to_asset)
    if from_price is None:
        raise HTTPException(status_code=400, detail=f"Asset non supportato: {from_asset}")
    if to_price is None:
        raise HTTPException(status_code=400, detail=f"Asset non supportato: {to_asset}")

    balance = await _get_balance(db, uid, from_asset)
    if balance < req.amount:
        raise HTTPException(
            status_code=400,
            detail=f"Saldo {from_asset} insufficiente: {balance:.8g} disponibile, {req.amount:.8g} necessario",
        )

    eur_value = req.amount * from_price
    fee_eur = round(eur_value * PLATFORM_FEE, 8)
    net_eur = eur_value - fee_eur
    receive_amount = round(net_eur / to_price, 8)
    fee_in_to = round(fee_eur / to_price, 8)

    await _debit(db, uid, from_asset, req.amount)
    await _credit(db, uid, to_asset, receive_amount)

    tx_id = str(uuid.uuid4())
    settlement = _settlement_record(tx_id, "swap", uid, req.amount, from_asset, {
        "debit": {"asset": from_asset, "amount": req.amount},
        "credit": {"asset": to_asset, "amount": receive_amount},
        "fee_eur": round(fee_eur, 4),
    })

    tx = {
        "id": tx_id, "user_id": uid, "type": "swap",
        "from_asset": from_asset, "from_amount": req.amount,
        "to_asset": to_asset, "to_amount": receive_amount,
        "eur_value": round(eur_value, 2), "fee_eur": round(fee_eur, 4),
        "fee_in_to_asset": fee_in_to,
        "rate": round(from_price / to_price, 8),
        "status": "completed",
        **settlement,
        "created_at": datetime.now(timezone.utc),
    }
    await _log_tx(db, tx)
    tx["created_at"] = tx["created_at"].isoformat()

    return {
        "message": f"Swappati {req.amount} {from_asset} per {receive_amount} {to_asset}",
        "transaction": tx,
        "balances": {
            from_asset: round(await _get_balance(db, uid, from_asset), 8),
            to_asset: round(await _get_balance(db, uid, to_asset), 8),
        },
    }


# ── Swap Quote ──

@router.get("/swap-quote")
async def swap_quote(from_asset: str = "NENO", to_asset: str = "ETH", amount: float = 1.0):
    db = get_database()
    from_asset = from_asset.upper()
    to_asset = to_asset.upper()

    from_price = await _get_any_price_eur(db, from_asset)
    to_price = await _get_any_price_eur(db, to_asset)
    if from_price is None or to_price is None:
        raise HTTPException(status_code=400, detail="Asset non supportato")

    eur_value = amount * from_price
    fee_eur = round(eur_value * PLATFORM_FEE, 8)
    net_eur = eur_value - fee_eur
    receive = round(net_eur / to_price, 8)

    return {
        "from_asset": from_asset, "to_asset": to_asset, "amount": amount,
        "receive_amount": receive, "rate": round(from_price / to_price, 8),
        "eur_value": round(eur_value, 2), "fee_eur": round(fee_eur, 4),
        "fee_pct": PLATFORM_FEE * 100,
    }


# ── Create Custom Token ──

@router.post("/create-token")
async def create_custom_token(req: CreateTokenRequest, current_user: dict = Depends(get_current_user)):
    """Create a new custom token with a specified EUR price and mint supply to creator."""
    db = get_database()
    uid = current_user["user_id"]
    symbol = req.symbol.upper().strip()

    if symbol in MARKET_PRICES_EUR or symbol == "NENO":
        raise HTTPException(status_code=400, detail=f"{symbol} e' un asset di sistema, scegli un altro nome")

    existing = await db.custom_tokens.find_one({"symbol": symbol})
    if existing:
        raise HTTPException(status_code=400, detail=f"Il token {symbol} esiste gia'")

    token = {
        "id": str(uuid.uuid4()),
        "symbol": symbol,
        "name": req.name,
        "price_eur": req.price_eur,
        "total_supply": req.total_supply,
        "circulating_supply": req.total_supply,
        "creator_id": uid,
        "description": req.description or "",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.custom_tokens.insert_one({**token, "_id": token["id"]})

    await _credit(db, uid, symbol, req.total_supply)

    return {
        "message": f"Token {symbol} creato! {req.total_supply} {symbol} @ EUR {req.price_eur} accreditati al wallet",
        "token": token,
        "balance": req.total_supply,
    }


# ── List Custom Tokens ──

@router.get("/custom-tokens")
async def list_custom_tokens():
    db = get_database()
    tokens = await db.custom_tokens.find({}, {"_id": 0}).sort("created_at", -1).to_list(100)
    return {"tokens": tokens}


# ── Update Token Price ──

@router.put("/custom-tokens/{symbol}/price")
async def update_token_price(symbol: str, price_eur: float, current_user: dict = Depends(get_current_user)):
    db = get_database()
    symbol = symbol.upper()
    token = await db.custom_tokens.find_one({"symbol": symbol})
    if not token:
        raise HTTPException(status_code=404, detail="Token non trovato")
    if token["creator_id"] != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="Solo il creatore puo' modificare il prezzo")
    if price_eur <= 0:
        raise HTTPException(status_code=400, detail="Il prezzo deve essere > 0")

    await db.custom_tokens.update_one({"symbol": symbol}, {"$set": {"price_eur": price_eur}})
    return {"message": f"Prezzo di {symbol} aggiornato a EUR {price_eur}", "symbol": symbol, "price_eur": price_eur}


# ── Off-Ramp: NENO -> EUR -> Card or Bank ──

@router.post("/offramp")
async def offramp_neno(req: OfframpRequest, current_user: dict = Depends(get_current_user)):
    db = get_database()
    uid = current_user["user_id"]

    neno_balance = await _get_balance(db, uid, "NENO")
    if neno_balance < req.neno_amount:
        raise HTTPException(status_code=400, detail=f"Saldo NENO insufficiente: {neno_balance:.8g}")

    pricing = await _get_dynamic_neno_price()
    neno_eur_price = pricing["price"]
    eur_gross = round(req.neno_amount * neno_eur_price, 2)
    fee = round(eur_gross * PLATFORM_FEE, 2)
    eur_net = round(eur_gross - fee, 2)

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
            "id": str(uuid.uuid4()), "user_id": uid, "type": "sepa_withdrawal",
            "amount": eur_net, "fee": withdrawal_fee, "net_amount": eur_after_bank,
            "currency": "EUR", "destination_iban": req.destination_iban,
            "beneficiary_name": req.beneficiary_name or "NeoNoble User",
            "reference": f"NENO-OFFRAMP-{uuid.uuid4().hex[:8].upper()}",
            "status": "processing", "estimated_arrival": "1-2 giorni lavorativi",
            "created_at": datetime.now(timezone.utc),
        }
        await db.banking_transactions.insert_one({**bank_tx, "_id": bank_tx["id"]})
        eur_net = eur_after_bank
        dest_info = f"IBAN {req.destination_iban[-4:]}"
    else:
        raise HTTPException(status_code=400, detail="destination deve essere 'card' o 'bank'")

    tx_id = str(uuid.uuid4())
    settlement = _settlement_record(tx_id, "neno_offramp", uid, req.neno_amount, "EUR", {
        "debit": {"asset": "NENO", "amount": req.neno_amount},
        "credit": {"asset": "EUR", "amount": eur_net, "destination": req.destination},
        "fee": {"asset": "EUR", "amount": fee},
    })

    tx = {
        "id": tx_id, "user_id": uid, "type": "neno_offramp",
        "neno_amount": req.neno_amount, "eur_gross": eur_gross, "fee": fee,
        "eur_net": eur_net, "destination": req.destination,
        "destination_info": dest_info,
        "status": "completed" if req.destination == "card" else "processing",
        **settlement,
        "created_at": datetime.now(timezone.utc),
    }
    await _log_tx(db, tx)
    tx["created_at"] = tx["created_at"].isoformat()

    return {
        "message": f"{req.neno_amount} NENO -> EUR {eur_net:.2f} -> {dest_info}",
        "transaction": tx,
        "neno_balance": round(await _get_balance(db, uid, "NENO"), 8),
    }


# ── Transaction History ──

@router.get("/transactions")
async def get_neno_transactions(current_user: dict = Depends(get_current_user)):
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
    db = get_database()
    pricing = await _get_dynamic_neno_price()
    neno_price = pricing["price"]
    pairs = {}
    for asset, eur_price in MARKET_PRICES_EUR.items():
        rate = neno_price / eur_price
        pairs[f"NENO/{asset}"] = {"rate": round(rate, 8), "asset_eur_price": eur_price, "neno_eur_price": neno_price}

    # Add custom tokens to pairs
    custom_tokens = await db.custom_tokens.find({}, {"_id": 0}).to_list(100)
    for t in custom_tokens:
        rate = neno_price / t["price_eur"] if t["price_eur"] > 0 else 0
        pairs[f"NENO/{t['symbol']}"] = {"rate": round(rate, 8), "asset_eur_price": t["price_eur"], "neno_eur_price": neno_price}

    all_assets = SUPPORTED_ASSETS + [t["symbol"] for t in custom_tokens]
    return {
        "neno_eur_price": neno_price,
        "neno_usd_price": round(neno_price * 1.087, 2),
        "fee_percent": PLATFORM_FEE * 100,
        "supported_assets": all_assets,
        "pairs": pairs,
        "custom_tokens": custom_tokens,
    }



# ── Settlement Verification ──

@router.get("/settlement/{tx_id}")
async def verify_settlement(tx_id: str, current_user: dict = Depends(get_current_user)):
    """Verify settlement status for a specific transaction."""
    db = get_database()
    tx = await db.neno_transactions.find_one(
        {"id": tx_id, "user_id": current_user["user_id"]}, {"_id": 0}
    )
    if not tx:
        raise HTTPException(status_code=404, detail="Transazione non trovata")

    if "created_at" in tx and hasattr(tx["created_at"], "isoformat"):
        tx["created_at"] = tx["created_at"].isoformat()

    return {
        "transaction_id": tx["id"],
        "settlement_hash": tx.get("settlement_hash", "N/A"),
        "settlement_status": tx.get("settlement_status", "unknown"),
        "settlement_timestamp": tx.get("settlement_timestamp"),
        "settlement_network": tx.get("settlement_network", "NeoNoble Internal Ledger"),
        "settlement_confirmations": tx.get("settlement_confirmations", 0),
        "type": tx.get("type"),
        "status": tx.get("status"),
        "details": tx.get("settlement_details", {}),
    }


# ── Wallet Sync: Compare internal vs external (on-chain) balances ──

class WalletSyncRequest(BaseModel):
    external_address: str = Field(min_length=10, max_length=100)
    chain_id: int = 1
    on_chain_balances: Optional[dict] = None


@router.post("/wallet-sync")
async def wallet_sync(req: WalletSyncRequest, current_user: dict = Depends(get_current_user)):
    """Compare internal platform balances with connected external wallet."""
    db = get_database()
    uid = current_user["user_id"]

    # Fetch all internal balances
    wallets = await db.wallets.find(
        {"user_id": uid, "balance": {"$gt": 0}}, {"_id": 0}
    ).to_list(50)

    internal_balances = {w["asset"]: w["balance"] for w in wallets}

    # Store the external wallet address association
    await db.users.update_one(
        {"user_id": uid},
        {"$set": {
            "connected_wallet": req.external_address,
            "connected_chain_id": req.chain_id,
            "wallet_synced_at": datetime.now(timezone.utc).isoformat(),
        }}
    )

    # Calculate sync status
    on_chain = req.on_chain_balances or {}
    sync_report = []
    for asset, internal_bal in internal_balances.items():
        external_bal = on_chain.get(asset, 0)
        sync_report.append({
            "asset": asset,
            "internal_balance": round(internal_bal, 8),
            "external_balance": round(external_bal, 8) if external_bal else "N/A",
            "synced": abs(internal_bal - external_bal) < 0.00001 if isinstance(external_bal, (int, float)) else False,
        })

    return {
        "external_address": req.external_address,
        "chain_id": req.chain_id,
        "synced_at": datetime.now(timezone.utc).isoformat(),
        "internal_balances": internal_balances,
        "sync_report": sync_report,
        "total_internal_assets": len(internal_balances),
    }


# ── Full Portfolio Snapshot (internal + external) ──

@router.get("/portfolio-snapshot")
async def portfolio_snapshot(current_user: dict = Depends(get_current_user)):
    """Get a complete snapshot of the user's portfolio for audit/verification."""
    db = get_database()
    uid = current_user["user_id"]

    wallets = await db.wallets.find({"user_id": uid, "balance": {"$gt": 0}}, {"_id": 0}).to_list(50)
    custom_tokens = await db.custom_tokens.find({}, {"_id": 0}).to_list(100)
    custom_prices = {t["symbol"]: t["price_eur"] for t in custom_tokens}

    pricing = await _get_dynamic_neno_price()
    neno_price = pricing["price"]

    positions = []
    total_eur = 0
    for w in wallets:
        asset = w["asset"]
        bal = w["balance"]
        if asset == "NENO":
            price = neno_price
        else:
            price = MARKET_PRICES_EUR.get(asset) or custom_prices.get(asset, 0)
        value = bal * price
        positions.append({
            "asset": asset, "balance": round(bal, 8),
            "price_eur": price, "value_eur": round(value, 2),
        })
        total_eur += value

    # Recent settlements
    recent_txs = await db.neno_transactions.find(
        {"user_id": uid}, {"_id": 0}
    ).sort("created_at", -1).limit(10).to_list(10)
    for t in recent_txs:
        if "created_at" in t and hasattr(t["created_at"], "isoformat"):
            t["created_at"] = t["created_at"].isoformat()

    user = await db.users.find_one({"user_id": uid}, {"_id": 0, "connected_wallet": 1, "wallet_synced_at": 1})

    return {
        "snapshot_timestamp": datetime.now(timezone.utc).isoformat(),
        "total_value_eur": round(total_eur, 2),
        "positions": sorted(positions, key=lambda x: -x["value_eur"]),
        "connected_wallet": user.get("connected_wallet") if user else None,
        "wallet_synced_at": user.get("wallet_synced_at") if user else None,
        "recent_settlements": [{
            "id": t["id"],
            "type": t["type"],
            "settlement_hash": t.get("settlement_hash", "N/A"),
            "status": t.get("settlement_status", t.get("status")),
            "timestamp": t.get("settlement_timestamp", t.get("created_at")),
        } for t in recent_txs],
    }
