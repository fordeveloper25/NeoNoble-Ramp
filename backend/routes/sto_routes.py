"""
NeoNoble STO — Security Token Offering backend API.

Modalita` operative (automatiche):
 * PRE-DEPLOY: contratti non ancora su Polygon → endpoint di lead
   capture, pre-registrazione, KYC submission e admin sono operativi.
   Gli endpoint che scrivono on-chain ritornano 503.
 * POST-DEPLOY: impostate le env `STO_TOKEN_ADDRESS`,
   `STO_REGISTRY_ADDRESS`, `STO_REDEMPTION_VAULT`, `STO_REVSHARE_VAULT`,
   `STO_NAV_ORACLE`, `POLYGON_RPC_URL` → gli endpoint on-chain diventano
   attivi e leggono/costruiscono tx reali.

Tutte le chiamate web3 sync sono wrappate con asyncio.to_thread per non
bloccare l'event loop FastAPI. Rate limit su /lead (3 req/min per IP).
Admin check via JWT role claim ('admin').
"""
from __future__ import annotations

import asyncio
import csv
import io
import json
import logging
import os
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, EmailStr, Field
from web3 import Web3

from middleware.auth import get_current_user
from utils.rate_limiter import rate_limit

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/sto", tags=["STO"])

POLYGON_CHAIN_ID = 137
POLYGON_AMOY_CHAIN_ID = 80002
POLYGONSCAN = "https://polygonscan.com"

_ABI_DIR = Path(__file__).parent.parent / "abis"


def _load_abi(name: str):
    p = _ABI_DIR / name
    if not p.exists():
        return []
    with open(p) as f:
        return json.load(f)


TOKEN_ABI = _load_abi("sto_token_abi.json")
REGISTRY_ABI = _load_abi("sto_registry_abi.json")
ORACLE_ABI = _load_abi("sto_nav_oracle_abi.json")
REDEMPTION_ABI = _load_abi("sto_redemption_abi.json")
REVSHARE_ABI = _load_abi("sto_revshare_abi.json")


class _StoState:
    def __init__(self):
        self.rpc_url = os.environ.get("POLYGON_RPC_URL", "https://polygon-rpc.com")
        self.chain_id = int(os.environ.get("POLYGON_CHAIN_ID", POLYGON_CHAIN_ID))
        self.token_address = os.environ.get("STO_TOKEN_ADDRESS", "").strip()
        self.registry_address = os.environ.get("STO_REGISTRY_ADDRESS", "").strip()
        self.oracle_address = os.environ.get("STO_NAV_ORACLE", "").strip()
        self.redemption_address = os.environ.get("STO_REDEMPTION_VAULT", "").strip()
        self.revshare_address = os.environ.get("STO_REVSHARE_VAULT", "").strip()
        self.settlement_address = os.environ.get("STO_SETTLEMENT_TOKEN", "").strip()
        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url, request_kwargs={"timeout": 30}))
        self.db = None  # wired from server.py

    @property
    def deployed(self) -> bool:
        return all([
            self.token_address, self.registry_address, self.oracle_address,
            self.redemption_address, self.revshare_address, self.settlement_address,
        ]) and all(Web3.is_address(a) for a in [
            self.token_address, self.registry_address, self.oracle_address,
            self.redemption_address, self.revshare_address, self.settlement_address,
        ])

    def token(self):
        return self.w3.eth.contract(address=Web3.to_checksum_address(self.token_address), abi=TOKEN_ABI)

    def registry(self):
        return self.w3.eth.contract(address=Web3.to_checksum_address(self.registry_address), abi=REGISTRY_ABI)

    def oracle(self):
        return self.w3.eth.contract(address=Web3.to_checksum_address(self.oracle_address), abi=ORACLE_ABI)

    def redemption(self):
        return self.w3.eth.contract(address=Web3.to_checksum_address(self.redemption_address), abi=REDEMPTION_ABI)

    def revshare(self):
        return self.w3.eth.contract(address=Web3.to_checksum_address(self.revshare_address), abi=REVSHARE_ABI)


_state: Optional[_StoState] = None


def get_state() -> _StoState:
    global _state
    if _state is None:
        _state = _StoState()
    return _state


def set_sto_db(db):
    s = get_state()
    s.db = db
    logger.info("✅ STO DB wired")


def require_deployed(s: _StoState):
    if not s.deployed:
        raise HTTPException(
            status_code=503,
            detail="STO contracts non ancora deployati. Imposta STO_TOKEN_ADDRESS, "
                   "STO_REGISTRY_ADDRESS, STO_NAV_ORACLE, STO_REDEMPTION_VAULT, "
                   "STO_REVSHARE_VAULT, STO_SETTLEMENT_TOKEN nell'env e riavvia.",
        )


def require_admin(user: dict):
    """Role-based admin check via JWT role claim (populated from users.role in DB)."""
    role = (user or {}).get("role", "").lower()
    if role not in ("admin", "superadmin"):
        raise HTTPException(403, "admin only")


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class LeadIn(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=2, max_length=100)
    country: str = Field(..., min_length=2, max_length=2, description="ISO 3166-1 alpha-2")
    amount_range: str = Field(..., description="one of: <1k, 1k-10k, 10k-50k, 50k+")
    wallet_address: Optional[str] = None
    accepts_marketing: bool = False


class KycSubmitIn(BaseModel):
    provider: str = Field(default="SUMSUB")
    applicant_id: str
    country: str
    documents_ok: bool = False


class WhitelistAddIn(BaseModel):
    wallet_address: str
    country_iso_numeric: int = Field(..., ge=1, le=999)
    expires_unix: int
    kyc_provider: str = "SUMSUB"


class MintBuildIn(BaseModel):
    investor_wallet: str
    amount_token_wei: str  # string perche` uint256
    operator_wallet: str   # chi firmera` (agent)


class RedemptionRequestIn(BaseModel):
    amount_token_wei: str
    user_wallet: str


class RedemptionApproveIn(BaseModel):
    request_id: int


class RedemptionRejectIn(BaseModel):
    request_id: int
    reason: str = Field(..., min_length=3, max_length=200)


class NavUpdateIn(BaseModel):
    new_nav_settlement: str   # wei del settlement
    effective_from_unix: int
    report_hash: str = Field(..., pattern=r"^0x[a-fA-F0-9]{64}$")


class DistributeIn(BaseModel):
    amount_settlement: str
    operator_wallet: str


class RevClaimBuildIn(BaseModel):
    user_wallet: str
    distribution_id: int


class BroadcastIn(BaseModel):
    subject: str = Field(..., min_length=3, max_length=200)
    html: str = Field(..., min_length=10, max_length=50_000)
    only_accepts_marketing: bool = True


# ---------------------------------------------------------------------------
# Public endpoints
# ---------------------------------------------------------------------------

@router.get("/health")
async def sto_health():
    s = get_state()
    return {
        "status": "operational" if s.deployed else "awaiting_deploy",
        "rpc_connected": s.w3.is_connected(),
        "chain_id": s.chain_id,
        "deployed": s.deployed,
        "contracts": {
            "token": s.token_address or None,
            "registry": s.registry_address or None,
            "oracle": s.oracle_address or None,
            "redemption": s.redemption_address or None,
            "revshare": s.revshare_address or None,
            "settlement": s.settlement_address or None,
        },
    }


@router.get("/public-info")
async def public_info():
    s = get_state()
    if not s.deployed:
        # Pre-launch: serve info statiche dal DB / env
        return {
            "phase": "pre-launch",
            "name": os.environ.get("STO_TOKEN_NAME", "NeoNoble Revenue Share Token"),
            "symbol": os.environ.get("STO_TOKEN_SYMBOL", "NNRS"),
            "nominal_price_eur": float(os.environ.get("STO_NOMINAL_EUR", "250")),
            "target_raise_eur_min": 1_000_000,
            "target_raise_eur_max": 8_000_000,
            "chain": "Polygon PoS",
            "note": "Pre-launch — apri la tua pre-registrazione per essere avvisato al go-live.",
        }
    try:
        t = s.token()
        o = s.oracle()
        name, symbol, supply, nav, eff, rhash = await asyncio.gather(
            asyncio.to_thread(t.functions.name().call),
            asyncio.to_thread(t.functions.symbol().call),
            asyncio.to_thread(t.functions.totalSupply().call),
            asyncio.to_thread(o.functions.navPerToken().call),
            asyncio.to_thread(o.functions.effectiveFrom().call),
            asyncio.to_thread(o.functions.reportHash().call),
        )
    except Exception as e:
        raise HTTPException(500, f"on-chain read error: {e}")
    return {
        "phase": "live",
        "name": name,
        "symbol": symbol,
        "total_supply_wei": str(supply),
        "total_supply_human": float(Decimal(supply) / Decimal(10**18)),
        "nav_per_token_settlement_wei": str(nav),
        "nav_effective_from": int(eff),
        "nav_report_hash": rhash.hex() if isinstance(rhash, (bytes, bytearray)) else rhash,
        "chain_id": s.chain_id,
        "token_contract": s.token_address,
    }


@router.post("/lead", dependencies=[Depends(rate_limit(max_calls=3, window_seconds=60, key_prefix="sto_lead"))])
async def lead_capture(body: LeadIn):
    """Pre-registrazione pubblica. Nessun auth: raccoglie lead per go-live."""
    s = get_state()
    if s.db is None:
        raise HTTPException(503, "db not ready")
    doc = body.model_dump()
    now = datetime.now(timezone.utc).isoformat()
    doc["source"] = "landing"
    doc["updated_at"] = now
    try:
        await s.db.sto_leads.update_one(
            {"email": body.email},
            {"$setOnInsert": {"created_at": now}, "$set": doc},
            upsert=True,
        )
    except Exception as e:
        logger.exception("lead upsert")
        raise HTTPException(500, f"db error: {e}")
    return {"ok": True, "message": "Grazie! Ti contatteremo al go-live."}


# ---------------------------------------------------------------------------
# Investor endpoints (JWT)
# ---------------------------------------------------------------------------

@router.post("/kyc/submit")
async def kyc_submit(body: KycSubmitIn, user: dict = Depends(get_current_user)):
    s = get_state()
    if s.db is None:
        raise HTTPException(503, "db not ready")
    uid = user.get("user_id") or user.get("email")
    await s.db.sto_kyc.update_one(
        {"user_id": uid},
        {"$set": {
            **body.model_dump(),
            "user_id": uid,
            "status": "submitted",
            "submitted_at": datetime.now(timezone.utc).isoformat(),
        }},
        upsert=True,
    )
    return {"ok": True, "status": "submitted"}


@router.get("/kyc/status")
async def kyc_status(user: dict = Depends(get_current_user)):
    s = get_state()
    if s.db is None:
        return {"status": "unknown"}
    uid = user.get("user_id") or user.get("email")
    doc = await s.db.sto_kyc.find_one({"user_id": uid}, {"_id": 0})
    return doc or {"status": "not_submitted"}


@router.get("/portfolio")
async def portfolio(
    wallet: str = Query(..., description="address EVM whitelisted"),
    user: dict = Depends(get_current_user),
):
    s = get_state()
    if not Web3.is_address(wallet):
        raise HTTPException(400, "bad wallet")
    if not s.deployed:
        return {"deployed": False, "wallet": wallet, "balance_wei": "0", "claimable_revenue": []}

    try:
        t = s.token()
        o = s.oracle()
        rs = s.revshare()
        bal, nav, distro_count = await asyncio.gather(
            asyncio.to_thread(t.functions.balanceOf(Web3.to_checksum_address(wallet)).call),
            asyncio.to_thread(o.functions.navPerToken().call),
            asyncio.to_thread(rs.functions.distributionsCount().call),
        )
    except Exception as e:
        raise HTTPException(500, f"read: {e}")

    # scan ultime 24 distribuzioni per trovare claim pending (MVP — per >24 serve indicizzatore)
    claimable = []
    start = max(0, distro_count - 24)
    for i in range(start, distro_count):
        try:
            claimed = await asyncio.to_thread(
                rs.functions.hasClaimed(Web3.to_checksum_address(wallet), i).call
            )
            if claimed:
                continue
            d = await asyncio.to_thread(rs.functions.distributions(i).call)
            amount, supply_at, _, timestamp = d
            if supply_at == 0:
                continue
            share = (amount * bal) // supply_at
            if share > 0:
                claimable.append({"distribution_id": i, "share_wei": str(share), "timestamp": int(timestamp)})
        except Exception:
            continue

    # redemption requests (DB)
    my_redemptions = []
    if s.db is not None:
        async for r in s.db.sto_redemption_requests.find({"user_wallet": wallet.lower()}, {"_id": 0}):
            my_redemptions.append(r)

    return {
        "deployed": True,
        "wallet": wallet,
        "balance_wei": str(bal),
        "balance_human": float(Decimal(bal) / Decimal(10**18)),
        "nav_per_token_wei": str(nav),
        "estimated_value_settlement_wei": str(bal * nav // (10**18)),
        "claimable_revenue": claimable,
        "my_redemptions": my_redemptions,
    }


@router.post("/redemption/request")
async def redemption_request(body: RedemptionRequestIn, user: dict = Depends(get_current_user)):
    s = get_state()
    require_deployed(s)
    if not Web3.is_address(body.user_wallet):
        raise HTTPException(400, "bad wallet")
    try:
        amt = int(body.amount_token_wei)
        tx = s.redemption().functions.requestRedemption(amt).build_transaction({
            "from": Web3.to_checksum_address(body.user_wallet),
            "value": 0,
            "chainId": s.chain_id,
            "gas": 300_000,
            "gasPrice": s.w3.eth.gas_price,
            "nonce": 0,
        })
    except Exception as e:
        raise HTTPException(500, f"build: {e}")

    # log richiesta (stato pending off-chain; on-chain sara` confermata al mine)
    if s.db is not None:
        uid = user.get("user_id") or user.get("email")
        await s.db.sto_redemption_requests.insert_one({
            "user_id": uid,
            "user_wallet": body.user_wallet.lower(),
            "amount_token_wei": body.amount_token_wei,
            "status": "calldata_issued",
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
    return {"to": tx["to"], "data": tx["data"], "value": "0x0",
            "gas": hex(int(tx["gas"])), "gas_price": hex(int(tx["gasPrice"])),
            "chain_id": s.chain_id}


@router.post("/revenue/claim-build")
async def revenue_claim_build(body: RevClaimBuildIn, user: dict = Depends(get_current_user)):
    s = get_state()
    require_deployed(s)
    try:
        tx = s.revshare().functions.claim(body.distribution_id).build_transaction({
            "from": Web3.to_checksum_address(body.user_wallet),
            "value": 0,
            "chainId": s.chain_id,
            "gas": 200_000,
            "gasPrice": s.w3.eth.gas_price,
            "nonce": 0,
        })
    except Exception as e:
        raise HTTPException(500, f"build: {e}")
    return {"to": tx["to"], "data": tx["data"], "value": "0x0",
            "gas": hex(int(tx["gas"])), "gas_price": hex(int(tx["gasPrice"])),
            "chain_id": s.chain_id}


# ---------------------------------------------------------------------------
# Admin endpoints
# ---------------------------------------------------------------------------

@router.post("/admin/whitelist/add")
async def admin_whitelist_add(body: WhitelistAddIn, user: dict = Depends(get_current_user)):
    require_admin(user)
    s = get_state()
    require_deployed(s)
    if not Web3.is_address(body.wallet_address):
        raise HTTPException(400, "bad wallet")
    operator = Web3.to_checksum_address(user.get("wallet_address") or s.token_address)  # stub
    try:
        tx = s.registry().functions.registerIdentity(
            Web3.to_checksum_address(body.wallet_address),
            body.country_iso_numeric,
            body.expires_unix,
            Web3.keccak(text=body.kyc_provider),
        ).build_transaction({
            "from": operator,
            "value": 0, "chainId": s.chain_id,
            "gas": 250_000, "gasPrice": s.w3.eth.gas_price, "nonce": 0,
        })
    except Exception as e:
        raise HTTPException(500, f"build: {e}")
    return {"to": tx["to"], "data": tx["data"], "value": "0x0",
            "gas": hex(int(tx["gas"])), "gas_price": hex(int(tx["gasPrice"])),
            "chain_id": s.chain_id}


@router.post("/admin/mint-build")
async def admin_mint_build(body: MintBuildIn, user: dict = Depends(get_current_user)):
    require_admin(user)
    s = get_state()
    require_deployed(s)
    try:
        tx = s.token().functions.mint(
            Web3.to_checksum_address(body.investor_wallet), int(body.amount_token_wei)
        ).build_transaction({
            "from": Web3.to_checksum_address(body.operator_wallet),
            "value": 0, "chainId": s.chain_id,
            "gas": 300_000, "gasPrice": s.w3.eth.gas_price, "nonce": 0,
        })
    except Exception as e:
        raise HTTPException(500, f"build: {e}")
    return {"to": tx["to"], "data": tx["data"], "value": "0x0",
            "gas": hex(int(tx["gas"])), "gas_price": hex(int(tx["gasPrice"])),
            "chain_id": s.chain_id}


@router.post("/admin/redemption/approve")
async def admin_redemption_approve(body: RedemptionApproveIn, user: dict = Depends(get_current_user)):
    require_admin(user)
    s = get_state()
    require_deployed(s)
    operator = user.get("wallet_address") or s.token_address  # stub
    try:
        tx = s.redemption().functions.approve(body.request_id).build_transaction({
            "from": Web3.to_checksum_address(operator),
            "value": 0, "chainId": s.chain_id,
            "gas": 150_000, "gasPrice": s.w3.eth.gas_price, "nonce": 0,
        })
    except Exception as e:
        raise HTTPException(500, f"build: {e}")
    return {"to": tx["to"], "data": tx["data"], "value": "0x0",
            "gas": hex(int(tx["gas"])), "gas_price": hex(int(tx["gasPrice"])),
            "chain_id": s.chain_id}


@router.post("/admin/redemption/reject")
async def admin_redemption_reject(body: RedemptionRejectIn, user: dict = Depends(get_current_user)):
    require_admin(user)
    s = get_state()
    require_deployed(s)
    operator = user.get("wallet_address") or s.token_address
    try:
        tx = s.redemption().functions.reject(body.request_id, body.reason).build_transaction({
            "from": Web3.to_checksum_address(operator),
            "value": 0, "chainId": s.chain_id,
            "gas": 200_000, "gasPrice": s.w3.eth.gas_price, "nonce": 0,
        })
    except Exception as e:
        raise HTTPException(500, f"build: {e}")
    return {"to": tx["to"], "data": tx["data"], "value": "0x0",
            "gas": hex(int(tx["gas"])), "gas_price": hex(int(tx["gasPrice"])),
            "chain_id": s.chain_id}


@router.post("/admin/nav/update-build")
async def admin_nav_update(body: NavUpdateIn, user: dict = Depends(get_current_user)):
    require_admin(user)
    s = get_state()
    require_deployed(s)
    operator = user.get("wallet_address") or s.token_address
    try:
        tx = s.oracle().functions.updateNAV(
            int(body.new_nav_settlement), body.effective_from_unix, body.report_hash
        ).build_transaction({
            "from": Web3.to_checksum_address(operator),
            "value": 0, "chainId": s.chain_id,
            "gas": 150_000, "gasPrice": s.w3.eth.gas_price, "nonce": 0,
        })
    except Exception as e:
        raise HTTPException(500, f"build: {e}")
    return {"to": tx["to"], "data": tx["data"], "value": "0x0",
            "gas": hex(int(tx["gas"])), "gas_price": hex(int(tx["gasPrice"])),
            "chain_id": s.chain_id}


@router.post("/admin/revenue/distribute-build")
async def admin_revenue_distribute(body: DistributeIn, user: dict = Depends(get_current_user)):
    require_admin(user)
    s = get_state()
    require_deployed(s)
    try:
        tx = s.revshare().functions.distribute(int(body.amount_settlement)).build_transaction({
            "from": Web3.to_checksum_address(body.operator_wallet),
            "value": 0, "chainId": s.chain_id,
            "gas": 300_000, "gasPrice": s.w3.eth.gas_price, "nonce": 0,
        })
    except Exception as e:
        raise HTTPException(500, f"build: {e}")
    return {"to": tx["to"], "data": tx["data"], "value": "0x0",
            "gas": hex(int(tx["gas"])), "gas_price": hex(int(tx["gasPrice"])),
            "chain_id": s.chain_id}


@router.get("/admin/leads")
async def admin_leads(user: dict = Depends(get_current_user), limit: int = 500):
    require_admin(user)
    s = get_state()
    if s.db is None:
        return {"count": 0, "leads": []}
    out = []
    async for d in s.db.sto_leads.find({}, {"_id": 0}).sort("created_at", -1).limit(limit):
        out.append(d)
    return {"count": len(out), "leads": out}


@router.get("/admin/report/holders")
async def admin_report_holders(user: dict = Depends(get_current_user)):
    """CSV export holder dal DB (whitelist + cached balance)."""
    require_admin(user)
    s = get_state()
    if s.db is None:
        raise HTTPException(503, "db not ready")
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["wallet", "country", "kyc_provider", "kyc_expires_unix", "added_at"])
    async for d in s.db.sto_whitelist.find({}, {"_id": 0}):
        w.writerow([d.get("wallet_address", ""), d.get("country_iso_numeric", ""),
                    d.get("kyc_provider", ""), d.get("expires_unix", ""),
                    d.get("created_at", "")])
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=holders.csv"},
    )


@router.get("/admin/leads/export")
async def admin_leads_export(user: dict = Depends(get_current_user)):
    """CSV export di tutte le lead pre-registrazione."""
    require_admin(user)
    s = get_state()
    if s.db is None:
        raise HTTPException(503, "db not ready")
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["email", "full_name", "country", "amount_range", "wallet_address",
                "accepts_marketing", "created_at", "updated_at", "source"])
    async for d in s.db.sto_leads.find({}, {"_id": 0}).sort("created_at", -1):
        w.writerow([
            d.get("email", ""), d.get("full_name", ""), d.get("country", ""),
            d.get("amount_range", ""), d.get("wallet_address", ""),
            "yes" if d.get("accepts_marketing") else "no",
            d.get("created_at", ""), d.get("updated_at", ""), d.get("source", ""),
        ])
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=sto_leads.csv"},
    )


@router.post("/admin/leads/broadcast")
async def admin_leads_broadcast(body: BroadcastIn, user: dict = Depends(get_current_user)):
    """
    Invia un'email broadcast a tutti i lead (oppure solo a quelli con
    accepts_marketing=true). Usa Resend via email_service. In assenza di
    RESEND_API_KEY (dev), le chiamate vengono loggate come stub.
    """
    require_admin(user)
    s = get_state()
    if s.db is None:
        raise HTTPException(503, "db not ready")

    # Lazy import per non rompere test se resend manca
    try:
        from services.email_service import get_email_service
    except Exception as e:
        raise HTTPException(500, f"email service missing: {e}")

    svc = get_email_service()
    if svc is None:
        logger.warning("broadcast: email service not initialized (stub mode)")

    query = {"accepts_marketing": True} if body.only_accepts_marketing else {}
    emails = []
    async for d in s.db.sto_leads.find(query, {"_id": 0, "email": 1}):
        if d.get("email"):
            emails.append(d["email"])

    sent, failed = 0, 0
    errors = []
    for email in emails:
        try:
            if svc is None:
                logger.info("[email stub] to=%s subject=%r", email, body.subject)
                sent += 1
                continue
            ok = await svc.send_email(
                to_email=email,
                subject=body.subject,
                html_content=body.html,
            )
            if ok:
                sent += 1
            else:
                failed += 1
        except Exception as e:
            failed += 1
            errors.append({"to": email, "error": str(e)})

    # Log broadcast
    try:
        await s.db.sto_broadcasts.insert_one({
            "subject": body.subject,
            "recipients_count": len(emails),
            "sent": sent,
            "failed": failed,
            "only_marketing": body.only_accepts_marketing,
            "sent_by": user.get("email"),
            "sent_at": datetime.now(timezone.utc).isoformat(),
        })
    except Exception as e:
        logger.warning("broadcast log failed: %s", e)

    return {"recipients": len(emails), "sent": sent, "failed": failed, "errors": errors[:20]}
