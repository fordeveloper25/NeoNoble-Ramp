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
- Real-time: WebSocket portfolio tracker with live price feeds

## Completed Features — ALL ROADMAP ITEMS DONE

### Phase 1-4: Core Platform
- User Auth, Trading Engine, Settlement, Blockchain Monitoring

### Phase 5: Financial Infrastructure
- Multi-chain Wallet Sync (ETH, BSC, Polygon)
- Virtual IBAN / SEPA Banking Rails (NIUM real + simulated fallback)
- Physical Card Issuing & Tracking (NIUM live)
- Internal NENO Exchange (dynamic pricing)

### Phase 6: Advanced Trading & Compliance
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

### Phase 7: Infrastructure & Tooling
- Real-time WebSocket NENO Order Book
- API Rate Limiting & Throttling
- Admin Audit Log Viewer
- Automated NIUM Customer Onboarding
- Export Portfolio/Trade/Margin data as CSV
- Full i18n context with translations
- Mobile-responsive CSS
- Microservices Architecture Plan

### Phase 8: Portfolio Tracker + Real NIUM (Current)
- Real-time Portfolio Tracker with WebSocket live price feeds
- NIUM Onboarding rewritten: ALL 4 KYC modes (E_KYC, MANUAL_KYC, E_DOC_VERIFY, SCREENING_KYC)
- Zero simulation: real NIUM API errors with troubleshooting
- Full NIUM compliance flow: create, status, upload documents, respond RFI, update

## Key API Endpoints
- `WS /api/ws/portfolio/{token}` — Real-time portfolio with live prices
- `WS /api/ws/orderbook/neno` — NENO order book streaming
- `GET /api/nium-onboarding/available-methods` — All NIUM KYC modes
- `POST /api/nium-onboarding/create-customer` — Real NIUM customer creation
- `GET /api/nium-onboarding/compliance-status` — Real-time compliance check
- `POST /api/nium-onboarding/upload-document` — KYC document upload to NIUM
- `GET /api/export/trades/csv` — Trade history CSV export

## Key Collections
users, wallets, orders, trades, trading_engine_pairs, margin_accounts, margin_positions, neno_transactions, cards, user_wallets, onchain_wallets, virtual_ibans, banking_transactions, kyc_profiles, kyc_tx_log, aml_alerts, advanced_orders, totp_secrets, notifications, nium_api_logs, nium_customers
