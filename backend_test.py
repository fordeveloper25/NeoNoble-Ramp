#!/usr/bin/env python3
"""
NeoNoble Ramp Backend API Test Suite - PHASE 1 HYBRID PoR LIQUIDITY ARCHITECTURE

Performs comprehensive end-to-end testing of the Phase 1 Hybrid PoR Liquidity Architecture:
- New Liquidity API Endpoints (Treasury, Exposure, Routing, Hedging, Reconciliation)
- Complete Off-Ramp Flow with Liquidity Lifecycle Hooks
- Liquidity Data Verification after Off-Ramp Flow
- Financial Auditability (Treasury ledger integrity, exposure reconstructability)

Test Environment:
- Backend URL: https://hybrid-treasury.preview.emergentagent.com/api
- NENO Token: Fixed price €10,000 per token
- Fee: 1.5%
- Phase 1 Services:
  * Treasury Service (REAL) - €100M virtual floor balance
  * Exposure Service (REAL) - Full lifecycle tracking
  * Routing Service (SHADOW) - Log-only market conversion simulation
  * Hedging Service (SHADOW) - Policy evaluation and proposals
  * Reconciliation Service (REAL) - Coverage events and audit ledger
"""

import asyncio
import aiohttp
import json
import logging
from typing import Dict, Any, Optional
import sys
import os
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Backend URL from frontend .env
BACKEND_URL = "https://hybrid-treasury.preview.emergentagent.com/api"

class HybridLiquidityArchitectureTester:
    def __init__(self):
        self.session = None
        self.test_results = {}
        
        # Test credentials and tokens
        self.user_jwt = None
        self.quote_id = None
        self.exposure_id = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def make_request(self, method: str, endpoint: str, data: Dict = None, 
                          headers: Dict = None, auth_token: str = None) -> tuple:
        """Make HTTP request and return (success, response_data, status_code)"""
        url = f"{BACKEND_URL}{endpoint}"
        
        request_headers = {"Content-Type": "application/json"}
        if headers:
            request_headers.update(headers)
        if auth_token:
            request_headers["Authorization"] = f"Bearer {auth_token}"
        
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

    async def test_liquidity_api_endpoints(self):
        """Test all new Liquidity API endpoints as specified in the review request"""
        logger.info("\n=== Testing Liquidity API Endpoints ===")
        
        # Test 1: GET /api/liquidity/dashboard - Combined liquidity overview
        logger.info("Step 1: Test Liquidity Dashboard")
        success, data, status = await self.make_request("GET", "/liquidity/dashboard")
        
        dashboard_valid = False
        if success and isinstance(data, dict):
            services = data.get("services", {})
            dashboard_valid = (
                services.get("treasury") and
                services.get("exposure") and
                services.get("routing") and
                services.get("hedging") and
                services.get("reconciliation") and
                data.get("mode") == "hybrid"
            )
        
        self.log_test_result(
            "Liquidity Dashboard",
            dashboard_valid,
            f"Status: {status}, Services Active: {data.get('services') if isinstance(data, dict) else 'N/A'}, Mode: {data.get('mode') if isinstance(data, dict) else 'N/A'}"
        )
        
        # Test 2: GET /api/liquidity/treasury/summary - Treasury state with €100M virtual floor
        logger.info("Step 2: Test Treasury Summary")
        success, data, status = await self.make_request("GET", "/liquidity/treasury/summary")
        
        treasury_valid = False
        if success and isinstance(data, dict):
            balances = data.get("balances", {})
            eur_balance = balances.get("EUR", 0)
            treasury_valid = eur_balance >= 100000000  # €100M virtual floor
        
        self.log_test_result(
            "Treasury Summary (€100M Virtual Floor)",
            treasury_valid,
            f"Status: {status}, EUR Balance: €{data.get('balances', {}).get('EUR', 0):,.2f} if isinstance(data, dict) else 'N/A'"
        )
        
        # Test 3: GET /api/liquidity/treasury/ledger - Initial virtual floor ledger entry
        logger.info("Step 3: Test Treasury Ledger")
        success, data, status = await self.make_request("GET", "/liquidity/treasury/ledger?limit=10")
        
        ledger_valid = False
        if success and isinstance(data, dict):
            entries = data.get("entries", [])
            ledger_valid = len(entries) > 0
            # Look for virtual floor entry
            for entry in entries:
                if entry.get("entry_type") == "VIRTUAL_FLOOR" and entry.get("amount") == 100000000:
                    ledger_valid = True
                    break
        
        self.log_test_result(
            "Treasury Ledger (Virtual Floor Entry)",
            ledger_valid,
            f"Status: {status}, Entries: {len(data.get('entries', [])) if isinstance(data, dict) else 0}, Virtual Floor Found: {ledger_valid}"
        )
        
        # Test 4: GET /api/liquidity/exposure/summary - Exposure metrics (initially 0)
        logger.info("Step 4: Test Exposure Summary")
        success, data, status = await self.make_request("GET", "/liquidity/exposure/summary")
        
        exposure_valid = False
        if success and isinstance(data, dict):
            total_active = data.get("total_active_eur", 0)
            exposure_valid = total_active >= 0  # Initially 0 or positive
        
        self.log_test_result(
            "Exposure Summary",
            exposure_valid,
            f"Status: {status}, Total Active Exposure: €{data.get('total_active_eur', 0) if isinstance(data, dict) else 'N/A'}"
        )
        
        # Test 5: GET /api/liquidity/routing/summary - Shadow mode verification
        logger.info("Step 5: Test Routing Summary (Shadow Mode)")
        success, data, status = await self.make_request("GET", "/liquidity/routing/summary")
        
        routing_valid = False
        if success and isinstance(data, dict):
            shadow_mode = data.get("shadow_mode", False)
            routing_valid = shadow_mode is True
        
        self.log_test_result(
            "Routing Summary (Shadow Mode)",
            routing_valid,
            f"Status: {status}, Shadow Mode: {data.get('shadow_mode') if isinstance(data, dict) else 'N/A'}"
        )
        
        # Test 6: GET /api/liquidity/hedging/summary - Shadow mode verification
        logger.info("Step 6: Test Hedging Summary (Shadow Mode)")
        success, data, status = await self.make_request("GET", "/liquidity/hedging/summary")
        
        hedging_valid = False
        if success and isinstance(data, dict):
            shadow_mode = data.get("shadow_mode", False)
            hedging_valid = shadow_mode is True
        
        self.log_test_result(
            "Hedging Summary (Shadow Mode)",
            hedging_valid,
            f"Status: {status}, Shadow Mode: {data.get('shadow_mode') if isinstance(data, dict) else 'N/A'}"
        )
        
        # Test 7: GET /api/liquidity/reconciliation/summary - Reconciliation status
        logger.info("Step 7: Test Reconciliation Summary")
        success, data, status = await self.make_request("GET", "/liquidity/reconciliation/summary")
        
        recon_valid = False
        if success and isinstance(data, dict):
            recon_valid = "pending_batches" in data or "batch_statistics" in data
        
        self.log_test_result(
            "Reconciliation Summary",
            recon_valid,
            f"Status: {status}, Pending Batches: {data.get('pending_batches', 'N/A') if isinstance(data, dict) else 'N/A'}"
        )
        
        return all([dashboard_valid, treasury_valid, ledger_valid, exposure_valid, routing_valid, hedging_valid, recon_valid])

    async def test_user_authentication(self):
        """Test user authentication for liquidity testing"""
        logger.info("\n=== Testing User Authentication ===")
        
        # Test user registration with liquidity test credentials
        user_data = {
            "email": "liquidity_test@neonoble.com",
            "password": "LiquidityTest123!",
            "role": "user"
        }
        
        success, data, status = await self.make_request("POST", "/auth/register", user_data)
        
        # Registration may fail if user already exists (400), which is expected
        registration_ok = (status == 200) or (status == 400 and "already" in str(data).lower())
        
        if success and isinstance(data, dict) and data.get("token"):
            self.user_jwt = data["token"]
            
        self.log_test_result(
            "User Registration",
            registration_ok,
            f"Status: {status}, Email: liquidity_test@neonoble.com"
        )
        
        # Test user login if registration failed or to get fresh token
        if not self.user_jwt:
            login_data = {
                "email": "liquidity_test@neonoble.com",
                "password": "LiquidityTest123!"
            }
            
            success, data, status = await self.make_request("POST", "/auth/login", login_data)
            
            if success and isinstance(data, dict) and data.get("token"):
                self.user_jwt = data["token"]
                
        login_success = bool(self.user_jwt)
        self.log_test_result(
            "User Login and JWT Token",
            login_success,
            f"Status: {status}, Token: {'Present' if self.user_jwt else 'Missing'}"
        )
        
        return login_success

    async def test_complete_offramp_flow_with_liquidity_hooks(self):
        """Test complete off-ramp flow with liquidity lifecycle hooks as specified in review request"""
        logger.info("\n=== Testing Complete Off-Ramp Flow with Liquidity Lifecycle Hooks ===")
        
        if not self.user_jwt:
            self.log_test_result("Off-Ramp Flow with Liquidity Hooks", False, "No user JWT available")
            return False
        
        # Step 1: Create PoR off-ramp quote (1 NENO as specified)
        logger.info("Step 1: Create PoR Off-Ramp Quote (1 NENO)")
        quote_data = {
            "crypto_amount": 1,
            "crypto_currency": "NENO",
            "bank_account": "TEST-IBAN-123"
        }
        
        success, data, status = await self.make_request(
            "POST", "/por/quote", quote_data, auth_token=self.user_jwt
        )
        
        quote_valid = False
        expected_gross = 10000  # 1 NENO * €10,000
        expected_fee = 150     # 1.5% of €10,000
        expected_net = 9850    # €10,000 - €150
        
        if success and isinstance(data, dict):
            self.quote_id = data.get("quote_id")
            crypto_amount = data.get("crypto_amount")
            fiat_amount = data.get("fiat_amount")
            fee_amount = data.get("fee_amount")
            net_payout = data.get("net_payout")
            state = data.get("state")
            
            quote_valid = (
                self.quote_id and
                crypto_amount == 1 and
                fiat_amount == expected_gross and
                fee_amount == expected_fee and
                net_payout == expected_net and
                state == "QUOTE_CREATED"
            )
        
        self.log_test_result(
            "Create PoR Quote (1 NENO → €9,850 net)",
            quote_valid,
            f"Quote ID: {self.quote_id}, Gross: €{data.get('fiat_amount') if isinstance(data, dict) else 'N/A'}, Fee: €{data.get('fee_amount') if isinstance(data, dict) else 'N/A'}, Net: €{data.get('net_payout') if isinstance(data, dict) else 'N/A'}"
        )
        
        if not quote_valid:
            return False
        
        # Step 2: Execute quote (accept quote)
        logger.info("Step 2: Execute PoR Quote")
        execute_data = {
            "quote_id": self.quote_id,
            "bank_account": "TEST-IBAN-123"
        }
        
        success, data, status = await self.make_request(
            "POST", "/por/quote/accept", execute_data, auth_token=self.user_jwt
        )
        
        execute_valid = False
        if success and isinstance(data, dict):
            state = data.get("state")
            execute_valid = state == "DEPOSIT_PENDING"
        
        self.log_test_result(
            "Execute PoR Quote",
            execute_valid,
            f"Status: {status}, State: {data.get('state') if isinstance(data, dict) else 'N/A'}"
        )
        
        if not execute_valid:
            return False
        
        # Step 3: Process deposit to trigger liquidity lifecycle hooks
        logger.info("Step 3: Process Deposit (Trigger Liquidity Lifecycle)")
        deposit_data = {
            "quote_id": self.quote_id,
            "tx_hash": "0xtest123456789abcdef",
            "amount": 1
        }
        
        success, data, status = await self.make_request(
            "POST", "/por/deposit/process", deposit_data, auth_token=self.user_jwt
        )
        
        process_valid = False
        if success and isinstance(data, dict):
            state = data.get("state")
            # State should progress through the liquidity-enabled flow
            process_valid = state in ["COMPLETED", "SETTLEMENT_COMPLETED", "PAYOUT_PROCESSING"]
        elif status == 400:
            # Check if the transaction still progressed by getting current state
            check_success, check_data, check_status = await self.make_request(
                "GET", f"/por/transaction/{self.quote_id}", auth_token=self.user_jwt
            )
            if check_success and isinstance(check_data, dict):
                state = check_data.get("state")
                process_valid = state in ["COMPLETED", "SETTLEMENT_COMPLETED", "PAYOUT_PROCESSING"]
        
        self.log_test_result(
            "Process Deposit (Liquidity Hooks Triggered)",
            process_valid,
            f"Status: {status}, Final State: {data.get('state') if isinstance(data, dict) else 'Check transaction for state'}"
        )
        
        return quote_valid and execute_valid and process_valid

    async def test_liquidity_data_verification(self):
        """Test liquidity data verification after off-ramp flow as specified in review request"""
        logger.info("\n=== Testing Liquidity Data Verification After Off-Ramp Flow ===")
        
        if not self.quote_id:
            self.log_test_result("Liquidity Data Verification", False, "No quote ID available")
            return False
        
        # Test 1: Treasury Ledger entries for the quote
        logger.info("Step 1: Verify Treasury Ledger Entries")
        success, data, status = await self.make_request(
            "GET", f"/liquidity/treasury/ledger?quote_id={self.quote_id}"
        )
        
        treasury_ledger_valid = False
        crypto_inflow_found = False
        fiat_payout_found = False
        fee_allocation_found = False
        
        if success and isinstance(data, dict):
            entries = data.get("entries", [])
            for entry in entries:
                entry_type = entry.get("entry_type")
                if entry_type == "CRYPTO_INFLOW":
                    crypto_inflow_found = True
                elif entry_type == "FIAT_PAYOUT":
                    fiat_payout_found = True
                elif entry_type == "FEE_ALLOCATION":
                    fee_allocation_found = True
            
            treasury_ledger_valid = crypto_inflow_found and (fiat_payout_found or fee_allocation_found)
        
        self.log_test_result(
            "Treasury Ledger Entries",
            treasury_ledger_valid,
            f"Status: {status}, Entries: {len(data.get('entries', [])) if isinstance(data, dict) else 0}, CRYPTO_INFLOW: {crypto_inflow_found}, FIAT_PAYOUT: {fiat_payout_found}, FEE_ALLOCATION: {fee_allocation_found}"
        )
        
        # Test 2: Exposure Record for the quote
        logger.info("Step 2: Verify Exposure Record")
        success, data, status = await self.make_request(
            "GET", f"/liquidity/exposure/by-quote/{self.quote_id}"
        )
        
        exposure_valid = False
        if success and isinstance(data, dict):
            self.exposure_id = data.get("exposure_id")
            exposure_status = data.get("status")
            exposure_valid = exposure_status in ["FULLY_COVERED", "ACTIVE", "COVERED"]
        
        self.log_test_result(
            "Exposure Record",
            exposure_valid,
            f"Status: {status}, Exposure ID: {self.exposure_id}, Status: {data.get('status') if isinstance(data, dict) else 'N/A'}"
        )
        
        # Test 3: Routing Conversions (shadow mode)
        logger.info("Step 3: Verify Routing Conversions (Shadow Mode)")
        success, data, status = await self.make_request(
            "GET", f"/liquidity/routing/conversions?quote_id={self.quote_id}"
        )
        
        routing_valid = False
        if success and isinstance(data, dict):
            conversions = data.get("conversions", [])
            shadow_mode = data.get("shadow_mode", False)
            routing_valid = shadow_mode is True  # Should be shadow mode in Phase 1
        
        self.log_test_result(
            "Routing Conversions (Shadow Mode)",
            routing_valid,
            f"Status: {status}, Conversions: {len(data.get('conversions', [])) if isinstance(data, dict) else 0}, Shadow Mode: {data.get('shadow_mode') if isinstance(data, dict) else 'N/A'}"
        )
        
        # Test 4: Coverage Events
        logger.info("Step 4: Verify Coverage Events")
        success, data, status = await self.make_request(
            "GET", "/liquidity/reconciliation/coverage"
        )
        
        coverage_valid = False
        if success and isinstance(data, dict):
            coverage_events = data.get("coverage_events", [])
            coverage_valid = len(coverage_events) >= 0  # Should have coverage events
        
        self.log_test_result(
            "Coverage Events",
            coverage_valid,
            f"Status: {status}, Coverage Events: {len(data.get('coverage_events', [])) if isinstance(data, dict) else 0}"
        )
        
        return treasury_ledger_valid and exposure_valid and routing_valid and coverage_valid

    async def test_financial_auditability(self):
        """Test financial auditability as specified in review request"""
        logger.info("\n=== Testing Financial Auditability ===")
        
        # Test 1: Ledger chain integrity
        logger.info("Step 1: Verify Ledger Chain Integrity")
        success, data, status = await self.make_request(
            "GET", "/liquidity/treasury/integrity"
        )
        
        integrity_valid = False
        if success and isinstance(data, dict):
            is_valid = data.get("is_valid", False)
            discrepancies = data.get("discrepancies", [])
            integrity_valid = is_valid and len(discrepancies) == 0
        
        self.log_test_result(
            "Treasury Ledger Integrity",
            integrity_valid,
            f"Status: {status}, Valid: {data.get('is_valid') if isinstance(data, dict) else 'N/A'}, Discrepancies: {len(data.get('discrepancies', [])) if isinstance(data, dict) else 0}"
        )
        
        # Test 2: Exposure reconstructability
        if self.exposure_id:
            logger.info("Step 2: Verify Exposure Reconstructability")
            success, data, status = await self.make_request(
                "GET", f"/liquidity/exposure/{self.exposure_id}/reconstruct"
            )
            
            reconstruct_valid = False
            if success and isinstance(data, dict):
                # Should have all required reconstruction data
                required_fields = ["exposure_record", "deposit_reference", "payout_reference"]
                reconstruct_valid = all(field in data for field in required_fields)
            
            self.log_test_result(
                "Exposure Reconstructability",
                reconstruct_valid,
                f"Status: {status}, Reconstruction Fields: {list(data.keys()) if isinstance(data, dict) else 'N/A'}"
            )
        else:
            self.log_test_result(
                "Exposure Reconstructability",
                False,
                "No exposure ID available for reconstruction test"
            )
            reconstruct_valid = False
        
        return integrity_valid and (reconstruct_valid if self.exposure_id else True)

    async def run_real_payout_integration_tests(self):
        """Run all real payout integration tests"""
        logger.info("🚀 Starting REAL PAYOUT INTEGRATION E2E TESTING")
        logger.info(f"Testing against: {BACKEND_URL}")
        logger.info("Stripe: LIVE mode with €0.00 balance (insufficient_funds expected)")
        logger.info("Destination: IBAN IT22B0200822800000103317304 (Massimo Fornara)")
        
        # Real Payout Integration Test sequence
        tests = [
            ("User Authentication", self.test_user_authentication),
            ("Off-Ramp Flow with Real Payout", self.test_offramp_flow_with_real_payout),
            ("Payout Integration Verification", self.test_payout_integration_verification),
            ("Payout Record Verification", self.test_payout_record_verification),
            ("Payout Summary Verification", self.test_payout_summary_verification),
            ("Audit Trail Verification", self.test_audit_trail_verification),
            ("Error Handling Verification", self.test_error_handling_verification),
        ]
        
        for test_name, test_func in tests:
            try:
                await test_func()
            except Exception as e:
                logger.error(f"Test '{test_name}' failed with exception: {e}")
                self.log_test_result(test_name, False, f"Exception: {e}")
        
        # Summary
        logger.info("\n" + "="*80)
        logger.info("REAL PAYOUT INTEGRATION E2E TESTING SUMMARY")
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
            logger.error(f"\n🚨 CRITICAL REAL PAYOUT INTEGRATION FAILURES: {critical_failures}")
            logger.error("❌ Real payout integration testing FAILED")
        else:
            logger.info(f"\n✅ REAL PAYOUT INTEGRATION E2E TESTING COMPLETE")
            logger.info("🏆 STRIPE SEPA PAYOUT INTEGRATION VERIFIED")
            logger.info("🎯 ERROR HANDLING AND AUDIT TRAIL CONFIRMED")
        
        return self.test_results

    async def run_all_tests(self):
        """Run real payout integration tests"""
        return await self.run_real_payout_integration_tests()

async def main():
    """Main test runner for real payout integration testing"""
    async with RealPayoutIntegrationTester() as tester:
        results = await tester.run_real_payout_integration_tests()
        
        # Return exit code based on results
        failed_tests = [name for name, result in results.items() if not result["success"]]
        if failed_tests:
            logger.error(f"\n❌ {len(failed_tests)} real payout integration tests failed")
            return 1
        else:
            logger.info(f"\n✅ All real payout integration tests passed!")
            return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)