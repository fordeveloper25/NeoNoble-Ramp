# NeoNoble Ramp — Product Requirements Document

## Original Problem Statement
Build "NeoNoble Ramp", a global enterprise-grade fintech infrastructure platform with full financial infrastructure including real banking rails, card issuing, crypto exchange, margin trading, KYC/AML compliance, and multi-chain wallet management.

## User Personas
- **Retail Traders**: Trade crypto with leveraged margin, professional charting tools, advanced order types
- **NENO Holders**: Buy/sell/off-ramp NENO token through internal exchange with dynamic pricing
- **Platform Admins**: Manage KYC applications, monitor AML alerts, oversee platform operations via audit logs
- **API Developers**: Integrate via developer portal with HMAC-secured API keys

## Core Architecture
- Backend: FastAPI + MongoDB (Motor) + Python 3.11
- Frontend: React.js + Tailwind CSS + Shadcn UI + lightweight-charts
- Blockchain: Web3 RPCs (Ethereum, BSC, Polygon)
- Banking: NIUM API (live production key) for IBAN/SEPA
- KYC: NIUM verification + AI OCR via GPT-4o (Emergent LLM key)
- Auth: JWT + TOTP 2FA (pyotp)
- Notifications: SSE (Server-Sent Events) + MongoDB persistence
- Card Issuing: NIUM API (live production key)
- i18n: 4 languages (IT, EN, DE, FR) via React Context
- Rate Limiting: In-memory sliding window middleware
- Microservices: Domain-based modular architecture (7 domains ready for split)

## Completed Features

### Phase 1-4
- User Auth, Trading Engine, Settlement, Blockchain Monitoring

### Phase 5
- Multi-chain Wallet Sync (ETH, BSC, Polygon)
- Virtual IBAN / SEPA Banking Rails (NIUM real + simulated fallback)
- Physical Card Issuing & Tracking (NIUM live)
- Internal NENO Exchange (dynamic pricing)

### Phase 6
- Full Margin Trading PRO with candlestick charts + 10 indicators
- Unified Wallet (internal + on-chain)
- Multi-chain Token Discovery
- KYC/AML Compliance (4-tier + AI verification)
- Dynamic NENO Pricing (order book pressure)
- Advanced Orders (Limit, Stop, Trailing Stop)
- 2FA TOTP Authentication
- Push Notifications (SSE)
- Portfolio Analytics (PnL chart, allocation pie)
- Settings page (Security, Language, Notifications)
- Multi-language support (IT, EN, DE, FR)
- Real NIUM IBAN/SEPA integration with fallback
- AI-powered KYC document verification (GPT-4o OCR)

### Phase 7 (Current Session - ROADMAP Completion)
- Real-time WebSocket NENO Order Book
- API Rate Limiting & Throttling (sliding window, per-route limits)
- Admin Audit Log Viewer (browse, filter, export CSV)
- Automated NIUM Customer Onboarding (with simulated fallback)
- Export Portfolio/Trade/Margin data as CSV
- Full i18n context with translations for all UI text (IT/EN/DE/FR)
- Mobile-responsive CSS optimizations
- Microservices Architecture Plan (7 domain groups, migration roadmap)
- Service Registry for modular initialization

## Key Collections
users, wallets, orders, trades, trading_engine_pairs, margin_accounts, margin_positions, neno_transactions, cards, user_wallets, onchain_wallets, virtual_ibans, banking_transactions, kyc_profiles, kyc_tx_log, aml_alerts, advanced_orders, totp_secrets, notifications

## API Endpoints (New in Phase 7)
- `GET /api/admin/audit/stats` — Platform audit statistics
- `GET /api/admin/audit/logs` — Paginated audit log viewer
- `GET /api/admin/audit/export/csv` — CSV export of audit data
- `GET /api/export/trades/csv` — User trade history CSV
- `GET /api/export/portfolio/csv` — User portfolio CSV
- `GET /api/export/margin/csv` — User margin positions CSV
- `POST /api/nium-onboarding/create-customer` — Auto NIUM customer creation
- `GET /api/nium-onboarding/status` — Onboarding status
- `GET /api/monitoring/architecture` — Microservices plan
- `WS /api/ws/orderbook/neno` — Real-time NENO order book

## All Completed — No Remaining Backlog
All P0-P3 features from the original ROADMAP have been implemented and tested.
