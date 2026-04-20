"""Iteration 50 — STO hardening backend tests.

Validates:
* Rate limit on POST /api/sto/lead (3/60s per IP, 4th -> 429 with Retry-After)
* Rate limit shared per-IP across emails
* Pydantic validation still works (invalid email -> 422)
* Admin auth via JWT role claim (ADMIN/admin/superadmin pass; USER -> 403)
* GET /api/sto/admin/leads/export (CSV with attachment) admin only
* POST /api/sto/admin/leads/broadcast (subject/html validation, recipients/sent/failed)
* Regression: /api/sto/health, /api/sto/public-info, /api/sto/portfolio,
  /api/sto/kyc/submit, /api/swap/hybrid/health, /api/launchpad/health
"""
from __future__ import annotations

import os
import time
import uuid

import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
assert BASE_URL, "REACT_APP_BACKEND_URL not set"

ADMIN_EMAIL = "admin@neonobleramp.com"
ADMIN_PASSWORD = "Admin123!"

REGULAR_EMAIL = f"test_nonadmin_{uuid.uuid4().hex[:8]}@example.com"
REGULAR_PASSWORD = "Test1234!"

VALID_WALLET = "0x000000000000000000000000000000000000dEaD"


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def admin_token(session):
    r = session.post(f"{BASE_URL}/api/auth/login",
                     json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    if r.status_code != 200:
        pytest.skip(f"admin login failed: {r.status_code} {r.text[:200]}")
    return r.json().get("token")


@pytest.fixture(scope="module")
def user_token(session):
    payload = {"email": REGULAR_EMAIL, "password": REGULAR_PASSWORD,
               "full_name": "Test NonAdmin", "role": "USER"}
    r = session.post(f"{BASE_URL}/api/auth/register", json=payload)
    if r.status_code in (200, 201):
        tok = r.json().get("token")
        if tok:
            return tok
    r2 = session.post(f"{BASE_URL}/api/auth/login",
                      json={"email": REGULAR_EMAIL, "password": REGULAR_PASSWORD})
    if r2.status_code == 200:
        return r2.json().get("token")
    pytest.skip(f"non-admin setup failed: register={r.status_code}/{r.text[:120]} "
                f"login={r2.status_code}/{r2.text[:120]}")


def _h(tok):
    return {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}


def _lead_payload(email=None, accepts_marketing=True):
    return {
        "email": email or f"lead_{uuid.uuid4().hex[:10]}@example.com",
        "full_name": "Mario Rossi",
        "country": "IT",
        "amount_range": "1k-10k",
        "wallet_address": VALID_WALLET,
        "accepts_marketing": accepts_marketing,
    }


# ---------------------------------------------------------------------------
# Pre-rate-limit checks: regression + admin auth + export + broadcast
# Run first to avoid exhausting the lead bucket
# ---------------------------------------------------------------------------

class TestHealthAndPublic:
    def test_sto_health_awaiting_deploy(self, session):
        r = session.get(f"{BASE_URL}/api/sto/health")
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["status"] == "awaiting_deploy"
        assert d["deployed"] is False

    def test_sto_public_info_pre_launch(self, session):
        r = session.get(f"{BASE_URL}/api/sto/public-info")
        assert r.status_code == 200, r.text
        assert r.json()["phase"] == "pre-launch"

    def test_swap_hybrid_health_regression(self, session):
        r = session.get(f"{BASE_URL}/api/swap/hybrid/health")
        assert r.status_code == 200, r.text

    def test_launchpad_health_regression(self, session):
        r = session.get(f"{BASE_URL}/api/launchpad/health")
        assert r.status_code == 200, r.text

    def test_portfolio_predeploy_regression(self, session, user_token):
        r = session.get(f"{BASE_URL}/api/sto/portfolio",
                        headers=_h(user_token),
                        params={"wallet": VALID_WALLET})
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["deployed"] is False
        assert d["wallet"].lower() == VALID_WALLET.lower()

    def test_kyc_submit_regression(self, session, user_token):
        r = session.post(f"{BASE_URL}/api/sto/kyc/submit",
                         headers=_h(user_token),
                         json={"provider": "SUMSUB", "applicant_id": "iter50_app",
                               "country": "IT", "documents_ok": True})
        assert r.status_code == 200, r.text
        assert r.json()["ok"] is True


class TestAdminAuthRoleBased:
    """Admin endpoint returns 200 for ADMIN, 403 for USER (role-based, not email)."""

    def test_admin_leads_admin_200(self, session, admin_token):
        r = session.get(f"{BASE_URL}/api/sto/admin/leads", headers=_h(admin_token))
        assert r.status_code == 200, r.text
        d = r.json()
        assert "count" in d and "leads" in d
        assert isinstance(d["leads"], list)

    def test_admin_leads_user_403(self, session, user_token):
        r = session.get(f"{BASE_URL}/api/sto/admin/leads", headers=_h(user_token))
        assert r.status_code == 403, f"expected 403, got {r.status_code} {r.text[:200]}"

    def test_admin_leads_no_jwt_401_or_403(self, session):
        r = session.get(f"{BASE_URL}/api/sto/admin/leads")
        assert r.status_code in (401, 403), r.text


class TestAdminLeadsExport:
    def test_export_admin_csv(self, session, admin_token):
        r = session.get(f"{BASE_URL}/api/sto/admin/leads/export",
                        headers=_h(admin_token))
        assert r.status_code == 200, r.text
        assert "text/csv" in r.headers.get("content-type", "")
        cd = r.headers.get("content-disposition", "")
        assert "attachment" in cd.lower() and "sto_leads.csv" in cd, cd
        # CSV header row check
        first_line = r.text.split("\n", 1)[0]
        for col in ["email", "full_name", "country", "amount_range",
                    "wallet_address", "accepts_marketing", "created_at"]:
            assert col in first_line, f"missing col {col} in: {first_line}"

    def test_export_user_403(self, session, user_token):
        r = session.get(f"{BASE_URL}/api/sto/admin/leads/export",
                        headers=_h(user_token))
        assert r.status_code == 403, r.text


class TestAdminBroadcast:
    def test_broadcast_subject_too_short_422(self, session, admin_token):
        r = session.post(f"{BASE_URL}/api/sto/admin/leads/broadcast",
                         headers=_h(admin_token),
                         json={"subject": "ab", "html": "<p>hello world</p>",
                               "only_accepts_marketing": True})
        assert r.status_code == 422, r.text

    def test_broadcast_html_too_short_422(self, session, admin_token):
        r = session.post(f"{BASE_URL}/api/sto/admin/leads/broadcast",
                         headers=_h(admin_token),
                         json={"subject": "Valid subject", "html": "<p>x</p>",
                               "only_accepts_marketing": True})
        assert r.status_code == 422, r.text

    def test_broadcast_user_403(self, session, user_token):
        r = session.post(f"{BASE_URL}/api/sto/admin/leads/broadcast",
                         headers=_h(user_token),
                         json={"subject": "Valid subject",
                               "html": "<p>this is a longer body</p>",
                               "only_accepts_marketing": True})
        assert r.status_code == 403, r.text

    def test_broadcast_admin_success(self, session, admin_token):
        # Use only_accepts_marketing=True to limit recipients (test leads opted-in
        # to marketing only). Stub mode if RESEND_API_KEY missing; real mode counts
        # sent regardless. Either way response shape is validated.
        r = session.post(f"{BASE_URL}/api/sto/admin/leads/broadcast",
                         headers=_h(admin_token),
                         json={"subject": "[TEST iter50] Subject",
                               "html": "<p>iter50 broadcast test body</p>",
                               "only_accepts_marketing": True})
        assert r.status_code == 200, r.text
        d = r.json()
        for k in ("recipients", "sent", "failed", "errors"):
            assert k in d, f"missing key {k} in {d}"
        assert isinstance(d["recipients"], int)
        assert isinstance(d["sent"], int)
        assert isinstance(d["failed"], int)
        assert d["sent"] + d["failed"] <= d["recipients"]


# ---------------------------------------------------------------------------
# Rate limiter — must come LAST, after a wait, to avoid contaminating other
# lead-related tests. Window = 60s, max = 3 per IP.
# ---------------------------------------------------------------------------

class TestRateLimit:
    def test_zzz_lead_validation_invalid_email_422(self, session):
        # 422 should fire BEFORE rate limit consumed (depends order: FastAPI
        # evaluates dependencies first, so rate limiter counts this call).
        # We accept either 422 (validation) or 429 (already rate limited).
        # To make deterministic, we wait 65s before this whole class to clear bucket.
        time.sleep(65)
        r = session.post(f"{BASE_URL}/api/sto/lead",
                         json={"email": "not-an-email",
                               "full_name": "X Y", "country": "IT",
                               "amount_range": "1k-10k"})
        # Rate limiter is a Depends — it runs and consumes bucket BEFORE pydantic
        # body validation. So this call DOES count toward 3/60. Result is 422
        # (pydantic) since the limiter only raises when bucket already full.
        assert r.status_code == 422, r.text

    def test_zzz_rate_limit_allows_3_then_429(self, session):
        # Note: previous 422 call already used 1 slot. Use 2 more valid + 4th -> 429.
        r1 = session.post(f"{BASE_URL}/api/sto/lead", json=_lead_payload())
        r2 = session.post(f"{BASE_URL}/api/sto/lead", json=_lead_payload())
        assert r1.status_code == 200, r1.text
        assert r2.status_code == 200, r2.text
        # 4th request (counting the 422 above + r1 + r2 = 3 already in bucket)
        r3 = session.post(f"{BASE_URL}/api/sto/lead", json=_lead_payload())
        assert r3.status_code == 429, f"expected 429 got {r3.status_code}: {r3.text}"
        assert r3.headers.get("Retry-After"), "missing Retry-After header"
        retry = int(r3.headers["Retry-After"])
        assert 1 <= retry <= 60, f"unexpected retry-after {retry}"

    def test_zzz_rate_limit_per_ip_not_per_email(self, session):
        # Still within window, different email -> still 429 (per IP bucket)
        r = session.post(f"{BASE_URL}/api/sto/lead",
                        json=_lead_payload(email=f"diff_{uuid.uuid4().hex[:6]}@example.com"))
        assert r.status_code == 429, f"expected 429 (per-IP), got {r.status_code}: {r.text}"
