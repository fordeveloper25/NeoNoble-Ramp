# 🚀 DEPLOY CHECKLIST — NeoNoble STO su Polygon Mainnet (15 passi)

> **Prerequisiti bloccanti prima di partire:**
> - [x] Audit smart contract completato e findings risolti (OpenZeppelin/Certik/Quantstamp)
> - [x] Avvocato fintech ha approvato il prospetto / esenzione art. 100-bis TUF
> - [x] Wallet dedicato alla tesoreria esistente e noto (es. multisig Gnosis Safe)
> - [x] ~5 MATIC disponibili nel wallet deployer (~€2.50)
> - [x] Chiave Polygonscan API per verifica sorgente

---

## Setup (~5 min)

### ⏱ Passo 1 — Apri Remix
Vai su <https://remix.ethereum.org>. Crea workspace "neonoble-sto".

### ⏱ Passo 2 — Carica i contracts
Dal tuo repo locale copia in Remix:
- `contracts/interfaces/*.sol` (4 file)
- `contracts/registry/IdentityRegistry.sol`
- `contracts/compliance/DefaultCompliance.sol`
- `contracts/token/NenoSecurityToken.sol`
- `contracts/oracle/NAVOracle.sol`
- `contracts/vault/RedemptionVault.sol`
- `contracts/vault/RevenueShareVault.sol`

### ⏱ Passo 3 — Compila
- Solidity compiler: **0.8.20**
- Optimizer: **ON**, runs = **200**
- viaIR: **ON**
- Compila tutti i file. Deve uscire **verde, 0 warning critical**.

### ⏱ Passo 4 — Collega MetaMask a Polygon Mainnet
- Network: Polygon PoS (chainId 137)
- RPC: `https://polygon-rpc.com`
- Saldo: verifica ≥ 5 MATIC nel wallet deployer

---

## Deploy contratti (~7 min, 6 transazioni)

### ⏱ Passo 5 — Deploy `IdentityRegistry`
- Seleziona contract: `IdentityRegistry`
- Argomento `_owner`: **il tuo wallet deployer** (0x...)
- Click **Deploy** → firma in MetaMask
- ✅ **COPIA l'indirizzo** → chiamalo `REGISTRY_ADDRESS`

### ⏱ Passo 6 — Deploy `DefaultCompliance`
- Contract: `DefaultCompliance`
- `_owner`: tuo wallet
- `_registry`: `REGISTRY_ADDRESS` (step 5)
- Deploy → firma
- ✅ **COPIA** → `COMPLIANCE_ADDRESS`

### ⏱ Passo 7 — Deploy `NenoSecurityToken`
- Contract: `NenoSecurityToken`
- `_name`: `"NeoNoble Revenue Share Token"`
- `_symbol`: `"NNRS"`
- `_owner`: tuo wallet
- `_registry`: `REGISTRY_ADDRESS`
- `_compliance`: `COMPLIANCE_ADDRESS`
- Deploy → firma
- ✅ **COPIA** → `TOKEN_ADDRESS`

### ⏱ Passo 8 — Deploy `NAVOracle`
- Contract: `NAVOracle`
- `_owner`: tuo wallet
- `_settlementToken`: `0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359` (USDC nativo Polygon)
- `_initialNav`: `250000000` (= 250 USDC a 6 decimali, modifica se prezzo nominale diverso)
- Deploy → firma
- ✅ **COPIA** → `ORACLE_ADDRESS`

### ⏱ Passo 9 — Deploy `RedemptionVault`
- Contract: `RedemptionVault`
- `_owner`: tuo wallet
- `_stoToken`: `TOKEN_ADDRESS`
- `_navOracle`: `ORACLE_ADDRESS`
- `_settlement`: `0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359` (USDC)
- Deploy → firma
- ✅ **COPIA** → `REDEMPTION_ADDRESS`

### ⏱ Passo 10 — Deploy `RevenueShareVault`
- Contract: `RevenueShareVault`
- `_owner`: tuo wallet
- `_stoToken`: `TOKEN_ADDRESS`
- `_settlement`: `0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359`
- Deploy → firma
- ✅ **COPIA** → `REVSHARE_ADDRESS`

---

## Wiring (~3 min, 6 transazioni)

### ⏱ Passo 11 — Wire compliance ← token
Su `DefaultCompliance` deployato, call:
```
setToken(TOKEN_ADDRESS)   → firma
setExempt(REDEMPTION_ADDRESS, true)   → firma
setExempt(REVSHARE_ADDRESS, true)   → firma
```

Su `NenoSecurityToken` deployato, call:
```
setAgent(<tuo-wallet-deployer>, true)   → firma   // ti rende agent per mint/whitelist
setAgent(REDEMPTION_ADDRESS, true)   → firma      // il vault puo` burn()
```

### ⏱ Passo 12 — Configura compliance rules
Su `DefaultCompliance`:
```
setMaxHolders(149)   → firma   // < 150 per esenzione art. 100-bis TUF
setLockup(<unix_12_mesi_da_adesso>)   → firma
```

Tool per calcolare il timestamp 12 mesi: `date -d '+12 months' +%s` (Linux/Mac) oppure <https://www.epochconverter.com>.

### ⏱ Passo 13 — Country allowlist (facoltativo — SKIP se consigliato dall'avvocato)
Su `DefaultCompliance`:
```
setCountryAllowed(380, true)   // IT
setCountryAllowed(276, true)   // DE
setCountryAllowed(250, true)   // FR
setCountryAllowed(724, true)   // ES
setCountryAllowed(528, true)   // NL
setCountryAllowed(056, true)   // BE
setCountryAllowed(040, true)   // AT
setCountryAllowed(442, true)   // LU
setCountryAllowed(372, true)   // IE
setCountryAllowed(620, true)   // PT
setCountryAllowed(246, true)   // FI
setCountryAllowed(752, true)   // SE
setCountryAllowed(208, true)   // DK
setCountryAllowed(756, true)   // CH
```
Ogni riga è 1 firma MetaMask. Serve solo se l'avvocato ti conferma di attivare la allowlist subito.

---

## Verifica + backend live (~5 min)

### ⏱ Passo 14 — Verifica sorgente su Polygonscan
Su Remix, per ciascun contratto deployato → tab "Verify" → inserisci Polygonscan API key → clicca Verify.

Alternativa da CLI:
```bash
cd /app/contracts/sto
# in .env metti: POLYGONSCAN_API_KEY=...
export REGISTRY=<REGISTRY_ADDRESS>
export COMPLIANCE=<COMPLIANCE_ADDRESS>
export TOKEN=<TOKEN_ADDRESS>
export ORACLE=<ORACLE_ADDRESS>
export REDEMPTION=<REDEMPTION_ADDRESS>
export REVSHARE=<REVSHARE_ADDRESS>
yarn verify:polygon
```

Verifica che su <https://polygonscan.com/address/TOKEN_ADDRESS#code> compaia "Contract Source Code Verified".

### ⏱ Passo 15 — Switch backend a live-mode
Su **Railway**, in "Variables" del servizio backend, aggiungi/modifica:

```bash
POLYGON_RPC_URL=https://polygon-rpc.com
POLYGON_CHAIN_ID=137
STO_TOKEN_ADDRESS=<TOKEN_ADDRESS>
STO_REGISTRY_ADDRESS=<REGISTRY_ADDRESS>
STO_NAV_ORACLE=<ORACLE_ADDRESS>
STO_REDEMPTION_VAULT=<REDEMPTION_ADDRESS>
STO_REVSHARE_VAULT=<REVSHARE_ADDRESS>
STO_SETTLEMENT_TOKEN=0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359
STO_TOKEN_NAME=NeoNoble Revenue Share Token
STO_TOKEN_SYMBOL=NNRS
STO_NOMINAL_EUR=250
```

Railway riavvia il servizio automaticamente. Attendi 1-2 minuti.

**Smoke test**:
```bash
curl https://<tuo-dominio>/api/sto/health
# atteso: {"status":"operational","deployed":true, ...}

curl https://<tuo-dominio>/api/sto/public-info
# atteso: {"phase":"live","name":"NeoNoble...", ...}
```

Se ritorna `awaiting_deploy` → env non caricate, verifica Railway.

---

## 🎉 Sei live!

### Post-deploy action items (nei giorni seguenti)

**Entro 24h:**
- [ ] Annotare tutti e 6 gli indirizzi in password manager condiviso team
- [ ] Screenshot Polygonscan verification per archivio legale
- [ ] Aggiornare `STO_DEPLOY_SUMMARY.md` con indirizzi + data + tx hash

**Entro 48h:**
- [ ] Dry-run con 1 wallet pilota:
  1. `registry.registerIdentity(pilot_wallet, 380, <unix_1_year>, keccak256("SUMSUB"))`
  2. `token.mint(pilot_wallet, 1e18)` → 1 token
  3. Pilot: `stoToken.approve(REDEMPTION, 1e18)` + `redemption.requestRedemption(1e18)`
  4. Treasury: `USDC.approve(REDEMPTION, 250e6)` + `redemption.fund(250e6)`
  5. Admin: `redemption.approve(1)`
  6. Pilot: `redemption.claim(1)` → riceve 250 USDC
- [ ] Se tutto OK → backup tx hash per audit trail

**Entro 7 giorni:**
- [ ] Annuncio go-live agli iscritti della landing `/sto` via broadcast email (`/admin/sto/leads`)
- [ ] Post Twitter/LinkedIn/Telegram con OG-image `/og-sto.png`
- [ ] Avvia campagna marketing (Google Ads EU, crypto Telegram IT, PR fintech)

**Ogni mese:**
- [ ] Tesoreria top-up `RedemptionVault.fund()` con 30% ricavi netti mensili in USDC
- [ ] Review distribution list per revenue share

**Ogni trimestre:**
- [ ] Vedi `NAV_PROCEDURE.md` (calcolo NAV, certificazione revisore, aggiornamento on-chain, apertura finestra redemption)

---

## Troubleshooting

| Errore | Causa | Rimedio |
|---|---|---|
| `insufficient funds for gas` | MATIC finito nel deployer | Top-up con 2-3 MATIC |
| `contract deployment failed` | Constructor revert (valore zero o indirizzo sbagliato) | Ricontrolla argomenti costruttore |
| Backend `awaiting_deploy` dopo aver settato env | Env non ancora ricaricate | Forza restart: Railway → Deployments → Redeploy |
| `isVerified` ritorna false per investitore | `registerIdentity` non chiamata oppure `expiresAt` nel passato | Ricall con expiresAt futuro |
| `compliance` revert su mint | Max holders raggiunto o lockup attivo per transfer | Aumentare `maxHolders` o attendere lockup |
| Polygonscan verify fallisce | viaIR o Solidity version mismatch | Usa stesso compiler 0.8.20 + viaIR=true + runs=200 |

## Contatti emergenza durante il deploy

- Support Polygon: <https://support.polygon.technology>
- Polygonscan API issues: <https://polygonscan.com/apis>
- MetaMask support: <https://support.metamask.io>
- Me (agente E1): pingami in questa chat in qualunque momento — rispondo con il passo successivo.

---

**Buon deploy! 🚀**
