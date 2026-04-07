# NeoNoble Ramp — PRD

## Problema originale
Piattaforma fintech enterprise per acquisto/vendita/swap di criptovalute con bridge token interno $NENO (EUR 10.000 fisso). Include wallet multichain, Market Maker interno, integrazione NIUM banking, esecuzione reale on-chain, e compliance.

## Utente principale
- Massimo Fornara (massimo.fornara.2212@gmail.com) — owner Treasury/Admin

## Requisiti Core
1. Exchange $NENO (buy/sell/swap/offramp) con Market Maker dinamico Bid/Ask/Spread
2. Treasury = Account Massimo (NENO, BNB on-chain + EUR, ETH, BTC interni)
3. Esecuzione reale on-chain per SWAP/SELL/Withdraw (NENO, BNB, ETH/WETH, BTC/BTCB su BSC)
4. Payout fiat reale via Stripe SEPA per SELL/OFF-RAMP EUR→bank
5. Security Hardening: caps (€50k/tx, €200k/day, 50 NENO/tx), rate limit (10 ops/min), reentrancy lock, private key masking
6. Status enforcement: solo "completed" con proof (tx_hash/payout_id), altrimenti "pending_execution"/"pending_settlement"/"failed"
7. WebSocket balance sync + polling fallback
8. Audit logging aggressivo PRE/POST su ogni operazione
9. DCA Trading Bot, PDF Compliance, SMS Notifications (Twilio-ready)

## Architettura
- Backend: FastAPI + MongoDB (Motor) + Web3.py
- Frontend: React + Tailwind + Shadcn/UI
- BSC Mainnet: NENO (0xeF3F...974), WETH (0x2170...F8), BTCB (0x7130...9c)

## Stato implementazione — Fase attuale COMPLETATA
- [x] Exchange completo con Market Maker
- [x] Treasury unificata (on-chain + interna)
- [x] Security Hardening (caps, rate limit, reentrancy, key masking)
- [x] WebSocket balance sync
- [x] Esecuzione reale on-chain (NENO, BNB, ETH, BTC via BEP-20)
- [x] Stripe SEPA payout reale
- [x] Status enforcement con proof
- [x] Endpoint withdraw-real per ETH/BTC interni→reali
- [x] Frontend aggiornato con proof display, delivery info, status badges

## P0 completati
- Security Guard: /app/backend/services/security_guard.py
- Enhanced Execution Engine: send_bep20, send_asset_real
- Exchange routes: sell, swap, offramp con real delivery
- withdraw-real endpoint per ETH/BTC→on-chain
- WebSocket + polling fallback nel frontend

## Backlog
- P1: Microservices split
- P1: Admin Treasury Dashboard con grafici PnL
- P2: Dynamic NENO pricing da order book reale
- P2: Referral System con NENO bonuses
- P2: NIUM onboarding (bloccato su templateId utente)
