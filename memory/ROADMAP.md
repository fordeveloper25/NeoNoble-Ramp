# NeoNoble Ramp — Roadmap

## Completed
- [x] Phase 1-4: Core Trading, Auth, Settlement, Blockchain Monitoring
- [x] Phase 5: Multi-chain, Banking Rails, Cards, Internal NENO Exchange
- [x] Phase 6: Margin Trading PRO, Unified Wallet, Token Discovery, KYC/AML, Dynamic NENO Pricing

## P0 — All Done
No remaining P0 items.

## P1 — Microservices Refactoring
- [ ] Split FastAPI monolith into distinct services:
  - Exchange Service (trading_engine, neno_exchange)
  - Wallet Service (wallet, multichain, settlement)
  - Compliance Service (kyc, aml)
  - Cards & Banking Service (card_routes, banking_routes)
  - Gateway Service (auth, API routing)
- [ ] Implement service-to-service communication (gRPC or HTTP)
- [ ] Shared MongoDB → service-specific databases

## P2 — Future Enhancements
- [ ] Automated KYC document verification (OCR + ID matching)
- [ ] Real-time order book for NENO (WebSocket)
- [ ] Advanced order types: Limit orders, Stop orders, Trailing stops
- [ ] Portfolio analytics dashboard with P&L charts
- [ ] Mobile-responsive optimization
- [ ] Multi-language support (EN, DE, FR besides IT)
- [ ] 2FA authentication (TOTP)
- [ ] Push notifications for trade execution and alerts
