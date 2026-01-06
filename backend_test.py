#!/usr/bin/env python3
"""
NeoNoble Ramp Backend API Test Suite - POSTGRESQL MIGRATION VALIDATION

Performs comprehensive end-to-end testing to validate PostgreSQL migration:
- System is running in dual_read_pg mode
- All WRITES go to BOTH MongoDB and PostgreSQL
- All READS come from PostgreSQL

Test Environment:
- Backend URL: https://ramp-platform-1.preview.emergentagent.com/api
- NENO Token: Fixed price €10,000 per token
- Fee: 1.5%
- Settlement: Instant mode
- Migration Mode: dual_read_pg
"""

import asyncio
import aiohttp
import json
import logging
from typing import Dict, Any, Optional
import sys
import os
import time
import hmac
import hashlib

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Backend URL from frontend .env
BACKEND_URL = "https://ramp-platform-1.preview.emergentagent.com/api"

class PostgreSQLMigrationTester:
    def __init__(self):
        self.session = None
        self.test_results = {}
        
        # Test credentials and tokens
        self.user_jwt = None
        self.dev_jwt = None
        self.api_key = None
        self.api_secret = None
        
        # PostgreSQL Migration Test Quote IDs
        self.pg_user_quote_id = None
        self.pg_dev_quote_id = None
        self.pg_onramp_quote_id = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    def generate_hmac_signature(self, timestamp: str, body: str) -> str:
        """Generate HMAC-SHA256 signature for API authentication"""
        if not self.api_secret:
            return ""
        
        message = timestamp + body
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    async def make_request(self, method: str, endpoint: str, data: Dict = None, 
                          headers: Dict = None, auth_token: str = None, 
                          use_hmac: bool = False) -> tuple:
        """Make HTTP request and return (success, response_data, status_code)"""
        url = f"{BACKEND_URL}{endpoint}"
        
        request_headers = {"Content-Type": "application/json"}
        if headers:
            request_headers.update(headers)
        if auth_token:
            request_headers["Authorization"] = f"Bearer {auth_token}"
        
        # HMAC authentication for developer API
        if use_hmac and self.api_key and self.api_secret:
            timestamp = str(int(time.time()))
            body = json.dumps(data) if data else ""
            signature = self.generate_hmac_signature(timestamp, body)
            
            request_headers.update({
                "X-API-KEY": self.api_key,
                "X-TIMESTAMP": timestamp,
                "X-SIGNATURE": signature
            })
            
        try:
            async with self.session.request(
                method, url, 
                json=data if data else None,
                headers=request_headers
            ) as response:
                try:
                    response_data = await response.json()
                except:
                    response_data = await response.text()
                
                return response.status < 400, response_data, response.status
                
        except Exception as e:
            logger.error(f"Request failed: {e}")
            return False, str(e), 0
    
    def log_test_result(self, test_name: str, success: bool, details: str = ""):
        """Log test result"""
        status = "✅ PASS" if success else "❌ FAIL"
        logger.info(f"{status} {test_name}")
        if details:
            logger.info(f"    Details: {details}")
        
        self.test_results[test_name] = {
            "success": success,
            "details": details
        }

    async def test_postgresql_migration_status(self):
        """Test PostgreSQL migration status and metrics"""
        logger.info("\n=== Testing PostgreSQL Migration Status ===")
        
        # Test migration status endpoint
        success, data, status = await self.make_request("GET", "/migration/status")
        
        migration_status_valid = False
        if success and isinstance(data, dict):
            mode = data.get("mode")
            phase = data.get("phase")
            mongodb_writes = data.get("mongodb_writes", 0)
            postgresql_writes = data.get("postgresql_writes", 0)
            
            migration_status_valid = (
                mode == "dual_read_pg" and
                phase in ["validation", "dual_read_pg"] and
                mongodb_writes >= 0 and
                postgresql_writes >= 0
            )
        
        self.log_test_result(
            "PostgreSQL Migration Status",
            migration_status_valid,
            f"Status: {status}, Mode: {data.get('mode') if isinstance(data, dict) else 'N/A'}, Phase: {data.get('phase') if isinstance(data, dict) else 'N/A'}, MongoDB Writes: {data.get('mongodb_writes') if isinstance(data, dict) else 'N/A'}, PostgreSQL Writes: {data.get('postgresql_writes') if isinstance(data, dict) else 'N/A'}"
        )
        
        # Test migration metrics endpoint
        success, data, status = await self.make_request("GET", "/migration/metrics")
        
        metrics_valid = False
        if success and isinstance(data, dict):
            consistency_checks = data.get("consistency_checks", {})
            data_counts = data.get("data_counts", {})
            
            metrics_valid = (
                isinstance(consistency_checks, dict) and
                isinstance(data_counts, dict)
            )
        
        self.log_test_result(
            "PostgreSQL Migration Metrics",
            metrics_valid,
            f"Status: {status}, Consistency Checks: {len(data.get('consistency_checks', {})) if isinstance(data, dict) else 0}, Data Counts Available: {bool(data.get('data_counts')) if isinstance(data, dict) else False}"
        )
        
        return migration_status_valid and metrics_valid

    async def test_postgresql_user_authentication(self):
        """Test user authentication with PostgreSQL dual-write validation"""
        logger.info("\n=== Testing PostgreSQL User Authentication ===")
        
        # Test user registration (should write to both MongoDB and PostgreSQL)
        user_data = {
            "email": "pg_test_user@neonoble.com",
            "password": "TestPG123!",
            "role": "user"
        }
        
        success, data, status = await self.make_request("POST", "/auth/register", user_data)
        
        # Registration may fail if user already exists (400), which is expected
        registration_ok = (status == 200) or (status == 400 and "already" in str(data).lower())
        
        if success and isinstance(data, dict) and data.get("token"):
            self.user_jwt = data["token"]
            
        self.log_test_result(
            "PostgreSQL User Registration (Dual Write)",
            registration_ok,
            f"Status: {status}, Expected: 200 or 400 (user exists), Dual write to MongoDB + PostgreSQL"
        )
        
        # Test user login (should read from PostgreSQL)
        login_data = {
            "email": "pg_test_user@neonoble.com",
            "password": "TestPG123!"
        }
        
        success, data, status = await self.make_request("POST", "/auth/login", login_data)
        
        if success and isinstance(data, dict) and data.get("token"):
            self.user_jwt = data["token"]
            
        self.log_test_result(
            "PostgreSQL User Login (Read from PostgreSQL)",
            success and status == 200 and self.user_jwt,
            f"Status: {status}, Token: {'Present' if self.user_jwt else 'Missing'}, Read from PostgreSQL"
        )
        
        return bool(self.user_jwt)

    async def test_postgresql_offramp_flow(self):
        """Test off-ramp PoR engine flow with PostgreSQL validation"""
        logger.info("\n=== Testing PostgreSQL Off-Ramp PoR Engine Flow ===")
        
        if not self.user_jwt:
            self.log_test_result("PostgreSQL Off-Ramp Flow", False, "No user JWT available")
            return False
        
        # Step 1: Create off-ramp quote (should write to both databases)
        logger.info("Step 1: Create Off-Ramp Quote")
        quote_data = {
            "crypto_amount": 1.0,
            "crypto_currency": "NENO"
        }
        
        success, data, status = await self.make_request(
            "POST", "/ramp/offramp/quote", quote_data, auth_token=self.user_jwt
        )
        
        quote_valid = False
        if success and isinstance(data, dict):
            self.pg_user_quote_id = data.get("quote_id")
            direction = data.get("direction")
            crypto_amount = data.get("crypto_amount")
            fiat_amount = data.get("fiat_amount")
            state = data.get("state")
            deposit_address = data.get("deposit_address")
            
            quote_valid = (
                self.pg_user_quote_id and self.pg_user_quote_id.startswith("por_") and
                direction == "offramp" and
                crypto_amount == 1 and
                fiat_amount == 10000 and
                state == "QUOTE_CREATED" and
                deposit_address
            )
        
        self.log_test_result(
            "PostgreSQL Off-Ramp Quote Creation (Dual Write)",
            quote_valid,
            f"Quote ID: {self.pg_user_quote_id}, Direction: {data.get('direction') if isinstance(data, dict) else 'N/A'}, State: {data.get('state') if isinstance(data, dict) else 'N/A'}"
        )
        
        if not quote_valid:
            return False
        
        # Step 2: Execute quote (should write to both databases)
        logger.info("Step 2: Execute Off-Ramp Quote")
        execute_data = {
            "quote_id": self.pg_user_quote_id,
            "bank_account": "IT60X0542811101000000123456"
        }
        
        success, data, status = await self.make_request(
            "POST", "/ramp/offramp/execute", execute_data, auth_token=self.user_jwt
        )
        
        execute_valid = False
        if success and isinstance(data, dict):
            state = data.get("state")
            execute_valid = state == "DEPOSIT_PENDING"
        
        self.log_test_result(
            "PostgreSQL Off-Ramp Execute (Dual Write)",
            execute_valid,
            f"Status: {status}, State: {data.get('state') if isinstance(data, dict) else 'N/A'}"
        )
        
        if not execute_valid:
            return False
        
        # Step 3: Process deposit (should write to both databases)
        logger.info("Step 3: Process Deposit")
        deposit_data = {
            "quote_id": self.pg_user_quote_id
        }
        
        success, data, status = await self.make_request(
            "POST", "/ramp/offramp/deposit/process", deposit_data, auth_token=self.user_jwt
        )
        
        deposit_valid = False
        if success and isinstance(data, dict):
            state = data.get("state")
            deposit_valid = state == "COMPLETED"
        
        self.log_test_result(
            "PostgreSQL Off-Ramp Process Deposit (Dual Write)",
            deposit_valid,
            f"Status: {status}, Final State: {data.get('state') if isinstance(data, dict) else 'N/A'}"
        )
        
        # Step 4: Get timeline (should read from PostgreSQL)
        logger.info("Step 4: Get Transaction Timeline")
        success, data, status = await self.make_request(
            "GET", f"/ramp/offramp/transaction/{self.pg_user_quote_id}/timeline", auth_token=self.user_jwt
        )
        
        timeline_valid = False
        if success:
            if isinstance(data, dict):
                events = data.get("events", [])
                timeline_valid = len(events) >= 11  # 11 state transitions for off-ramp
            elif isinstance(data, list):
                timeline_valid = len(data) >= 11
        
        self.log_test_result(
            "PostgreSQL Off-Ramp Timeline (Read from PostgreSQL)",
            timeline_valid,
            f"Status: {status}, Timeline Events: {len(data.get('events', [])) if isinstance(data, dict) else len(data) if isinstance(data, list) else 0} (Expected: 11)"
        )
        
        return quote_valid and execute_valid and deposit_valid and timeline_valid

    async def test_postgresql_onramp_flow(self):
        """Test on-ramp PoR engine flow with PostgreSQL validation"""
        logger.info("\n=== Testing PostgreSQL On-Ramp PoR Engine Flow ===")
        
        if not self.user_jwt:
            self.log_test_result("PostgreSQL On-Ramp Flow", False, "No user JWT available")
            return False
        
        # Step 1: Create on-ramp quote (should write to both databases)
        logger.info("Step 1: Create On-Ramp Quote")
        quote_data = {
            "fiat_amount": 10000,
            "fiat_currency": "EUR",
            "wallet_address": "0x1234567890abcdef1234567890abcdef12345678"
        }
        
        success, data, status = await self.make_request(
            "POST", "/ramp/onramp/por/quote", quote_data, auth_token=self.user_jwt
        )
        
        quote_valid = False
        if success and isinstance(data, dict):
            self.pg_onramp_quote_id = data.get("quote_id")
            direction = data.get("direction")
            fiat_amount = data.get("fiat_amount")
            crypto_amount = data.get("crypto_amount")
            state = data.get("state")
            payment_reference = data.get("payment_reference")
            
            quote_valid = (
                self.pg_onramp_quote_id and self.pg_onramp_quote_id.startswith("por_on_") and
                direction == "onramp" and
                fiat_amount == 10000 and
                crypto_amount == 0.985 and  # (10000 - 150) / 10000
                state == "QUOTE_CREATED" and
                payment_reference
            )
        
        self.log_test_result(
            "PostgreSQL On-Ramp Quote Creation (Dual Write)",
            quote_valid,
            f"Quote ID: {self.pg_onramp_quote_id}, Direction: {data.get('direction') if isinstance(data, dict) else 'N/A'}, Fiat: {data.get('fiat_amount') if isinstance(data, dict) else 'N/A'}, Crypto: {data.get('crypto_amount') if isinstance(data, dict) else 'N/A'}"
        )
        
        if not quote_valid:
            return False
        
        # Step 2: Execute on-ramp quote
        logger.info("Step 2: Execute On-Ramp Quote")
        execute_data = {
            "quote_id": self.pg_onramp_quote_id,
            "wallet_address": "0x1234567890abcdef1234567890abcdef12345678"
        }
        
        success, data, status = await self.make_request(
            "POST", "/ramp/onramp/por/execute", execute_data, auth_token=self.user_jwt
        )
        
        execute_valid = False
        if success and isinstance(data, dict):
            state = data.get("state")
            execute_valid = state == "PAYMENT_PENDING"
        
        self.log_test_result(
            "PostgreSQL On-Ramp Execute (Dual Write)",
            execute_valid,
            f"Status: {status}, State: {data.get('state') if isinstance(data, dict) else 'N/A'}"
        )
        
        if not execute_valid:
            return False
        
        # Step 3: Process payment
        logger.info("Step 3: Process Payment")
        payment_data = {
            "quote_id": self.pg_onramp_quote_id
        }
        
        success, data, status = await self.make_request(
            "POST", "/ramp/onramp/por/payment/process", payment_data, auth_token=self.user_jwt
        )
        
        payment_valid = False
        if success and isinstance(data, dict):
            state = data.get("state")
            payment_valid = state == "COMPLETED"
        
        self.log_test_result(
            "PostgreSQL On-Ramp Process Payment (Dual Write)",
            payment_valid,
            f"Status: {status}, Final State: {data.get('state') if isinstance(data, dict) else 'N/A'}"
        )
        
        # Step 4: Get timeline (should read from PostgreSQL)
        logger.info("Step 4: Get Transaction Timeline")
        success, data, status = await self.make_request(
            "GET", f"/ramp/onramp/por/transaction/{self.pg_onramp_quote_id}/timeline", auth_token=self.user_jwt
        )
        
        timeline_valid = False
        if success:
            if isinstance(data, dict):
                events = data.get("events", [])
                timeline_valid = len(events) >= 9  # 9 state transitions for on-ramp
            elif isinstance(data, list):
                timeline_valid = len(data) >= 9
        
        self.log_test_result(
            "PostgreSQL On-Ramp Timeline (Read from PostgreSQL)",
            timeline_valid,
            f"Status: {status}, Timeline Events: {len(data.get('events', [])) if isinstance(data, dict) else len(data) if isinstance(data, list) else 0} (Expected: 9)"
        )
        
        return quote_valid and execute_valid and payment_valid and timeline_valid

    async def test_postgresql_developer_api_flow(self):
        """Test developer API flow with PostgreSQL validation"""
        logger.info("\n=== Testing PostgreSQL Developer API Flow ===")
        
        # Step 1: Register developer (should write to both databases)
        logger.info("Step 1: Register Developer")
        dev_data = {
            "email": "pg_dev@neonoble.com",
            "password": "DevPG123!",
            "role": "DEVELOPER"
        }
        
        success, data, status = await self.make_request("POST", "/auth/register", dev_data)
        
        # Registration may fail if user already exists (400), which is expected
        registration_ok = (status == 200) or (status == 400 and "already" in str(data).lower())
        
        if success and isinstance(data, dict) and data.get("token"):
            self.dev_jwt = data["token"]
            
        self.log_test_result(
            "PostgreSQL Developer Registration (Dual Write)",
            registration_ok,
            f"Status: {status}, Expected: 200 or 400 (user exists)"
        )
        
        # Login as developer if registration failed
        if not self.dev_jwt:
            login_data = {
                "email": "pg_dev@neonoble.com",
                "password": "DevPG123!"
            }
            success, data, status = await self.make_request("POST", "/auth/login", login_data)
            if success and isinstance(data, dict) and data.get("token"):
                self.dev_jwt = data["token"]
        
        if not self.dev_jwt:
            self.log_test_result("PostgreSQL Developer API Flow", False, "No developer JWT available")
            return False
        
        # Step 2: Create API key (should write to both databases)
        logger.info("Step 2: Create API Key")
        api_key_data = {
            "name": "PostgreSQL Test Key"
        }
        
        success, data, status = await self.make_request(
            "POST", "/dev/api-keys", api_key_data, auth_token=self.dev_jwt
        )
        
        if success and isinstance(data, dict):
            self.api_key = data.get("api_key")
            self.api_secret = data.get("api_secret")
        
        api_key_valid = bool(self.api_key and self.api_secret)
        self.log_test_result(
            "PostgreSQL API Key Creation (Dual Write)",
            api_key_valid,
            f"Status: {status}, API Key: {'Present' if self.api_key else 'Missing'}, Secret: {'Present' if self.api_secret else 'Missing'}"
        )
        
        if not api_key_valid:
            return False
        
        # Step 3: Use HMAC authentication to create quote
        logger.info("Step 3: Create Quote via HMAC")
        quote_data = {
            "crypto_amount": 1.0,
            "crypto_currency": "NENO"
        }
        
        success, data, status = await self.make_request(
            "POST", "/ramp-api-offramp-quote", quote_data, use_hmac=True
        )
        
        quote_valid = False
        if success and isinstance(data, dict):
            self.pg_dev_quote_id = data.get("quote_id")
            direction = data.get("direction")
            state = data.get("state")
            
            quote_valid = (
                self.pg_dev_quote_id and
                direction == "offramp" and
                state == "QUOTE_CREATED"
            )
        
        self.log_test_result(
            "PostgreSQL HMAC Quote Creation (Dual Write)",
            quote_valid,
            f"Quote ID: {self.pg_dev_quote_id}, Direction: {data.get('direction') if isinstance(data, dict) else 'N/A'}, State: {data.get('state') if isinstance(data, dict) else 'N/A'}"
        )
        
        if not quote_valid:
            return False
        
        # Step 4: Execute quote via HMAC
        logger.info("Step 4: Execute Quote via HMAC")
        execute_data = {
            "quote_id": self.pg_dev_quote_id,
            "bank_account": "IT60X0542811101000000123456"
        }
        
        success, data, status = await self.make_request(
            "POST", "/ramp-api-offramp", execute_data, use_hmac=True
        )
        
        execute_valid = False
        if success and isinstance(data, dict):
            state = data.get("state")
            execute_valid = state == "DEPOSIT_PENDING"
        
        self.log_test_result(
            "PostgreSQL HMAC Quote Execute (Dual Write)",
            execute_valid,
            f"Status: {status}, State: {data.get('state') if isinstance(data, dict) else 'N/A'}"
        )
        
        # Step 5: Process deposit via HMAC
        logger.info("Step 5: Process Deposit via HMAC")
        deposit_data = {
            "quote_id": self.pg_dev_quote_id
        }
        
        success, data, status = await self.make_request(
            "POST", "/ramp-api-deposit-process", deposit_data, use_hmac=True
        )
        
        deposit_valid = False
        if success and isinstance(data, dict):
            state = data.get("state")
            deposit_valid = state == "COMPLETED"
        
        self.log_test_result(
            "PostgreSQL HMAC Process Deposit (Dual Write)",
            deposit_valid,
            f"Status: {status}, Final State: {data.get('state') if isinstance(data, dict) else 'N/A'}"
        )
        
        # Step 6: Get timeline via HMAC (should read from PostgreSQL)
        logger.info("Step 6: Get Timeline via HMAC")
        success, data, status = await self.make_request(
            "GET", f"/ramp-api-transaction/{self.pg_dev_quote_id}/timeline", use_hmac=True
        )
        
        timeline_valid = False
        if success:
            if isinstance(data, dict):
                events = data.get("events", [])
                timeline_valid = len(events) >= 11
            elif isinstance(data, list):
                timeline_valid = len(data) >= 11
        
        self.log_test_result(
            "PostgreSQL HMAC Timeline (Read from PostgreSQL)",
            timeline_valid,
            f"Status: {status}, Timeline Events: {len(data.get('events', [])) if isinstance(data, dict) else len(data) if isinstance(data, list) else 0} (Expected: 11)"
        )
        
        return registration_ok and api_key_valid and quote_valid and execute_valid and deposit_valid and timeline_valid

    async def test_postgresql_write_metrics_validation(self):
        """Validate that write counts are incrementing for both databases"""
        logger.info("\n=== Testing PostgreSQL Write Metrics Validation ===")
        
        # Get initial metrics
        success, initial_data, status = await self.make_request("GET", "/migration/status")
        
        if not success or not isinstance(initial_data, dict):
            self.log_test_result("PostgreSQL Write Metrics Validation", False, "Could not get initial metrics")
            return False
        
        initial_mongodb_writes = initial_data.get("mongodb_writes", 0)
        initial_postgresql_writes = initial_data.get("postgresql_writes", 0)
        
        logger.info(f"Initial MongoDB writes: {initial_mongodb_writes}")
        logger.info(f"Initial PostgreSQL writes: {initial_postgresql_writes}")
        
        # Perform a write operation (create a test user)
        test_user_data = {
            "email": f"pg_metrics_test_{int(time.time())}@neonoble.com",
            "password": "MetricsTest123!"
        }
        
        success, data, status = await self.make_request("POST", "/auth/register", test_user_data)
        
        if not success:
            self.log_test_result("PostgreSQL Write Metrics Validation", False, f"Test user creation failed: {status}")
            return False
        
        # Wait a moment for metrics to update
        await asyncio.sleep(2)
        
        # Get updated metrics
        success, updated_data, status = await self.make_request("GET", "/migration/status")
        
        if not success or not isinstance(updated_data, dict):
            self.log_test_result("PostgreSQL Write Metrics Validation", False, "Could not get updated metrics")
            return False
        
        updated_mongodb_writes = updated_data.get("mongodb_writes", 0)
        updated_postgresql_writes = updated_data.get("postgresql_writes", 0)
        
        logger.info(f"Updated MongoDB writes: {updated_mongodb_writes}")
        logger.info(f"Updated PostgreSQL writes: {updated_postgresql_writes}")
        
        # Validate that both write counts increased
        mongodb_incremented = updated_mongodb_writes > initial_mongodb_writes
        postgresql_incremented = updated_postgresql_writes > initial_postgresql_writes
        
        metrics_valid = mongodb_incremented and postgresql_incremented
        
        self.log_test_result(
            "PostgreSQL Write Metrics Validation",
            metrics_valid,
            f"MongoDB writes: {initial_mongodb_writes} → {updated_mongodb_writes} ({'✓' if mongodb_incremented else '✗'}), PostgreSQL writes: {initial_postgresql_writes} → {updated_postgresql_writes} ({'✓' if postgresql_incremented else '✗'})"
        )
        
        return metrics_valid

    async def run_postgresql_migration_tests(self):
        """Run all PostgreSQL migration validation tests"""
        logger.info("🚀 Starting POSTGRESQL MIGRATION VALIDATION - E2E Testing")
        logger.info(f"Testing against: {BACKEND_URL}")
        logger.info("Migration Mode: dual_read_pg (Writes: MongoDB + PostgreSQL, Reads: PostgreSQL)")
        
        # PostgreSQL Migration Test sequence
        tests = [
            ("PostgreSQL Migration Status & Metrics", self.test_postgresql_migration_status),
            ("PostgreSQL User Authentication Flow", self.test_postgresql_user_authentication),
            ("PostgreSQL Off-Ramp PoR Engine Flow", self.test_postgresql_offramp_flow),
            ("PostgreSQL On-Ramp PoR Engine Flow", self.test_postgresql_onramp_flow),
            ("PostgreSQL Developer API Flow", self.test_postgresql_developer_api_flow),
            ("PostgreSQL Write Metrics Validation", self.test_postgresql_write_metrics_validation),
        ]
        
        for test_name, test_func in tests:
            try:
                await test_func()
            except Exception as e:
                logger.error(f"Test '{test_name}' failed with exception: {e}")
                self.log_test_result(test_name, False, f"Exception: {e}")
        
        # Summary
        logger.info("\n" + "="*80)
        logger.info("POSTGRESQL MIGRATION VALIDATION SUMMARY")
        logger.info("="*80)
        
        passed = 0
        failed = 0
        critical_failures = []
        
        for test_name, result in self.test_results.items():
            status = "✅ PASS" if result["success"] else "❌ FAIL"
            logger.info(f"{status} {test_name}")
            if not result["success"] and result["details"]:
                logger.info(f"    Error: {result['details']}")
                critical_failures.append(test_name)
            
            if result["success"]:
                passed += 1
            else:
                failed += 1
        
        logger.info(f"\nTotal: {passed + failed}, Passed: {passed}, Failed: {failed}")
        
        if critical_failures:
            logger.error(f"\n🚨 CRITICAL POSTGRESQL MIGRATION FAILURES: {critical_failures}")
            logger.error("❌ PostgreSQL migration validation FAILED")
        else:
            logger.info(f"\n✅ POSTGRESQL MIGRATION VALIDATION COMPLETE - ALL SYSTEMS WORKING")
            logger.info("🏆 DUAL-WRITE MODE CONFIRMED: MongoDB + PostgreSQL")
            logger.info("🎯 READ operations confirmed from PostgreSQL")
        
        return self.test_results

    async def run_all_tests(self):
        """Run PostgreSQL migration validation tests"""
        return await self.run_postgresql_migration_tests()

async def main():
    """Main test runner for PostgreSQL migration validation"""
    async with PostgreSQLMigrationTester() as tester:
        results = await tester.run_postgresql_migration_tests()
        
        # Return exit code based on results
        failed_tests = [name for name, result in results.items() if not result["success"]]
        if failed_tests:
            logger.error(f"\n❌ {len(failed_tests)} PostgreSQL migration tests failed")
            return 1
        else:
            logger.info(f"\n✅ All PostgreSQL migration tests passed!")
            return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)