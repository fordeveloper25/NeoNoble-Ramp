# NeoNoble Ramp — Changelog

## 2026-04-02 (Phase 6 — Current Session)

### Full Margin Trading (P0)
- Implemented professional `MarginTrading.js` page at `/margin`
- Professional candlestick charts with `lightweight-charts` v4.2.0
- 4 chart types: Candlestick, Line, Area, Bar
- 10 technical indicators: SMA 20/50/200, EMA 12/26/50, RSI 14, MACD, Bollinger Bands, Volume
- Indicator selector panel with search and toggle
- Oscillator panels (RSI, MACD) rendered as sub-charts
- Margin account management: deposit/withdraw, leverage 2-20x
- LONG/SHORT position opening with SL/TP
- Position table with real-time PnL tracking
- 8 trading pairs (BTC-EUR, ETH-EUR, BNB-EUR, NENO-EUR, SOL-EUR, XRP-EUR, ADA-EUR, DOGE-EUR)
- 6 intervals (1m, 5m, 15m, 1H, 4H, 1D)

### Unified Wallet (P0)
- Added "Unificato" tab to WalletPage showing internal + on-chain balances
- Displays internal_balance, external_balance, total_balance, eur_value per asset
- Source indicator (Piattaforma, On-Chain, Sync)
- Automatic refresh on tab switch

### Multi-chain Token Discovery (P0)
- "Scopri Token" button on On-Chain tab
- Chain selector for targeted discovery (Ethereum, BSC, Polygon)
- Displays discovered tokens with balances and custom token indicator

### KYC/AML Compliance Layer (P1)
- New KYC routes at `/api/kyc/*`
- 4-tier KYC system: Tier 0 (Non Verificato, no trading) → Tier 1 (Base, 1000 EUR/day) → Tier 2 (Verificato, 50k/day) → Tier 3 (Premium, unlimited)
- KYC form submission with personal info, address, document
- Admin review workflow (approve, reject, request_info)
- AML monitoring: large transaction alerts (>10k EUR), daily velocity alerts (>25k EUR), structuring detection (5+ tx/hour)
- AML dashboard with statistics
- KYC page at `/kyc` with status, submit, admin review, and AML tabs

### Dynamic NENO Pricing (P2)
- NENO price now adjusts based on 24h buy/sell volume pressure
- Base price: €10,000, max deviation: ±5%
- New endpoint `GET /api/neno-exchange/price` returns real-time price data
- Quote and buy/sell endpoints updated to use dynamic pricing
- NENO Exchange frontend updated to display price shift percentage

### Dashboard Updates
- Added "Margin Trading" link card (red gradient, "Leva fino a 20x, Grafici PRO")
- Added "KYC / AML" link card (teal gradient, "Verifica identita e compliance")

### Testing
- iteration_10.json: Margin Trading + Unified Wallet (19/19 backend, 100% frontend)
- iteration_11.json: KYC/AML + Dynamic Pricing (15/15 backend, 100% frontend)
