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
    working: "NA"
    file: "/app/frontend/src/pages/Swap.js"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "Professional Swap page with token selector (NENO, USDT, BTCB, BUSD, WBNB, USDC, CAKE, ETH), auto-quote on input, slippage selector, wallet-connect requirement, BSC chain check, swap history, and health badges. Linked from Dashboard and route /swap."

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
  current_focus:
    - "Backend server boot-safety after refactor"
    - "Swap Engine Health & Tokens"
    - "Swap Quote Endpoint"
    - "Swap Execute Endpoint (Tier 1→4 fallback)"
    - "Swap History & Auth Protection"
  stuck_tasks: []
  test_all: false
  test_priority: "high_first"

agent_communication:
  - agent: "testing"
    message: "Password Reset feature testing completed successfully. All backend APIs are working correctly."
  - agent: "testing"
    message: "✅ Frontend Password Reset Testing Complete."
  - agent: "main"
    message: "Implemented production on-chain Swap engine (BSC) with Tier 1→4 fallback (1inch → PancakeSwap V2 → Direct hot-wallet transfer → Ledger credit + queue). Hot wallet configured from .env (HOT_WALLET_ADDRESS, HOT_WALLET_PRIVATE_KEY), 1inch API key in ONEINCH_API_KEY. New endpoints under /api/swap/* (health, tokens, quote, execute, history, legacy POST /). Fixed multiple pre-existing syntax errors in server.py, connector_manager.py, routing_service.py, ramp_api.py, neno_exchange_routes.py, por_engine.py, wallet_service.py that prevented backend startup. Please test: (1) backend health /api/health and auth endpoints still work; (2) /api/swap/health returns hot_wallet_configured=true rpc_connected=true oneinch_configured=true; (3) /api/swap/tokens returns 8 tokens; (4) /api/swap/quote for USDT→BTCB returns source='1inch' with non-zero estimated_amount_out; (5) NENO→USDT quote returns source='estimate' with fallback note; (6) POST /api/swap/execute WITHOUT auth returns 401; (7) POST /api/swap/execute WITH auth using test user returns success=true (likely tier4/queued because hot wallet has no on-chain token reserves in test env — this is the designed behavior); (8) /api/swap/history requires auth and lists the authenticated user's swaps. Do NOT attempt UI testing yet."
  - agent: "testing"
    message: "✅ NeoNoble On-Chain Swap Backend Testing Complete. All requested tests passed successfully: (1) Backend health /api/health working ✅ (2) Swap health endpoint returns all required fields with correct values ✅ (3) Swap tokens returns 8 BSC tokens ✅ (4) USDT→BTCB quote returns 1inch source with estimated_amount_out=0.001321655289183958 ✅ (5) NENO→USDT returns source='estimate' with fallback note ✅ (6) Execute without auth returns 401 ✅ (7) Execute with auth returns success=true, tier=tier4, queued=true as expected ✅ (8) History requires auth and returns user swaps ✅. Auth endpoints (register/login/me) working correctly. Server boot-safety verified after refactor. Note: Admin user admin@neonobleramp.com does not exist in database, but registration/login flow works properly."

