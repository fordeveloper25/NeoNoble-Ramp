# NeoNoble Ramp — PRD (Product Requirements Document)

## Original Problem Statement
Enterprise-grade fintech platform for crypto on/off-ramp, NENO token exchange, card issuing, and multi-chain wallet management. Built with FastAPI + React + MongoDB.

## Core Requirements
1. Real NIUM banking integration (card issuing, KYC)
2. NENO internal exchange (buy/sell/swap/off-ramp/deposit)
3. Multi-chain wallet (BSC, ETH, Polygon)
4. WalletConnect/MetaMask integration with real transaction signing
5. Automated DCA Trading Bot
6. PDF Compliance Reports
7. Margin Trading
8. Multi-channel Notifications (SSE, Push, SMS)

## Architecture
- Backend: FastAPI, MongoDB (Motor), Web3.py, Alchemy BSC RPC
- Frontend: React.js, Tailwind, Wagmi v3/viem, WalletConnect, qrcode.react
- NENO Token: BSC Mainnet contract `0xeF3F5C1892A8d7A3304E4A15959E124402d69974`
- Platform Hot Wallet: `0x18CE1930820d5e1B87F37a8a2F7Cf59E7BF6da4E`
- BSC RPC: Alchemy (`https://bnb-mainnet.g.alchemy.com/v2/...`)

## What's Been Implemented
- [x] NENO Exchange: buy/sell/swap/off-ramp with real error handling (XHR-based)
- [x] Deposit NENO widget with QR code and hot wallet address
- [x] Real on-chain NENO balance via Wagmi useReadContract
- [x] MetaMask transaction signing for sell/swap/off-ramp
- [x] On-chain deposit verification endpoint (verify-deposit)
- [x] Platform hot wallet endpoint (derived from mnemonic)
- [x] Alchemy BSC RPC configuration
- [x] CORS fix: XMLHttpRequest helpers (bypass Emergent fetch interception)
- [x] NIUM Banking integration (V2 Unified API)
- [x] DCA Trading Bot + Background Scheduler
- [x] PDF Compliance Reports + SMS Notifications
- [x] Margin Trading + Monte Carlo VaR + PEP screening
- [x] Multi-language support + Microservices routing

## Backlog
- [ ] NIUM templateId configuration (blocked on user's NIUM portal)
- [ ] Dynamic NENO pricing from order book
- [ ] Referral system with NENO bonuses
- [ ] BSC RPC error cleanup in blockchain_listener.py
