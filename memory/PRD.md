# NeoNoble Ramp — PRD

## Architecture
- Backend: FastAPI, MongoDB, Web3.py, Alchemy BSC RPC
- Frontend: React.js, Tailwind, Wagmi v3/viem, WalletConnect, qrcode.react
- NENO Contract: `0xeF3F5C1892A8d7A3304E4A15959E124402d69974` (BSC Mainnet)
- Hot Wallet: `0x18CE1930820d5e1B87F37a8a2F7Cf59E7BF6da4E`

## Implemented Features (100% Operativa)
- [x] NENO Exchange: buy/sell/swap/off-ramp/deposit (on-chain + internal)
- [x] **verify-deposit**: Verifica on-chain → accredita NENO → crea record → notifica
- [x] **Hot wallet monitor**: Blockchain listener attivo, scansiona NENO transfers
- [x] Deposit widget: QR code, indirizzo copiabile, 3-step flow
- [x] Real on-chain NENO balance (Wagmi useReadContract)
- [x] MetaMask transaction signing (sell/swap/off-ramp)
- [x] CORS fix: XMLHttpRequest bypasses Emergent fetch interception
- [x] Alchemy BSC RPC + POA middleware
- [x] NIUM Banking V2, DCA Bot, PDF Reports, SMS, Margin Trading
- [x] Monte Carlo VaR, PEP screening, multi-language, microservices routing

## Production Readiness
- End-to-end test su BSC Mainnet: COMPLETATO (5 NENO deposit + sell)
- TX hash verificato: `0x4aba1b5b9abba545583e42330babeee89bf8201d5432fd796bae833cb127ceb7`
- Hot wallet monitor: ATTIVO (polling 120s)

## Backlog
- [ ] NIUM templateId (in attesa da utente)
- [ ] Dynamic NENO pricing da order book
- [ ] Referral system con bonus NENO
