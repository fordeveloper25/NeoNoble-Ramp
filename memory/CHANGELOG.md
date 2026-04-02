# NeoNoble Ramp — Changelog

## 2026-04-02 (Phase 8 — Portfolio Tracker + Real NIUM)

### Real-time Portfolio Tracker (WebSocket) - DONE
- WebSocket endpoint at /api/ws/portfolio/{jwt_token}
- JWT authentication in URL path (uses 'sub' claim)
- Live price feeds streaming every 2 seconds
- Per-asset EUR value with price change percentages
- Session sparkline chart tracking portfolio value over time
- Margin positions count and unrealized PnL
- Auto-reconnect on disconnect
- Frontend: dark themed with asset cards, live ticker, connection status
- Dashboard navigation card with animated LIVE badge

### NIUM Onboarding — Completely Rewritten (Zero Simulation) - DONE
- ALL simulated fallbacks REMOVED
- 4 KYC modes: E_KYC, MANUAL_KYC, E_DOC_VERIFY, SCREENING_KYC
- /available-methods endpoint: returns all modes, required fields, and NIUM Portal setup instructions
- /create-customer: real NIUM API call with full EU compliance fields
- /customer-details: retrieve full NIUM customer data
- /compliance-status: real-time KYC/compliance monitoring
- /upload-document: upload KYC documents directly to NIUM
- /respond-rfi: respond to NIUM Request for Information
- /update-customer: update existing customer details
- NIUM_API_BASE updated to https://gateway.nium.com
- Real error responses with detailed troubleshooting steps
- All API calls logged to nium_api_logs collection

### Bugfix: WebSocket JWT Auth - DONE
- Fixed JWT token validation using 'sub' claim instead of 'user_id'
- Applied to Portfolio Tracker WebSocket endpoint

### Testing
- iteration_14: Portfolio Tracker + Real NIUM (10/10 backend, 100% frontend)

## 2026-04-02 (Phase 7 — ROADMAP Complete)

### Features Implemented
- Real-time WebSocket NENO Order Book
- API Rate Limiting & Throttling (sliding window)
- Admin Audit Log Viewer (browse, filter, export CSV)
- Automated NIUM Customer Onboarding
- Export Portfolio/Trade/Margin CSV
- Full i18n (IT/EN/DE/FR)
- Mobile-Responsive CSS
- Microservices Architecture Plan
- NENO Exchange /market bugfix

### Testing
- iteration_13: All features (18/18 backend, 100% frontend)

## 2026-04-02 (Phase 6 — Advanced Trading & Compliance)

### Features Implemented
- Margin Trading PRO, Unified Wallet, Token Discovery
- KYC/AML, Dynamic NENO Pricing, Advanced Orders
- 2FA TOTP, Notifications, Portfolio Analytics, Settings
- Real NIUM IBAN/SEPA, AI KYC OCR

### Testing
- iterations 10-12: All passed 100%
