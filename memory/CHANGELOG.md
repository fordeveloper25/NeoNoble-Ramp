# Changelog

## 2026-04-03 — Alchemy RPC + Deposit NENO Widget
- **Configured**: Alchemy BSC RPC (`bnb-mainnet.g.alchemy.com`) replacing Infura
- **Verified**: Alchemy RPC stable — block 90M+, NENO contract reads working
- **Added**: "Deposita" tab in NENO Exchange with QR code widget
  - QRCodeSVG renders platform hot wallet address
  - Copyable full address with visual feedback
  - 3-step deposit instructions in Italian
  - Token contract info (ERC-20, BSC, 18 decimals, BscScan link)
  - Security warning (only send NENO on BSC Mainnet)
- **Testing**: iteration_25.json — 100% pass (15 backend + full frontend)

## 2026-04-03 — CORS Fix + Real Web3 Integration
- **Fixed**: "Errore di rete" on 400 responses (Emergent fetch interception → XHR)
- **Added**: On-chain NENO balance, MetaMask signing, platform-wallet endpoint, verify-deposit
- **Testing**: iteration_24.json — 100% pass

## Previous Sessions
- Phase 5: DCA Bot, PDF Reports, SMS Notifications
- NIUM V2 Unified API, deployment build fixes
- Margin Trading, Monte Carlo VaR, PEP screening, multi-language
