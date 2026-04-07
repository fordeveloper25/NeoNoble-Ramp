# Changelog

## 2026-04-07 - Production-Grade Settlement System

### Settlement Ledger & State Machine
- Created `settlement_ledger.py` with 5-state machine: on_chain_executed → internal_credited → payout_pending → payout_sent → payout_settled
- Every sell/swap/offramp creates a ledger entry with full audit trail (state_history)
- `GET /api/neno-exchange/ledger` returns user's complete settlement history
- `GET /api/neno-exchange/tx-state/{tx_id}` returns transaction + ledger + payout status

### Payout Queue (Off-Ramp)
- `payout_queue` collection with retry logic (max 3 retries)
- Offramp creates payout entry with IBAN, beneficiary, amount, state
- `GET /api/neno-exchange/payouts` shows queue status
- Background processor runs every 30s, executes via NIUM when API key present
- Webhook-ready architecture for settlement confirmation

### Force Balance Sync
- `POST /api/neno-exchange/force-balance-sync` - Submit tx_hash to force-credit
- Reads on-chain receipt, parses Transfer event, credits internally
- Prevents double-credit with onchain_deposits dedup
- UI: Force Sync section in deposit tab with input + button

### Blockchain Listener Enhancement
- BSC_POLL_INTERVAL reduced from 120s to 3s for near-real-time detection
- Extended lookback window from 100 to 500 blocks on startup
- Enhanced user matching: connected_wallets, web3_address, neno_transactions, onchain_deposits
- New `_find_user_by_wallet()` method with 3-level fallback

### Reconciliation Engine
- `POST /api/neno-exchange/reconcile` (admin only) scans unmatched deposits
- Background reconciliation every 15s via scheduler
- Auto-credits any deposits that slipped through

### Balance Sync Fix
- All sell/swap/offramp now ALWAYS debit internally (no `if not onchain_tx` guard)
- verify-deposit credits → sell/swap debits = net 0 for NENO (correct)
- 5s polling in NenoExchange.js for real-time balance display
- Immediate balance update from transaction response

### Test Results
- Iteration 29: 18/18 backend tests passed, all frontend UI verified
- Iteration 28: 14/14 passed (balance sync bug fix)
- Iteration 27: 18/18 passed (custom token features)

## 2026-04-06 - Phase 1-4 Custom Token System
- Token creation, buy/sell, swap, live balances
- Custom token marketplace page
- Dashboard integration

## 2026-04-06 - Balance Sync Bug Fix
- Removed `if not onchain_tx` guard from sell/swap/offramp debit operations
