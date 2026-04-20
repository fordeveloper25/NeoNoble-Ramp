# NeoNoble Ramp — Product Requirements Document

## Problema Originale
Piattaforma fintech enterprise (IPO-Ready) per trading, exchange, wallet e banking con esecuzione reale su blockchain (BSC/PancakeSwap), Circle USDC, Stripe SEPA. Obiettivo: Full Money Loop + Real Cards + Profit Engine + Mass User Growth + Pipeline Finanziario Autonomo + Institutional Liquidity Routing + **Launchpad per token custom con bonding curve (zero capitale piattaforma)**.

## Utenti
- **Admin**: Treasury, revenue withdrawal, growth analytics, monetization, pipeline autonomo, liquidity routing
- **Trader**: Compra/vendi/swap NENO e altri asset, best execution multi-venue
- **Utente Banking**: IBAN virtuale, carte, bonifici SEPA
- **Referrer**: Guadagni passivi da network di invitati
- **Token Creator (nuovo, Feb 2026)**: Crea token ERC20 con bonding curve sulla piattaforma, paga solo ~0.05 BNB di deploy fee, riceve 1% su ogni trade del suo token automaticamente

## Architettura Core
- Backend: FastAPI + MongoDB (Motor async)
- Frontend: React + Tailwind + Shadcn + wagmi/viem
- Blockchain: Web3.py (BSC), PancakeSwap V2, 1inch Aggregator, **Launchpad factory custom**
- Swap Model: **USER-SIGNED DEX ONLY** (zero platform capital)
- Launchpad Model: **Virtual constant-product AMM bonding curve** stile Pump.fun
- Wallets: Circle USDC (Client/Treasury/Revenue segregation)
- Payments: Stripe SEPA (LIVE) + Autonomous Pipeline
- Card Issuing: Abstraction layer (Marqeta/NIUM/Adyen/Stripe/Internal)

## Swap Engine — USER-SIGNED DEX (Feb 2026)
Tutti gli swap (NENO, custom, BEP-20) vengono firmati dal wallet dell'utente via 1inch + PancakeSwap V2. Zero capitale piattaforma. Dettagli in iteration 46 (14/14 PASS).

## Launchpad — Bonding Curve Token Factory (Feb 2026)

### Architettura
Un utente crea un token ERC20 pagando **solo** una deploy fee (~0.05 BNB). Il token ha una curva di prezzo virtuale `x*y=k` bootstrap con reserve virtuali. I buyer mettono BNB nella curva e ricevono token mintati; i seller bruciano token e ricevono BNB dalla curva. A **85 BNB raccolti** la curva si chiude (graduation) e 200M token vengono riservati per migrare su PancakeSwap.

### Fee Economics
- Deploy fee: 0.05 BNB (modificabile owner-only)
- Platform fee: 1% su ogni buy/sell (va a `platformFeeRecipient`)
- Creator fee: 1% su ogni buy/sell (va al creator del token)
- Zero capitale richiesto alla piattaforma
- Zero collateral richiesto al creator (solo la deploy fee)

### Contracts
- `/app/contracts/Launchpad.sol` — factory, deploy dei token
- `/app/contracts/BondingCurveToken.sol` — ERC20 minimal + curve buy/sell/graduation
- `/app/contracts/DEPLOY.md` — guida deploy via Remix

### Endpoint API
| Endpoint | Uso |
|---|---|
| `GET /api/launchpad/health` | Stato factory + RPC |
| `GET /api/launchpad/config` | Fee, graduation threshold, token count |
| `GET /api/launchpad/tokens` | Lista token con paginazione |
| `GET /api/launchpad/tokens/{addr}` | Dettaglio + reserve + price live |
| `GET /api/launchpad/quote-buy` | Preventivo buy (BNB → token) |
| `GET /api/launchpad/quote-sell` | Preventivo sell (token → BNB) |
| `POST /api/launchpad/build-create` | Calldata deploy nuovo token |
| `POST /api/launchpad/build-buy` | Calldata buy (user-signed) |
| `POST /api/launchpad/build-sell` | Calldata sell (user-signed) |

### Config ENV
```
LAUNCHPAD_FACTORY_ADDRESS=0x...  # impostato dopo deploy del factory
```
Se assente, gli endpoint ritornano 503 con istruzioni di deploy.

### Frontend Pages
- `/launchpad` — lista token con progress bar graduation
- `/launchpad/create` — form creazione token (user-signed)
- `/launchpad/:address` — dettaglio + buy/sell UI (user-signed)

## Endpoint API Completi (Swap + NENO + Banking)
(invariati, vedi sezioni precedenti)

## Testing History
| Iteration | Scope | Result |
|-----------|-------|--------|
| 41 | Idempotency / UI | 100% PASS |
| 42 | Card / Growth Engine | 100% PASS |
| 43 | Autonomous Pipeline | 23/23 PASS |
| 44 | Liquidity Router / KYC | 21/22 PASS |
| 45 | FINAL Production Hardening | 30/30 PASS |
| 46 | User-Signed DEX Swap | 14/14 PASS |
| 47 | **Launchpad Bonding Curve (Feb 2026)** | **21/21 PASS** |

## Backlog
- [ ] **Deploy del Launchpad factory su BSC Mainnet** (responsabilità utente) + impostare `LAUNCHPAD_FACTORY_ADDRESS`
- [ ] Migrazione automatica post-graduation su PancakeSwap V3 (v2)
- [ ] Grafico prezzo live sulla pagina token (TradingView o recharts)
- [ ] Pagina FAQ dedicata al modello user-signed DEX + Launchpad
- [ ] Fix smart contract "ERC20: burn amount exceeds balance" su `redeemCustom` (bug legacy)
- [ ] Supporto Bitcoin nativo (oggi via BTCB)
- [ ] Sumsub API keys per KYC reale
- [ ] NIUM fiat rail (templateId)
- [ ] Rate limiting su endpoint build-* (da code review iter47)
- [ ] Endpoint admin per reload config senza restart (da code review iter47)
