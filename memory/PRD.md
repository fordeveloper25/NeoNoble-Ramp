# NeoNoble Ramp — Product Requirements Document

## Original Problem Statement
Build "NeoNoble Ramp", a global enterprise-grade fintech infrastructure platform with full financial infrastructure including real banking rails, card issuing, crypto exchange, margin trading, KYC/AML compliance, multi-chain wallet management, and multi-channel notifications.

## Core Architecture
- Backend: FastAPI + MongoDB (Motor) + Python 3.11
- Frontend: React.js + Tailwind CSS + Shadcn UI + lightweight-charts
- Blockchain: Web3 RPCs (Ethereum, BSC, Polygon)
- Banking: NIUM API (real Client Hash: 24dba820-d8da-4ce6-b72f-d07f98ffa2fd)
- KYC: NIUM + AI OCR via GPT-4o (Emergent LLM key)
- Auth: JWT + TOTP 2FA
- Notifications: Multi-channel (Email/Resend + In-app/SSE + Browser Push + WebSocket)
- Rate Limiting: Sliding window middleware
- i18n: IT, EN, DE, FR

## ALL Features Complete

### Core Platform (Phase 1-4)
User Auth, Trading Engine, Settlement, Blockchain Monitoring

### Financial Infrastructure (Phase 5)
Multi-chain Wallet, IBAN/SEPA Banking, Card Issuing, NENO Exchange

### Advanced Trading & Compliance (Phase 6)
Margin Trading PRO, Unified Wallet, Token Discovery, KYC/AML, Dynamic Pricing, Advanced Orders, 2FA, Notifications, Portfolio Analytics, Settings, i18n, Real NIUM IBAN/SEPA, AI KYC OCR

### Infrastructure & Tooling (Phase 7)
WebSocket NENO Order Book, Rate Limiting, Admin Audit Log, NIUM Onboarding, Export CSV, Mobile Responsive, Microservices Plan

### Real-time & Multi-channel (Phase 8)
- Real-time Portfolio Tracker (WebSocket live prices, session sparkline, margin PnL)
- NIUM Onboarding (4 KYC modes, zero simulation, real API only)
- Multi-channel Notification Dispatch (Email + In-app + Browser Push)
- Price Alerts (create, trigger, delete, multi-channel notification on trigger)
- Browser Push Notifications (Web Notification API polling)
- Trade event notifications (NENO buy/sell → email + in-app + push)

## Key New Endpoints (Phase 8)
- `WS /api/ws/portfolio/{token}` — Real-time portfolio
- `POST /api/alerts/create` — Price alert
- `GET /api/alerts` — List alerts
- `POST /api/alerts/check` — Check & trigger alerts
- `GET /api/browser-push/pending` — Browser push polling
- `POST /api/browser-push/delivered` — Mark push delivered

## Key Collections
users, wallets, orders, trades, margin_positions, neno_transactions, cards, banking_transactions, kyc_profiles, advanced_orders, totp_secrets, notifications, price_alerts, browser_push_queue, nium_api_logs
