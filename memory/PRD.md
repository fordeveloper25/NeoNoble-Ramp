# NeoNoble Ramp - Product Requirements Document

## Original Problem Statement
Enterprise-grade fintech platform with multi-chain crypto wallet, NENO token exchange, real Web3/BSC integration, custom token creation, and complete banking/card infrastructure.

## Current Status: PRODUCTION-GRADE — FULLY OPERATIONAL

### What's 100% Operativo (No Dependencies)
- Custom Token Creation (Phase 1)
- Buy/Sell Custom Tokens (Phase 2)
- Swap Custom/Native tokens (Phase 3)
- Settlement Ledger with state machine
- Force Balance Sync from tx_hash
- Blockchain Listener (3s aggressive polling)
- Deposit Reconciliation (auto every 15s)
- Live Balance Polling (5s)
- DCA Trading Bot
- PDF Compliance Reports
- Referral System
- Margin Trading
- Multi-channel Notifications (SSE, Push)

### Attivabile con API Key/Provider
- Off-Ramp Payout Queue → needs NIUM API key to execute real bank transfers
- SMS Notifications → needs Twilio API keys
- NIUM Card Issuing → needs templateId configuration

## Transaction State Machine
```
on_chain_executed → internal_credited → payout_pending → payout_sent → payout_settled
                                                       ↘ payout_failed (retries up to 3x)
```

## Architecture
- Backend: FastAPI + MongoDB (Motor) + Web3.py + Alchemy BSC RPC
- Frontend: React.js + Tailwind + Wagmi/WalletConnect
- API calls: XMLHttpRequest (not fetch) to bypass Emergent interceptor
- Background: Blockchain listener (3s), DCA scheduler, price alerts, payout queue (30s), reconciliation (15s)

## Key API Endpoints
- `POST /api/neno-exchange/sell` - Sell NENO → state: internal_credited
- `POST /api/neno-exchange/swap` - Swap tokens → state: internal_credited
- `POST /api/neno-exchange/offramp` - Off-ramp → state: payout_pending, payout queued
- `POST /api/neno-exchange/force-balance-sync` - Force sync on-chain tx
- `POST /api/neno-exchange/reconcile` - Admin: reconcile unmatched deposits
- `GET /api/neno-exchange/ledger` - Settlement ledger with audit trail
- `GET /api/neno-exchange/payouts` - Payout queue status
- `GET /api/neno-exchange/tx-state/{tx_id}` - Full transaction state
- `GET /api/neno-exchange/live-balances` - Real-time balance polling
- `POST /api/neno-exchange/create-token` - Create custom token
- `POST /api/neno-exchange/buy-custom-token` - Buy custom tokens
- `POST /api/neno-exchange/sell-custom-token` - Sell custom tokens
- `GET /api/neno-exchange/my-tokens` - User's custom tokens

## Key DB Collections
- `settlement_ledger`: Full audit trail with state_history
- `payout_queue`: Off-ramp payouts with retry logic
- `onchain_deposits`: On-chain deposit tracking
- `custom_tokens`: User-created tokens
- `wallets`: Asset balances per user
- `neno_transactions`: Transaction history
