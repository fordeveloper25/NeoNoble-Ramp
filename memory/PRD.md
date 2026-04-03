# NeoNoble Ramp — Product Requirements Document

## Original Problem Statement
Build "NeoNoble Ramp", a global enterprise-grade fintech infrastructure platform featuring:
- Custom internal NENO Exchange (bypassing 3rd party providers like Transak) with fixed base price EUR 10,000
- Full Margin Trading with advanced orders
- Multi-chain Token Discovery and Unified Wallet (ETH, BSC, Polygon)
- IBAN/SEPA Banking Rails
- Real Card Issuing via NIUM (production key)
- AI KYC Verification
- Real-time Portfolio Tracker via WebSockets
- Multi-channel Notifications (email, in-app, browser push, SMS)
- Background Scheduler (cron jobs for price alerts, DCA bot)
- PDF Compliance Reports
- DCA (Dollar-Cost Averaging) Trading Bot
- Data Export (CSV/PDF)
- Admin Audit Logging
- Referral System with NENO bonuses
- Advanced Portfolio Analytics (Sharpe ratio, Sortino ratio, drawdown, volatility)
- Enhanced KYC/AML Compliance (risk scoring, PEP screening, compliance reports)
- Multi-language i18n (IT, EN, DE, FR, ES, PT, JA, ZH, AR)
- Monte Carlo VaR Simulation
- PEP Screening & Sanctions List
- Microservices Domain Registry

## Completed Features (100%)
- [x] Trading Engine + Margin Trading (up to 20x leverage)
- [x] NENO Custom Exchange — Buy, Sell, Swap, Off-Ramp, Create Token
- [x] Custom Token Creation + Immediate Wallet Credit + Swap/Sell/Off-Ramp
- [x] Dynamic NENO Pricing (order book pressure based)
- [x] Multi-Chain Wallet Sync (ETH, BSC, Polygon)
- [x] Banking Rails (Virtual IBAN, SEPA)
- [x] Card Issuing via NIUM
- [x] AI KYC Verification (GPT Image OCR)
- [x] Real-time Portfolio Tracker (WebSocket)
- [x] Multi-channel Notifications (email, in-app, push, SMS-ready)
- [x] DCA Trading Bot
- [x] PDF Compliance Reports
- [x] Data Export (CSV/PDF)
- [x] Admin Audit Logging
- [x] Referral System with NENO bonuses
- [x] Advanced Portfolio Analytics
- [x] Monte Carlo VaR Simulation
- [x] PEP Screening & Sanctions List
- [x] i18n (9 languages)
- [x] Microservices Domain Registry

## Critical Bug Fixes
- [x] "body stream already read" — Fixed with res.clone() triple-fallback pattern in safeJson
- [x] NENO not recognized in swap quotes — Fixed _get_any_price_eur
- [x] 520 Deployment Health Check — Fixed with background_init in lifespan
- [x] Webpack build errors — Fixed with craco.config.js polyfills

## External Blockers
- NIUM templateId: Must be configured in NIUM Admin portal
- Twilio SMS: Keys not yet provided
