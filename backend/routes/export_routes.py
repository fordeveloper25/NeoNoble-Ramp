"""
Data Export Routes — CSV/PDF export for portfolio and trade data.

Provides:
- Export trade history as CSV
- Export portfolio snapshot as CSV
- Export margin positions as CSV
"""

from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import StreamingResponse
from datetime import datetime, timezone, timedelta
from typing import Optional
import io
import csv

from database.mongodb import get_database
from routes.auth import get_current_user

router = APIRouter(prefix="/export", tags=["Export"])


@router.get("/trades/csv")
async def export_trades_csv(
    days: int = Query(90, ge=1, le=365),
    current_user: dict = Depends(get_current_user),
):
    """Export user's trade history as CSV."""
    db = get_database()
    uid = current_user["user_id"]
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Data", "Tipo", "Asset", "Quantita", "Prezzo", "Valore EUR", "Fee", "Stato"])

    # NENO transactions
    async for tx in db.neno_transactions.find(
        {"user_id": uid, "created_at": {"$gte": cutoff}}, {"_id": 0}
    ).sort("created_at", -1):
        ts = tx.get("created_at", "")
        if hasattr(ts, "isoformat"):
            ts = ts.isoformat()
        writer.writerow([
            ts, tx.get("type", ""),
            tx.get("pay_asset", tx.get("receive_asset", "NENO")),
            tx.get("neno_amount", ""),
            tx.get("neno_eur_price", tx.get("rate", "")),
            tx.get("pay_amount", tx.get("receive_amount", "")),
            tx.get("fee", ""),
            tx.get("status", ""),
        ])

    # Trading engine orders
    async for order in db.orders.find(
        {"user_id": uid}, {"_id": 0}
    ).sort("created_at", -1).limit(500):
        ts = order.get("created_at", "")
        if hasattr(ts, "isoformat"):
            ts = ts.isoformat()
        writer.writerow([
            ts, order.get("side", ""),
            order.get("pair_id", ""),
            order.get("amount", order.get("quantity", "")),
            order.get("price", ""),
            order.get("total", ""),
            order.get("fee", ""),
            order.get("status", ""),
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=trades_{days}d.csv"},
    )


@router.get("/portfolio/csv")
async def export_portfolio_csv(
    current_user: dict = Depends(get_current_user),
):
    """Export user's current portfolio as CSV."""
    db = get_database()
    uid = current_user["user_id"]

    wallets = await db.wallets.find({"user_id": uid, "balance": {"$gt": 0}}, {"_id": 0}).to_list(100)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Asset", "Saldo", "Valore Stimato EUR"])

    # Market reference prices
    prices = {
        "BTC": 60787.0, "ETH": 1769.0, "BNB": 555.36, "USDT": 0.92,
        "USDC": 0.92, "MATIC": 0.55, "SOL": 74.72, "NENO": 10000.0,
        "EUR": 1.0, "USD": 0.92, "XRP": 1.21, "ADA": 0.38, "DOGE": 0.082,
    }

    total_eur = 0
    for w in wallets:
        asset = w.get("asset", "")
        balance = w.get("balance", 0)
        eur_price = prices.get(asset, 0)
        eur_value = round(balance * eur_price, 2)
        total_eur += eur_value
        writer.writerow([asset, round(balance, 8), eur_value])

    writer.writerow([])
    writer.writerow(["TOTALE", "", round(total_eur, 2)])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=portfolio.csv"},
    )


@router.get("/margin/csv")
async def export_margin_csv(
    current_user: dict = Depends(get_current_user),
):
    """Export user's margin positions as CSV."""
    db = get_database()
    uid = current_user["user_id"]

    positions = await db.margin_positions.find({"user_id": uid}, {"_id": 0}).sort("opened_at", -1).to_list(200)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Data Apertura", "Coppia", "Direzione", "Leva", "Prezzo Entrata", "Margine", "PnL", "Stato"])

    for p in positions:
        ts = p.get("opened_at", p.get("created_at", ""))
        if hasattr(ts, "isoformat"):
            ts = ts.isoformat()
        writer.writerow([
            ts, p.get("pair_id", ""),
            p.get("side", ""), p.get("leverage", ""),
            p.get("entry_price", ""), p.get("margin_amount", ""),
            p.get("realized_pnl", p.get("unrealized_pnl", "")),
            p.get("status", ""),
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=margin_positions.csv"},
    )
