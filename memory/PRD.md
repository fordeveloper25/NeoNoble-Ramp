# NeoNoble Ramp — Product Requirements Document

## Problema Originale
Piattaforma fintech enterprise (IPO-Ready) per trading, exchange, wallet e banking con esecuzione reale su blockchain (BSC/PancakeSwap), Circle USDC, Stripe SEPA. Obiettivo: Full Money Loop + Real Cards + Profit Engine + Mass User Growth + Pipeline Finanziario Autonomo.

## Utenti
- **Admin**: Gestione treasury, revenue withdrawal, growth analytics, monetization monitoring, pipeline autonomo
- **Trader**: Compra/vendi/swap NENO e altri asset con cashback dinamico
- **Utente Banking**: IBAN virtuale, carte (issue/reveal/spend), bonifici SEPA
- **Referrer**: Guadagni passivi da network di invitati

## Architettura Core
- Backend: FastAPI + MongoDB (Motor async)
- Frontend: React + Tailwind + Shadcn
- Blockchain: Web3.py (BSC), PancakeSwap V2
- Wallets: Circle USDC (Client/Treasury/Revenue segregation)
- Payments: Stripe SEPA (LIVE)
- Card Issuing: Abstraction layer (Marqeta/NIUM/Adyen/Stripe/Internal)
- Pipeline: Autonomous Financial Pipeline (zero-click money loop)

## Fasi Completate

### Phase 1-4: Foundation to Advanced Features
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
- Universal xhrFetch wrapper (safeFetch)
- Revenue Withdrawal endpoint + Admin Dashboard

### Phase 7: Card Issuing + Growth Domination (2026-04-09)
- Card Issuing Engine (multi-provider abstraction)
- Monetization Engine (interchange, FX, trading spread, card fees)
- Incentive Engine (cashback 5 tier, bonus primo top-up)
- Referral Viral Loop (network volume, viral multiplier)
- Growth Analytics Engine (funnel 8 step, retention, ARPU)
- Admin Dashboard (Growth/Monetization/Revenue/Pipeline tabs)
- Card Reveal UI (PCI-compliant 2FA con OTP)

### Phase 8: Autonomous Financial Pipeline (2026-04-09)
- Stripe Live PaymentIntents per user EUR deposits
- Fee extraction automatica (2% platform fee)
- Auto-payout SEPA quando balance >= threshold (10 EUR)
- Stripe Webhooks (payment_intent.succeeded, payout.paid, balance.available, payout.failed, charge.succeeded)
- Background loop autonomo (check ogni 120s)
- Auto-fund da revenue ledger a Stripe
- Pipeline status in Admin Dashboard (ATTIVO, Stripe balance, cicli, depositi, payouts)
- E2E Testing: 23/23 backend tests passati (iteration_43)

## Endpoint API Chiave

### Autonomous Pipeline
- `GET /api/pipeline/status` — Stato pipeline (running, cycle_count, deposits, payouts, stripe_balance)
- `POST /api/pipeline/deposit` — Crea deposit Stripe PaymentIntent (auth required)
- `GET /api/pipeline/deposits` — Storico depositi utente
- `GET /api/pipeline/payouts` — Storico payouts auto (admin only)
- `POST /api/pipeline/auto-payout-check` — Trigger manuale auto-payout (admin)
- `POST /api/pipeline/auto-fund` — Trigger auto-fund da revenue (admin)
- `POST /api/stripe/webhook` — Webhook Stripe (tutti gli eventi)

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

## Backlog (P1/P2)
- [ ] NIUM fiat rail activation (blocked on templateId)
- [ ] Microservices Architecture (splitting monolite)
- [ ] KYC/AML provider reale (Sumsub/Onfido)
- [ ] Dynamic NENO pricing (order book reale)
- [ ] Visa/Mastercard BIN sponsor integration
- [ ] Multi-country/multi-currency scaling
- [ ] SWIFT gpi real integration
- [ ] External auditor integration (Big 4)
- [ ] Marqeta API keys per card issuing reale
- [ ] TOTP vero per card reveal (produzione)
