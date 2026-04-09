# NeoNoble Ramp — Product Requirements Document

## Problema Originale
Piattaforma fintech enterprise (IPO-Ready) per trading, exchange, wallet e banking con esecuzione reale su blockchain (BSC/PancakeSwap), Circle USDC, Stripe SEPA. Obiettivo: Full Money Loop + Real Cards + Profit Engine + Mass User Growth.

## Utenti
- **Admin**: Gestione treasury, revenue withdrawal, growth analytics, monetization monitoring
- **Trader**: Compra/vendi/swap NENO e altri asset con cashback dinamico
- **Utente Banking**: IBAN virtuale, carte (issue/reveal/spend), bonifici SEPA
- **Referrer**: Guadagni passivi da network di invitati

## Architettura Core
- Backend: FastAPI + MongoDB (Motor async)
- Frontend: React + Tailwind + Shadcn
- Blockchain: Web3.py (BSC), PancakeSwap V2
- Wallets: Circle USDC (Client/Treasury/Revenue segregation)
- Payments: Stripe SEPA
- Card Issuing: Abstraction layer (Marqeta/NIUM/Adyen/Stripe/Internal)

## Fasi Completate

### Phase 1-4: Foundation → Advanced Features
- Auth JWT + Ruoli (USER/DEVELOPER/ADMIN)
- NENO Exchange (buy/sell/swap/offramp)
- Multichain Wallet + Banking
- Card Management + KYC/AML
- Margin Trading + Order Book
- DCA Trading Bot + PDF Compliance + SMS/Push Notifications

### Phase 5: Real Money Activation
- Circle USDC Programmable Wallets
- Wallet Segregation (Client/Treasury/Revenue)
- Autonomous Profit Extraction Engine
- PancakeSwap V2 DEX (real swaps)
- Real-time Sync + EventBus

### Phase 6: Production Hardening (2026-04-08)
- Idempotency keys su tutte le operazioni finanziarie
- Safe transaction logging (upsert)
- Universal xhrFetch wrapper
- Revenue Withdrawal endpoint + Admin Dashboard

### Phase 7: Card Issuing + Growth Domination (2026-04-09)
- **Card Issuing Engine** — Abstraction layer multi-provider (Marqeta/NIUM/Adyen/Stripe)
  - `/api/card-engine/issue` — Emissione carte virtuali/fisiche
  - `/api/card-engine/reveal` — PCI-compliant con 2FA (OTP 6 cifre, sessione 60s)
  - `/api/card-engine/authorize` — Check balance + limiti + interchange fees
  - `/api/card-engine/settlement` — Settlement transazioni
  - `/api/card-engine/monetization` — Statistiche revenue carte (admin)
- **Monetization Engine** — Tracking revenue: interchange (1.5%), FX spread (0.5%), trading spread, card fees
- **Incentive Engine** — Cashback dinamico a 5 tier (Base 1% → Diamond 5%), bonus primo top-up 5 EUR
- **Referral Viral Loop** — Network volume tracking, viral multiplier, cashback 0.5% su spesa referred users
- **Growth Analytics Engine** — Funnel (8 step), retention (DAU/MAU), ARPU, revenue breakdown
- **Admin Dashboard** — Nuovi tab: Growth (funnel + retention + revenue), Monetization (card stats + ARPU)
- **Card Reveal UI** — Modal con input OTP, PAN/CVV/scadenza con countdown 60s

## Endpoint API Chiave
### Card Engine
- `POST /api/card-engine/issue` — Emissione carta
- `POST /api/card-engine/reveal` — Reveal PCI (2FA)
- `POST /api/card-engine/authorize` — Autorizzazione transazione
- `POST /api/card-engine/settlement` — Settlement
- `GET /api/card-engine/monetization` — Stats revenue (admin)

### Growth Engine
- `GET /api/growth/dashboard` — Dashboard completo (admin)
- `GET /api/growth/revenue` — Breakdown revenue per fonte
- `GET /api/growth/revenue/daily` — Grafico revenue giornaliero
- `GET /api/growth/my-tier` — Tier cashback utente
- `GET /api/growth/my-rewards` — Sommario premi utente
- `POST /api/growth/claim-topup-bonus` — Reclama bonus primo top-up

### Referral
- `GET /api/referral/viral-stats` — Network volume, viral multiplier

### Cashout
- `POST /api/cashout/revenue-withdraw` — Prelievo revenue (admin SEPA/SWIFT/Crypto)
- `GET /api/cashout/revenue-history` — Storico prelievi

## Backlog (P2+)
- [ ] Microservices Architecture (splitting monolite)
- [ ] KYC/AML provider reale (Sumsub/Onfido)
- [ ] Visa/Mastercard BIN sponsor attivazione
- [ ] Multi-country/multi-currency scaling
- [ ] Pricing NENO dinamico (order book reale)
- [ ] GA4 + Meta Pixel integration (chiavi necessarie)
- [ ] Marqeta API keys per card issuing reale
- [ ] TOTP vero per card reveal (produzione)
