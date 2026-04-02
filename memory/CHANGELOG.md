# NeoNoble Ramp — Changelog

## April 2, 2026 - Sprint Finale
### DCA Trading Bot (P0)
- Created `/app/backend/routes/dca_routes.py` — Full CRUD: create, list, pause, resume, cancel, history
- Integrated DCA executor into background scheduler (runs every 60s)
- Created `/app/frontend/src/pages/DCABot.js` — Full UI with plan cards, execution history table
- Added DCA Bot link card on Dashboard with AUTO badge
- Registered `/dca` route in App.js

### PDF Compliance Reports (P0)
- Added `GET /api/export/compliance/pdf` to export_routes.py
- Generates professional PDF with: KYC status, portfolio summary, trade history, margin positions, DCA plans
- Uses ReportLab with NeoNoble purple branding
- PDF download button on DCA Bot page

### NIUM Onboarding Improvements (P0)
- Updated customer creation payload: added `region`, enum codes for `estimatedMonthlyFunding`/`intendedUseOfAccount`
- Multi-version retry: v2 > v3 > v4 > v1 (v2 Unified API as primary)
- Added `GET /api/nium-onboarding/diagnostic` — full integration health check
- Added `GET /api/nium-onboarding/templates` — template discovery
- Added `GET /api/nium-onboarding/corporate-constants` — fetch NIUM config
- Added `POST /api/nium-onboarding/set-template-id` — admin runtime template config
- Template ID loaded from DB on startup (no .env edit required)

### SMS Notifications (P1)
- Added `_send_sms_notification()` to notification_dispatch.py
- Twilio-ready: uses TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER env vars
- Silent fallback when Twilio not configured
- SMS logging to `sms_log` collection

### Bug Fixes
- Fixed blockchain listener `KeyError: 'address'` — now handles both `address` and `deposit_address` keys
- Fixed NIUM version priority (v2 first instead of v3)

### Testing
- Iteration 17: 24/24 tests passed (100% backend, 100% frontend)

## April 2, 2026 - Phase 6: Future Tasks Complete

### Referral System (P2)
- Created `/app/backend/routes/referral_routes.py` — Code generation, apply code, stats, leaderboard
- Referrer bonus: 0.001 NENO per successful referral
- Referred welcome bonus: 0.0005 NENO
- Trade bonus: 0.0005 NENO when referred user makes first trade
- Anti-abuse: Cannot use own code, one code per user
- Public leaderboard (top 20 referrers, anonymized usernames)
- Created `/app/frontend/src/pages/ReferralPage.js` — Full UI with code display, copy, share, apply, stats, leaderboard
- Added Referral card on Dashboard with BONUS badge
- Registered `/referral` route in App.js

### Advanced Portfolio Analytics (P2)
- Created `/app/backend/routes/advanced_analytics_routes.py`
- Sharpe Ratio (annualized, risk-free rate 4%)
- Sortino Ratio (downside deviation only)
- Max Drawdown (absolute EUR and percentage)
- Volatility (daily and annualized)
- Calmar Ratio (return / max drawdown)
- Best/Worst day, Win/Loss day counts
- Asset Correlation endpoint with Diversification Score (0-100) and HHI index
- Enhanced PortfolioAnalytics.js with risk metrics cards and diversification score visualization

### Enhanced KYC/AML Compliance (P2)
- Added Risk Scoring system (0-100 scale) with factors: KYC tier, transaction velocity, AML alert history, account age
- Risk levels: low (0-30), medium (31-60), high (61-100)
- Added full Compliance Report endpoint: KYC tier, risk score, volume (daily/weekly/monthly), limits, AML alerts
- Added Admin Compliance Overview: tier distribution, risk distribution, alert counts
- Cached risk scores in kyc_risk_scores collection

### Multi-Language i18n Completion (P2)
- Added Spanish (es) translations — complete coverage of all keys
- Extended all 5 languages with new keys for: referral, advanced analytics, risk, compliance
- Updated SettingsPage.js with 5 language options: IT, EN, DE, FR, ES

### Webhook System Enhancement (P2)
- Added new webhook event types: KYC events (submitted, approved, rejected, tier upgraded), AML events, Referral events, Trading events (executed, margin open/close/liquidation), DCA events

### BSC RPC Error Fix (P2)
- Added hex block format fallback in blockchain_listener.py
- Retry with integer blocks if hex format fails
- Demoted RPC parameter errors to debug-level logging (reduces log noise)

### Server Architecture Refactoring
- Created ServiceContainer pattern in `/app/backend/services/service_container.py`
- Centralizes all service instantiation, wiring, initialization, and shutdown
- Added database indexes for new collections: referral_codes, referral_links, referral_bonus_log, kyc_risk_scores

### Testing
- Iteration 18: 22/22 tests passed (100% backend, 100% frontend)
