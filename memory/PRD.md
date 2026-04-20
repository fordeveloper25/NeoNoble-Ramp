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
- Blockchain: Web3.py (BSC), PancakeSwap V2, 1inch Aggregator
- Swap Model: **USER-SIGNED DEX ONLY** (zero platform capital — vedi sezione Swap Engine)
- Wallets: Circle USDC (Client/Treasury/Revenue segregation)
- Payments: Stripe SEPA (LIVE) + Autonomous Pipeline
- Card Issuing: Abstraction layer (Marqeta/NIUM/Adyen/Stripe/Internal)
- KYC/AML: Sumsub (ready) + AI Document Verification (fallback)

## Swap Engine — USER-SIGNED DEX (Implementato: Feb 2026)

### Architettura
Tutti gli swap (NENO, custom tokens, BEP-20 standard) vengono eseguiti **dal wallet dell'utente** (MetaMask) con liquidità proveniente da pool DEX pubblici esistenti:

1. **1inch Aggregator (BSC)** — aggrega PancakeSwap V2/V3, Biswap, ApeSwap, MDEX, Uniswap V3 BSC, ecc.
2. **PancakeSwap V2** — fallback diretto per coppie semplici.

Il backend ritorna **solo calldata non firmata** (`execution_mode: "on-chain"`); la piattaforma **non deposita capitale**, **non esegue swap server-side**, **non detiene hot-wallet con riserve token**.

### Endpoint
| Endpoint | Uso |
|---|---|
| `GET /api/swap/health` | Stato RPC + 1inch |
| `GET /api/swap/tokens` | Lista 8 token BSC supportati |
| `POST /api/swap/quote` | Preventivo via 1inch→PancakeSwap |
| `POST /api/swap/build` | Calldata per MetaMask |
| `POST /api/swap/track` | Registra tx hash firmato |
| `GET /api/swap/history` | Storico user |
| `GET /api/swap/hybrid/health` | Stesso del v2 (alias) |
| `POST /api/swap/hybrid/quote` | Stesso del v2 (alias) |
| `POST /api/swap/hybrid/build` | Stesso del v2 (alias, con `execution_mode=on-chain`) |
| `POST /api/swap/hybrid/execute` | **410 Gone** — server-side execution disabilitata |

### Rationale
Il modello Market Maker + CEX withdrawal (via ccxt) è stato rimosso perché richiedeva capitale depositato dalla piattaforma. Le API CEX non creano liquidità dal nulla: richiedono saldo nell'exchange. Il modello user-signed DEX è l'unica soluzione economicamente valida a **zero-capitale**.

### Limite
Se una coppia non ha **alcun** pool DEX su BSC (né PancakeSwap né aggregati 1inch), lo swap è fisicamente impossibile: il backend ritorna `source: "estimate"` + nota, e `/build` ritorna HTTP 422.

## Production Hardening Status: COMPLETE

### safeFetch Migration, Idempotency, Stripe Webhook, Liquidity Router, KYC
(invariati rispetto a versioni precedenti)

## Endpoint API Completi (riepilogo)

### Auth
- `POST /api/auth/login` | `POST /api/auth/register` | `GET /api/auth/me`
- `POST /api/auth/2fa/setup` | `POST /api/auth/2fa/verify` | `POST /api/auth/2fa/disable`
- `POST /api/password/forgot` | `POST /api/password/reset` | `POST /api/password/verify-token`

### Wallet & Banking
- `GET /api/wallet/balances` | `POST /api/wallet/deposit` | `POST /api/wallet/withdraw`
- `GET /api/banking/accounts` | `POST /api/banking/transfer`

### NENO Exchange (Idempotent)
- `GET /api/neno/pricing` | `POST /api/neno/buy` | `POST /api/neno/sell`
- `POST /api/neno/swap` | `POST /api/neno/off-ramp` | `GET /api/neno/quote`

### Card Engine, Growth, KYC, Admin
(invariati)

## Testing History
| Iteration | Scope | Result |
|-----------|-------|--------|
| 41 | Idempotency / UI fixes | 100% PASS |
| 42 | Card / Growth Engine | 100% PASS |
| 43 | Autonomous Pipeline | 23/23 PASS |
| 44 | Liquidity Router / KYC | 21/22 PASS |
| 45 | FINAL Production Hardening | 30/30 PASS |
| 46 | **User-Signed DEX Swap** (Feb 2026) | **14/14 PASS** |

## Backlog
- [ ] Supporto Bitcoin nativo (attualmente via BTCB su BSC)
- [ ] Banner "Low BNB Gas" più prominente con link a bridge/ramp
- [ ] Pagina FAQ dedicata al modello user-signed
- [ ] Fix smart contract "ERC20: burn amount exceeds balance" su `redeemCustom`
- [ ] Sumsub API keys per KYC reale
- [ ] NIUM fiat rail (templateId)
- [ ] Dynamic NENO pricing
