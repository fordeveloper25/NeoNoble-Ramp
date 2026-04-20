"""Iteration 49 — STO (Security Token Offering) backend tests.

Validates pre-deploy phase: lead capture, KYC, portfolio (read), admin auth stub,
graceful 503 for on-chain endpoints, and no regression on swap/launchpad.
"""
from __future__ import annotations

import os
import time
import uuid

import pytest
import requests

BASE_URL = os.environ.get(
    "REACT_APP_BACKEND_URL",
    "https://neno-swap-live.preview.emergentagent.com",
).rstrip("/")

ADMIN_EMAIL = "admin@neonobleramp.com"
ADMIN_PASSWORD = "Admin123!"

REGULAR_EMAIL = f"test_sto_{uuid.uuid4().hex[:8]}@example.com"
REGULAR_PASSWORD = "Test1234!"

VALID_WALLET = "0x0000000000000000000000000000000000000001"
INVALID_WALLET = "not-an-address"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def admin_token(session):
    """Login admin (ends with neonobleramp.com -> require_admin passes)."""
    r = session.post(f"{BASE_URL}/api/auth/login",
                     json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    if r.status_code != 200:
        pytest.skip(f"admin login failed: {r.status_code} {r.text[:200]}")
    return r.json().get("token")


@pytest.fixture(scope="module")
def user_token(session):
    """Register a fresh non-admin user (email not ending in neonobleramp.com)."""
    payload = {"email": REGULAR_EMAIL, "password": REGULAR_PASSWORD, "role": "USER"}
    r = session.post(f"{BASE_URL}/api/auth/register", json=payload)
    if r.status_code == 200:
        return r.json().get("token")
    # Fallback: try login if user already existed
    r2 = session.post(f"{BASE_URL}/api/auth/login",
                      json={"email": REGULAR_EMAIL, "password": REGULAR_PASSWORD})
    if r2.status_code == 200:
        return r2.json().get("token")
    pytest.skip(f"non-admin user setup failed: register={r.status_code}/{r.text[:150]} login={r2.status_code}/{r2.text[:150]}")


def _h(tok):
    return {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}


# ---------------------------------------------------------------------------
# Public endpoints
# ---------------------------------------------------------------------------

class TestPublic:
    def test_health(self, session):
        r = session.get(f"{BASE_URL}/api/sto/health")
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["status"] == "awaiting_deploy"
        assert d["rpc_connected"] is True
        assert d["chain_id"] == 137
        assert d["deployed"] is False

    def test_public_info_pre_launch(self, session):
        r = session.get(f"{BASE_URL}/api/sto/public-info")
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["phase"] == "pre-launch"
        assert "name" in d and "symbol" in d
        assert d["nominal_price_eur"] == 250
        assert d["target_raise_eur_min"] == 1_000_000
        assert d["target_raise_eur_max"] == 8_000_000
        assert d["chain"] == "Polygon PoS"


# ---------------------------------------------------------------------------
# Lead capture
# ---------------------------------------------------------------------------

LEAD_EMAIL = f"lead_{uuid.uuid4().hex[:8]}@example.com"


class TestLead:
    def test_lead_create_then_idempotent_upsert(self, session):
        payload = {
            "email": LEAD_EMAIL,
            "full_name": "Mario Rossi",
            "country": "IT",
            "amount_range": "1k-10k",
            "wallet_address": VALID_WALLET,
            "accepts_marketing": True,
        }
        r1 = session.post(f"{BASE_URL}/api/sto/lead", json=payload)
        assert r1.status_code == 200, r1.text
        assert r1.json()["ok"] is True

        # Same email again -> upsert (still 200)
        payload["full_name"] = "Mario Rossi UPDATED"
        r2 = session.post(f"{BASE_URL}/api/sto/lead", json=payload)
        assert r2.status_code == 200, r2.text
        assert r2.json()["ok"] is True

    def test_lead_invalid_email(self, session):
        r = session.post(f"{BASE_URL}/api/sto/lead", json={
            "email": "not-an-email",
            "full_name": "Mario Rossi",
            "country": "IT",
            "amount_range": "1k-10k",
        })
        assert r.status_code == 422, r.text

    def test_lead_full_name_too_short(self, session):
        r = session.post(f"{BASE_URL}/api/sto/lead", json={
            "email": f"x_{uuid.uuid4().hex[:6]}@example.com",
            "full_name": "M",
            "country": "IT",
            "amount_range": "1k-10k",
        })
        assert r.status_code == 422, r.text

    def test_lead_country_wrong_length(self, session):
        r = session.post(f"{BASE_URL}/api/sto/lead", json={
            "email": f"x_{uuid.uuid4().hex[:6]}@example.com",
            "full_name": "Mario Rossi",
            "country": "ITA",
            "amount_range": "1k-10k",
        })
        assert r.status_code == 422, r.text


# ---------------------------------------------------------------------------
# KYC
# ---------------------------------------------------------------------------

class TestKyc:
    def test_kyc_submit_no_jwt(self, session):
        r = session.post(f"{BASE_URL}/api/sto/kyc/submit", json={
            "provider": "SUMSUB",
            "applicant_id": "app_123",
            "country": "IT",
            "documents_ok": True,
        })
        assert r.status_code in (401, 403), f"expected 401/403, got {r.status_code} {r.text}"

    def test_kyc_submit_with_jwt(self, session, user_token):
        r = session.post(
            f"{BASE_URL}/api/sto/kyc/submit",
            headers=_h(user_token),
            json={"provider": "SUMSUB", "applicant_id": "app_xyz",
                  "country": "IT", "documents_ok": True},
        )
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["ok"] is True
        assert d["status"] == "submitted"

    def test_kyc_status_after_submit(self, session, user_token):
        r = session.get(f"{BASE_URL}/api/sto/kyc/status", headers=_h(user_token))
        assert r.status_code == 200, r.text
        d = r.json()
        assert d.get("status") == "submitted"
        assert d.get("applicant_id") == "app_xyz"


# ---------------------------------------------------------------------------
# Portfolio
# ---------------------------------------------------------------------------

class TestPortfolio:
    def test_portfolio_predeploy(self, session, user_token):
        r = session.get(
            f"{BASE_URL}/api/sto/portfolio",
            headers=_h(user_token),
            params={"wallet": VALID_WALLET},
        )
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["deployed"] is False
        assert d["wallet"].lower() == VALID_WALLET.lower()

    def test_portfolio_invalid_wallet(self, session, user_token):
        r = session.get(
            f"{BASE_URL}/api/sto/portfolio",
            headers=_h(user_token),
            params={"wallet": INVALID_WALLET},
        )
        assert r.status_code == 400, r.text


# ---------------------------------------------------------------------------
# 503 graceful (contracts not deployed)
# ---------------------------------------------------------------------------

class TestNotDeployed:
    def test_redemption_request_503(self, session, user_token):
        r = session.post(
            f"{BASE_URL}/api/sto/redemption/request",
            headers=_h(user_token),
            json={"amount_token_wei": "1000000000000000000", "user_wallet": VALID_WALLET},
        )
        assert r.status_code == 503, r.text

    def test_revenue_claim_build_503(self, session, user_token):
        r = session.post(
            f"{BASE_URL}/api/sto/revenue/claim-build",
            headers=_h(user_token),
            json={"user_wallet": VALID_WALLET, "distribution_id": 0},
        )
        assert r.status_code == 503, r.text


# ---------------------------------------------------------------------------
# Admin authorization stub + 503
# ---------------------------------------------------------------------------

class TestAdmin:
    def test_whitelist_add_non_admin_403(self, session, user_token):
        r = session.post(
            f"{BASE_URL}/api/sto/admin/whitelist/add",
            headers=_h(user_token),
            json={
                "wallet_address": VALID_WALLET,
                "country_iso_numeric": 380,
                "expires_unix": int(time.time()) + 86400,
                "kyc_provider": "SUMSUB",
            },
        )
        assert r.status_code == 403, r.text

    def test_whitelist_add_admin_503(self, session, admin_token):
        r = session.post(
            f"{BASE_URL}/api/sto/admin/whitelist/add",
            headers=_h(admin_token),
            json={
                "wallet_address": VALID_WALLET,
                "country_iso_numeric": 380,
                "expires_unix": int(time.time()) + 86400,
                "kyc_provider": "SUMSUB",
            },
        )
        assert r.status_code == 503, r.text

    def test_admin_mint_build_503(self, session, admin_token):
        r = session.post(
            f"{BASE_URL}/api/sto/admin/mint-build",
            headers=_h(admin_token),
            json={
                "investor_wallet": VALID_WALLET,
                "amount_token_wei": "1000000000000000000",
                "operator_wallet": VALID_WALLET,
            },
        )
        assert r.status_code == 503, r.text

    def test_admin_nav_update_bad_hash_422(self, session, admin_token):
        r = session.post(
            f"{BASE_URL}/api/sto/admin/nav/update-build",
            headers=_h(admin_token),
            json={
                "new_nav_settlement": "1000",
                "effective_from_unix": int(time.time()),
                "report_hash": "0xdeadbeef",  # too short
            },
        )
        assert r.status_code == 422, r.text

    def test_admin_nav_update_valid_503(self, session, admin_token):
        r = session.post(
            f"{BASE_URL}/api/sto/admin/nav/update-build",
            headers=_h(admin_token),
            json={
                "new_nav_settlement": "1000000000000000000",
                "effective_from_unix": int(time.time()),
                "report_hash": "0x" + "ab" * 32,
            },
        )
        assert r.status_code == 503, r.text

    def test_admin_leads_includes_test_lead(self, session, admin_token):
        r = session.get(f"{BASE_URL}/api/sto/admin/leads", headers=_h(admin_token))
        assert r.status_code == 200, r.text
        d = r.json()
        assert "count" in d and "leads" in d
        emails = [lead.get("email") for lead in d["leads"]]
        assert LEAD_EMAIL in emails, f"test lead {LEAD_EMAIL} not found in {len(emails)} leads"

    def test_admin_report_holders_csv(self, session, admin_token):
        r = session.get(f"{BASE_URL}/api/sto/admin/report/holders", headers=_h(admin_token))
        assert r.status_code == 200, r.text
        ct = r.headers.get("content-type", "")
        assert "text/csv" in ct, f"unexpected content-type: {ct}"


# ---------------------------------------------------------------------------
# Regression — swap and launchpad
# ---------------------------------------------------------------------------

class TestRegression:
    def test_swap_hybrid_health(self, session):
        r = session.get(f"{BASE_URL}/api/swap/hybrid/health")
        assert r.status_code == 200, r.text

    def test_swap_hybrid_quote(self, session):
        # Minimal payload — endpoint shape may vary, accept 200 or graceful 4xx but not 5xx
        payload = {
            "from_token": "USDC",
            "to_token": "NENO",
            "amount": "100",
            "chain": "BSC",
        }
        r = session.post(f"{BASE_URL}/api/swap/hybrid/quote", json=payload)
        assert r.status_code < 500, f"server error: {r.status_code} {r.text[:200]}"

    def test_launchpad_health(self, session):
        r = session.get(f"{BASE_URL}/api/launchpad/health")
        assert r.status_code == 200, r.text
