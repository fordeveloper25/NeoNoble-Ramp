# Changelog

## 2026-04-06 - Phase 1-4 Custom Token System (Complete)

### Phase 1: Custom Token Creation
- Updated `POST /api/neno-exchange/create-token`: Symbol max 8 chars, price_usd with 2 decimals
- Added `GET /api/neno-exchange/my-tokens`: User's tokens with balances
- Rewrote `TokenCreation.js` with simplified form (Name, Symbol, Supply, Price USD) using XHR
- Added "Crea Token Personalizzato" button and "I Miei Token Personalizzati" section to Dashboard

### Phase 2: Buy/Sell Custom Tokens
- Added `POST /api/neno-exchange/buy-custom-token`: Buy any custom token with EUR/USDT/BTC/ETH/BNB/NENO
- Added `POST /api/neno-exchange/sell-custom-token`: Sell custom tokens for any asset
- Created `CustomTokenTrade.js` page with Buy/Sell tabs

### Phase 3: Swap Logic
- Enhanced existing `POST /api/neno-exchange/swap` to handle custom tokens via NENO bridge
- Swap tab added to CustomTokenTrade page with real-time quotes
- Swap direction toggle for convenience

### Phase 4: Real-Time Balance Sync
- Added `GET /api/neno-exchange/live-balances`: Polling endpoint for real-time balance updates
- Dashboard shows live balances widget with auto-refresh (5s polling)
- CustomTokenTrade sidebar shows live balances with LIVE indicator

### Backend changes
- `neno_exchange_routes.py`: Added USD_EUR_RATE, BuyCustomTokenRequest, SellCustomTokenRequest models
- Updated CreateTokenRequest: symbol max 8 chars, price_usd field
- Backward compatible: old tokens without price_usd get it computed from price_eur

### Frontend changes
- `TokenCreation.js`: Complete rewrite with XHR, dark theme, simplified form
- `Dashboard.js`: Added xhrGet helper, myTokens/liveBalances state, token section + balances widget
- `CustomTokenTrade.js`: New page with Buy/Sell/Swap tabs, live balances sidebar
- `App.js`: Added /custom-tokens route

### Test Results
- Iteration 27: 18/18 backend tests passed, all frontend UI elements verified
