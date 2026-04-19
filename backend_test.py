#!/usr/bin/env python3
"""
NeoNoble Ramp Backend Testing Suite

Tests the new on-chain swap feature and verifies existing auth/ramp backend
functionality after the significant cleanup of broken syntax in server.py.

Test credentials from /app/memory/test_credentials.md:
- Platform admin: admin@neonobleramp.com / Admin1234!
- Or register a new test user via POST /api/auth/register

Backend base URL: from REACT_APP_BACKEND_URL in /app/frontend/.env
All routes MUST be prefixed with /api
"""

import asyncio
import json
import os
import sys
from decimal import Decimal
from typing import Dict, Any, Optional

import aiohttp
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class NeoNobleBackendTester:
    def __init__(self):
        # Read backend URL from frontend .env
        self.base_url = self._get_backend_url()
        self.session: Optional[aiohttp.ClientSession] = None
        self.jwt_token: Optional[str] = None
        self.test_user_id: Optional[str] = None
        
        # Test credentials - try both passwords from review request and test_credentials.md
        self.admin_email = "admin@neonobleramp.com"
        self.admin_password = "NeoNoble2025!"  # From review request
        self.fallback_password = "Admin1234!"  # From test_credentials.md
        
        # Test results
        self.results = {
            "boot_health": {"passed": False, "details": ""},
            "auth_login": {"passed": False, "details": ""},
            "swap_health": {"passed": False, "details": ""},
            "swap_tokens": {"passed": False, "details": ""},
            "swap_quote_valid": {"passed": False, "details": ""},
            "swap_quote_neno": {"passed": False, "details": ""},
            "swap_quote_invalid": {"passed": False, "details": ""},
            "swap_execute_no_auth": {"passed": False, "details": ""},
            "swap_execute_invalid_wallet": {"passed": False, "details": ""},
            "swap_execute_same_token": {"passed": False, "details": ""},
            "swap_execute_valid": {"passed": False, "details": ""},
            "swap_history_no_auth": {"passed": False, "details": ""},
            "swap_history_with_auth": {"passed": False, "details": ""},
            "auth_register": {"passed": False, "details": ""},
            "auth_me": {"passed": False, "details": ""},
            "existing_endpoints": {"passed": False, "details": ""}
        }

    def _get_backend_url(self) -> str:
        """Read REACT_APP_BACKEND_URL from frontend/.env"""
        try:
            env_path = "/app/frontend/.env"
            with open(env_path, 'r') as f:
                for line in f:
                    if line.startswith('REACT_APP_BACKEND_URL='):
                        url = line.split('=', 1)[1].strip()
                        logger.info(f"Backend URL from .env: {url}")
                        return url
            raise ValueError("REACT_APP_BACKEND_URL not found in .env")
        except Exception as e:
            logger.error(f"Failed to read backend URL: {e}")
            # Fallback
            return "https://neno-swap-live.preview.emergentagent.com"

    async def setup_session(self):
        """Initialize aiohttp session"""
        timeout = aiohttp.ClientTimeout(total=30)
        self.session = aiohttp.ClientSession(timeout=timeout)

    async def cleanup_session(self):
        """Close aiohttp session"""
        if self.session:
            await self.session.close()

    async def make_request(self, method: str, endpoint: str, data: Dict = None, 
                          headers: Dict = None, expect_status: int = 200) -> Dict[str, Any]:
        """Make HTTP request to backend"""
        url = f"{self.base_url}/api{endpoint}"
        
        # Add auth header if we have a token
        if self.jwt_token and headers is None:
            headers = {}
        if self.jwt_token and headers is not None:
            headers["Authorization"] = f"Bearer {self.jwt_token}"
        
        try:
            async with self.session.request(method, url, json=data, headers=headers) as resp:
                response_text = await resp.text()
                
                # Try to parse as JSON
                try:
                    response_data = json.loads(response_text) if response_text else {}
                except json.JSONDecodeError:
                    response_data = {"raw_response": response_text}
                
                return {
                    "status": resp.status,
                    "data": response_data,
                    "headers": dict(resp.headers),
                    "success": resp.status == expect_status
                }
        except Exception as e:
            logger.error(f"Request failed {method} {url}: {e}")
            return {
                "status": 0,
                "data": {"error": str(e)},
                "headers": {},
                "success": False
            }

    async def test_boot_health(self):
        """Test 1: Boot health - GET /api/health"""
        logger.info("🔍 Testing boot health...")
        
        try:
            result = await self.make_request("GET", "/health")
            
            if result["success"] and result["status"] == 200:
                data = result["data"]
                if "status" in data and data["status"] == "healthy":
                    self.results["boot_health"]["passed"] = True
                    self.results["boot_health"]["details"] = "✅ Health endpoint working"
                    logger.info("✅ Boot health check passed")
                else:
                    self.results["boot_health"]["details"] = f"❌ Unexpected health response: {data}"
            else:
                self.results["boot_health"]["details"] = f"❌ Health check failed: {result['status']} - {result['data']}"
                
        except Exception as e:
            self.results["boot_health"]["details"] = f"❌ Health check error: {e}"
            logger.error(f"Boot health test failed: {e}")

    async def test_auth_login(self):
        """Test 2: Auth login with admin credentials"""
        logger.info("🔍 Testing auth login...")
        
        try:
            # Try primary password first
            login_data = {
                "email": self.admin_email,
                "password": self.admin_password
            }
            
            result = await self.make_request("POST", "/auth/login", data=login_data)
            
            # If primary fails, try fallback password
            if result["status"] == 401:
                logger.info("Primary password failed, trying fallback...")
                login_data["password"] = self.fallback_password
                result = await self.make_request("POST", "/auth/login", data=login_data)
            
            # If both admin passwords fail, try to register a new test user
            if result["status"] == 401:
                logger.info("Admin login failed, registering new test user...")
                import time
                test_email = f"testuser_{int(time.time())}@example.com"
                register_data = {
                    "email": test_email,
                    "password": "TestPassword123!",
                    "role": "USER"
                }
                
                register_result = await self.make_request("POST", "/auth/register", data=register_data)
                if register_result["status"] == 200 and register_result["data"].get("token"):
                    self.jwt_token = register_result["data"]["token"]
                    self.results["auth_login"]["passed"] = True
                    self.results["auth_login"]["details"] = f"✅ New test user registered and logged in: {test_email}"
                    logger.info("✅ Auth login passed via registration")
                    return
            
            if result["success"] and result["status"] == 200:
                data = result["data"]
                if "token" in data and data.get("success"):
                    self.jwt_token = data["token"]
                    if "user" in data:
                        self.test_user_id = data["user"].get("id")
                    self.results["auth_login"]["passed"] = True
                    self.results["auth_login"]["details"] = "✅ Admin login successful, JWT received"
                    logger.info("✅ Auth login passed")
                else:
                    self.results["auth_login"]["details"] = f"❌ Login response missing token: {data}"
            else:
                self.results["auth_login"]["details"] = f"❌ Login failed: {result['status']} - {result['data']}"
                
        except Exception as e:
            self.results["auth_login"]["details"] = f"❌ Login error: {e}"
            logger.error(f"Auth login test failed: {e}")

    async def test_swap_health(self):
        """Test 3: Swap engine health"""
        logger.info("🔍 Testing swap engine health...")
        
        try:
            result = await self.make_request("GET", "/swap/health")
            
            if result["success"] and result["status"] == 200:
                data = result["data"]
                
                # Check required fields
                required_fields = ["hot_wallet_configured", "rpc_connected", "oneinch_configured", "supported_tokens"]
                missing_fields = [f for f in required_fields if f not in data]
                
                if not missing_fields:
                    # Check specific values
                    hot_wallet = data.get("hot_wallet", "")
                    hot_wallet_configured = data.get("hot_wallet_configured", False)
                    rpc_connected = data.get("rpc_connected", False)
                    oneinch_configured = data.get("oneinch_configured", False)
                    supported_tokens = data.get("supported_tokens", [])
                    
                    if (hot_wallet == "0x18CE1930820d5e1B87F37a8a2F7Cf59E7BF6da4E" and
                        hot_wallet_configured and rpc_connected and oneinch_configured and
                        len(supported_tokens) == 8):
                        
                        self.results["swap_health"]["passed"] = True
                        self.results["swap_health"]["details"] = "✅ Swap health check passed - all systems configured"
                        logger.info("✅ Swap health check passed")
                    else:
                        self.results["swap_health"]["details"] = (
                            f"❌ Swap health check failed - "
                            f"hot_wallet_configured: {hot_wallet_configured}, "
                            f"rpc_connected: {rpc_connected}, "
                            f"oneinch_configured: {oneinch_configured}, "
                            f"supported_tokens count: {len(supported_tokens)}"
                        )
                else:
                    self.results["swap_health"]["details"] = f"❌ Missing required fields: {missing_fields}"
            else:
                self.results["swap_health"]["details"] = f"❌ Swap health failed: {result['status']} - {result['data']}"
                
        except Exception as e:
            self.results["swap_health"]["details"] = f"❌ Swap health error: {e}"
            logger.error(f"Swap health test failed: {e}")

    async def test_swap_tokens(self):
        """Test 4: Swap tokens endpoint"""
        logger.info("🔍 Testing swap tokens...")
        
        try:
            result = await self.make_request("GET", "/swap/tokens")
            
            if result["success"] and result["status"] == 200:
                data = result["data"]
                
                if "chain" in data and "tokens" in data:
                    chain = data["chain"]
                    tokens = data["tokens"]
                    
                    if chain == "bsc" and len(tokens) == 8:
                        # Check for expected tokens
                        expected_symbols = {"NENO", "USDT", "BTCB", "BUSD", "WBNB", "USDC", "CAKE", "ETH"}
                        actual_symbols = {token["symbol"] for token in tokens}
                        
                        if expected_symbols == actual_symbols:
                            # Check token structure
                            valid_tokens = all(
                                "symbol" in token and "address" in token and 
                                "decimals" in token and "name" in token and "logo" in token
                                for token in tokens
                            )
                            
                            if valid_tokens:
                                self.results["swap_tokens"]["passed"] = True
                                self.results["swap_tokens"]["details"] = "✅ Swap tokens endpoint working - 8 BSC tokens returned"
                                logger.info("✅ Swap tokens test passed")
                            else:
                                self.results["swap_tokens"]["details"] = "❌ Token structure invalid"
                        else:
                            missing = expected_symbols - actual_symbols
                            extra = actual_symbols - expected_symbols
                            self.results["swap_tokens"]["details"] = f"❌ Token mismatch - missing: {missing}, extra: {extra}"
                    else:
                        self.results["swap_tokens"]["details"] = f"❌ Expected BSC chain with 8 tokens, got {chain} with {len(tokens)} tokens"
                else:
                    self.results["swap_tokens"]["details"] = f"❌ Missing chain or tokens in response: {data}"
            else:
                self.results["swap_tokens"]["details"] = f"❌ Swap tokens failed: {result['status']} - {result['data']}"
                
        except Exception as e:
            self.results["swap_tokens"]["details"] = f"❌ Swap tokens error: {e}"
            logger.error(f"Swap tokens test failed: {e}")

    async def test_swap_quote_valid(self):
        """Test 5: Valid swap quote (USDT -> BTCB)"""
        logger.info("🔍 Testing valid swap quote (USDT -> BTCB)...")
        
        try:
            quote_data = {
                "from_token": "USDT",
                "to_token": "BTCB",
                "amount_in": 100
            }
            
            result = await self.make_request("POST", "/swap/quote", data=quote_data)
            
            if result["success"] and result["status"] == 200:
                data = result["data"]
                
                required_fields = ["from_token", "to_token", "amount_in", "estimated_amount_out", "source"]
                missing_fields = [f for f in required_fields if f not in data]
                
                if not missing_fields:
                    source = data.get("source")
                    estimated_out = data.get("estimated_amount_out", 0)
                    
                    if source == "1inch" and estimated_out > 0:
                        self.results["swap_quote_valid"]["passed"] = True
                        self.results["swap_quote_valid"]["details"] = f"✅ Valid quote received - source: {source}, estimated_out: {estimated_out}"
                        logger.info("✅ Valid swap quote test passed")
                    else:
                        self.results["swap_quote_valid"]["details"] = f"❌ Quote validation failed - source: {source}, estimated_out: {estimated_out}"
                else:
                    self.results["swap_quote_valid"]["details"] = f"❌ Missing required fields: {missing_fields}"
            else:
                self.results["swap_quote_valid"]["details"] = f"❌ Quote request failed: {result['status']} - {result['data']}"
                
        except Exception as e:
            self.results["swap_quote_valid"]["details"] = f"❌ Valid quote error: {e}"
            logger.error(f"Valid swap quote test failed: {e}")

    async def test_swap_quote_neno(self):
        """Test 6: NENO swap quote (fallback expected)"""
        logger.info("🔍 Testing NENO swap quote (NENO -> USDT)...")
        
        try:
            quote_data = {
                "from_token": "NENO",
                "to_token": "USDT",
                "amount_in": 10
            }
            
            result = await self.make_request("POST", "/swap/quote", data=quote_data)
            
            if result["success"] and result["status"] == 200:
                data = result["data"]
                
                required_fields = ["from_token", "to_token", "amount_in", "estimated_amount_out", "source"]
                missing_fields = [f for f in required_fields if f not in data]
                
                if not missing_fields:
                    source = data.get("source")
                    estimated_out = data.get("estimated_amount_out", 0)
                    
                    # Accept any valid source (1inch, pancakeswap, or estimate)
                    valid_sources = {"1inch", "pancakeswap", "estimate"}
                    if source in valid_sources and estimated_out > 0:
                        self.results["swap_quote_neno"]["passed"] = True
                        self.results["swap_quote_neno"]["details"] = f"✅ NENO quote received - source: {source}, estimated_out: {estimated_out}"
                        logger.info("✅ NENO swap quote test passed")
                    else:
                        self.results["swap_quote_neno"]["details"] = f"❌ NENO quote validation failed - source: {source}, estimated_out: {estimated_out}"
                else:
                    self.results["swap_quote_neno"]["details"] = f"❌ Missing required fields: {missing_fields}"
            else:
                self.results["swap_quote_neno"]["details"] = f"❌ NENO quote request failed: {result['status']} - {result['data']}"
                
        except Exception as e:
            self.results["swap_quote_neno"]["details"] = f"❌ NENO quote error: {e}"
            logger.error(f"NENO swap quote test failed: {e}")

    async def test_swap_quote_invalid(self):
        """Test 7: Invalid token quote"""
        logger.info("🔍 Testing invalid token quote...")
        
        try:
            quote_data = {
                "from_token": "FOO",
                "to_token": "USDT",
                "amount_in": 1
            }
            
            result = await self.make_request("POST", "/swap/quote", data=quote_data, expect_status=400)
            
            if result["status"] == 400:
                self.results["swap_quote_invalid"]["passed"] = True
                self.results["swap_quote_invalid"]["details"] = "✅ Invalid token correctly rejected with 400"
                logger.info("✅ Invalid token quote test passed")
            else:
                self.results["swap_quote_invalid"]["details"] = f"❌ Expected 400, got {result['status']}"
                
        except Exception as e:
            self.results["swap_quote_invalid"]["details"] = f"❌ Invalid quote error: {e}"
            logger.error(f"Invalid swap quote test failed: {e}")

    async def test_swap_execute_no_auth(self):
        """Test 8: Execute without auth"""
        logger.info("🔍 Testing swap execute without auth...")
        
        try:
            execute_data = {
                "from_token": "USDT",
                "to_token": "BTCB",
                "amount_in": 1,
                "user_wallet_address": "0x18CE1930820d5e1B87F37a8a2F7Cf59E7BF6da4E"
            }
            
            # Make request without auth header
            result = await self.make_request("POST", "/swap/execute", data=execute_data, 
                                           headers={}, expect_status=401)
            
            if result["status"] == 401:
                self.results["swap_execute_no_auth"]["passed"] = True
                self.results["swap_execute_no_auth"]["details"] = "✅ Execute without auth correctly rejected with 401"
                logger.info("✅ Execute without auth test passed")
            else:
                self.results["swap_execute_no_auth"]["details"] = f"❌ Expected 401, got {result['status']}"
                
        except Exception as e:
            self.results["swap_execute_no_auth"]["details"] = f"❌ Execute no auth error: {e}"
            logger.error(f"Execute without auth test failed: {e}")

    async def test_swap_execute_invalid_wallet(self):
        """Test 9: Execute with invalid wallet address"""
        logger.info("🔍 Testing swap execute with invalid wallet...")
        
        try:
            execute_data = {
                "from_token": "USDT",
                "to_token": "BTCB",
                "amount_in": 1,
                "user_wallet_address": "not-an-address"
            }
            
            result = await self.make_request("POST", "/swap/execute", data=execute_data)
            
            # Should return success=false with error about invalid wallet
            if result["status"] == 200:
                data = result["data"]
                if not data.get("success") and "Invalid user_wallet_address" in str(data.get("error", "")):
                    self.results["swap_execute_invalid_wallet"]["passed"] = True
                    self.results["swap_execute_invalid_wallet"]["details"] = "✅ Invalid wallet address correctly rejected"
                    logger.info("✅ Invalid wallet address test passed")
                else:
                    self.results["swap_execute_invalid_wallet"]["details"] = f"❌ Unexpected response: {data}"
            elif result["status"] in [400, 422]:  # Could also be 4xx
                self.results["swap_execute_invalid_wallet"]["passed"] = True
                self.results["swap_execute_invalid_wallet"]["details"] = f"✅ Invalid wallet address rejected with {result['status']}"
                logger.info("✅ Invalid wallet address test passed")
            else:
                self.results["swap_execute_invalid_wallet"]["details"] = f"❌ Unexpected status: {result['status']}"
                
        except Exception as e:
            self.results["swap_execute_invalid_wallet"]["details"] = f"❌ Invalid wallet error: {e}"
            logger.error(f"Invalid wallet test failed: {e}")

    async def test_swap_execute_same_token(self):
        """Test 10: Execute with same from/to token"""
        logger.info("🔍 Testing swap execute with same token...")
        
        try:
            execute_data = {
                "from_token": "USDT",
                "to_token": "USDT",
                "amount_in": 1,
                "user_wallet_address": "0x18CE1930820d5e1B87F37a8a2F7Cf59E7BF6da4E"
            }
            
            result = await self.make_request("POST", "/swap/execute", data=execute_data)
            
            # Should return success=false with error about same tokens
            if result["status"] == 200:
                data = result["data"]
                if not data.get("success") and "from_token == to_token" in str(data.get("error", "")):
                    self.results["swap_execute_same_token"]["passed"] = True
                    self.results["swap_execute_same_token"]["details"] = "✅ Same token swap correctly rejected"
                    logger.info("✅ Same token swap test passed")
                else:
                    self.results["swap_execute_same_token"]["details"] = f"❌ Unexpected response: {data}"
            else:
                self.results["swap_execute_same_token"]["details"] = f"❌ Unexpected status: {result['status']}"
                
        except Exception as e:
            self.results["swap_execute_same_token"]["details"] = f"❌ Same token error: {e}"
            logger.error(f"Same token test failed: {e}")

    async def test_swap_execute_valid(self):
        """Test 11: Valid swap execute (likely Tier 4)"""
        logger.info("🔍 Testing valid swap execute...")
        
        try:
            execute_data = {
                "from_token": "USDT",
                "to_token": "BTCB",
                "amount_in": 1,
                "user_wallet_address": "0x18CE1930820d5e1B87F37a8a2F7Cf59E7BF6da4E",
                "slippage": 0.8
            }
            
            result = await self.make_request("POST", "/swap/execute", data=execute_data)
            
            if result["status"] == 200:
                data = result["data"]
                
                required_fields = ["success", "swap_id", "tier", "tier_label"]
                missing_fields = [f for f in required_fields if f not in data]
                
                if not missing_fields:
                    success = data.get("success")
                    swap_id = data.get("swap_id")
                    tier = data.get("tier")
                    tier_label = data.get("tier_label")
                    
                    if success and swap_id:
                        # Check tier response
                        valid_tiers = {"tier1", "tier2", "tier3", "tier4"}
                        if tier in valid_tiers:
                            if tier == "tier4":
                                # Tier 4 should have queued=true
                                queued = data.get("queued", False)
                                if queued:
                                    self.results["swap_execute_valid"]["passed"] = True
                                    self.results["swap_execute_valid"]["details"] = f"✅ Valid swap executed - Tier 4 (queued) as expected"
                                    logger.info("✅ Valid swap execute test passed (Tier 4)")
                                else:
                                    self.results["swap_execute_valid"]["details"] = f"❌ Tier 4 should have queued=true"
                            else:
                                # Tier 1/2/3 should have tx_hash
                                tx_hash = data.get("tx_hash")
                                if tx_hash and tx_hash.startswith("0x"):
                                    self.results["swap_execute_valid"]["passed"] = True
                                    self.results["swap_execute_valid"]["details"] = f"✅ Valid swap executed - {tier} with tx_hash"
                                    logger.info(f"✅ Valid swap execute test passed ({tier})")
                                else:
                                    self.results["swap_execute_valid"]["details"] = f"❌ {tier} should have valid tx_hash"
                        else:
                            self.results["swap_execute_valid"]["details"] = f"❌ Invalid tier: {tier}"
                    else:
                        self.results["swap_execute_valid"]["details"] = f"❌ Execute failed - success: {success}, swap_id: {swap_id}"
                else:
                    self.results["swap_execute_valid"]["details"] = f"❌ Missing required fields: {missing_fields}"
            else:
                self.results["swap_execute_valid"]["details"] = f"❌ Execute request failed: {result['status']} - {result['data']}"
                
        except Exception as e:
            self.results["swap_execute_valid"]["details"] = f"❌ Valid execute error: {e}"
            logger.error(f"Valid swap execute test failed: {e}")

    async def test_swap_history_no_auth(self):
        """Test 12: History without auth"""
        logger.info("🔍 Testing swap history without auth...")
        
        try:
            result = await self.make_request("GET", "/swap/history", headers={}, expect_status=401)
            
            if result["status"] == 401:
                self.results["swap_history_no_auth"]["passed"] = True
                self.results["swap_history_no_auth"]["details"] = "✅ History without auth correctly rejected with 401"
                logger.info("✅ History without auth test passed")
            else:
                self.results["swap_history_no_auth"]["details"] = f"❌ Expected 401, got {result['status']}"
                
        except Exception as e:
            self.results["swap_history_no_auth"]["details"] = f"❌ History no auth error: {e}"
            logger.error(f"History without auth test failed: {e}")

    async def test_swap_history_with_auth(self):
        """Test 13: History with auth"""
        logger.info("🔍 Testing swap history with auth...")
        
        try:
            result = await self.make_request("GET", "/swap/history")
            
            if result["status"] == 200:
                data = result["data"]
                
                required_fields = ["user_id", "count", "history"]
                missing_fields = [f for f in required_fields if f not in data]
                
                if not missing_fields:
                    user_id = data.get("user_id")
                    count = data.get("count")
                    history = data.get("history", [])
                    
                    if user_id and isinstance(count, int) and isinstance(history, list):
                        self.results["swap_history_with_auth"]["passed"] = True
                        self.results["swap_history_with_auth"]["details"] = f"✅ History retrieved - user_id: {user_id}, count: {count}"
                        logger.info("✅ History with auth test passed")
                    else:
                        self.results["swap_history_with_auth"]["details"] = f"❌ Invalid history response structure"
                else:
                    self.results["swap_history_with_auth"]["details"] = f"❌ Missing required fields: {missing_fields}"
            else:
                self.results["swap_history_with_auth"]["details"] = f"❌ History request failed: {result['status']} - {result['data']}"
                
        except Exception as e:
            self.results["swap_history_with_auth"]["details"] = f"❌ History with auth error: {e}"
            logger.error(f"History with auth test failed: {e}")

    async def test_auth_register(self):
        """Test 14: Auth register"""
        logger.info("🔍 Testing auth register...")
        
        try:
            # Create a unique test user
            import time
            test_email = f"test_{int(time.time())}@example.com"
            
            register_data = {
                "email": test_email,
                "password": "TestPassword123!",
                "role": "USER"
            }
            
            result = await self.make_request("POST", "/auth/register", data=register_data)
            
            if result["status"] == 200:
                data = result["data"]
                
                if data.get("success") and "token" in data and "user" in data:
                    self.results["auth_register"]["passed"] = True
                    self.results["auth_register"]["details"] = f"✅ User registration successful - email: {test_email}"
                    logger.info("✅ Auth register test passed")
                else:
                    self.results["auth_register"]["details"] = f"❌ Registration response invalid: {data}"
            else:
                self.results["auth_register"]["details"] = f"❌ Registration failed: {result['status']} - {result['data']}"
                
        except Exception as e:
            self.results["auth_register"]["details"] = f"❌ Registration error: {e}"
            logger.error(f"Auth register test failed: {e}")

    async def test_auth_me(self):
        """Test 15: Auth me endpoint"""
        logger.info("🔍 Testing auth me...")
        
        try:
            result = await self.make_request("GET", "/auth/me")
            
            if result["status"] == 200:
                data = result["data"]
                
                required_fields = ["id", "email", "role"]
                missing_fields = [f for f in required_fields if f not in data]
                
                if not missing_fields:
                    user_id = data.get("id")
                    email = data.get("email")
                    role = data.get("role")
                    
                    if user_id and email and role:
                        self.results["auth_me"]["passed"] = True
                        self.results["auth_me"]["details"] = f"✅ User profile retrieved - email: {email}, role: {role}"
                        logger.info("✅ Auth me test passed")
                    else:
                        self.results["auth_me"]["details"] = f"❌ Invalid user profile data"
                else:
                    self.results["auth_me"]["details"] = f"❌ Missing required fields: {missing_fields}"
            else:
                self.results["auth_me"]["details"] = f"❌ Auth me failed: {result['status']} - {result['data']}"
                
        except Exception as e:
            self.results["auth_me"]["details"] = f"❌ Auth me error: {e}"
            logger.error(f"Auth me test failed: {e}")

    async def test_existing_endpoints(self):
        """Test 16: Existing endpoints still work"""
        logger.info("🔍 Testing existing endpoints...")
        
        try:
            # Test a few existing endpoints to ensure they still work
            endpoints_to_test = [
                ("/", "GET"),
                ("/docs", "GET"),
            ]
            
            working_endpoints = []
            failed_endpoints = []
            
            for endpoint, method in endpoints_to_test:
                try:
                    result = await self.make_request(method, endpoint)
                    if result["status"] in [200, 404]:  # 404 is ok for some endpoints
                        working_endpoints.append(endpoint)
                    else:
                        failed_endpoints.append(f"{endpoint} ({result['status']})")
                except Exception as e:
                    failed_endpoints.append(f"{endpoint} (error: {e})")
            
            if len(working_endpoints) > 0 and len(failed_endpoints) == 0:
                self.results["existing_endpoints"]["passed"] = True
                self.results["existing_endpoints"]["details"] = f"✅ Existing endpoints working: {working_endpoints}"
                logger.info("✅ Existing endpoints test passed")
            else:
                self.results["existing_endpoints"]["details"] = f"❌ Some endpoints failed: {failed_endpoints}"
                
        except Exception as e:
            self.results["existing_endpoints"]["details"] = f"❌ Existing endpoints error: {e}"
            logger.error(f"Existing endpoints test failed: {e}")

    async def run_all_tests(self):
        """Run all tests in sequence"""
        logger.info("🚀 Starting NeoNoble Backend Test Suite...")
        
        await self.setup_session()
        
        try:
            # Run tests in order
            await self.test_boot_health()
            await self.test_auth_login()
            
            # Only run swap tests if we have auth
            if self.jwt_token:
                await self.test_swap_health()
                await self.test_swap_tokens()
                await self.test_swap_quote_valid()
                await self.test_swap_quote_neno()
                await self.test_swap_quote_invalid()
                await self.test_swap_execute_no_auth()
                await self.test_swap_execute_invalid_wallet()
                await self.test_swap_execute_same_token()
                await self.test_swap_execute_valid()
                await self.test_swap_history_no_auth()
                await self.test_swap_history_with_auth()
                await self.test_auth_register()
                await self.test_auth_me()
                await self.test_existing_endpoints()
            else:
                logger.warning("⚠️ Skipping swap tests - no JWT token available")
                
        finally:
            await self.cleanup_session()

    def print_results(self):
        """Print test results summary"""
        logger.info("\n" + "="*80)
        logger.info("🧪 TEST RESULTS SUMMARY")
        logger.info("="*80)
        
        passed = 0
        total = 0
        
        for test_name, result in self.results.items():
            total += 1
            if result["passed"]:
                passed += 1
                status = "✅ PASS"
            else:
                status = "❌ FAIL"
            
            logger.info(f"{status} | {test_name}: {result['details']}")
        
        logger.info("="*80)
        logger.info(f"📊 OVERALL: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
        logger.info("="*80)
        
        return passed, total

async def main():
    """Main test runner"""
    tester = NeoNobleBackendTester()
    await tester.run_all_tests()
    passed, total = tester.print_results()
    
    # Exit with appropriate code
    if passed == total:
        logger.info("🎉 All tests passed!")
        sys.exit(0)
    else:
        logger.error(f"💥 {total - passed} tests failed!")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())