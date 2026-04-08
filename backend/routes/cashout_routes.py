"""
Cashout API Routes — NeoNoble Ramp.

Endpoints for monitoring and controlling the autonomous cashout engine:
- Cashout status and metrics
- Cashout history
- EUR account management
- Conversion opportunities
- Manual trigger / stop
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Optional

from routes.auth import get_current_user
from services.cashout_engine import CashoutEngine, EUR_ACCOUNTS
from services.auto_conversion_engine import AutoConversionEngine

router = APIRouter(prefix="/cashout", tags=["Cashout Engine"])


# ── ENGINE STATUS ──

@router.get("/status")
async def cashout_status(current_user: dict = Depends(get_current_user)):
    """Full cashout engine status with metrics, accounts, and recent operations."""
    engine = CashoutEngine.get_instance()
    return await engine.get_status()


@router.get("/history")
async def cashout_history(
    limit: int = 100,
    current_user: dict = Depends(get_current_user),
):
    """Cashout operation history."""
    engine = CashoutEngine.get_instance()
    history = await engine.get_cashout_history(limit)
    return {"cashouts": history, "count": len(history)}


# ── ENGINE CONTROL ──

@router.post("/start")
async def start_cashout(current_user: dict = Depends(get_current_user)):
    """Start the autonomous cashout engine (admin only)."""
    if current_user.get("role") != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin only")
    engine = CashoutEngine.get_instance()
    await engine.start()
    return {"status": "started", "message": "Cashout engine avviato"}


@router.post("/stop")
async def stop_cashout(current_user: dict = Depends(get_current_user)):
    """Stop the autonomous cashout engine (admin only)."""
    if current_user.get("role") != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin only")
    engine = CashoutEngine.get_instance()
    await engine.stop()
    return {"status": "stopped", "message": "Cashout engine fermato"}


# ── EUR ACCOUNTS ──

@router.get("/eur-accounts")
async def get_eur_accounts(current_user: dict = Depends(get_current_user)):
    """Get configured EUR payout accounts (SEPA/SWIFT destinations)."""
    return {
        "accounts": EUR_ACCOUNTS,
        "routing_rules": {
            "sepa_instant": "< 5,000 EUR",
            "sepa_standard": "5,000 — 100,000 EUR",
            "swift": "> 100,000 EUR (batch, uses BE account)",
        },
    }


# ── CONVERSION ──

@router.get("/conversions/opportunities")
async def conversion_opportunities(current_user: dict = Depends(get_current_user)):
    """Evaluate current crypto → USDC conversion opportunities."""
    from services.execution_engine import ExecutionEngine
    engine = ExecutionEngine.get_instance()
    hot_wallet = await engine.get_hot_wallet_status()

    converter = AutoConversionEngine.get_instance()
    opps = await converter.evaluate_conversions(hot_wallet)

    return {
        "hot_wallet": hot_wallet,
        "opportunities": opps,
        "count": len(opps),
    }


@router.get("/conversions/history")
async def conversion_history(
    limit: int = 50,
    current_user: dict = Depends(get_current_user),
):
    """Conversion history log."""
    converter = AutoConversionEngine.get_instance()
    history = await converter.get_conversion_history(limit)
    return {"conversions": history, "count": len(history)}


@router.get("/conversions/summary")
async def conversion_summary(current_user: dict = Depends(get_current_user)):
    """Conversion summary by pair."""
    converter = AutoConversionEngine.get_instance()
    return await converter.get_summary()


# ── COMPREHENSIVE REPORT ──

@router.get("/report")
async def comprehensive_report(current_user: dict = Depends(get_current_user)):
    """
    Full cashout report: engine status + wallet balances + conversions + EUR accounts.
    Single endpoint for complete visibility.
    """
    from services.circle_wallet_service import CircleWalletService, WalletRole
    from services.execution_engine import ExecutionEngine

    cashout = CashoutEngine.get_instance()
    circle = CircleWalletService.get_instance()
    exec_engine = ExecutionEngine.get_instance()
    converter = AutoConversionEngine.get_instance()

    # Parallel data collection
    status = await cashout.get_status()
    usdc_balances = await circle.get_all_wallet_balances("BSC")
    hot_wallet = await exec_engine.get_hot_wallet_status()
    opportunities = await converter.evaluate_conversions(hot_wallet)
    conv_summary = await converter.get_summary()

    return {
        "engine": {
            "running": status["running"],
            "cycles": status["cycle_count"],
            "interval": status["interval_seconds"],
        },
        "extracted": status["cumulative"],
        "usdc_wallets": {
            role: usdc_balances["wallets"].get(role, {}).get("balance", 0)
            for role in [WalletRole.CLIENT, WalletRole.TREASURY, WalletRole.REVENUE]
        },
        "usdc_total": usdc_balances.get("total_usdc", 0),
        "hot_wallet": {
            "bnb": hot_wallet.get("bnb_balance", 0),
            "neno": hot_wallet.get("neno_balance", 0),
            "available": hot_wallet.get("available", False),
        },
        "conversion_opportunities": len(opportunities),
        "conversions": conv_summary,
        "eur_accounts": EUR_ACCOUNTS,
        "by_type": status.get("by_type", {}),
        "recent_cashouts": status.get("recent_cashouts", [])[:5],
        "timestamp": __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc
        ).isoformat(),
    }
