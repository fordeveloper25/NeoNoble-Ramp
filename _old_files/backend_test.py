#!/usr/bin/env python3
"""
Backend Testing for NeoNoble User-Signed Swap Endpoints
Testing the new /api/swap/build and /api/swap/track endpoints
"""

import asyncio
import json
import os
import sys
import uuid
from decimal import Decimal

import aiohttp

# Backend URL from frontend/.env
BACKEND_URL = "https://sto-deployment-full.preview.emergentagent.com"
API_BASE = f"{BACKEND_URL}/api"

# Test credentials
TEST_USER = {
    "email": "test@example.com",
    "password": "Test1234!",
    "first_name": "Test",
    "last_name": "User"
}

# Test wallet address for BSC
TEST_WALLET = "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb1"

class SwapTester:
    def __init__(self):
        self.session = None
        self.jwt_token = None
        self.user_id = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def register_and_login(self):
        """Register a fresh test user and get JWT token"""
        print("🔐 Registering test user...")
        
        # Register user
        register_data = {
            "email": TEST_USER["email"],
            "password": TEST_USER["password"],
            "first_name": TEST_USER["first_name"],
            "last_name": TEST_USER["last_name"]
        }
        
        async with self.session.post(f"{API_BASE}/auth/register", json=register_data) as resp:
            if resp.status == 200:
                data = await resp.json()
                if data.get("success"):
                    print("✅ User registered successfully")
                    # Check if token is provided in registration response
                    if "token" in data:
                        self.jwt_token = data["token"]
                        if "user" in data and "id" in data["user"]:
                            self.user_id = data["user"]["id"]
                        print(f"✅ JWT from registration: {self.jwt_token[:20]}...")
                        return True
                else:
                    print("ℹ️ Registration response indicates failure, proceeding to login")
            elif resp.status == 400:
                # User might already exist, try login
                print("ℹ️ User already exists, proceeding to login")
            else:
                text = await resp.text()
                print(f"❌ Registration failed: {resp.status} - {text}")
                return False
        
        # Login to get JWT (if not already obtained from registration)
        if not self.jwt_token:
            login_data = {
                "email": TEST_USER["email"],
                "password": TEST_USER["password"]
            }
            
            async with self.session.post(f"{API_BASE}/auth/login", json=login_data) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    self.jwt_token = data.get("access_token") or data.get("token")
                    self.user_id = data.get("user_id") or (data.get("user", {}).get("id"))
                    print(f"✅ Login successful, JWT: {self.jwt_token[:20]}...")
                    return True
                else:
                    text = await resp.text()
                    print(f"❌ Login failed: {resp.status} - {text}")
                    return False
        
        return True
    
    def get_auth_headers(self):
        """Get authorization headers with JWT"""
        if not self.jwt_token:
            return {}
        return {"Authorization": f"Bearer {self.jwt_token}"}
    
    async def test_sanity_checks(self):
        """Test basic endpoints that should already be working"""
        print("\n🔍 SANITY CHECKS")
        print("=" * 50)
        
        # Test health endpoint
        print("Testing GET /api/swap/health...")
        async with self.session.get(f"{API_BASE}/swap/health") as resp:
            if resp.status == 200:
                data = await resp.json()
                print(f"✅ Health check passed")
                print(f"   Mode: {data.get('mode')}")
                print(f"   RPC Connected: {data.get('rpc_connected')}")
                print(f"   1inch Configured: {data.get('oneinch_configured')}")
                print(f"   Chain ID: {data.get('chain_id')}")
                print(f"   Supported Tokens: {len(data.get('supported_tokens', []))}")
                
                # Verify expected values
                if data.get('mode') != 'user_signed':
                    print(f"⚠️ Expected mode='user_signed', got '{data.get('mode')}'")
                if data.get('chain_id') != 56:
                    print(f"⚠️ Expected chain_id=56, got {data.get('chain_id')}")
                if len(data.get('supported_tokens', [])) != 8:
                    print(f"⚠️ Expected 8 tokens, got {len(data.get('supported_tokens', []))}")
                if 'hot_wallet' in data and data['hot_wallet']:
                    print(f"⚠️ Hot wallet should be absent or empty in user-signed mode, got: {data['hot_wallet']}")
            else:
                text = await resp.text()
                print(f"❌ Health check failed: {resp.status} - {text}")
        
        # Test tokens endpoint
        print("\nTesting GET /api/swap/tokens...")
        async with self.session.get(f"{API_BASE}/swap/tokens") as resp:
            if resp.status == 200:
                data = await resp.json()
                tokens = data.get('tokens', [])
                print(f"✅ Tokens endpoint passed - {len(tokens)} tokens")
                if len(tokens) != 8:
                    print(f"⚠️ Expected 8 tokens, got {len(tokens)}")
            else:
                text = await resp.text()
                print(f"❌ Tokens endpoint failed: {resp.status} - {text}")
        
        # Test quote endpoint
        print("\nTesting POST /api/swap/quote...")
        quote_data = {
            "from_token": "USDT",
            "to_token": "BTCB",
            "amount_in": 100
        }
        async with self.session.post(f"{API_BASE}/swap/quote", json=quote_data) as resp:
            if resp.status == 200:
                data = await resp.json()
                print(f"✅ Quote endpoint passed")
                print(f"   Source: {data.get('source')}")
                print(f"   Estimated output: {data.get('estimated_amount_out')}")
                if data.get('estimated_amount_out', 0) <= 0:
                    print(f"⚠️ Expected positive estimated_amount_out")
            else:
                text = await resp.text()
                print(f"❌ Quote endpoint failed: {resp.status} - {text}")
    
    async def test_swap_build(self):
        """Test the new /api/swap/build endpoint"""
        print("\n🔨 TESTING /api/swap/build")
        print("=" * 50)
        
        # A1: Unauthenticated call
        print("A1: Testing unauthenticated call...")
        build_data = {
            "from_token": "USDT",
            "to_token": "BTCB",
            "amount_in": 1,
            "user_wallet_address": TEST_WALLET
        }
        async with self.session.post(f"{API_BASE}/swap/build", json=build_data) as resp:
            if resp.status == 401:
                print("✅ A1 PASSED: Unauthenticated call correctly rejected with 401")
            else:
                text = await resp.text()
                print(f"❌ A1 FAILED: Expected 401, got {resp.status} - {text}")
        
        # A2: Happy path with JWT
        print("\nA2: Testing happy path (USDT→BTCB)...")
        headers = self.get_auth_headers()
        async with self.session.post(f"{API_BASE}/swap/build", json=build_data, headers=headers) as resp:
            if resp.status == 200:
                data = await resp.json()
                print("✅ A2 PASSED: Build endpoint returned 200")
                
                # Verify required fields
                required_fields = [
                    'swap_id', 'source', 'to', 'data', 'value', 'chain_id',
                    'spender', 'needs_approve', 'estimated_amount_out',
                    'estimated_amount_out_human', 'amount_in', 'amount_in_human',
                    'user_wallet', 'slippage_pct'
                ]
                
                for field in required_fields:
                    if field not in data:
                        print(f"❌ Missing required field: {field}")
                    else:
                        print(f"   ✓ {field}: {data[field]}")
                
                # Verify specific values
                if data.get('chain_id') != 56:
                    print(f"❌ Expected chain_id=56, got {data.get('chain_id')}")
                
                if data.get('source') not in ['1inch', 'pancakeswap']:
                    print(f"❌ Expected source '1inch' or 'pancakeswap', got '{data.get('source')}'")
                
                if not data.get('to', '').startswith('0x') or len(data.get('to', '')) != 42:
                    print(f"❌ Invalid 'to' address: {data.get('to')}")
                
                if not data.get('data', '').startswith('0x') or len(data.get('data', '')) <= 10:
                    print(f"❌ Invalid 'data' field: {data.get('data', '')[:50]}...")
                
                if not data.get('value', '').startswith('0x'):
                    print(f"❌ Invalid 'value' field: {data.get('value')}")
                
                if data.get('amount_in_human') != 1:
                    print(f"❌ Expected amount_in_human=1, got {data.get('amount_in_human')}")
                
                if data.get('user_wallet').lower() != TEST_WALLET.lower():
                    print(f"❌ Expected user_wallet={TEST_WALLET}, got {data.get('user_wallet')}")
                
                # Check approval logic
                if data.get('needs_approve'):
                    approve_cd = data.get('approve_calldata')
                    if not approve_cd:
                        print("❌ needs_approve=true but approve_calldata is missing")
                    else:
                        print(f"   ✓ Approval needed, calldata provided")
                        if not approve_cd.get('to', '').lower() == '0x55d398326f99059fF775485246999027B3197955'.lower():
                            print(f"❌ Expected USDT contract in approve_calldata.to, got {approve_cd.get('to')}")
                        if not approve_cd.get('data', '').startswith('0x095ea7b3'):
                            print(f"❌ Expected approve selector 0x095ea7b3, got {approve_cd.get('data', '')[:10]}")
                        if len(approve_cd.get('data', '')) != 138:
                            print(f"❌ Expected approve calldata length 138, got {len(approve_cd.get('data', ''))}")
                
                # Store swap_id for tracking test
                self.test_swap_id = data.get('swap_id')
                print(f"   ✓ Stored swap_id for tracking: {self.test_swap_id}")
                
            else:
                text = await resp.text()
                print(f"❌ A2 FAILED: Expected 200, got {resp.status} - {text}")
        
        # A3: Invalid wallet address
        print("\nA3: Testing invalid wallet address...")
        invalid_build_data = {
            "from_token": "USDT",
            "to_token": "BTCB",
            "amount_in": 1,
            "user_wallet_address": "not-a-hex-address"
        }
        async with self.session.post(f"{API_BASE}/swap/build", json=invalid_build_data, headers=headers) as resp:
            if resp.status == 400:
                print("✅ A3 PASSED: Invalid wallet address correctly rejected with 400")
            else:
                text = await resp.text()
                print(f"❌ A3 FAILED: Expected 400, got {resp.status} - {text}")
        
        # A4: Same token
        print("\nA4: Testing same token swap...")
        same_token_data = {
            "from_token": "USDT",
            "to_token": "USDT",
            "amount_in": 1,
            "user_wallet_address": TEST_WALLET
        }
        async with self.session.post(f"{API_BASE}/swap/build", json=same_token_data, headers=headers) as resp:
            if resp.status == 400:
                print("✅ A4 PASSED: Same token swap correctly rejected with 400")
            else:
                text = await resp.text()
                print(f"❌ A4 FAILED: Expected 400, got {resp.status} - {text}")
        
        # A5: Unsupported token
        print("\nA5: Testing unsupported token...")
        unsupported_token_data = {
            "from_token": "FAKE",
            "to_token": "BTCB",
            "amount_in": 1,
            "user_wallet_address": TEST_WALLET
        }
        async with self.session.post(f"{API_BASE}/swap/build", json=unsupported_token_data, headers=headers) as resp:
            if resp.status == 400:
                print("✅ A5 PASSED: Unsupported token correctly rejected with 400")
            else:
                text = await resp.text()
                print(f"❌ A5 FAILED: Expected 400, got {resp.status} - {text}")
    
    async def test_swap_track(self):
        """Test the new /api/swap/track endpoint"""
        print("\n📍 TESTING /api/swap/track")
        print("=" * 50)
        
        # B1: Unauthenticated call
        print("B1: Testing unauthenticated call...")
        track_data = {
            "swap_id": str(uuid.uuid4()),
            "tx_hash": "0x0000000000000000000000000000000000000000000000000000000000000001"
        }
        async with self.session.post(f"{API_BASE}/swap/track", json=track_data) as resp:
            if resp.status == 401:
                print("✅ B1 PASSED: Unauthenticated call correctly rejected with 401")
            else:
                text = await resp.text()
                print(f"❌ B1 FAILED: Expected 401, got {resp.status} - {text}")
        
        # B2: Valid JWT with non-existent tx hash
        print("\nB2: Testing valid JWT with non-existent tx hash...")
        headers = self.get_auth_headers()
        test_swap_id = getattr(self, 'test_swap_id', str(uuid.uuid4()))
        track_data = {
            "swap_id": test_swap_id,
            "tx_hash": "0x0000000000000000000000000000000000000000000000000000000000000001"
        }
        async with self.session.post(f"{API_BASE}/swap/track", json=track_data, headers=headers) as resp:
            if resp.status == 200:
                data = await resp.json()
                print("✅ B2 PASSED: Track endpoint returned 200")
                print(f"   Status: {data.get('status')}")
                print(f"   Explorer URL: {data.get('explorer_url')}")
                print(f"   Block number: {data.get('block_number')}")
                print(f"   Gas used: {data.get('gas_used')}")
                
                # Verify expected values
                if data.get('status') != 'pending':
                    print(f"❌ Expected status='pending', got '{data.get('status')}'")
                
                expected_url = f"https://bscscan.com/tx/{track_data['tx_hash']}"
                if data.get('explorer_url') != expected_url:
                    print(f"❌ Expected explorer_url='{expected_url}', got '{data.get('explorer_url')}'")
                
                if data.get('block_number') is not None:
                    print(f"⚠️ Expected block_number=null for pending tx, got {data.get('block_number')}")
                
                if data.get('gas_used') is not None:
                    print(f"⚠️ Expected gas_used=null for pending tx, got {data.get('gas_used')}")
                
            else:
                text = await resp.text()
                print(f"❌ B2 FAILED: Expected 200, got {resp.status} - {text}")
        
        # B3: Valid JWT with prefixless hex
        print("\nB3: Testing prefixless hex tx hash...")
        track_data_no_prefix = {
            "swap_id": str(uuid.uuid4()),
            "tx_hash": "0000000000000000000000000000000000000000000000000000000000000002"
        }
        async with self.session.post(f"{API_BASE}/swap/track", json=track_data_no_prefix, headers=headers) as resp:
            if resp.status == 200:
                data = await resp.json()
                print("✅ B3 PASSED: Track endpoint handled prefixless hex")
                returned_hash = data.get('tx_hash')
                if returned_hash and returned_hash.startswith('0x'):
                    print(f"   ✓ Correctly added 0x prefix: {returned_hash}")
                else:
                    print(f"❌ Expected 0x prefix to be added, got: {returned_hash}")
            else:
                text = await resp.text()
                print(f"❌ B3 FAILED: Expected 200, got {resp.status} - {text}")
    
    async def test_swap_history(self):
        """Test the swap history endpoint"""
        print("\n📜 TESTING /api/swap/history")
        print("=" * 50)
        
        headers = self.get_auth_headers()
        async with self.session.get(f"{API_BASE}/swap/history", headers=headers) as resp:
            if resp.status == 200:
                data = await resp.json()
                print("✅ History endpoint passed")
                print(f"   User ID: {data.get('user_id')}")
                print(f"   Count: {data.get('count')}")
                print(f"   History length: {len(data.get('history', []))}")
                
                # Check if we have the built swap from earlier test
                history = data.get('history', [])
                if history:
                    latest = history[0]
                    print(f"   Latest swap status: {latest.get('status')}")
                    print(f"   Latest swap mode: {latest.get('mode')}")
                    if latest.get('status') not in ['built', 'pending', 'success']:
                        print(f"⚠️ Unexpected status: {latest.get('status')}")
                    if latest.get('mode') != 'user_signed':
                        print(f"⚠️ Expected mode='user_signed', got '{latest.get('mode')}'")
                
            else:
                text = await resp.text()
                print(f"❌ History endpoint failed: {resp.status} - {text}")
    
    async def test_auth_regression(self):
        """Test that auth endpoints still work"""
        print("\n🔐 AUTH REGRESSION TESTS")
        print("=" * 50)
        
        # Test /api/auth/me
        print("Testing GET /api/auth/me...")
        headers = self.get_auth_headers()
        async with self.session.get(f"{API_BASE}/auth/me", headers=headers) as resp:
            if resp.status == 200:
                data = await resp.json()
                print("✅ /api/auth/me working")
                print(f"   User ID: {data.get('user_id')}")
                print(f"   Email: {data.get('email')}")
            else:
                text = await resp.text()
                print(f"❌ /api/auth/me failed: {resp.status} - {text}")
    
    async def run_all_tests(self):
        """Run all tests in sequence"""
        print("🚀 STARTING USER-SIGNED SWAP ENDPOINT TESTS")
        print("=" * 60)
        
        # Register and login
        if not await self.register_and_login():
            print("❌ Failed to authenticate, aborting tests")
            return
        
        # Run test suites
        await self.test_sanity_checks()
        await self.test_swap_build()
        await self.test_swap_track()
        await self.test_swap_history()
        await self.test_auth_regression()
        
        print("\n🏁 TESTING COMPLETE")
        print("=" * 60)

async def main():
    """Main test runner"""
    async with SwapTester() as tester:
        await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())