# NeoNoble Ramp — Product Requirements Document

## Original Problem Statement
Build "NeoNoble Ramp", a global enterprise-grade fintech infrastructure platform with: Trading Engine, Internal NENO Exchange (bypassing Transak), Multi-chain Wallet sync, Banking Rails, Card Issuing (NIUM), Full Margin Trading with professional charts, Unified Wallet, Token Discovery, KYC/AML Compliance, and Dynamic NENO Pricing.

## User Personas
- **Retail Traders**: Trade crypto with leveraged margin, professional charting tools
- **NENO Holders**: Buy/sell/off-ramp NENO token through internal exchange
- **Platform Admins**: Manage KYC applications, monitor AML alerts, oversee platform operations
- **API Developers**: Integrate via developer portal with HMAC-secured API keys

## Core Requirements

### Phase 1-4 (COMPLETED)
- User Auth (registration, login, password reset)
- Trading Engine with Order Book
- Internal PoR Settlement
- Blockchain monitoring (BSC)
- Wallet management with multi-asset balances
- Admin promotion & user management

### Phase 5 (COMPLETED)
- Multi-chain Wallet Sync (ETH, BSC, Polygon)
- Virtual IBAN / SEPA Banking Rails (simulated)
- Physical Card Issuing & Tracking (NIUM live key)
- Internal NENO Exchange (€10,000 base, 12 assets, card/bank off-ramp)

### Phase 6 (COMPLETED — Current Session)
- **Full Margin Trading** — Professional candlestick charts (lightweight-charts), 4 chart types (Candlestick, Line, Area, Bar), 10 technical indicators (SMA 20/50/200, EMA 12/26/50, RSI 14, MACD, Bollinger Bands, Volume), leveraged LONG/SHORT positions up to 20x
- **Unified Wallet** — Tab showing internal + on-chain balances synced across all chains
- **Multi-chain Token Discovery** — Auto-discover ERC-20/BEP-20 tokens in connected wallets
- **KYC/AML Compliance Layer** — 4-tier KYC system (Non Verificato → Base → Verificato → Premium), admin review workflow, AML monitoring (large tx alerts, velocity alerts, structuring detection)
- **Dynamic NENO Pricing** — Order book pressure-based pricing with max 5% deviation from €10,000 base

## Tech Stack
- Backend: FastAPI + MongoDB (Motor) + Python 3.11
- Frontend: React.js + Tailwind CSS + Shadcn UI + lightweight-charts
- Blockchain: Web3 RPCs (Ethereum, BSC, Polygon)
- Card Issuing: NIUM API (live production key)
- Auth: JWT-based custom authentication

## Architecture
Monolithic FastAPI application with router-based separation:
```
/app/backend/
├── server.py (main app, lifespan, router mounting)
├── routes/ (23+ routers)
│   ├── auth.py, trading_engine_routes.py, multichain_routes.py
│   ├── neno_exchange_routes.py, banking_routes.py, card_routes.py
│   ├── kyc_routes.py, wallet_routes.py, ...
├── services/ (15+ services)
├── database/ (MongoDB + dual manager)
└── middleware/ (auth, HMAC)
```

## Key DB Collections
- `users`, `wallets`, `orders`, `trades`, `trading_pairs`
- `margin_accounts`, `margin_positions`
- `neno_transactions`, `cards`, `user_wallets`, `onchain_wallets`
- `ibans`, `banking_transactions`
- `kyc_profiles`, `kyc_tx_log`, `aml_alerts`
