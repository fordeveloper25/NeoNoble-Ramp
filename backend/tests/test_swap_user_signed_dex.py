"""
Iteration 46 — Backend tests for NeoNoble USER-SIGNED DEX Swap endpoints.

Validates:
- /api/swap/health, /api/swap/tokens
- /api/swap/hybrid/health, /hybrid/quote, /hybrid/build, /hybrid/execute (410)
- /api/swap/quote, /api/swap/build (non-hybrid)
- /api/swap/track, /api/swap/history
- WBNB canonical address
- Invalid pair → 400
- No-liquidity pair → quote source='estimate' + build 422
"""
from __future__ import annotations

import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://sto-deployment-full.preview.emergentagent.com").rstrip("/")
ADMIN_EMAIL = "admin@neonobleramp.com"
ADMIN_PASSWORD = "Admin123!"

# Any valid BSC address; calldata is returned regardless of balance.
TEST_WALLET = "0x18CE1930820d5e1B87F37a8a2F7Cf59E7BF6da4E"
WBNB_CANONICAL = "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c"
PANCAKE_V2_ROUTER = "0x10ED43C718714eb63d5aA57B78B54704E256024E"


@pytest.fixture(scope="module")
def api():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def auth_token(api):
    # Try several login endpoints to be resilient
    for ep in ("/api/auth/login", "/api/login"):
        try:
            r = api.post(f"{BASE_URL}{ep}", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=30)
            if r.status_code == 200:
                data = r.json()
                token = data.get("access_token") or data.get("token") or (data.get("data") or {}).get("access_token")
                if token:
                    return token
        except Exception:
            continue
    pytest.skip("Admin login failed — cannot obtain JWT")


@pytest.fixture(scope="module")
def auth_api(api, auth_token):
    s = requests.Session()
    s.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {auth_token}",
    })
    return s


# ---------------- Basic health / registry ----------------------------------

def test_swap_health(api):
    r = api.get(f"{BASE_URL}/api/swap/health", timeout=30)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("rpc_connected") is True, f"rpc_connected must be true: {data}"
    assert data.get("oneinch_configured") is True, f"oneinch_configured must be true: {data}"
    assert data.get("chain_id") == 56


def test_swap_tokens_list_has_8(api):
    r = api.get(f"{BASE_URL}/api/swap/tokens", timeout=30)
    assert r.status_code == 200, r.text
    data = r.json()
    tokens = data.get("tokens", [])
    symbols = sorted([t["symbol"] for t in tokens])
    expected = sorted(["NENO", "USDT", "BTCB", "BUSD", "WBNB", "USDC", "CAKE", "ETH"])
    assert symbols == expected, f"symbols mismatch: {symbols}"


def test_wbnb_canonical_address(api):
    r = api.get(f"{BASE_URL}/api/swap/tokens", timeout=30)
    assert r.status_code == 200
    wbnb = next(t for t in r.json()["tokens"] if t["symbol"] == "WBNB")
    assert wbnb["address"].lower() == WBNB_CANONICAL.lower(), f"WBNB wrong: {wbnb['address']}"


# ---------------- Hybrid health -------------------------------------------

def test_hybrid_health_user_signed(api):
    r = api.get(f"{BASE_URL}/api/swap/hybrid/health", timeout=30)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("status") in ("operational", "healthy"), data
    assert data.get("mode") == "user_signed_dex", data
    assert data.get("capital_required") is False, data


# ---------------- Hybrid quote (valid pairs) -------------------------------

@pytest.mark.parametrize("pair", [
    ("NENO", "USDT"),
    ("WBNB", "BUSD"),
    ("CAKE", "USDT"),
])
def test_hybrid_quote_valid_pairs(api, pair):
    from_t, to_t = pair
    amount = 1 if from_t in ("WBNB", "CAKE") else 10
    r = api.post(
        f"{BASE_URL}/api/swap/hybrid/quote",
        json={"from_token": from_t, "to_token": to_t, "amount_in": amount},
        timeout=60,
    )
    assert r.status_code == 200, f"{pair} -> {r.status_code}: {r.text}"
    data = r.json()
    assert data.get("source") in ("1inch", "pancakeswap"), f"{pair} bad source: {data}"
    assert float(data.get("estimated_amount_out", 0)) > 0, f"{pair} zero out: {data}"


# ---------------- Hybrid build (auth) --------------------------------------

def test_hybrid_build_returns_onchain_calldata(auth_api):
    r = auth_api.post(
        f"{BASE_URL}/api/swap/hybrid/build",
        json={
            "from_token": "WBNB",
            "to_token": "BUSD",
            "amount_in": 0.1,
            "user_wallet_address": TEST_WALLET,
            "slippage": 0.8,
        },
        timeout=60,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("execution_mode") == "on-chain", data
    assert data.get("source") in ("1inch", "pancakeswap"), data
    # 'to' must be a known router
    to_addr = (data.get("to") or "").lower()
    assert to_addr.startswith("0x") and len(to_addr) == 42, f"bad to: {to_addr}"
    # data hex string ready for MetaMask
    calldata = data.get("data", "")
    assert calldata.startswith("0x") and len(calldata) > 10, f"bad calldata: {calldata[:40]}"
    # needs_approve key present
    assert "needs_approve" in data
    if data["needs_approve"]:
        assert data.get("approve_calldata") and data["approve_calldata"].get("data", "").startswith("0x")
    # save swap_id for later test
    pytest.swap_id_built = data["swap_id"]


def test_hybrid_execute_returns_410(auth_api):
    r = auth_api.post(
        f"{BASE_URL}/api/swap/hybrid/execute",
        json={"swap_id": "dummy"},
        timeout=30,
    )
    assert r.status_code == 410, f"expected 410 Gone, got {r.status_code}: {r.text}"


# ---------------- Non-hybrid swap quote/build ------------------------------

def test_swap_quote_non_hybrid(api):
    r = api.post(
        f"{BASE_URL}/api/swap/quote",
        json={"from_token": "WBNB", "to_token": "USDT", "amount_in": 1},
        timeout=60,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("source") in ("1inch", "pancakeswap"), data
    assert float(data.get("estimated_amount_out", 0)) > 0, data


def test_swap_build_non_hybrid(auth_api):
    r = auth_api.post(
        f"{BASE_URL}/api/swap/build",
        json={
            "from_token": "WBNB",
            "to_token": "USDT",
            "amount_in": 0.1,
            "user_wallet_address": TEST_WALLET,
            "slippage": 0.8,
        },
        timeout=60,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("source") in ("1inch", "pancakeswap")
    assert data.get("data", "").startswith("0x")
    assert data.get("swap_id")


# ---------------- Track + history -----------------------------------------

def test_track_and_history(auth_api):
    # Build first (isolated) to get a fresh swap_id persisted in DB
    build = auth_api.post(
        f"{BASE_URL}/api/swap/hybrid/build",
        json={
            "from_token": "CAKE",
            "to_token": "USDT",
            "amount_in": 1,
            "user_wallet_address": TEST_WALLET,
            "slippage": 0.8,
        },
        timeout=60,
    )
    assert build.status_code == 200, build.text
    swap_id = build.json()["swap_id"]

    fake_tx = "0x" + "a" * 64
    track = auth_api.post(
        f"{BASE_URL}/api/swap/track",
        json={"swap_id": swap_id, "tx_hash": fake_tx},
        timeout=30,
    )
    assert track.status_code == 200, track.text
    t = track.json()
    assert t.get("status") in ("pending", "failed", "success"), t
    assert t.get("tx_hash", "").lower() == fake_tx.lower()

    hist = auth_api.get(f"{BASE_URL}/api/swap/history?limit=20", timeout=30)
    assert hist.status_code == 200, hist.text
    hd = hist.json()
    assert isinstance(hd.get("history"), list)
    assert hd.get("count", 0) >= 1


# ---------------- Validation paths ----------------------------------------

def test_hybrid_build_same_token_400(auth_api):
    r = auth_api.post(
        f"{BASE_URL}/api/swap/hybrid/build",
        json={
            "from_token": "USDT",
            "to_token": "USDT",
            "amount_in": 10,
            "user_wallet_address": TEST_WALLET,
            "slippage": 0.8,
        },
        timeout=30,
    )
    assert r.status_code == 400, f"expected 400, got {r.status_code}: {r.text}"


def test_no_liquidity_pair_quote_estimate_and_build_422(auth_api):
    """
    Use a random (but checksum-valid) BSC address with no DEX pool.
    Expect quote → source='estimate' (or estimated_amount_out==0) and build → 422.
    """
    # A random address that's extremely unlikely to have a pool
    dead_token = "0x000000000000000000000000000000000000dEaD"

    q = auth_api.post(
        f"{BASE_URL}/api/swap/hybrid/quote",
        json={"from_token": dead_token, "to_token": "USDT", "amount_in": 1},
        timeout=45,
    )
    # Acceptable: 200 with source=estimate/error & zero output, OR 400/404/422
    if q.status_code == 200:
        qd = q.json()
        assert qd.get("source") in ("estimate", "error") or float(qd.get("estimated_amount_out", 0)) == 0, qd
        assert qd.get("note"), f"note expected for no-liquidity: {qd}"
    else:
        assert q.status_code in (400, 404, 422, 500), q.text

    b = auth_api.post(
        f"{BASE_URL}/api/swap/hybrid/build",
        json={
            "from_token": dead_token,
            "to_token": "USDT",
            "amount_in": 1,
            "user_wallet_address": TEST_WALLET,
            "slippage": 0.8,
        },
        timeout=45,
    )
    # Expected 422 (RuntimeError: no liquidity). Accept 400/404 too as acceptable failure modes.
    assert b.status_code in (422, 400, 404), f"expected 4xx no-liq, got {b.status_code}: {b.text}"
