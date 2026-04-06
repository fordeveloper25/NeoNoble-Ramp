# NeoNoble Ramp - Product Requirements Document

## Original Problem Statement
Enterprise-grade fintech platform (NeoNoble Ramp) with multi-chain crypto wallet, NENO token exchange, real Web3 integration (BSC Mainnet via Alchemy), MetaMask transaction signing, and complete banking/card infrastructure.

## 4-Phase Custom Token Roadmap (Completed Feb 2026)

### Phase 1 - Custom Token Creation ✅
- Form: Name, Symbol (max 8 chars), Initial Supply, Price USD (2 decimals)
- Saved to MongoDB `custom_tokens` collection
- "Crea Token Personalizzato" button in Dashboard
- "I Miei Token Personalizzati" list in Dashboard
- Endpoint: `POST /api/neno-exchange/create-token`
- Endpoint: `GET /api/neno-exchange/my-tokens`

### Phase 2 - Buy/Sell Custom Tokens ✅
- Buy custom tokens with any supported asset (EUR, USDT, BTC, ETH, BNB, NENO)
- Sell custom tokens for any supported asset
- Balance validation and 0.3% platform fee
- Endpoint: `POST /api/neno-exchange/buy-custom-token`
- Endpoint: `POST /api/neno-exchange/sell-custom-token`
- Dedicated /custom-tokens page with Buy/Sell tabs

### Phase 3 - Swap Logic Custom/Native ✅
- Swap any token pair (custom ↔ native) via NENO bridge
- Real-time swap quotes with fee calculation
- Slippage estimation
- Endpoint: `POST /api/neno-exchange/swap`
- Endpoint: `GET /api/neno-exchange/swap-quote`
- Swap tab in /custom-tokens page

### Phase 4 - Off-Ramp + Real-Time Balance Sync ✅
- Live balances endpoint with polling (5s interval)
- USD values and custom token flag for each balance
- Off-ramp to card/bank already implemented
- Dashboard shows real-time balances widget
- Endpoint: `GET /api/neno-exchange/live-balances`

## Backlog (Previously Completed)
- Dynamic NENO pricing based on order book pressure ✅
- Referral System with NENO bonuses ✅
- DCA Trading Bot ✅
- PDF Compliance Reports ✅
- SMS Notifications (Twilio-ready) ✅

## Architecture
- Backend: FastAPI + MongoDB (Motor) + Web3.py
- Frontend: React.js + Tailwind + Wagmi/WalletConnect
- API calls: XMLHttpRequest (not fetch) to bypass Emergent interceptor
- Background: Blockchain listener, DCA scheduler, price alerts

## Key Collections
- `custom_tokens`: {id, symbol, name, price_usd, price_eur, total_supply, creator_id, created_at}
- `wallets`: {user_id, asset, balance}
- `neno_transactions`: {id, user_id, type, ...}

## Key Routes
- `/tokens/create` - Token creation form
- `/custom-tokens` - Buy/Sell/Swap marketplace
- `/dashboard` - Main dashboard with all quick access
- `/neno-exchange` - NENO exchange
