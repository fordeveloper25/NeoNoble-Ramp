# Changelog

## 2026-04-05 — verify-deposit Fix + Hot Wallet Monitor (100% Operativa)
- **Fixed**: verify-deposit ora esegue il flusso completo:
  - (a) Accredita NENO al wallet interno dell'utente
  - (b) Crea record transazione in `neno_transactions` (tipo `onchain_deposit`)
  - (c) Registra deposito in `onchain_deposits` con `credited: true`
  - (d) Invia notifica all'utente
- **Added**: Hot wallet monitor nel blockchain listener
  - Scansiona ogni 120s TUTTI i trasferimenti NENO in arrivo al hot wallet
  - Auto-match utente tramite indirizzo wallet connesso
  - Auto-credit NENO + auto-registra transazione
  - Gestisce anche depositi da utenti non ancora associati (status: pending_user_match)
- **Verified**: Test end-to-end su BSC Mainnet COMPLETATO
  - TX: `0x4aba1b5b9abba545583e42330babeee89bf8201d5432fd796bae833cb127ceb7`
  - 5.0 NENO depositati e accreditati correttamente
- **Testing**: iteration_26.json — 100% pass (15 backend + full frontend + MongoDB + listener)

## 2026-04-03 — RPC Cleanup + Pre-Deploy Optimizations
- blockchain_listener.py: POA middleware, clean RPC calls, no log spam
- Alchemy BSC RPC configurato e stabile

## 2026-04-03 — Alchemy RPC + Deposit NENO Widget
- Tab "Deposita" con QR code, indirizzo copiabile, istruzioni, warning
- iteration_25.json — 100% pass

## 2026-04-03 — CORS Fix + Real Web3 Integration
- "Errore di rete" risolto (XHR bypass Emergent fetch interception)
- On-chain NENO balance, MetaMask signing, platform-wallet, verify-deposit
- iteration_24.json — 100% pass
