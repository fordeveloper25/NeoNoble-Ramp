# NeoNoble Ramp - Product Requirements Document

## Vision
NeoNoble Ramp is a global, enterprise-grade fintech infrastructure platform - a token-native financial platform comparable to Stripe, Coinbase, or MoonPay.

## Core Architecture
- **Backend:** FastAPI + MongoDB (Motor async client)
- **Frontend:** React + Craco + Tailwind CSS
- **Auth:** JWT-based with roles: USER, DEVELOPER, ADMIN
- **Web3:** Web3Modal + Wagmi + viem for wallet connectivity

## Implemented Features

### Phase 0 - Foundation (Complete)
- [x] User authentication (register, login, JWT)
- [x] Role-based access control (USER, DEVELOPER, ADMIN)
- [x] Password reset via email (Resend integration)
- [x] Dashboard with live crypto prices
- [x] Transak On/Off-Ramp integration
- [x] Multi-wallet connectivity (Web3Modal)
- [x] Candlestick charts (lightweight-charts v4)
- [x] Transaction timeline and audit service

### Phase 1 - Core Economic Engine (Complete - March 2026)
- [x] **Token Creation Infrastructure** - Full form with name, symbol, supply, price, chain selection, validation. POST /api/tokens/create
- [x] **Token Listing Marketplace** - Users can request Standard (€500), Premium (€2,000), Featured (€5,000) listings. Admin approval workflow (pending → approved → live)
- [x] **Subscription System** - 6 tiered plans (Free, Pro Trader, Premium, Developer Basic, Developer Pro, Enterprise). Monthly/yearly billing with 17% annual discount. Subscribe/cancel functionality
- [x] **Admin Dashboard** - Real-time overview with stats (users, tokens, listings, subscriptions, MRR). Token management (approve/reject/go_live/pause). Listing approval workflow. User management. Subscription monitoring
- [x] **Deployment Fix** - Resolved build blocker from Web3Modal peer deps via webpack fallbacks

### Phase 1 Key APIs
- POST /api/tokens/create - Create token (€100 fee)
- GET /api/tokens/list - List tokens with filters
- POST /api/tokens/{id}/admin-action - Admin token management
- GET /api/tokens/stats/overview - Token statistics
- POST /api/tokens/listings/create - Request listing
- GET /api/subscriptions/plans/list - 6 subscription plans
- POST /api/subscriptions/subscribe - Subscribe to plan
- POST /api/subscriptions/cancel - Cancel subscription
- GET /api/subscriptions/admin/stats - Subscription analytics
- GET /api/auth/admin/users - Admin user list

## Roadmap

### P1 - Crypto Market Data Integration
- Integrate CoinGecko API for 30+ cryptocurrencies
- Display price, market cap, volume, % change
- Real-time price updates on dashboard

### P2 - Full Exchange Engine & Order Book
- Matching engine for buy/sell orders
- Order book with bid/ask levels
- Trade execution and settlement

### P3 - TradingView Integration
- Professional charting interface
- Multiple timeframes and indicators
- Integration with platform trading pairs

### P4 - Developer API Ecosystem
- Public REST APIs for third-party developers
- API key management
- Rate limiting and usage tracking

### P5 - Microservices Architecture
- Decompose monolith into services
- Authentication, Wallet, Trading, Market Data, Token, Subscription services

## Test Credentials
- Admin: admin@neonobleramp.com / Admin1234!
- User: testchart@example.com / Test1234!

## Fee Structure
- Token Creation: €100
- Standard Listing: €500
- Premium Listing: €2,000
- Featured Listing: €5,000
- Trading Pair: €50
