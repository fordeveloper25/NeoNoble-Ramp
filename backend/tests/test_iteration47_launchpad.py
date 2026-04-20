"""
Iteration 47 — Backend tests for NeoNoble Launchpad (bonding-curve token factory).

Factory is NOT deployed yet (LAUNCHPAD_FACTORY_ADDRESS unset) so all data/build
endpoints must gracefully return 503 with Italian deploy instructions.

Also:
- /health still returns 200 with status='awaiting_deploy'
- JWT enforcement on build-* endpoints
- Pydantic validation (bnb_in=0, empty name) returns 422
- Regression: /api/swap/hybrid/health, /api/swap/hybrid/quote still work
- ABI JSON files parse correctly
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
import requests

BASE_URL = os.environ.get(
    "REACT_APP_BACKEND_URL",
    "https://neno-swap-live.preview.emergentagent.com",
).rstrip("/")
ADMIN_EMAIL = "admin@neonobleramp.com"
ADMIN_PASSWORD = "Admin123!"

TEST_WALLET = "0x18CE1930820d5e1B87F37a8a2F7Cf59E7BF6da4E"
DUMMY_TOKEN = "0x000000000000000000000000000000000000dEaD"


# ---------------- Fixtures --------------------------------------------------

@pytest.fixture(scope="module")
def api():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def auth_token(api):
    for ep in ("/api/auth/login", "/api/login"):
        try:
            r = api.post(f"{BASE_URL}{ep}",
                         json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=30)
            if r.status_code == 200:
                data = r.json()
                token = (data.get("access_token")
                         or data.get("token")
                         or (data.get("data") or {}).get("access_token"))
                if token:
                    return token
        except Exception:
            continue
    pytest.skip("Admin login failed — cannot obtain JWT")


@pytest.fixture(scope="module")
def auth_api(auth_token):
    s = requests.Session()
    s.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {auth_token}",
    })
    return s


# ---------------- ABI JSON files -------------------------------------------

def test_factory_abi_is_valid_json():
    p = Path("/app/backend/abis/launchpad_abi.json")
    assert p.exists(), "missing launchpad_abi.json"
    data = json.loads(p.read_text())
    assert isinstance(data, list) and len(data) > 0
    names = {item.get("name") for item in data if item.get("type") == "function"}
    for fn in ("deployFee", "allTokens", "allTokensLength",
               "createToken", "platformFeeRecipient", "owner"):
        assert fn in names, f"ABI missing function: {fn}"


def test_token_abi_is_valid_json():
    p = Path("/app/backend/abis/bonding_curve_abi.json")
    assert p.exists(), "missing bonding_curve_abi.json"
    data = json.loads(p.read_text())
    assert isinstance(data, list) and len(data) > 0
    names = {item.get("name") for item in data if item.get("type") == "function"}
    for fn in ("name", "symbol", "totalSupply", "creator", "graduated",
               "virtualBnbReserve", "virtualTokenReserve",
               "realBnbReserve", "realTokenReserve",
               "currentPriceWei", "marketCapWei",
               "getTokensOut", "getBnbOut", "buy", "sell", "GRADUATION_BNB"):
        assert fn in names, f"ABI missing function: {fn}"


# ---------------- /health (always 200) -------------------------------------

def test_launchpad_health_awaiting_deploy(api):
    r = api.get(f"{BASE_URL}/api/launchpad/health", timeout=30)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d.get("status") == "awaiting_deploy", d
    assert d.get("rpc_connected") is True, d
    assert d.get("chain_id") == 56, d
    assert d.get("factory_deployed") is False, d
    assert d.get("capital_required_from_platform") is False, d
    assert d.get("model") == "virtual_constant_product_amm", d
    # factory_address should be null/empty
    assert not d.get("factory_address"), d


# ---------------- Data endpoints → 503 when factory absent -----------------

def test_config_503_when_not_deployed(api):
    r = api.get(f"{BASE_URL}/api/launchpad/config", timeout=30)
    assert r.status_code == 503, r.text
    detail = (r.json().get("detail") or "").lower()
    assert "deploy" in detail
    assert "/app/contracts/deploy.md" in detail


def test_tokens_list_503_when_not_deployed(api):
    r = api.get(f"{BASE_URL}/api/launchpad/tokens", timeout=30)
    assert r.status_code == 503, r.text
    assert "deploy" in (r.json().get("detail") or "").lower()


def test_tokens_list_503_with_pagination_params(api):
    r = api.get(f"{BASE_URL}/api/launchpad/tokens?limit=10&offset=0", timeout=30)
    assert r.status_code == 503, r.text


def test_token_detail_503_when_not_deployed(api):
    r = api.get(f"{BASE_URL}/api/launchpad/tokens/{DUMMY_TOKEN}", timeout=30)
    assert r.status_code == 503, r.text


def test_quote_buy_503_when_not_deployed(api):
    r = api.get(
        f"{BASE_URL}/api/launchpad/quote-buy?token={DUMMY_TOKEN}&bnb_in=0.1",
        timeout=30,
    )
    assert r.status_code == 503, r.text


def test_quote_sell_503_when_not_deployed(api):
    r = api.get(
        f"{BASE_URL}/api/launchpad/quote-sell?token={DUMMY_TOKEN}&tokens_in=1000",
        timeout=30,
    )
    assert r.status_code == 503, r.text


# ---------------- Build endpoints: JWT required ----------------------------

def test_build_create_unauth_returns_401(api):
    r = api.post(
        f"{BASE_URL}/api/launchpad/build-create",
        json={"name": "Test", "symbol": "TST",
              "metadata_uri": "", "user_wallet_address": TEST_WALLET},
        timeout=30,
    )
    assert r.status_code in (401, 403), f"expected 401/403, got {r.status_code}: {r.text}"


def test_build_buy_unauth_returns_401(api):
    r = api.post(
        f"{BASE_URL}/api/launchpad/build-buy",
        json={"token_address": DUMMY_TOKEN, "bnb_in": 0.1,
              "user_wallet_address": TEST_WALLET, "slippage_pct": 3.0},
        timeout=30,
    )
    assert r.status_code in (401, 403), f"expected 401/403, got {r.status_code}: {r.text}"


def test_build_sell_unauth_returns_401(api):
    r = api.post(
        f"{BASE_URL}/api/launchpad/build-sell",
        json={"token_address": DUMMY_TOKEN, "tokens_in": 1000,
              "user_wallet_address": TEST_WALLET, "slippage_pct": 3.0},
        timeout=30,
    )
    assert r.status_code in (401, 403), f"expected 401/403, got {r.status_code}: {r.text}"


# ---------------- Build endpoints (authorized) → 503 -----------------------

def test_build_create_auth_returns_503(auth_api):
    r = auth_api.post(
        f"{BASE_URL}/api/launchpad/build-create",
        json={"name": "Test Token", "symbol": "TST",
              "metadata_uri": "ipfs://xx",
              "user_wallet_address": TEST_WALLET},
        timeout=30,
    )
    assert r.status_code == 503, f"expected 503, got {r.status_code}: {r.text}"


def test_build_buy_auth_returns_503(auth_api):
    r = auth_api.post(
        f"{BASE_URL}/api/launchpad/build-buy",
        json={"token_address": DUMMY_TOKEN, "bnb_in": 0.1,
              "user_wallet_address": TEST_WALLET, "slippage_pct": 3.0},
        timeout=30,
    )
    assert r.status_code == 503, f"expected 503, got {r.status_code}: {r.text}"


def test_build_sell_auth_returns_503(auth_api):
    r = auth_api.post(
        f"{BASE_URL}/api/launchpad/build-sell",
        json={"token_address": DUMMY_TOKEN, "tokens_in": 1000,
              "user_wallet_address": TEST_WALLET, "slippage_pct": 3.0},
        timeout=30,
    )
    assert r.status_code == 503, f"expected 503, got {r.status_code}: {r.text}"


# ---------------- Pydantic validation (422) --------------------------------

def test_build_buy_bnb_in_zero_returns_422(auth_api):
    r = auth_api.post(
        f"{BASE_URL}/api/launchpad/build-buy",
        json={"token_address": DUMMY_TOKEN, "bnb_in": 0,
              "user_wallet_address": TEST_WALLET, "slippage_pct": 3.0},
        timeout=30,
    )
    assert r.status_code == 422, f"expected 422, got {r.status_code}: {r.text}"


def test_build_create_empty_name_returns_422(auth_api):
    r = auth_api.post(
        f"{BASE_URL}/api/launchpad/build-create",
        json={"name": "", "symbol": "TST",
              "metadata_uri": "", "user_wallet_address": TEST_WALLET},
        timeout=30,
    )
    assert r.status_code == 422, f"expected 422, got {r.status_code}: {r.text}"


def test_build_sell_tokens_in_zero_returns_422(auth_api):
    r = auth_api.post(
        f"{BASE_URL}/api/launchpad/build-sell",
        json={"token_address": DUMMY_TOKEN, "tokens_in": 0,
              "user_wallet_address": TEST_WALLET, "slippage_pct": 3.0},
        timeout=30,
    )
    assert r.status_code == 422, f"expected 422, got {r.status_code}: {r.text}"


# ---------------- Regression: swap endpoints still work --------------------

def test_swap_hybrid_health_regression(api):
    r = api.get(f"{BASE_URL}/api/swap/hybrid/health", timeout=30)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d.get("status") in ("operational", "healthy"), d
    assert d.get("mode") == "user_signed_dex", d
    assert d.get("capital_required") is False, d


def test_swap_hybrid_quote_regression(api):
    r = api.post(
        f"{BASE_URL}/api/swap/hybrid/quote",
        json={"from_token": "WBNB", "to_token": "BUSD", "amount_in": 1},
        timeout=60,
    )
    assert r.status_code == 200, r.text
    d = r.json()
    assert d.get("source") in ("1inch", "pancakeswap"), d
    assert float(d.get("estimated_amount_out", 0)) > 0, d


def test_swap_health_regression(api):
    r = api.get(f"{BASE_URL}/api/swap/health", timeout=30)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d.get("rpc_connected") is True
    assert d.get("chain_id") == 56
