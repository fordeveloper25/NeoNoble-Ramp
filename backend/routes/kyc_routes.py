"""
KYC/AML Compliance Layer — NeoNoble Ramp.

Tiers:
  - Tier 0: Unverified (no trading, view only)
  - Tier 1: Email verified, basic info (trade up to EUR 1,000/day)
  - Tier 2: ID verified (trade up to EUR 50,000/day)
  - Tier 3: Enhanced due diligence (unlimited)

AML Rules:
  - Transaction monitoring with threshold alerts
  - Suspicious activity detection (velocity, amount, pattern)
  - Automatic hold for review above thresholds
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timezone, timedelta
import uuid

from database.mongodb import get_database
from routes.auth import get_current_user


def admin_required(current_user: dict = Depends(get_current_user)):
    if current_user.get("role") != "ADMIN":
        raise HTTPException(status_code=403, detail="Accesso admin richiesto")
    return current_user

router = APIRouter(prefix="/kyc", tags=["KYC / AML Compliance"])

# ── KYC Tier limits (EUR/day) ──
TIER_LIMITS = {
    0: {"daily_limit": 0, "label": "Non Verificato", "can_trade": False, "can_withdraw": False},
    1: {"daily_limit": 1_000, "label": "Base", "can_trade": True, "can_withdraw": False},
    2: {"daily_limit": 50_000, "label": "Verificato", "can_trade": True, "can_withdraw": True},
    3: {"daily_limit": float("inf"), "label": "Premium", "can_trade": True, "can_withdraw": True},
}

# AML thresholds
AML_SINGLE_TX_ALERT = 10_000  # Single transaction alert threshold EUR
AML_DAILY_VELOCITY = 25_000   # Daily velocity alert EUR
AML_STRUCTURING_WINDOW = 3600  # 1 hour window for structuring detection
AML_STRUCTURING_COUNT = 5      # Transactions within window triggering alert


# ── Models ──

class KYCSubmission(BaseModel):
    first_name: str
    last_name: str
    date_of_birth: str
    nationality: str
    address_line1: str
    address_city: str
    address_country: str
    address_postal: str
    tax_id: Optional[str] = None
    document_type: str = Field(description="passport, id_card, drivers_license")
    document_number: str


class KYCReviewAction(BaseModel):
    user_id: str
    action: str = Field(description="approve, reject, request_info")
    new_tier: Optional[int] = None
    reason: Optional[str] = None


class AMLAlertAction(BaseModel):
    alert_id: str
    action: str = Field(description="dismiss, escalate, block_user")
    notes: Optional[str] = None


class DocumentVerifyRequest(BaseModel):
    image_base64: str
    mime_type: str = "image/jpeg"


# ── Endpoints ──

@router.get("/status")
async def get_kyc_status(current_user: dict = Depends(get_current_user)):
    """Get current KYC status for the authenticated user."""
    db = get_database()
    kyc = await db.kyc_profiles.find_one({"user_id": current_user["user_id"]}, {"_id": 0})

    if not kyc:
        tier = 0
        kyc = {
            "user_id": current_user["user_id"],
            "tier": 0,
            "status": "not_started",
            "submitted_at": None,
            "reviewed_at": None,
        }
    else:
        tier = kyc.get("tier", 0)

    tier_info = TIER_LIMITS.get(tier, TIER_LIMITS[0])

    # Get 24h volume
    now = datetime.now(timezone.utc)
    day_ago = now - timedelta(hours=24)
    pipeline = [
        {"$match": {"user_id": current_user["user_id"], "created_at": {"$gte": day_ago.isoformat()}}},
        {"$group": {"_id": None, "total": {"$sum": "$eur_value"}}},
    ]
    agg = await db.kyc_tx_log.aggregate(pipeline).to_list(1)
    daily_volume = agg[0]["total"] if agg else 0

    return {
        "tier": tier,
        "tier_label": tier_info["label"],
        "status": kyc.get("status", "not_started"),
        "daily_limit": tier_info["daily_limit"] if tier_info["daily_limit"] != float("inf") else -1,
        "daily_used": round(daily_volume, 2),
        "can_trade": tier_info["can_trade"],
        "can_withdraw": tier_info["can_withdraw"],
        "submitted_at": kyc.get("submitted_at"),
        "reviewed_at": kyc.get("reviewed_at"),
        "rejection_reason": kyc.get("rejection_reason"),
    }


@router.post("/submit")
async def submit_kyc(data: KYCSubmission, current_user: dict = Depends(get_current_user)):
    """Submit KYC documents for verification."""
    db = get_database()
    existing = await db.kyc_profiles.find_one({"user_id": current_user["user_id"]})

    if existing and existing.get("status") == "pending":
        raise HTTPException(status_code=400, detail="Una richiesta KYC è già in attesa di revisione")

    now = datetime.now(timezone.utc).isoformat()
    profile = {
        "user_id": current_user["user_id"],
        "email": current_user.get("email", ""),
        "first_name": data.first_name,
        "last_name": data.last_name,
        "date_of_birth": data.date_of_birth,
        "nationality": data.nationality,
        "address": {
            "line1": data.address_line1,
            "city": data.address_city,
            "country": data.address_country,
            "postal": data.address_postal,
        },
        "tax_id": data.tax_id,
        "document": {
            "type": data.document_type,
            "number": data.document_number,
        },
        "tier": existing.get("tier", 0) if existing else 0,
        "status": "pending",
        "submitted_at": now,
        "reviewed_at": None,
        "rejection_reason": None,
    }

    await db.kyc_profiles.update_one(
        {"user_id": current_user["user_id"]},
        {"$set": profile},
        upsert=True,
    )

    return {"message": "Richiesta KYC inviata con successo", "status": "pending"}


@router.post("/verify-document")
async def verify_document(data: DocumentVerifyRequest, current_user: dict = Depends(get_current_user)):
    """AI-powered document verification using GPT Image OCR."""
    from services.kyc_verification_service import verify_document_with_ai

    db = get_database()
    kyc = await db.kyc_profiles.find_one({"user_id": current_user["user_id"]}, {"_id": 0})

    if not kyc:
        raise HTTPException(status_code=400, detail="Invia prima i dati KYC, poi carica il documento")

    submitted_data = {
        "user_id": current_user["user_id"],
        "first_name": kyc.get("first_name", ""),
        "last_name": kyc.get("last_name", ""),
        "date_of_birth": kyc.get("date_of_birth", ""),
        "document_number": kyc.get("document", {}).get("number", ""),
        "nationality": kyc.get("nationality", ""),
        "document_type": kyc.get("document", {}).get("type", ""),
    }

    result = await verify_document_with_ai(
        image_base64=data.image_base64,
        submitted_data=submitted_data,
        mime_type=data.mime_type,
    )

    now = datetime.now(timezone.utc).isoformat()
    await db.kyc_profiles.update_one(
        {"user_id": current_user["user_id"]},
        {"$set": {
            "ai_verification": result,
            "ai_verified_at": now,
            "status": "ai_verified" if result.get("verified") else "pending",
        }},
    )

    # Auto-approve to Tier 1 if AI verification passes
    if result.get("verified") and result.get("recommendation") == "approve":
        current_tier = kyc.get("tier", 0)
        if current_tier < 1:
            new_tier = 1
            await db.kyc_profiles.update_one(
                {"user_id": current_user["user_id"]},
                {"$set": {"tier": new_tier, "status": "approved", "reviewed_at": now}},
            )
            await db.users.update_one({"id": current_user["user_id"]}, {"$set": {"kyc_tier": new_tier}})
            result["auto_approved"] = True
            result["new_tier"] = new_tier

    return {
        "message": "Verifica documento completata" if result.get("verified") else "Documento richiede revisione manuale",
        "verification": result,
    }


@router.post("/ocr-extract")
async def ocr_extract_document(data: DocumentVerifyRequest, current_user: dict = Depends(get_current_user)):
    """Extract data from an ID document using AI OCR (pre-fill helper)."""
    from services.kyc_verification_service import extract_document_data

    result = await extract_document_data(
        image_base64=data.image_base64,
        mime_type=data.mime_type,
    )

    return result




@router.get("/admin/pending")
async def list_pending_kyc(current_user: dict = Depends(admin_required)):
    """Admin: list all pending KYC applications."""
    db = get_database()
    pending = await db.kyc_profiles.find({"status": "pending"}, {"_id": 0}).sort("submitted_at", -1).to_list(100)
    return {"pending": pending, "total": len(pending)}


@router.post("/admin/review")
async def review_kyc(data: KYCReviewAction, current_user: dict = Depends(admin_required)):
    """Admin: approve or reject a KYC application."""
    db = get_database()
    profile = await db.kyc_profiles.find_one({"user_id": data.user_id})
    if not profile:
        raise HTTPException(status_code=404, detail="Profilo KYC non trovato")

    now = datetime.now(timezone.utc).isoformat()
    update = {"reviewed_at": now, "reviewed_by": current_user["user_id"]}

    if data.action == "approve":
        new_tier = data.new_tier if data.new_tier is not None else min(profile.get("tier", 0) + 1, 3)
        update["status"] = "approved"
        update["tier"] = new_tier
        # Also update user record
        await db.users.update_one({"id": data.user_id}, {"$set": {"kyc_tier": new_tier}})
    elif data.action == "reject":
        update["status"] = "rejected"
        update["rejection_reason"] = data.reason or "Non conforme ai requisiti"
    elif data.action == "request_info":
        update["status"] = "info_requested"
        update["rejection_reason"] = data.reason or "Informazioni aggiuntive richieste"
    else:
        raise HTTPException(status_code=400, detail="Azione non valida")

    await db.kyc_profiles.update_one({"user_id": data.user_id}, {"$set": update})

    return {"message": f"KYC {data.action} per utente {data.user_id}", "new_status": update["status"]}


# ── AML Monitoring ──

@router.get("/aml/alerts")
async def get_aml_alerts(current_user: dict = Depends(admin_required), status: str = "open"):
    """Admin: get AML alerts."""
    db = get_database()
    query = {} if status == "all" else {"status": status}
    alerts = await db.aml_alerts.find(query, {"_id": 0}).sort("created_at", -1).to_list(200)
    return {"alerts": alerts, "total": len(alerts)}


@router.post("/aml/review")
async def review_aml_alert(data: AMLAlertAction, current_user: dict = Depends(admin_required)):
    """Admin: review an AML alert."""
    db = get_database()
    alert = await db.aml_alerts.find_one({"id": data.alert_id})
    if not alert:
        raise HTTPException(status_code=404, detail="Alert non trovato")

    now = datetime.now(timezone.utc).isoformat()
    update = {"reviewed_at": now, "reviewed_by": current_user["user_id"], "notes": data.notes or ""}

    if data.action == "dismiss":
        update["status"] = "dismissed"
    elif data.action == "escalate":
        update["status"] = "escalated"
    elif data.action == "block_user":
        update["status"] = "blocked"
        await db.users.update_one({"id": alert["user_id"]}, {"$set": {"blocked": True, "blocked_reason": "AML violation"}})
    else:
        raise HTTPException(status_code=400, detail="Azione non valida")

    await db.aml_alerts.update_one({"id": data.alert_id}, {"$set": update})
    return {"message": f"Alert {data.alert_id} -> {update['status']}"}


@router.get("/aml/stats")
async def aml_statistics(current_user: dict = Depends(admin_required)):
    """Admin: AML dashboard statistics."""
    db = get_database()
    open_count = await db.aml_alerts.count_documents({"status": "open"})
    escalated = await db.aml_alerts.count_documents({"status": "escalated"})
    blocked = await db.users.count_documents({"blocked": True})
    total = await db.aml_alerts.count_documents({})

    return {
        "open_alerts": open_count,
        "escalated": escalated,
        "blocked_users": blocked,
        "total_alerts": total,
    }


# ── AML Check utility (to be called from trading/exchange routes) ──

async def check_aml_compliance(user_id: str, eur_value: float, tx_type: str = "trade") -> dict:
    """
    Check if a transaction passes AML rules. Returns {allowed: bool, reason: str}.
    Should be called before executing trades, withdrawals, conversions.
    """
    db = get_database()
    now = datetime.now(timezone.utc)

    # Check KYC tier limits
    kyc = await db.kyc_profiles.find_one({"user_id": user_id})
    tier = kyc.get("tier", 0) if kyc else 0
    tier_info = TIER_LIMITS.get(tier, TIER_LIMITS[0])

    if not tier_info["can_trade"] and tx_type == "trade":
        return {"allowed": False, "reason": "KYC non completato. Completa la verifica per operare."}

    if not tier_info["can_withdraw"] and tx_type == "withdraw":
        return {"allowed": False, "reason": "Livello KYC insufficiente per prelievi. Richiesto Tier 2+."}

    # Check daily limit
    day_ago = now - timedelta(hours=24)
    pipeline = [
        {"$match": {"user_id": user_id, "created_at": {"$gte": day_ago.isoformat()}}},
        {"$group": {"_id": None, "total": {"$sum": "$eur_value"}}},
    ]
    agg = await db.kyc_tx_log.aggregate(pipeline).to_list(1)
    daily_total = (agg[0]["total"] if agg else 0) + eur_value

    if tier_info["daily_limit"] != float("inf") and daily_total > tier_info["daily_limit"]:
        return {"allowed": False, "reason": f"Limite giornaliero superato ({tier_info['daily_limit']} EUR). Upgrade KYC per aumentare il limite."}

    # Log transaction for velocity tracking
    await db.kyc_tx_log.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "eur_value": eur_value,
        "tx_type": tx_type,
        "created_at": now.isoformat(),
    })

    # AML alert generation
    alerts = []

    # Single transaction threshold
    if eur_value >= AML_SINGLE_TX_ALERT:
        alerts.append({
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "type": "large_transaction",
            "description": f"Transazione singola di EUR {eur_value:,.2f} supera la soglia di {AML_SINGLE_TX_ALERT:,}",
            "eur_value": eur_value,
            "tx_type": tx_type,
            "status": "open",
            "severity": "high",
            "created_at": now.isoformat(),
        })

    # Daily velocity alert
    if daily_total >= AML_DAILY_VELOCITY:
        alerts.append({
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "type": "high_velocity",
            "description": f"Volume giornaliero di EUR {daily_total:,.2f} supera {AML_DAILY_VELOCITY:,}",
            "eur_value": daily_total,
            "tx_type": tx_type,
            "status": "open",
            "severity": "medium",
            "created_at": now.isoformat(),
        })

    # Structuring detection (many small transactions)
    window_start = now - timedelta(seconds=AML_STRUCTURING_WINDOW)
    recent_count = await db.kyc_tx_log.count_documents({
        "user_id": user_id,
        "created_at": {"$gte": window_start.isoformat()},
    })
    if recent_count >= AML_STRUCTURING_COUNT:
        alerts.append({
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "type": "structuring",
            "description": f"Possibile structuring: {recent_count} transazioni in {AML_STRUCTURING_WINDOW // 60} minuti",
            "eur_value": eur_value,
            "tx_type": tx_type,
            "status": "open",
            "severity": "high",
            "created_at": now.isoformat(),
        })

    if alerts:
        await db.aml_alerts.insert_many(alerts)

    return {"allowed": True, "reason": "OK", "alerts_generated": len(alerts)}
