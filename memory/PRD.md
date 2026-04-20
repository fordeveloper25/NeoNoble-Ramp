# NeoNoble Ramp — Product Requirements Document

## Problema Originale
Piattaforma fintech enterprise per trading, exchange, wallet e banking con esecuzione reale su blockchain (BSC/PancakeSwap), Circle USDC, Stripe SEPA. Obiettivo: Full Money Loop + Real Cards + Launchpad token custom + STO security token offering regolamentato.

## Utenti
- **Admin**: Treasury, revenue withdrawal, growth analytics, monetization, pipeline autonomo
- **Trader**: Compra/vendi/swap NENO e altri asset
- **Banking**: IBAN virtuale, carte, bonifici SEPA
- **Token Creator (Launchpad, Feb 2026)**: Crea token bonding-curve su BSC, zero collateral
- **Investitore STO (Feb 2026)**: Sottoscrive security token revenue-share, KYC-gated, redeem a NAV

## Architettura Core
- Backend: FastAPI + MongoDB (Motor async)
- Frontend: React + Tailwind + Shadcn + wagmi/viem
- Blockchain: Web3.py (BSC), PancakeSwap V2, 1inch, Launchpad factory custom (BSC), **STO contracts (Polygon)**
- Swap Model: **USER-SIGNED DEX ONLY** (zero platform capital)
- Launchpad: **Virtual constant-product AMM bonding curve** stile Pump.fun (BSC)
- STO: **ERC-3643-inspired** security token + NAV oracle + Redemption Vault + Revenue Share (Polygon)

## Swap Engine — USER-SIGNED DEX (Feb 2026)
Iteration 46: 14/14 PASS. User-signed via 1inch + PancakeSwap V2.

## Launchpad — Bonding Curve (Feb 2026)
Iteration 47: 21/21 PASS.
- Contracts: `/app/contracts/{Launchpad,BondingCurveToken}.sol`
- Backend: `/api/launchpad/*` (9 endpoint)
- Frontend: `/launchpad`, `/launchpad/create`, `/launchpad/:address`
- Deploy pending user action (factory non ancora in mainnet BSC)
- Fee: 0.05 BNB deploy, 1% platform + 1% creator per trade, graduation @ 85 BNB

## STO — Security Token Offering (Feb 2026, NEW)

### Architettura Contratti (Solidity, Polygon PoS target)
```
/app/contracts/sto/
├── contracts/
│   ├── interfaces/ (IIdentityRegistry, ICompliance, INAVOracle, IRedemptionVault)
│   ├── registry/IdentityRegistry.sol          — whitelist KYC on-chain
│   ├── compliance/DefaultCompliance.sol       — regole transfer (KYC, lockup, max holders, country, exempt vaults)
│   ├── token/NenoSecurityToken.sol            — ERC-20 + transfer restrictions + forced transfer + pause
│   ├── oracle/NAVOracle.sol                   — NAV trimestrale + reportHash auditabile
│   └── vault/
│       ├── RedemptionVault.sol                — redemption a NAV con riserva dedicata
│       └── RevenueShareVault.sol              — distribuzione pro-rata ricavi agli holder
├── scripts/ (deploy, verify, whitelist-add, nav-update)
├── test/NenoSecurityToken.test.js             — 9/9 PASS
├── hardhat.config.js                          — Polygon mainnet + Amoy testnet
├── .env.example
└── STO_DEPLOY.md                              — guida completa (architettura, deploy, operations)
```

### Modello economico
- **Tipo token**: Utility + revenue share (1d)
- **Emissione target**: €1M–€8M (esenzione art. 100-bis TUF)
- **Chain**: Polygon PoS (mainnet 137 / Amoy testnet 80002)
- **Redemption**: a NAV con riserva dedicata in USDC (4b)
- **Timeline**: 6 mesi (5b) — audit obbligatorio + prospetto

### Test Solidity (9/9 PASS)
1. Mint solo verso address whitelisted
2. Transfer blocca destinatari non KYC
3. Max holders enforced (per esenzione prospetto)
4. Redemption a NAV con riserva sufficiente
5. Redemption rifiutata se riserva insufficiente
6. Revenue share pro-rata
7. Forced transfer loggato con compliance sul destinatario
8. Pause blocca transfer secondari ma non mint/burn agent
9. Lockup blocca transfer ma non mint

### Comandi chiave
```bash
cd /app/contracts/sto
yarn install
yarn compile      # compila 11 contratti in Solidity 0.8.20
yarn test         # 9/9 PASS
yarn deploy:amoy  # testnet
yarn deploy:polygon # mainnet (DOPO audit)
```

## Testing History
| Iteration | Scope | Result |
|-----------|-------|--------|
| 41 | Idempotency / UI | 100% PASS |
| 42 | Card / Growth Engine | 100% PASS |
| 43 | Autonomous Pipeline | 23/23 PASS |
| 44 | Liquidity Router / KYC | 21/22 PASS |
| 45 | FINAL Production Hardening | 30/30 PASS |
| 46 | User-Signed DEX Swap | 14/14 PASS |
| 47 | Launchpad Bonding Curve | 21/21 PASS |
| 48 | STO Contracts (Solidity Hardhat) | 9/9 PASS |
| 49 | STO Backend + Frontend Landing | 23/23 PASS |
| 50 | **STO Hardening (role auth + rate limit + broadcast)** | **18/18 PASS** |

## Backlog
- [ ] **Avvocato fintech** nominato + prospetto/esenzione CONSOB
- [ ] **Audit smart contract STO** (OpenZeppelin/Certik/Quantstamp) — €15–30k
- [ ] Deploy STO su Amoy testnet → end-to-end test con 3 wallet
- [ ] Deploy STO su Polygon mainnet (dopo audit)
- [ ] Backend endpoint `/api/sto/*` (KYC submit, whitelist, subscribe, redeem, reports)
- [ ] Frontend pagine `/sto/invest`, `/sto/portfolio`, `/admin/sto`
- [ ] Deploy Launchpad factory su BSC Mainnet (user action, guida in `/app/contracts/DEPLOY.md`)
- [ ] Migrazione automatica post-graduation su PancakeSwap V3
- [ ] Fix smart contract legacy "ERC20: burn amount exceeds balance" (necessario sorgente dall'utente)
- [ ] Supporto Bitcoin nativo
- [ ] Grafico prezzo live (Trading View / recharts) nel detail Launchpad
- [ ] Sumsub API keys per KYC reale + integrazione con IdentityRegistry
- [ ] Rate limiting su endpoint build-*

## Checklist STO pre-emissione (vedi `/app/contracts/sto/STO_DEPLOY.md` per dettaglio)
- [ ] Audit contratti
- [ ] Prospetto / esenzione approvata dall'avvocato
- [ ] Sumsub integration + KYC flow backend
- [ ] Treasury bancario segregato per riserva redemption
- [ ] Procedura revisione NAV trimestrale firmata con revisore
- [ ] Registro OAM (se VASP)
- [ ] Dry-run con investitore pilota
