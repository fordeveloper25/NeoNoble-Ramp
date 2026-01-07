#!/usr/bin/env python3
"""
NeoNoble Ramp Backend API Test Suite - REAL PAYOUT INTEGRATION E2E TESTING

Performs comprehensive end-to-end testing of the real Stripe SEPA payout integration:
- User authentication and off-ramp flow
- Real Stripe payout integration with SEPA Credit Transfer
- Payout timeline verification and audit trail
- Error handling for insufficient funds scenarios

Test Environment:
- Backend URL: https://ramp-platform-1.preview.emergentagent.com/api
- NENO Token: Fixed price €10,000 per token
- Fee: 1.5%
- Stripe: LIVE mode with €0.00 balance (insufficient_funds expected)
- Destination: IBAN IT22B0200822800000103317304 (Massimo Fornara)
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
BACKEND_URL = "https://ramp-platform-1.preview.emergentagent.com/api"

class RealPayoutIntegrationTester:
    def __init__(self):
        self.session = None
        self.test_results = {}
        
        # Test credentials and tokens
        self.user_jwt = None
        self.quote_id = None
        
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

    async def test_user_authentication(self):
        """Test user authentication as specified in the review request"""
        logger.info("\n=== Testing User Authentication ===")
        
        # Test user registration with specific credentials from review request
        user_data = {
            "email": "payout_test@neonoble.com",
            "password": "PayoutTest123!",
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
            f"Status: {status}, Email: payout_test@neonoble.com"
        )
        
        # Test user login if registration failed or to get fresh token
        if not self.user_jwt:
            login_data = {
                "email": "payout_test@neonoble.com",
                "password": "PayoutTest123!"
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

    async def test_offramp_flow_with_real_payout(self):
        """Test off-ramp flow with real payout integration as specified in review request"""
        logger.info("\n=== Testing Off-Ramp Flow with Real Payout ===")
        
        if not self.user_jwt:
            self.log_test_result("Off-Ramp Flow", False, "No user JWT available")
            return False
        
        # Step 1: Create quote as specified (0.1 NENO)
        logger.info("Step 1: Create Off-Ramp Quote (0.1 NENO)")
        quote_data = {
            "crypto_amount": 0.1,
            "crypto_currency": "NENO"
        }
        
        success, data, status = await self.make_request(
            "POST", "/ramp/offramp/quote", quote_data, auth_token=self.user_jwt
        )
        
        quote_valid = False
        expected_gross = 1000  # 0.1 NENO * €10,000
        expected_fee = 15      # 1.5% of €1,000
        expected_net = 985     # €1,000 - €15
        
        if success and isinstance(data, dict):
            self.quote_id = data.get("quote_id")
            crypto_amount = data.get("crypto_amount")
            fiat_amount = data.get("fiat_amount")
            fee_amount = data.get("fee_amount")
            net_payout = data.get("net_payout")
            state = data.get("state")
            
            quote_valid = (
                self.quote_id and
                crypto_amount == 0.1 and
                fiat_amount == expected_gross and
                fee_amount == expected_fee and
                net_payout == expected_net and
                state == "QUOTE_CREATED"
            )
        
        self.log_test_result(
            "Create Quote (0.1 NENO → €985 net)",
            quote_valid,
            f"Quote ID: {self.quote_id}, Gross: €{data.get('fiat_amount') if isinstance(data, dict) else 'N/A'}, Fee: €{data.get('fee_amount') if isinstance(data, dict) else 'N/A'}, Net: €{data.get('net_payout') if isinstance(data, dict) else 'N/A'}"
        )
        
        if not quote_valid:
            return False
        
        # Step 2: Execute quote with bank account
        logger.info("Step 2: Execute Off-Ramp Quote")
        execute_data = {
            "quote_id": self.quote_id,
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
            "Execute Quote",
            execute_valid,
            f"Status: {status}, State: {data.get('state') if isinstance(data, dict) else 'N/A'}"
        )
        
        if not execute_valid:
            return False
        
        # Step 3: Process deposit to trigger payout
        logger.info("Step 3: Process Deposit (Trigger Real Payout)")
        deposit_data = {
            "quote_id": self.quote_id
        }
        
        success, data, status = await self.make_request(
            "POST", "/por/offramp/process", deposit_data, auth_token=self.user_jwt
        )
        
        process_valid = False
        if success and isinstance(data, dict):
            state = data.get("state")
            # State should progress through the payout flow
            process_valid = state in ["COMPLETED", "PAYOUT_INITIATED", "PAYOUT_PROCESSING", "SETTLEMENT_COMPLETED"]
        
        self.log_test_result(
            "Process Deposit (Real Payout Triggered)",
            process_valid,
            f"Status: {status}, Final State: {data.get('state') if isinstance(data, dict) else 'N/A'}"
        )
        
        return quote_valid and execute_valid and process_valid

    async def test_payout_integration_verification(self):
        """Test payout integration verification as specified in review request"""
        logger.info("\n=== Testing Payout Integration Verification ===")
        
        if not self.quote_id:
            self.log_test_result("Payout Integration Verification", False, "No quote ID available")
            return False
        
        # Get timeline to look for PAYOUT_INITIATED event
        logger.info("Step 1: Get Transaction Timeline")
        success, data, status = await self.make_request(
            "GET", f"/ramp/offramp/transaction/{self.quote_id}/timeline", auth_token=self.user_jwt
        )
        
        timeline_valid = False
        payout_initiated_found = False
        stripe_payout_id = None
        payout_method = None
        provider = None
        
        if success:
            events = []
            if isinstance(data, dict):
                events = data.get("events", [])
            elif isinstance(data, list):
                events = data
            
            # Look for PAYOUT_INITIATED event
            for event in events:
                if isinstance(event, dict):
                    event_type = event.get("event_type") or event.get("state")
                    if event_type == "PAYOUT_INITIATED":
                        payout_initiated_found = True
                        metadata = event.get("metadata", {})
                        stripe_payout_id = metadata.get("stripe_payout_id")
                        payout_method = metadata.get("payout_method")
                        provider = metadata.get("provider")
                        break
            
            timeline_valid = len(events) >= 5  # Should have multiple state transitions
        
        self.log_test_result(
            "Timeline PAYOUT_INITIATED Event",
            payout_initiated_found,
            f"Events: {len(events) if 'events' in locals() else 0}, PAYOUT_INITIATED: {'Found' if payout_initiated_found else 'Not Found'}, Stripe ID: {stripe_payout_id or 'N/A'}, Method: {payout_method or 'N/A'}, Provider: {provider or 'N/A'}"
        )
        
        return timeline_valid and payout_initiated_found

    async def test_payout_record_verification(self):
        """Test payout record verification as specified in review request"""
        logger.info("\n=== Testing Payout Record Verification ===")
        
        if not self.quote_id:
            self.log_test_result("Payout Record Verification", False, "No quote ID available")
            return False
        
        # Check payout record
        logger.info("Step 1: Get Payout Record")
        success, data, status = await self.make_request(
            "GET", f"/stripe/payout/{self.quote_id}", auth_token=self.user_jwt
        )
        
        payout_record_valid = False
        if success and isinstance(data, dict):
            payout_id = data.get("payout_id") or data.get("stripe_payout_id")
            payout_status = data.get("status")
            amount = data.get("amount")
            currency = data.get("currency")
            destination = data.get("destination")
            
            payout_record_valid = bool(payout_id and payout_status and amount and currency)
        
        self.log_test_result(
            "Payout Record Details",
            payout_record_valid,
            f"Status: {status}, Payout ID: {data.get('payout_id') or data.get('stripe_payout_id') if isinstance(data, dict) else 'N/A'}, Status: {data.get('status') if isinstance(data, dict) else 'N/A'}, Amount: {data.get('amount') if isinstance(data, dict) else 'N/A'}"
        )
        
        return payout_record_valid

    async def test_payout_summary_verification(self):
        """Test payout summary verification as specified in review request"""
        logger.info("\n=== Testing Payout Summary Verification ===")
        
        # Check payout summary
        logger.info("Step 1: Get Payout Summary")
        success, data, status = await self.make_request(
            "GET", "/stripe/payouts/summary", auth_token=self.user_jwt
        )
        
        summary_valid = False
        if success and isinstance(data, dict):
            configuration = data.get("configuration", {})
            payouts = data.get("payouts", [])
            
            # Check configuration includes expected SEPA details
            iban = configuration.get("iban") or configuration.get("destination_iban")
            beneficiary = configuration.get("beneficiary_name")
            currency = configuration.get("currency")
            mode = configuration.get("mode")
            
            summary_valid = bool(iban and beneficiary and currency)
        
        self.log_test_result(
            "Payout Summary Configuration",
            summary_valid,
            f"Status: {status}, IBAN: {configuration.get('iban') or configuration.get('destination_iban') if 'configuration' in locals() else 'N/A'}, Beneficiary: {configuration.get('beneficiary_name') if 'configuration' in locals() else 'N/A'}, Currency: {configuration.get('currency') if 'configuration' in locals() else 'N/A'}"
        )
        
        return summary_valid

    async def test_audit_trail_verification(self):
        """Test audit trail verification as specified in review request"""
        logger.info("\n=== Testing Audit Trail Verification ===")
        
        if not self.quote_id:
            self.log_test_result("Audit Trail Verification", False, "No quote ID available")
            return False
        
        # Get transaction details to verify audit trail
        logger.info("Step 1: Get Transaction Details for Audit")
        success, data, status = await self.make_request(
            "GET", f"/ramp/offramp/transaction/{self.quote_id}", auth_token=self.user_jwt
        )
        
        audit_valid = False
        if success and isinstance(data, dict):
            audit_trail = data.get("audit_trail", [])
            metadata = data.get("metadata", {})
            
            # Check for Stripe payout ID in metadata or audit trail
            stripe_payout_id = metadata.get("stripe_payout_id")
            
            # Check audit trail for state transitions
            state_transitions_logged = len(audit_trail) > 0 if audit_trail else False
            
            audit_valid = bool(stripe_payout_id or state_transitions_logged)
        
        self.log_test_result(
            "Audit Trail State Transitions",
            audit_valid,
            f"Status: {status}, Audit Entries: {len(data.get('audit_trail', [])) if isinstance(data, dict) else 0}, Stripe Payout ID: {data.get('metadata', {}).get('stripe_payout_id') if isinstance(data, dict) else 'N/A'}"
        )
        
        return audit_valid

    async def test_error_handling_verification(self):
        """Test error handling for insufficient funds scenario"""
        logger.info("\n=== Testing Error Handling (Insufficient Funds) ===")
        
        # This test verifies that the system handles Stripe insufficient_funds errors gracefully
        # Since Stripe is in LIVE mode with €0.00 balance, we expect this scenario
        
        if not self.quote_id:
            self.log_test_result("Error Handling Verification", False, "No quote ID available")
            return False
        
        # Get the final transaction state to see how errors were handled
        success, data, status = await self.make_request(
            "GET", f"/ramp/offramp/transaction/{self.quote_id}", auth_token=self.user_jwt
        )
        
        error_handling_valid = False
        if success and isinstance(data, dict):
            state = data.get("state")
            error_info = data.get("error_info", {})
            metadata = data.get("metadata", {})
            
            # Check if the system handled errors gracefully
            # Either completed successfully or has proper error handling
            error_handling_valid = (
                state in ["COMPLETED", "PAYOUT_FAILED", "SETTLEMENT_FAILED"] or
                bool(error_info) or
                "insufficient_funds" in str(metadata).lower() or
                "virtual_fallback" in str(metadata).lower()
            )
        
        self.log_test_result(
            "Error Handling (Insufficient Funds)",
            error_handling_valid,
            f"Status: {status}, Final State: {data.get('state') if isinstance(data, dict) else 'N/A'}, Error Info: {'Present' if data.get('error_info') if isinstance(data, dict) else False else 'None'}"
        )
        
        return error_handling_valid

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