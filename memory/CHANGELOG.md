# NeoNoble Ramp — Changelog

## April 3, 2026 (Session 4 — Continued)
### Settlement Tracking & Wallet Sync (P0)
- Added `_settlement_record()` function generating 0x-prefixed SHA-256 settlement hashes
- Every Buy/Sell/Swap/OffRamp transaction now includes: settlement_hash, settlement_status, settlement_timestamp, settlement_network, settlement_confirmations, settlement_details
- New endpoints: GET /settlement/{tx_id}, POST /wallet-sync, GET /portfolio-snapshot
- Frontend shows settlement hash in green banner with copy button
- Transaction history displays settlement hashes + checkmark icons for settled transactions

### WalletConnect Error Fix
- Conditional WalletConnect loading: only initializes if REACT_APP_WALLETCONNECT_PROJECT_ID is set and not 'demo-project-id'
- Eliminates "preloadListings" console errors in production

### Blockchain Listener Rate Limiting
- Increased poll interval from 15s to 60s to avoid Infura 429 rate limits
- Downgraded RPC errors from ERROR to DEBUG level logging

### Web3 Wallet Integration in Exchange
- Integrated useWeb3() context into NenoExchange
- Shows connected wallet address + on-chain balance in header
- Auto-syncs wallet after every exchange operation

### Testing (4 iterations, all 100% pass)
- Iteration 19: NENO Exchange core (19/19 pass)
- Iteration 20: P2 Features — Monte Carlo, PEP, Languages (15/15 pass)
- Iteration 21: body-stream-already-read fix (100% pass)
- Iteration 22: Settlement tracking + wallet sync (16/16 pass)

## April 3, 2026 (Session 4 — Start)
### P0 — Fix "body stream already read"
- Replaced direct res.text()/res.json() with triple-fallback safeJson() using res.clone()

### P2 Features
- Monte Carlo VaR Simulation
- PEP Screening & Sanctions List
- 4 additional languages (PT, JA, ZH, AR)
- Microservices Domain Registry

## Prior Sessions
- Sessions 1-3: Full platform build, all Phase 5 features, deployment fixes
