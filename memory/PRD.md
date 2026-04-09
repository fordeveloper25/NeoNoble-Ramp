# NeoNoble Ramp — Product Requirements Document

## Problema Originale
Piattaforma fintech enterprise (IPO-Ready) per trading, exchange, wallet e banking con esecuzione reale su blockchain (BSC/PancakeSwap), Circle USDC, Stripe SEPA. Obiettivo: Full Money Loop + Real Cards + Profit Engine + Mass User Growth + Pipeline Finanziario Autonomo + Institutional Liquidity Routing.

## Utenti
- **Admin**: Gestione treasury, revenue withdrawal, growth analytics, monetization monitoring, pipeline autonomo, liquidity routing
- **Trader**: Compra/vendi/swap NENO e altri asset con cashback dinamico, best execution multi-venue
- **Utente Banking**: IBAN virtuale, carte (issue/reveal/spend), bonifici SEPA
- **Referrer**: Guadagni passivi da network di invitati

## Architettura Core
- Backend: FastAPI + MongoDB (Motor async)
- Frontend: React + Tailwind + Shadcn
- Blockchain: Web3.py (BSC), PancakeSwap V2
- Wallets: Circle USDC (Client/Treasury/Revenue segregation)
- Payments: Stripe SEPA (LIVE) + Autonomous Pipeline
- Card Issuing: Abstraction layer (Marqeta/NIUM/Adyen/Stripe/Internal)
- Liquidity: Institutional Router (Binance/Kraken/MEXC/DEX/Internal)
- KYC/AML: Sumsub (ready) + AI Document Verification (fallback)

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
- Card Reveal UI (PCI-compliant 2FA con OTP)

### Phase 8: Autonomous Financial Pipeline (2026-04-09)
- Stripe Live PaymentIntents per user EUR deposits
- Fee extraction automatica (2% platform fee)
- Auto-payout SEPA quando balance >= threshold (10 EUR)
- Stripe Webhooks con signature enforcement
- Background loop autonomo (120s check interval)
- 23/23 test passati (iteration_43)

### Phase 9: Institutional Liquidity + KYC/AML (2026-04-09)
- **Stripe Webhook URL** registrato su Stripe portal (endpoint live)
- **Institutional Liquidity Router** — Multi-venue aggregation engine:
  - Quote parallele da 5 venue (Internal, PancakeSwap, Binance, Kraken, MEXC)
  - Best execution scoring (prezzo netto, fee, slippage, latenza, profondità)
  - Order splitting automatico per ordini > €5,000
  - Slippage guard 2%
  - Audit trail completo su ogni routing decision
- **MEXC Connector** — Nuovo adapter CEX (API key configurata, connesso)
- **Custom Token Fallback Matrix** — 4 strategie:
  1. Direct CEX listing (MEXC lista molti micro-cap)
  2. DEX direct swap (PancakeSwap V2)
  3. Intermediate pair routing (TOKEN→WBNB→USDT)
  4. Internal RFQ / market maker inventory
- **KYC/AML Provider** — Sumsub integration ready:
  - Creazione applicant, verification URL, status check
  - Webhook receiver per aggiornamenti stato
  - AI document verification come fallback
- **Risk Controls** — Pre-check fondi, venue availability, slippage guard, retry/failover
- 21/22 test passati (iteration_44, 1 skippato per fixture scope)

## Endpoint API Chiave

### Institutional Liquidity Router
- `GET /api/router/status` — Stato venue, routing decisions, split threshold
- `POST /api/router/quote` — Best execution quote multi-venue
- `POST /api/router/execute` — Esecuzione ordine instradato
- `GET /api/router/venues` — Connettività venue real-time
- `GET /api/router/fallback-matrix` — Standard pairs + custom token strategies

### KYC/AML Provider
- `POST /api/kyc-provider/applicant` — Crea applicant KYC
- `GET /api/kyc-provider/status` — Stato verifica utente
- `GET /api/kyc-provider/verification-url` — URL SDK Sumsub / istruzioni AI
- `GET /api/kyc-provider/provider-status` — Configurazione provider (admin)
- `POST /api/kyc-provider/webhook` — Webhook Sumsub

### Autonomous Pipeline
- `GET /api/pipeline/status` — Stato pipeline
- `POST /api/pipeline/deposit` — Deposit Stripe PaymentIntent
- `POST /api/stripe/webhook` — Webhook Stripe (signature enforced)

### Card Engine
- `POST /api/card-engine/issue` — Emissione carta
- `POST /api/card-engine/reveal` — Reveal PCI (2FA)

### Growth Engine
- `GET /api/growth/dashboard` — Dashboard completo (admin)

## Venue Connectivity (Production)
| Venue | Status | Note |
|-------|--------|------|
| NeoNoble Internal | ONLINE | Market maker, treasury liquidity |
| Kraken | ONLINE | BTC/ETH/SOL/XRP trading |
| MEXC | ONLINE | Micro-cap friendly, BTC/ETH + many altcoins |
| Coinbase | ONLINE | Limited trading pairs |
| Binance | OFFLINE | HTTP 451 geo-blocked (infrastruttura) |
| PancakeSwap V2 | AVAILABLE | DEX on-chain per token custom |

## Backlog
- [ ] Sumsub API keys (SUMSUB_APP_TOKEN, SUMSUB_SECRET_KEY) per KYC reale
- [ ] NIUM fiat rail activation (blocked on templateId)
- [ ] Microservices Architecture (splitting monolite)
- [ ] Dynamic NENO pricing (order book reale)
- [ ] Visa/Mastercard BIN sponsor integration
- [ ] Multi-country/multi-currency scaling
- [ ] Marqeta API keys per card issuing reale
