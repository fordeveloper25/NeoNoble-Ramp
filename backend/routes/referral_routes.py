"""
Referral System — NeoNoble Ramp.

Allows users to generate referral codes, invite friends,
and earn NENO bonuses when referred users complete actions.

Bonuses:
- Referrer: 0.001 NENO per successful referral (KYC completed)
- Referred: 0.0005 NENO welcome bonus
- Tier bonus: Extra 0.0005 NENO when referred user makes first trade
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timezone
import uuid
import secrets
import string

from database.mongodb import get_database
from routes.auth import get_current_user

router = APIRouter(prefix="/referral", tags=["Referral System"])

REFERRER_BONUS_NENO = 0.001
REFERRED_BONUS_NENO = 0.0005
TRADE_BONUS_NENO = 0.0005


def _generate_code(length=8):
    chars = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(chars) for _ in range(length))


class ApplyReferralRequest(BaseModel):
    code: str = Field(description="Referral code to apply")


# ── Endpoints ──

@router.get("/code")
async def get_or_create_referral_code(current_user: dict = Depends(get_current_user)):
    """Get or create the user's referral code."""
    db = get_database()
    uid = current_user["user_id"]

    ref = await db.referral_codes.find_one({"user_id": uid}, {"_id": 0})
    if ref:
        return ref

    code = _generate_code()
    while await db.referral_codes.find_one({"code": code}):
        code = _generate_code()

    doc = {
        "id": str(uuid.uuid4()),
        "user_id": uid,
        "code": code,
        "total_referrals": 0,
        "total_bonus_earned": 0.0,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.referral_codes.insert_one(doc)
    doc.pop("_id", None)
    return doc


@router.post("/apply")
async def apply_referral_code(req: ApplyReferralRequest, current_user: dict = Depends(get_current_user)):
    """Apply a referral code (one-time per user)."""
    db = get_database()
    uid = current_user["user_id"]

    existing = await db.referral_links.find_one({"referred_user_id": uid})
    if existing:
        raise HTTPException(400, "Hai gia utilizzato un codice referral")

    ref_code = await db.referral_codes.find_one({"code": req.code.upper()})
    if not ref_code:
        raise HTTPException(404, "Codice referral non valido")

    if ref_code["user_id"] == uid:
        raise HTTPException(400, "Non puoi usare il tuo stesso codice")

    link_doc = {
        "id": str(uuid.uuid4()),
        "referrer_user_id": ref_code["user_id"],
        "referred_user_id": uid,
        "code": req.code.upper(),
        "status": "pending",
        "referrer_bonus_paid": False,
        "referred_bonus_paid": False,
        "trade_bonus_paid": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.referral_links.insert_one(link_doc)

    # Credit welcome bonus to referred user
    await _credit_neno(db, uid, REFERRED_BONUS_NENO, "referral_welcome_bonus")
    await db.referral_links.update_one(
        {"id": link_doc["id"]},
        {"$set": {"referred_bonus_paid": True, "status": "active"}},
    )

    # Credit referrer bonus
    await _credit_neno(db, ref_code["user_id"], REFERRER_BONUS_NENO, "referral_bonus")
    await db.referral_links.update_one(
        {"id": link_doc["id"]},
        {"$set": {"referrer_bonus_paid": True}},
    )
    await db.referral_codes.update_one(
        {"code": req.code.upper()},
        {"$inc": {"total_referrals": 1, "total_bonus_earned": REFERRER_BONUS_NENO}},
    )

    return {
        "message": f"Codice referral applicato! Hai ricevuto {REFERRED_BONUS_NENO} NENO di bonus",
        "bonus_neno": REFERRED_BONUS_NENO,
    }


@router.get("/stats")
async def get_referral_stats(current_user: dict = Depends(get_current_user)):
    """Get referral statistics for the current user."""
    db = get_database()
    uid = current_user["user_id"]

    code_doc = await db.referral_codes.find_one({"user_id": uid}, {"_id": 0})
    referrals = await db.referral_links.find(
        {"referrer_user_id": uid}, {"_id": 0}
    ).to_list(100)

    referred_by = await db.referral_links.find_one(
        {"referred_user_id": uid}, {"_id": 0}
    )

    return {
        "my_code": code_doc.get("code") if code_doc else None,
        "total_referrals": code_doc.get("total_referrals", 0) if code_doc else 0,
        "total_bonus_earned": code_doc.get("total_bonus_earned", 0) if code_doc else 0,
        "referrals": referrals,
        "referred_by": referred_by.get("referrer_user_id") if referred_by else None,
        "referral_bonus": REFERRER_BONUS_NENO,
        "welcome_bonus": REFERRED_BONUS_NENO,
        "trade_bonus": TRADE_BONUS_NENO,
    }


@router.get("/leaderboard")
async def referral_leaderboard():
    """Public leaderboard of top referrers."""
    db = get_database()
    pipeline = [
        {"$match": {"total_referrals": {"$gt": 0}}},
        {"$sort": {"total_referrals": -1}},
        {"$limit": 20},
        {"$lookup": {
            "from": "users",
            "localField": "user_id",
            "foreignField": "id",
            "as": "user_info",
        }},
        {"$project": {
            "_id": 0,
            "code": 1,
            "total_referrals": 1,
            "total_bonus_earned": 1,
            "username": {"$arrayElemAt": [
                {"$map": {
                    "input": "$user_info",
                    "as": "u",
                    "in": {"$concat": [
                        {"$substrCP": ["$$u.email", 0, 3]},
                        "***"
                    ]}
                }}, 0
            ]},
        }},
    ]
    leaders = await db.referral_codes.aggregate(pipeline).to_list(20)
    return {"leaderboard": leaders}


async def check_trade_bonus(user_id: str):
    """Called after a user's first trade to grant trade bonus to referrer."""
    db = get_database()
    link = await db.referral_links.find_one({
        "referred_user_id": user_id,
        "trade_bonus_paid": False,
    })
    if not link:
        return

    await _credit_neno(db, link["referrer_user_id"], TRADE_BONUS_NENO, "referral_trade_bonus")
    await db.referral_links.update_one(
        {"id": link["id"]},
        {"$set": {"trade_bonus_paid": True}},
    )
    await db.referral_codes.update_one(
        {"code": link["code"]},
        {"$inc": {"total_bonus_earned": TRADE_BONUS_NENO}},
    )


async def _credit_neno(db, user_id: str, amount: float, reason: str):
    """Credit NENO to user wallet."""
    wallet = await db.wallets.find_one({"user_id": user_id, "asset": "NENO"})
    if wallet:
        await db.wallets.update_one(
            {"user_id": user_id, "asset": "NENO"},
            {"$inc": {"balance": amount}},
        )
    else:
        await db.wallets.insert_one({
            "user_id": user_id,
            "asset": "NENO",
            "balance": amount,
            "locked": 0,
            "chain": "BSC",
        })

    await db.referral_bonus_log.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "amount": amount,
        "reason": reason,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
