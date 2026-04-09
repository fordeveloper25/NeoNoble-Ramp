# NeoNoble Ramp — CHANGELOG

## 2026-04-09 — Autonomous Financial Pipeline E2E Validated
- Pipeline Finanziario Autonomo: deposit → fee extraction → auto-payout SEPA
- Stripe Live: PaymentIntents, Webhooks (5 event types), Auto-Payout Engine
- Background loop autonomo (120s check interval, threshold 10 EUR)
- Admin Dashboard Pipeline panel con status real-time
- Fix xhrFetch error handling per PipelineStatusPanel
- 23/23 test backend passati (iteration_43) + Frontend 100% verificato

## 2026-04-08 — Full Real Money System Activation
- FIX: Wallet & Banking "body stream already read" → safeFetch wrapper con response.clone()
- Hybrid Liquidity Engine: user matching → market maker → DEX fallback
- Dynamic spread 100-300bps con inventory skew e volume tiers (5 livelli)
- Internal order book con netting user↔user
- Fee layer 0.5% + referral bonus 10%
- Full loop: UI→Execution→Matching→Settlement→Cashout→UI Sync
- 25/25 test passati (iteration_40)

## 2026-04-08 — DEX PancakeSwap V2 + Live Pipeline
- 2 swap reali: NENO→USDC + BNB→USDC (TX hashes verificati)
- NENO/WBNB pool trovato: 0x27f9610f...
- Pipeline E2E: Assess→Quote→Swap→Settle→Reconcile→Fiat
- 28/28 test passati (iteration_39)

## 2026-04-08 — Real-Time Sync + Instant Withdraw + EventBus
- 28/28 test passati (iteration_38)

## 2026-04-08 — Cashout Engine + Auto-Conversion
- 24/24 test passati (iteration_37)

## 2026-04-08 — Circle USDC + Wallet Segregation
- 18/18 test passati (iteration_36)

## 2026-04-08 — Virtual→Real + IPO Plan | 9/9 (iter_35)
## 2026-04-08 — IPO-Ready Exchange | 19/19 (iter_34)
## 2026-04-07 — Security + Real Execution | 19/19 (iter_33)
