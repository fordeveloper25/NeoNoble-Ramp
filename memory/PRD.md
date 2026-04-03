# NeoNoble Ramp — Product Requirements Document

## Original Problem Statement
Enterprise-grade fintech platform with NENO custom exchange, multi-chain wallet, NIUM banking, margin trading, DCA bot, compliance tools, and full settlement tracking.

## Architecture
- **Backend**: FastAPI + MongoDB (Motor) + Background Scheduler
- **Frontend**: React.js + Tailwind + Wagmi (MetaMask/Coinbase Wallet)
- **Settlement**: Internal Ledger with deterministic SHA-256 settlement hashes (0x-prefixed)
- **Wallet Sync**: Web3Context integration — Exchange reads connected wallet balance

## Completed Features (100%)
- [x] NENO Exchange: Buy, Sell, Swap, Off-Ramp, Create Token
- [x] Settlement Tracking: Every transaction gets a unique 0x-prefixed settlement_hash
- [x] Settlement Verification API: GET /api/neno-exchange/settlement/{tx_id}
- [x] Wallet Sync API: POST /api/neno-exchange/wallet-sync
- [x] Portfolio Snapshot API: GET /api/neno-exchange/portfolio-snapshot
- [x] Custom Token Creation with immediate wallet credit
- [x] Dynamic NENO Pricing (order book pressure)
- [x] Margin Trading (up to 20x leverage)
- [x] Multi-Chain Wallet Sync (ETH, BSC, Polygon)
- [x] IBAN/SEPA Banking Rails
- [x] Card Issuing (NIUM)
- [x] AI KYC Verification
- [x] DCA Trading Bot
- [x] PDF Compliance Reports
- [x] Referral System with NENO bonuses
- [x] Advanced Portfolio Analytics (Sharpe, Sortino, Drawdown)
- [x] Monte Carlo VaR Simulation
- [x] PEP Screening & Sanctions List
- [x] i18n (9 languages: IT, EN, DE, FR, ES, PT, JA, ZH, AR)
- [x] Microservices Domain Registry
- [x] WalletConnect Error Fix (conditional loading)
- [x] Blockchain Listener Rate Limiting (60s intervals)
- [x] Zero console errors in production

## Key API Endpoints
- POST /api/neno-exchange/buy — Buy NENO (returns settlement_hash)
- POST /api/neno-exchange/sell — Sell NENO (returns settlement_hash)
- POST /api/neno-exchange/swap — Swap tokens (returns settlement_hash)
- POST /api/neno-exchange/offramp — Off-ramp to card/bank (returns settlement_hash)
- POST /api/neno-exchange/create-token — Create custom token
- GET /api/neno-exchange/settlement/{tx_id} — Verify settlement
- POST /api/neno-exchange/wallet-sync — Sync external wallet
- GET /api/neno-exchange/portfolio-snapshot — Full portfolio with settlements

## External Blockers
- NIUM templateId: Must be configured in NIUM Admin portal
- Twilio SMS: Keys not yet provided
- WalletConnect: Requires real project ID from cloud.walletconnect.com for QR scanning

## Future / Backlog
- Full Microservices Split
- Real-time PEP screening (Dow Jones, Refinitiv)
- WebSocket price feeds for NENO
