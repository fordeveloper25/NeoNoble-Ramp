# NeoNoble Ramp — Product Requirements Document

## Original Problem Statement
Build "NeoNoble Ramp", a global enterprise-grade fintech infrastructure platform.

## Core Architecture
- Backend: FastAPI + MongoDB + Python 3.11
- Frontend: React.js + Tailwind + Shadcn + lightweight-charts
- NIUM: Auto-discovered auth (x-api-key @ gateway.nium.com, multi-version v3/v4/v2/v1)
- Notifications: Multi-channel (Email/Resend + In-app/SSE + Browser Push + WebSocket)
- Background: Scheduler with periodic tasks (alerts 60s, rate limiter 300s, NIUM auth 1800s)
- i18n: IT, EN, DE, FR

## ALL Features Complete (Phase 1-8)

### Current Phase: NIUM Auto-Discovery + Background Scheduler
- Multi-Strategy Auth Discovery: 6 strategies on 3 URLs, auto-cached
- Multi-Version API Retry: v3→v4→v2→v1 with adaptive payload
- Background Scheduler: Price alerts, rate limiter cleanup, NIUM auth refresh
- Price Alerts: CRUD + auto-trigger via scheduler
- Browser Push: Web Notification API polling
- Multi-channel Dispatch: Trade/margin/KYC/security/banking/card/price notifications

### NIUM Status
- Auth: WORKING (x-api-key on gateway.nium.com)
- Customer Creation: Requires templateId configuration in NIUM Portal
- Client Hash: 24dba820-d8da-4ce6-b72f-d07f98ffa2fd

## Key New Endpoints
- `GET /api/nium-onboarding/auth-discovery-status`
- `POST /api/nium-onboarding/auth-discovery-reset`
- `POST /api/alerts/create` / `GET /api/alerts`
- `POST /api/alerts/check` (background task)
- `GET /api/browser-push/pending`
