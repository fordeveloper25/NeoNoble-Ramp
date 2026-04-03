# NeoNoble Ramp — Changelog

## April 3, 2026 (Session 4)
### P0 CRITICAL — Fix "body stream already read" Bug
- **Root cause**: `res.text()` called on response whose body was already consumed by browser proxy/service worker/wallet extensions
- **Fix**: Replaced direct `res.text()` / `res.json()` with triple-fallback `safeJson(res)` using `res.clone()`:
  1. Primary: `res.clone().json()`
  2. Fallback: `res.clone().text()` → `JSON.parse()`
  3. Final: generic error message
- Added `safeGet()` and `safePost()` helpers — all fetch calls now use safe pattern
- Removed all direct response body reads
- Verified: BUY, SELL, SWAP, OFF-RAMP, CREATE TOKEN — all green, zero errors

### P2 — Monte Carlo VaR Simulation
- `GET /api/analytics/montecarlo/var` — configurable simulations, horizon, confidence
- Returns VaR, CVaR, portfolio positions, distribution percentiles, risk assessment

### P2 — PEP Screening & Sanctions
- `POST /api/pep/screen` — OFAC, UN, EU, internal watchlist, PEP database
- `POST /api/pep/watchlist`, `GET /api/pep/history`, `GET /api/pep/stats`

### P2 — Additional Languages
- Added PT, JA, ZH, AR (total 9 languages)

### P2 — Microservices Domain Registry
- 9 logical domains mapped in service_registry.py

### Testing
- Iteration 19: NENO Exchange backend (19/19 pass)
- Iteration 20: P2 Features (15/15 pass)
- Iteration 21: Bug fix + full E2E (100% backend + 100% frontend)

## Prior Sessions
- Sessions 1-3: Full platform build, all Phase 5 features, deployment fixes
