backend:
  - task: "Swap Engine Health & Tokens"
    implemented: true
    working: true
    file: "/app/backend/routes/swap_routes.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: "NA"
        agent: "main"
        comment: "New on-chain swap engine. GET /api/swap/health should return hot_wallet_configured=true, rpc_connected=true, oneinch_configured=true. GET /api/swap/tokens should return 8 BSC tokens (NENO, USDT, BTCB, BUSD, WBNB, USDC, CAKE, ETH)."
      - working: true
        agent: "testing"
        comment: "✅ Swap engine health and tokens endpoints working correctly. GET /api/swap/health returns hot_wallet=0x18CE1930820d5e1B87F37a8a2F7Cf59E7BF6da4E, hot_wallet_configured=true, rpc_connected=true, oneinch_configured=true, and 8 supported tokens. GET /api/swap/tokens returns BSC chain with all 8 expected tokens (NENO, USDT, BTCB, BUSD, WBNB, USDC, CAKE, ETH) with proper structure."

  - task: "Swap Quote Endpoint"
    implemented: true
    working: true
    file: "/app/backend/engines/swap_engine.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: "NA"
        agent: "main"
        comment: "POST /api/swap/quote returns estimated output via 1inch (primary) with PancakeSwap V2 fallback. For USDT→BTCB should return real 1inch quote. For NENO (no liquidity) should return source='estimate' with fallback note. No auth required."
      - working: true
        agent: "testing"
        comment: "✅ Swap quote endpoint working correctly. USDT→BTCB returns 1inch quote with estimated_amount_out=0.001321655289183958. NENO→USDT returns source='estimate' with fallback note as expected. Invalid token 'FOO' correctly rejected with 400 error. No auth required as designed."

  - task: "Swap Execute Endpoint (Tier 1→4 fallback)"
    implemented: true
    working: true
    file: "/app/backend/engines/swap_engine.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: "NA"
        agent: "main"
        comment: "POST /api/swap/execute requires JWT auth. Orchestrates Tier 1 (1inch) → Tier 2 (PancakeSwap) → Tier 3 (direct hot-wallet transfer) → Tier 4 (ledger credit + queue). Saves record to `swaps` collection. Requires valid user_wallet_address (BSC). Rate limited to 100/min/user. Note: Tier 1/2/3 will likely fail in the test env because the hot wallet has no actual BSC token reserves — expected behavior is that tiers progress and Tier 4 fires ('queued'), with record persisted and response success=true, queued=true. This is by design."
      - working: true
        agent: "testing"
        comment: "✅ Swap execute endpoint working correctly. JWT auth required (401 without token). Tier 1→4 fallback working as designed - executed swap fell back to Tier 4 (queued) as expected due to insufficient hot wallet reserves. Response: success=true, tier=tier4, queued=true, swap_id generated, record saved to database. Invalid wallet addresses and same token swaps properly rejected."

  - task: "Swap History & Auth Protection"
    implemented: true
    working: true
    file: "/app/backend/routes/swap_routes.py"
    stuck_count: 0
    priority: "medium"
    needs_retesting: false
    status_history:
      - working: "NA"
        agent: "main"
        comment: "GET /api/swap/history returns the authenticated user's swaps (JWT required). Unauthenticated call must return 401. Rate limiter configured via SWAP_RATE_LIMIT_PER_MIN=100."
      - working: true
        agent: "testing"
        comment: "✅ Swap history endpoint working correctly. Requires JWT auth (401 without token). With auth returns proper structure: user_id, count, history array. Successfully retrieved swap history showing the executed Tier 4 swap with all details including attempts array showing tier progression."

  - task: "Backend server boot-safety after refactor"
    implemented: true
    working: true
    file: "/app/backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: "NA"
        agent: "main"
        comment: "Fixed multiple pre-existing syntax errors (connector_manager.py rewrite, routing_service.py dedup, ramp_api.py repair, neno_exchange_routes.py cleanup, por_engine.py repair) that prevented backend from starting. All top-level heavy engine imports now use safe try/except. Verify auth (login/register/me) and existing ramp endpoints still work."
      - working: true
        agent: "testing"
        comment: "✅ Backend server boot-safety verified. Server starts successfully and all endpoints accessible. Health check returns 200. Auth endpoints working: registration successful, login working, /api/auth/me returns user profile. Existing endpoints like /api/ and /api/docs accessible. No critical startup errors observed."

  - task: "Swap Build Endpoint (user-signed calldata for MetaMask)"
    implemented: true
    working: true
    file: "/app/backend/engines/swap_engine_v2.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: "NA"
        agent: "main"
        comment: "NEW: POST /api/swap/build (JWT required) returns unsigned BSC transaction calldata for the user's wallet to sign (MetaMask). Replaces the previous server-side execute flow. Must return swap_id, source ('1inch' or 'pancakeswap'), to (router address), data (hex calldata), value, gas, chain_id=56, spender, needs_approve (bool), approve_calldata (null or {to,data,value}), estimated_amount_out, user_wallet, slippage_pct. Also creates a DB record with status='built'. For USDT→BTCB on a fresh wallet address (one that has never approved the 1inch router) needs_approve should be true and approve_calldata.to should be the USDT contract 0x55d398326f99059fF775485246999027B3197955. Unauth → 401. Invalid wallet → 400. Same-token → 400."
      - working: true
        agent: "testing"
        comment: "✅ Swap Build endpoint working perfectly. All test cases passed: (A1) Unauthenticated calls correctly rejected with 401. (A2) Happy path USDT→BTCB returns complete response with swap_id, source='1inch', valid router address, hex calldata, chain_id=56, needs_approve=true with correct approve_calldata pointing to USDT contract 0x55d398326f99059fF775485246999027B3197955, approve selector 0x095ea7b3, length 138 chars. (A3) Invalid wallet addresses rejected with 400. (A4) Same token swaps rejected with 400. (A5) Unsupported tokens rejected with 400. Database record created with status='built' and mode='user_signed'. All required fields present and correctly formatted."

  - task: "Swap Track Endpoint (user-signed flow)"
    implemented: true
    working: true
    file: "/app/backend/engines/swap_engine_v2.py"
    stuck_count: 0
    priority: "medium"
    needs_retesting: false
    status_history:
      - working: "NA"
        agent: "main"
        comment: "NEW: POST /api/swap/track {swap_id, tx_hash} (JWT required). Queries the BSC RPC for the tx receipt and updates the swaps collection (status = pending|success|failed). Returns {swap_id, tx_hash, status, block_number, gas_used, explorer_url}. For a tx_hash that does not exist on BSC, status should be 'pending' (not an error). For a real confirmed tx_hash (hard to test without a real swap), status=success and block_number populated. At minimum: (1) unauth → 401; (2) valid JWT + random 0x…64 hex hash → status='pending', no crash; (3) DB record created/updated."
      - working: true
        agent: "testing"
        comment: "✅ Swap Track endpoint working correctly. All test cases passed: (B1) Unauthenticated calls correctly rejected with 401. (B2) Valid JWT with non-existent tx hash returns status='pending', correct explorer_url='https://bscscan.com/tx/0x...', block_number=null, gas_used=null without crashing. (B3) Prefixless hex tx hashes correctly handled by adding 0x prefix. Database records properly created/updated. No errors or crashes observed."

frontend:
    implemented: true
    working: true
    file: "/app/backend/routes/password_routes.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: true
        agent: "testing"
        comment: "✅ Service status endpoint working correctly. Returns email_configured: false (no API key set) and token_expiry_hours: 1 as expected."

  - task: "Password Reset Request Flow"
    implemented: true
    working: true
    file: "/app/backend/routes/password_routes.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: true
        agent: "testing"
        comment: "✅ Password reset request flow working correctly. Creates test user, handles existing email requests, prevents email enumeration for non-existent emails. All responses return success status as expected."

  - task: "Token Verification"
    implemented: true
    working: true
    file: "/app/backend/routes/password_routes.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: true
        agent: "testing"
        comment: "✅ Token verification working correctly. Invalid tokens return 400 error with 'Token non valido o scaduto' message as expected."

  - task: "Password Change (Authenticated)"
    implemented: true
    working: true
    file: "/app/backend/routes/password_routes.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: false
        agent: "testing"
        comment: "❌ Initial test failed due to password hashing mismatch between auth service (bcrypt) and password routes (SHA-256)."
      - working: true
        agent: "testing"
        comment: "✅ FIXED: Updated password routes to use bcrypt hashing consistent with auth service. Password change now works correctly with current password verification."

  - task: "Login Verification with New Password"
    implemented: true
    working: true
    file: "/app/backend/routes/auth.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: true
        agent: "testing"
        comment: "✅ Login with new password works correctly after password change. JWT token is returned successfully."

  - task: "Old Password Rejection"
    implemented: true
    working: true
    file: "/app/backend/routes/auth.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: true
        agent: "testing"
        comment: "✅ Old password is correctly rejected after password change. Returns 401 Unauthorized as expected."

  - task: "Swap Frontend Page (/swap)"
    implemented: true
    working: true
    file: "/app/frontend/src/pages/Swap.js"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: "NA"
        agent: "main"
        comment: "Professional Swap page with token selector (NENO, USDT, BTCB, BUSD, WBNB, USDC, CAKE, ETH), auto-quote on input, slippage selector, wallet-connect requirement, BSC chain check, swap history, and health badges. Linked from Dashboard and route /swap."
      - working: "NA"
        agent: "main"
        comment: "UPDATED: Added Low BNB Gas banner (shows when connected wallet has < 0.002 BNB). Banner displays in amber/orange gradient with warning icon, informs user about gas requirements. Also added Help link in header pointing to /help page. Needs frontend testing."
      - working: true
        agent: "testing"
        comment: "✅ Swap page fully functional. All elements verified: (1) Header with '⚡ Swap On-Chain' title, (2) '❓ Aiuto' link to Help page, (3) '← Dashboard' link, (4) Health badges showing RPC connected, 1inch enabled, BSC chain 56, User-signed mode, (5) Token selector fields (You pay / You receive) with 8 tokens, (6) Slippage selector with preset buttons (0.5%, 0.8%, 1%, 2%), (7) Connect wallet button (wallet not connected - expected), (8) Swap history section showing recent swaps, (9) Swap button. Low BNB Gas banner NOT visible (correct - wallet not connected). Banner code logic verified in Swap.js: threshold 0.002 BNB, amber/orange gradient styling, Italian message about gas requirements. Visual design consistent with dark gradient theme (slate/purple). All navigation working correctly."

  - task: "Help/FAQ Page (/help)"
    implemented: true
    working: true
    file: "/app/frontend/src/pages/Help.js"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: "NA"
        agent: "main"
        comment: "NEW: Created comprehensive Help/FAQ page accessible at /help. Contains 5 sections: (1) How to Connect MetaMask, (2) Why BNB is needed for gas, (3) How to do Approve + Swap, (4) How to verify transactions on BscScan, (5) Security best practices. All content in Italian, dark mode design consistent with app theme, includes CTA button to Swap page. Route added to App.js as protected route. Needs frontend testing."
      - working: true
        agent: "testing"
        comment: "✅ Help/FAQ page fully functional. All elements verified: (1) Header with '❓ Guida agli Swap On-Chain' title, (2) '→ Vai a Swap' and '← Dashboard' links in header, (3) All 5 FAQ sections present with correct icons: 🔗 Come Connettere MetaMask, ⛽ Perché Serve BNB per il Gas, 🔄 Come Fare Approve + Swap di Token, 🔍 Come Verificare la Transazione su BscScan, 🛡️ Sicurezza e Best Practices, (4) CTA button '🚀 Vai a Swap On-Chain' at bottom redirects to /swap, (5) All content in Italian language, (6) Visual design consistent with app theme (dark gradient slate/purple, proper spacing, rounded corners, backdrop blur effects). Navigation links working correctly: Help ↔ Swap ↔ Dashboard. Page accessible from Swap page via '❓ Aiuto' link."

  - task: "Forgot Password Page"
    implemented: true
    working: true
    file: "/app/frontend/src/pages/ForgotPassword.js"
    stuck_count: 0
    priority: "medium"
    needs_retesting: false
    status_history:
      - working: "NA"
        agent: "testing"
        comment: "Frontend testing not performed as per testing agent limitations."
      - working: true
        agent: "testing"
        comment: "✅ Forgot Password page fully functional. Login page has 'Password dimenticata?' link that correctly navigates to /forgot-password. Page displays proper UI with email input, submit button, and shows success state with green checkmark after email submission. All expected elements present and working correctly."

  - task: "Reset Password Page"
    implemented: true
    working: true
    file: "/app/frontend/src/pages/ResetPassword.js"
    stuck_count: 0
    priority: "medium"
    needs_retesting: false
    status_history:
      - working: "NA"
        agent: "testing"
        comment: "Frontend testing not performed as per testing agent limitations."
      - working: true
        agent: "testing"
        comment: "✅ Reset Password page implemented with complete functionality including token verification, password input fields with validation, and success state handling. Component properly handles token validation and password reset flow."

metadata:
  created_by: "testing_agent"
  version: "1.0"
  test_sequence: 1
  run_ui: false

test_plan:
  current_focus: []
  stuck_tasks: []
  test_all: false
  test_priority: "high_first"

agent_communication:
  - agent: "testing"
    message: "Password Reset feature testing completed successfully. All backend APIs are working correctly."
  - agent: "testing"
    message: "✅ Frontend Password Reset Testing Complete."
  - agent: "main"
    message: "Previous Tier 1→4 swap engine replaced with USER-SIGNED mode after product decision. The backend no longer executes swaps on behalf of users; it only provides quotes + unsigned transaction calldata, which the user's own wallet (MetaMask) signs. The user pays the gas (no drip). Hot wallet private key is still present in .env but is NOT used by the new /api/swap/* endpoints. New endpoints: /api/swap/build (auth, returns calldata), /api/swap/track (auth, verifies user-submitted tx hash). The /api/swap/execute endpoint is REMOVED. /api/swap/health now returns mode='user_signed'. Please test only the two new tasks listed in test_plan.current_focus."
  - agent: "testing"
    message: "✅ NeoNoble On-Chain Swap Backend Testing Complete. All previous Tier 1-4 tests passed."
  - agent: "testing"
    message: "✅ User-Signed Swap Endpoints Testing Complete. Both /api/swap/build and /api/swap/track endpoints working perfectly. All authentication, validation, error handling, and database persistence working correctly. Sanity checks (health, tokens, quote) also confirmed working. Auth regression tests passed. Ready for production use."
  - agent: "testing"
    message: "✅ NeoNoble Ramp Swap Frontend Testing Complete. Tested Swap page (/swap) and Help/FAQ page (/help) including Low BNB Gas banner logic. All features working correctly: (1) Login flow successful, (2) Swap page loads with all expected elements (header, health badges, token selectors, slippage, wallet connect, swap history), (3) Low BNB banner code verified (not visible without wallet - correct behavior), (4) Help page accessible with all 5 FAQ sections in Italian, (5) All navigation links working (Help ↔ Swap ↔ Dashboard), (6) CTA button redirects correctly, (7) Visual design consistent across pages. NOTE: admin@neonobleramp.com user not found in database - used test@example.com for testing. Main agent should create admin user if needed."

