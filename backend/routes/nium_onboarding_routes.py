"""
NIUM Customer Onboarding Routes.

Automated customer creation and hash management:
- Auto-create NIUM customer on KYC approval
- Link customer_hash to user profile
- Retrieve NIUM customer info
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timezone
import httpx
import os
import uuid
import logging

from database.mongodb import get_database
from routes.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/nium-onboarding", tags=["NIUM Onboarding"])

NIUM_API_KEY = os.environ.get("NIUM_API_KEY", "")
NIUM_BASE_URL = os.environ.get("NIUM_API_BASE", "https://api.nium.com")
NIUM_CLIENT_HASH = os.environ.get("NIUM_CLIENT_HASH_ID", "")


class OnboardCustomerRequest(BaseModel):
    first_name: str
    last_name: str
    email: str
    country_code: str = Field(default="IT", description="ISO 2-letter country code")
    nationality: str = Field(default="IT")


async def _nium_headers() -> dict:
    return {
        "x-api-key": NIUM_API_KEY,
        "Content-Type": "application/json",
    }


@router.post("/create-customer")
async def create_nium_customer(
    req: OnboardCustomerRequest,
    current_user: dict = Depends(get_current_user),
):
    """Create a NIUM customer and link to user profile."""
    db = get_database()
    uid = current_user["user_id"]

    # Check if already onboarded
    user = await db.users.find_one({"id": uid}, {"_id": 0})
    if user and user.get("nium_customer_hash"):
        return {
            "message": "Cliente NIUM gia presente",
            "customer_hash": user["nium_customer_hash"],
            "status": "existing",
        }

    if not NIUM_API_KEY:
        # Simulated mode
        sim_hash = f"sim_{uuid.uuid4().hex[:12]}"
        await db.users.update_one(
            {"id": uid},
            {"$set": {
                "nium_customer_hash": sim_hash,
                "nium_onboarded_at": datetime.now(timezone.utc).isoformat(),
                "nium_mode": "simulated",
            }},
        )
        return {
            "message": "Cliente NIUM creato (simulato)",
            "customer_hash": sim_hash,
            "status": "simulated",
        }

    # Real NIUM API call
    try:
        payload = {
            "email": req.email,
            "firstName": req.first_name,
            "lastName": req.last_name,
            "countryCode": req.country_code,
            "nationality": req.nationality,
            "customerType": "individual",
        }

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{NIUM_BASE_URL}/api/v1/client/{NIUM_CLIENT_HASH}/customer",
                json=payload,
                headers=await _nium_headers(),
            )

            if resp.status_code in (200, 201):
                data = resp.json()
                customer_hash = data.get("customerHashId", data.get("customer_hash_id", ""))

                await db.users.update_one(
                    {"id": uid},
                    {"$set": {
                        "nium_customer_hash": customer_hash,
                        "nium_onboarded_at": datetime.now(timezone.utc).isoformat(),
                        "nium_mode": "live",
                        "nium_data": {
                            "first_name": req.first_name,
                            "last_name": req.last_name,
                            "country": req.country_code,
                        },
                    }},
                )
                logger.info(f"[NIUM] Customer created: {customer_hash} for user {uid}")
                return {
                    "message": "Cliente NIUM creato con successo",
                    "customer_hash": customer_hash,
                    "status": "live",
                }
            else:
                logger.error(f"[NIUM] Customer creation failed: {resp.status_code} {resp.text}")
                # Fallback to simulated
                sim_hash = f"sim_{uuid.uuid4().hex[:12]}"
                await db.users.update_one(
                    {"id": uid},
                    {"$set": {
                        "nium_customer_hash": sim_hash,
                        "nium_onboarded_at": datetime.now(timezone.utc).isoformat(),
                        "nium_mode": "simulated_fallback",
                    }},
                )
                return {
                    "message": "Cliente NIUM creato (fallback simulato)",
                    "customer_hash": sim_hash,
                    "status": "simulated_fallback",
                    "nium_error": resp.text[:200],
                }

    except Exception as e:
        logger.error(f"[NIUM] Onboarding error: {e}")
        sim_hash = f"sim_{uuid.uuid4().hex[:12]}"
        await db.users.update_one(
            {"id": uid},
            {"$set": {
                "nium_customer_hash": sim_hash,
                "nium_onboarded_at": datetime.now(timezone.utc).isoformat(),
                "nium_mode": "simulated_error",
            }},
        )
        return {
            "message": "Cliente NIUM creato (fallback)",
            "customer_hash": sim_hash,
            "status": "simulated_error",
        }


@router.get("/status")
async def get_onboarding_status(current_user: dict = Depends(get_current_user)):
    """Get NIUM onboarding status for current user."""
    db = get_database()
    user = await db.users.find_one({"id": current_user["user_id"]}, {"_id": 0, "nium_customer_hash": 1, "nium_mode": 1, "nium_onboarded_at": 1})
    if not user or not user.get("nium_customer_hash"):
        return {"onboarded": False}
    return {
        "onboarded": True,
        "customer_hash": user["nium_customer_hash"],
        "mode": user.get("nium_mode", "unknown"),
        "onboarded_at": user.get("nium_onboarded_at"),
    }
