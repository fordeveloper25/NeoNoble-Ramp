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

### Phase 3: C-SAFE DEX Off-Ramp (SCAFFOLDED)
- DEX aggregation (1inch, PancakeSwap)
- Batch execution (TWAP-style)
- On-chain settlement
- **BLOCKED**: Requires private key for conversion wallet

### Phase 4: Transak Integration (COMPLETED)
- Transak widget embedded in dashboard
- Buy/Sell crypto modes
- Order tracking

### Phase 5: Exchange Connectors (COMPLETED)
- Binance connector (mainnet - currently geo-blocked 451)
- Kraken connector (working)
- Market data and trading API integration

### Phase 6: Password Reset via Email (COMPLETED)
- Resend integration for transactional emails
- Forgot password flow
- Reset password with token

### Phase 7: Transak Audit Log (COMPLETED - March 9, 2026)
- Session-based audit tracking
- Event logging (mode selection, amount, currency, wallet, orders)
- Visual timeline component with phases (setup, kyc, payment, transfer, completion)
- Export compliance reports

## Technical Stack
- **Backend**: FastAPI, Python 3.11
- **Frontend**: React 18, Tailwind CSS, Shadcn/UI
- **Database**: MongoDB (primary), PostgreSQL (migration in progress)
- **Blockchain**: BSC via web3.py
- **Payments**: Stripe
- **Email**: Resend
- **Exchanges**: Binance, Kraken

## Key API Endpoints
- `/api/auth/*` - Authentication
- `/api/ramp/*` - On/off-ramp quotes
- `/api/por/*` - Provider-of-Record engine
- `/api/transak/*` - Transak widget integration
- `/api/exchanges/*` - Exchange connectors status
- `/api/audit/*` - Transaction audit log
- `/api/password/*` - Password reset

## Environment Variables
See `/app/backend/.env` for configuration. Critical variables:
- `MONGO_URL`, `DB_NAME`
- `STRIPE_SECRET_KEY`
- `RESEND_API_KEY`
- `BINANCE_API_KEY`, `BINANCE_API_SECRET`
- `KRAKEN_API_KEY`, `KRAKEN_API_SECRET`
- `CONVERSION_WALLET_PRIVATE_KEY` (required for C-SAFE)

## Known Issues
1. Binance API returns 451 (geo-blocked) - expected from certain regions
2. C-SAFE DEX Off-Ramp requires valid 32-byte private key
3. PostgreSQL migration incomplete (using MongoDB only mode)

## Backlog

### P0 - Blocked
- [ ] Configure C-SAFE wallet with valid private key

### P1 - Next
- [ ] Enable live trading on exchanges (verify Binance access or use Kraken only)
- [ ] PostgreSQL migration completion

### P2 - Future
- [ ] Repository pattern refactoring
- [ ] Fix concurrent_load_test.py script
- [ ] Add more exchange connectors (Coinbase, etc.)
