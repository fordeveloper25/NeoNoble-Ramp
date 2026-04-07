# NeoNoble Ramp — CHANGELOG

## 2026-04-07 — Security Hardening + Real Execution + WebSocket
- Security Guard service (treasury caps €50k/tx, €200k/day, 50 NENO/tx)
- Execution rate limiting (10 ops/min per utente)
- Reentrancy locks per utente su tutte le operazioni
- Private key masking nei log
- Status enforcement: solo "completed" con proof verificabile
- Esecuzione reale on-chain per SELL/SWAP: BEP-20 transfers (NENO, BNB, ETH/WETH, BTC/BTCB)
- Stripe SEPA payout reale per SELL/OFF-RAMP EUR→bank
- Endpoint /api/neno-exchange/withdraw-real per ETH/BTC interni→reali on-chain
- WebSocket balance sync (/ws/balances/{token}) + polling fallback
- Frontend: execution proof display, delivery tx hash, payout ID, new status badges
- 19/19 test passati (iteration_33)

## 2026-04-06 — Market Maker + Treasury + Audit
- Market Maker interno con Bid/Ask/Spread dinamici
- Treasury mappata su account Massimo
- Audit logging aggressivo PRE/POST
- 20/20 aggressive trades test passati

## 2026-04-05 — Phase 5 Completion
- DCA Trading Bot + Background Scheduler
- PDF Compliance Reports
- SMS Notifications (Twilio-ready)
- Deployment fixes (chokidar, requirements.txt)
