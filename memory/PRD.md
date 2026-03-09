# NeoNoble Ramp - Product Requirements Document

## Original Problem Statement
Build the "NeoNoble Ramp" platform, a full-stack crypto on/off-ramp application with FastAPI backend, React frontend, and PostgreSQL/MongoDB database.

## User Personas
- **Retail Users**: Buy/sell crypto with EUR
- **Developers**: Integrate NeoNoble via API

## Core Requirements

### Phase 1: Core Platform (COMPLETED)
- User authentication (register/login/JWT)
- On-ramp (EUR to crypto) and Off-ramp (crypto to EUR)
- Real-time pricing from external APIs
- BSC blockchain integration
- HD wallet generation

### Phase 2: Provider-of-Record Engine (COMPLETED)
- Real EUR payouts via Stripe
- Treasury management
- Exposure tracking
- Market routing (shadow mode)
- Hedging service (shadow mode)
- Reconciliation audit ledger

### Phase 3: C-SAFE DEX Off-Ramp (COMPLETED - March 9, 2026)
- DEX aggregation (1inch, PancakeSwap)
- Batch execution (TWAP-style)
- On-chain settlement
- **Wallets configured:**
  - Conversion: `0x18CE1930820d5e1B87F37a8a2F7Cf59E7BF6da4E`
  - Settlement: `0xD91bFc93976054B9fF17672169F6AB558caBCf59`

### Phase 4: Transak Integration (COMPLETED)
- Transak widget embedded in dashboard
- Buy/Sell crypto modes
- Order tracking
- Audit log timeline

### Phase 5: Exchange Connectors (COMPLETED - March 9, 2026)
- Binance connector (mainnet - geo-blocked from server region)
- Kraken connector (WORKING - connected)
- **Coinbase connector (NEW - needs API keys)**
- Market data and trading API integration
- **LIVE TRADING ENABLED (shadow_mode=false)**

### Phase 6: Password Reset via Email (COMPLETED)
- Resend integration for transactional emails
- Forgot password flow
- Reset password with token

### Phase 7: Transak Audit Log (COMPLETED)
- Session-based audit tracking
- Event logging
- Visual timeline component

### Phase 8: PostgreSQL Migration (COMPLETED - March 9, 2026)
- PostgreSQL 15 installed and configured
- All 11 tables created (users, transactions, settlements, etc.)
- **DUAL-WRITE MODE ACTIVE**
- Data syncs to both MongoDB and PostgreSQL

## Technical Stack
- **Backend**: FastAPI, Python 3.11
- **Frontend**: React 18, Tailwind CSS, Shadcn/UI
- **Database**: MongoDB + PostgreSQL (dual-write)
- **Blockchain**: BSC via web3.py
- **Payments**: Stripe
- **Email**: Resend
- **Exchanges**: Kraken (live), Binance (geo-blocked), Coinbase (pending)

## Configured Wallets
- **Conversion Wallet**: `0x18CE1930820d5e1B87F37a8a2F7Cf59E7BF6da4E`
- **Settlement Wallet**: `0xD91bFc93976054B9fF17672169F6AB558caBCf59`

## Live Trading Status (Updated March 9, 2026)
| Service | Status |
|---------|--------|
| DEX | ✅ ENABLED, READY |
| Exchange Trading | ✅ LIVE MODE (shadow_mode=false) |
| Kraken | ✅ Connected |
| Coinbase | ✅ Connected |
| Binance | ⚠️ Geo-blocked 451 |
| PostgreSQL | ✅ **PRIMARY (postgresql_only mode)** |
| MongoDB | ✅ Connected (legacy backup) |

## Key API Endpoints
- `/api/auth/*` - Authentication
- `/api/ramp/*` - On/off-ramp quotes
- `/api/por/*` - Provider-of-Record engine
- `/api/transak/*` - Transak widget integration
- `/api/exchanges/*` - Exchange connectors
- `/api/dex/*` - DEX operations
- `/api/audit/*` - Transaction audit log
- `/api/password/*` - Password reset
- `/api/migration/*` - Database migration status

## Environment Variables
See `/app/backend/.env` for configuration:
- `MONGO_URL`, `DB_NAME`
- `POSTGRES_*` - PostgreSQL connection
- `DATABASE_MODE=dual_write`
- `STRIPE_SECRET_KEY`
- `RESEND_API_KEY`
- `BINANCE_API_KEY`, `BINANCE_API_SECRET`
- `KRAKEN_API_KEY`, `KRAKEN_API_SECRET`
- `COINBASE_API_KEY`, `COINBASE_API_SECRET` (empty)
- `CONVERSION_WALLET_PRIVATE_KEY`
- `SETTLEMENT_WALLET_PRIVATE_KEY`

## Backlog

### P0 - Immediate
- [ ] Provide Coinbase API keys to enable third exchange

### P1 - Next
- [ ] Run migration validation once data accumulates
- [ ] Switch to `postgresql_only` mode after validation passes

### P2 - Future
- [ ] Repository pattern refactoring
- [ ] Add more exchange connectors
- [ ] Performance optimization
