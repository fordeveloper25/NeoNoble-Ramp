# NeoNoble Ramp - Changelog

## [5.1.0] - 2026-03-31 - Transak $NENO On/Off-Ramp Widget

### Changed
- **TransakWidget** rewritten with official `@transak/transak-sdk` v4.0.2
  - Uses real Transak SDK iframe (replaces custom mock widget)
  - Pre-configured for $NENO on BSC with EUR fiat default
  - Supports BUY and SELL modes
  - Transak event listeners: order created, successful, failed, widget close
  - Dark theme matching NeoNoble brand (`#7c3aed`)
- Dashboard "$NENO On/Off-Ramp" card with Acquista/Vendi buttons (Italian)
- Installed `@transak/transak-sdk@4.0.2`, pinned `query-string@7.1.3` for CJS compat

### Note
- Using Transak **staging** API key — iframe content loads fully only with production key + whitelisted domain

### Added
- **Multi-Chain Wallet Service** (`multichain_service.py`) - Real on-chain balance sync for ETH/BSC/Polygon via public RPCs
- **Multi-Chain API Routes** (`multichain_routes.py`) - Link wallet, sync balances, chain discovery
- **Banking Rails** (`banking_routes.py`) - Virtual IBAN assignment, SEPA deposit/withdrawal, transaction history, admin overview
- **Enhanced Card Issuing** - Physical cards with shipping address, tracking number (NN-*), delivery estimates
- **Wallet & Banking Frontend** (`WalletPage.js`) - 3-tab page: Wallet (balances, convert), On-Chain (multi-chain sync), Banking (IBAN/SEPA)
- **Dashboard Navigation** - "Wallet & Banking" card added to dashboard quick links
- Card shipping status endpoint `GET /api/cards/{id}/shipping`
- Card creation now validates shipping address for physical cards (400 error if missing)
- Physical cards start with `pending_shipment` status (virtual remain `active`)

### Validated (E2E - 100% pass rate, 24/24 tests + frontend)
- Multi-chain wallet sync (3 chains)
- Banking Rails (IBAN assign, SEPA deposit/withdrawal)
- Enhanced card issuing (physical + shipping)
- Crypto-to-Fiat payment pipeline
- Wallet & Banking UI (all 3 tabs)

## [4.0.0] - 2026-03-12 - Final Execution Phase Validation

### Fixed
- **CRITICAL**: Duplicate key error in `settlements` collection - conflicting unique index on `settlement_id` between `settlement_service.py` and `settlement_engine.py`. Fixed by adding `settlement_id` field to settlement_engine.py documents and making index sparse
- **CRITICAL**: `setInterval` naming conflict in TradingPage.js - React useState setter shadowed `window.setInterval`, breaking auto-refresh of ticker data. Renamed to `setChartInterval`
- Stop-Loss/Take-Profit orders with `pending_trigger` status couldn't be cancelled. Added `pending_trigger` to cancellable statuses
- Card `created_at` datetime serialization issue in card_routes.py response

### Added
- Stop-Loss (SL) and Take-Profit (TP) buttons in trading order form UI
- Trigger price input field for SL/TP orders in frontend
- Cancel button for `pending_trigger` orders in MyOrders component

### Validated (E2E - 100% pass rate, 33/33 tests)
- Card Issuing (NIUM integration)
- Crypto-to-Fiat Settlement Engine
- Trading Engine across all 15 pairs
- Conversion & Settlement Pipeline (Trade -> Convert -> Settle -> Wallet)
- NENO Token Liquidity (NENO-EUR, NENO-USDT)
- Advanced Trading Orders (Stop-Loss, Take-Profit)
- Margin Trading Infrastructure
- WebSocket Infrastructure
- Paper Trading Environment
- Token Compatibility Layer

## [3.0.0] - Phase 3: Trading & Developer Ecosystem
- Exchange Engine with matching engine
- Professional candlestick charts (lightweight-charts)
- Developer API portal
- Exchange connectors (Binance, Kraken, Coinbase)

## [2.0.0] - Phase 2: Platform Infrastructure
- Market Data (CoinGecko)
- Admin Analytics Dashboard
- Crypto Card UI
- Password Reset (Resend)

## [1.0.0] - Phase 1: Core Economic Engine
- Token Creation & Management
- Token Listing Marketplace
- Subscription Plans
- Authentication (JWT)
