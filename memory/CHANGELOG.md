# NeoNoble Ramp — Changelog

## 2026-04-02 (Session — Phase 7 ROADMAP Complete)

### Real-time WebSocket NENO Order Book - DONE
- WebSocket endpoint at /api/ws/orderbook/neno
- 15-level bid/ask ladder generated from dynamic pricing engine
- Spread, mid price, and 24h volume data streamed in real-time

### API Rate Limiting & Throttling - DONE
- Sliding window rate limiter middleware
- Per-route configurable limits (auth: 10/min, AI KYC: 5/min, default: 120/min)
- X-RateLimit-Remaining and X-RateLimit-Limit headers on all API responses
- 429 Too Many Requests with Retry-After header

### Admin Audit Log Viewer - DONE
- Platform-wide audit trail for administrators
- Browse events from NENO exchange, banking, KYC, notifications
- Filter by user email, event type, severity, date range
- Paginated results with CSV export
- Stats dashboard: users, transactions, KYC status, AML alerts, margin positions

### Automated NIUM Customer Onboarding - DONE
- Auto-create NIUM customer on demand
- Link customer_hash to user profile
- Automatic simulated fallback when NIUM API unavailable
- Status endpoint for onboarding state

### Export Portfolio/Trade Data (CSV) - DONE
- Trade history export (/api/export/trades/csv)
- Portfolio snapshot export (/api/export/portfolio/csv)
- Margin positions export (/api/export/margin/csv)
- Export buttons added to Portfolio Analytics page header

### Full i18n Translations (IT/EN/DE/FR) - DONE
- I18nProvider React context wrapping entire app
- 100+ translation keys covering all UI sections
- Language selection persisted in localStorage
- Dashboard, wallet, margin, KYC, settings, portfolio, admin translations

### Mobile-Responsive CSS - DONE
- Responsive breakpoints for 768px and 640px screens
- Stacked layouts on mobile for trading forms and navigation cards
- Admin sidebar overlay on small screens
- Touch-friendly scrolling for tables
- Reduced padding and font sizes on mobile

### Microservices Architecture Plan - DONE
- Service Registry for modular initialization
- 7 domain groups defined: Core, Exchange, Wallet, Compliance, Infrastructure, Liquidity, Gateway
- Migration roadmap with 6 ordered steps
- Architecture plan endpoint at /api/monitoring/architecture

### NENO Exchange /market Bugfix - DONE
- Fixed reference to undefined NENO_EUR_PRICE variable
- Now correctly uses dynamic pricing from _get_dynamic_neno_price()

### Testing
- iteration_13: All new features (18/18 backend, 100% frontend)

## 2026-04-02 (Session — Phase 6 Complete)

### Margin Trading PRO (P0) - DONE
- Professional candlestick charts, 4 chart types, 10 indicators
- Margin account, LONG/SHORT, leverage 2-20x, SL/TP

### Unified Wallet (P0) - DONE
- Internal + on-chain balances synced in "Unificato" tab

### Multi-chain Token Discovery (P0) - DONE
- Auto-discover ERC-20/BEP-20 tokens

### KYC/AML Compliance (P1) - DONE
- 4-tier KYC (0->3), admin review, AML monitoring
- AI-powered document verification via GPT-4o OCR
- Auto-approval for verified documents

### Dynamic NENO Pricing (P2) - DONE
- Order book pressure-based, max +/-5% deviation from EUR 10,000 base

### Real NIUM IBAN/SEPA Banking - DONE
- NIUM API integration for real IBAN creation
- SEPA withdrawal processing
- Webhook support for deposits
- Automatic fallback to simulated mode

### Advanced Orders - DONE
- Limit orders (GTC, IOC, FOK)
- Stop orders and Stop-Limit orders
- Trailing Stop orders (amount or percentage)
- Order management (cancel, history)
- Fund reservation on order placement

### 2FA TOTP Authentication - DONE
- TOTP setup with QR code generation
- Verification flow with backup codes (8 codes)
- Enable/disable with code validation
- Status endpoint

### Push Notifications - DONE
- In-app notification system
- SSE real-time delivery
- Read/unread tracking, mark all read
- Notification types: trade, margin, kyc, security, system

### Portfolio Analytics - DONE
- PnL curve chart (lightweight-charts)
- Portfolio allocation pie chart (SVG)
- Summary cards: Total Value, Realized PnL, Unrealized PnL, Win Rate
- Open margin positions table
- Recent trades list

### Settings Page - DONE
- Security tab: 2FA TOTP setup/disable with QR code
- Language tab: IT, EN, DE, FR selection
- Notifications tab: Toggle preferences per category

### Dashboard Updates - DONE
- Notification bell with unread badge
- Settings gear icon
- Portfolio Analytics link
- All navigation cards complete

### Testing
- iteration_10: Margin + Unified (19/19, 100%)
- iteration_11: KYC + Dynamic Pricing (15/15, 100%)
- iteration_12: All new features (21/21, 100%)
