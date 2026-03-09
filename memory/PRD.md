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
1. Binance API returns 451 (geo-blocked) - expected from certain regions, Kraken works as fallback
2. DEX service disabled by default (enable via API when ready for live trading)

## Configured Wallets (March 9, 2026)
- **Conversion Wallet**: `0x18CE1930820d5e1B87F37a8a2F7Cf59E7BF6da4E`
- **Settlement Wallet**: `0xD91bFc93976054B9fF17672169F6AB558caBCf59`

## Backlog

### P0 - Ready to Enable
- [ ] Enable DEX service for live swaps (currently disabled for safety)
- [ ] Enable Exchange trading (shadow mode active)

### P1 - Next
- [ ] PostgreSQL migration completion
- [ ] Test live trading with small amounts

### P2 - Future
- [ ] Repository pattern refactoring
- [ ] Fix concurrent_load_test.py script
- [ ] Add more exchange connectors (Coinbase, etc.)
