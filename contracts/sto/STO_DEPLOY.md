# NeoNoble STO — Architettura e Deploy

Pacchetto completo per emettere un **Security Token** utility + revenue
share **conforme MiCA / TUF 100-bis**, su **Polygon PoS**.

## Indice

1. [Architettura contratti](#architettura-contratti)
2. [Flow end-to-end](#flow-end-to-end)
3. [Setup locale e test](#setup-locale-e-test)
4. [Deploy su Amoy (testnet)](#deploy-su-amoy-testnet)
5. [Deploy su Polygon Mainnet](#deploy-su-polygon-mainnet)
6. [Verifica contratti su Polygonscan](#verifica-contratti-su-polygonscan)
7. [Operazioni continue](#operazioni-continue)
8. [Checklist pre-emissione](#checklist-pre-emissione)
9. [Integrazione con l'avvocato](#integrazione-con-lavvocato)

---

## Architettura contratti

```
contracts/
├── interfaces/
│   ├── ICompliance.sol
│   ├── IIdentityRegistry.sol
│   ├── INAVOracle.sol
│   └── IRedemptionVault.sol
├── registry/
│   └── IdentityRegistry.sol       ← whitelist KYC on-chain
├── compliance/
│   └── DefaultCompliance.sol      ← regole transfer (KYC, lockup, max holders, country)
├── token/
│   └── NenoSecurityToken.sol      ← ERC-20 + transfer restrictions + forced transfer + pause
├── oracle/
│   └── NAVOracle.sol              ← NAV per token pubblicato trimestralmente
├── vault/
│   ├── RedemptionVault.sol        ← redemption a NAV con riserva dedicata
│   └── RevenueShareVault.sol      ← distribuzione pro-rata ricavi agli holder
└── test/
    └── MockERC20.sol              ← solo per test hardhat
```

### Token flow

```
                    ┌─────────────────┐
        KYC ok?  →  │ IdentityRegistry│
                    └────────┬────────┘
                             │ isVerified()
                             v
     ┌──────────┐       ┌────────────┐      ┌────────────────┐
     │ Investor │───────│ STO Token  │──────│ DefaultCompliance│
     └──────────┘  ERC-20 transfer    canTransfer / transferred
          │                │
          │                │ mint/burn
          v                v
  ┌───────────────┐  ┌─────────────────────┐
  │ Redemption    │  │  RevenueShareVault  │
  │ Vault (NAV)   │  │  (revenue share)    │
  └───────┬───────┘  └─────────┬───────────┘
          │ NAV                │
          v                    v
     ┌──────────┐          ┌──────────┐
     │ NAVOracle│          │  USDC    │
     └──────────┘          └──────────┘
```

---

## Flow end-to-end

### A. Subscription (investitore compra token)

1. Investitore completa KYC Sumsub nel backend NeoNoble
2. Backoffice (agent) chiama `IdentityRegistry.registerIdentity(investorAddress, country, expiresAt, "SUMSUB")`
3. Investitore bonifica EUR → Stripe / SEPA → conto NeoNoble S.r.l.
4. Backoffice (agent) chiama `NenoSecurityToken.mint(investorAddress, amount)`
5. L'investitore vede i suoi token on-chain

### B. Distribuzione revenue (trimestrale)

1. Tesoreria converte i ricavi trimestrali in USDC
2. Tesoreria chiama `USDC.approve(RevenueShareVault, amount)`
3. Tesoreria chiama `RevenueShareVault.distribute(amount)` → creato `distributionId`
4. Ogni holder chiama `RevenueShareVault.claim(distributionId)` e riceve la sua quota pro-rata

### C. Redemption a NAV (mensile/trimestrale)

1. Revisore certifica NAV trimestrale → produce report firmato
2. Operator chiama `NAVOracle.updateNAV(navInUsdc, effectiveFrom, reportHash)`
3. Investitore chiama `stoToken.approve(RedemptionVault, amount)` poi `RedemptionVault.requestRedemption(amount)` → NAV **congelato** al timestamp della richiesta
4. Tesoreria bonifica USDC sulla propria wallet e chiama `RedemptionVault.fund(amount)`
5. Operator chiama `RedemptionVault.approve(requestId)` o `reject(requestId, reason)`
6. Investitore chiama `RedemptionVault.claim(requestId)` e riceve USDC, i suoi token vengono bruciati

### D. Emergenze regolamentari

- **Pause**: `NenoSecurityToken.pause()` blocca tutti i trasferimenti secondari (non mint/burn). Usato per ordine CONSOB o incidente.
- **Forced transfer**: `NenoSecurityToken.forcedTransfer(from, to, amount, "ragione")` — solo agent, destinazione deve essere whitelisted, loggato on-chain. Usato per recupero chiavi perse o ordine giudiziario.
- **Wallet Lost**: `setLost(wallet, true)` blocca il wallet in attesa di forcedTransfer verso il nuovo indirizzo del legittimo proprietario.

---

## Setup locale e test

```bash
cd /app/contracts/sto
yarn install
cp .env.example .env   # compila con i tuoi valori
yarn compile
yarn test
```

Ci sono **9 test automatici** che coprono: mint KYC, transfer restrictions, max holders, lockup, redemption, pause, forced transfer, revenue share pro-rata.

Output atteso:
```
  NeoNoble STO — flow end-to-end
    ✓ mint funziona solo verso address whitelisted
    ✓ transfer blocca destinatari non KYC
    ✓ max holders enforced
    ✓ redemption a NAV con riserva
    ✓ redemption rifiutata se riserva insufficiente
    ✓ revenue share pro-rata
    ✓ forced transfer loggato e soggetto a compliance su destinatario
    ✓ pause blocca tutti i trasferimenti ma non mint/burn agent
    ✓ lockup blocca transfer tra investitori ma non mint
  9 passing
```

---

## Deploy su Amoy (testnet)

Amoy è la testnet Polygon attuale (sostituisce Mumbai, dismesso nel 2024).

```bash
# 1. Procura MATIC di test dal faucet
#    https://faucet.polygon.technology/
# 2. Compila .env con PRIVATE_KEY del wallet testnet
# 3. Deploy un mock USDC se non esiste già (oppure usa USDC già deployato su Amoy)

# Deploy full stack
yarn deploy:amoy
```

Output: indirizzi dei 6 contratti. Copiali nelle env del backend NeoNoble
(vedi sezione "Operazioni continue").

---

## Deploy su Polygon Mainnet

> ⚠️ **Non deployare in mainnet prima di:**
> 1. Aver passato tutti i test locali (`yarn test` → 9/9 PASS)
> 2. Aver deployato su Amoy e testato il flow end-to-end (subscription → redemption → revenue share) con almeno 2-3 investitori di test
> 3. **Audit smart contract** (OpenZeppelin, Certik, Quantstamp) — **obbligatorio** prima di emettere token con soldi reali
> 4. Avvocato approva il prospetto e le regole di compliance (country list, lockup, maxHolders)

### Passi deploy Polygon Mainnet

```bash
# 1. Verificare l'ambiente
cd /app/contracts/sto
yarn test                                # 9/9 PASS obbligatorio
yarn compile

# 2. Setup .env di produzione
cat > .env <<EOF
PRIVATE_KEY=0x...                        # Wallet deployer con >= 5 MATIC
POLYGON_RPC_URL=https://polygon-rpc.com  # Oppure Alchemy/Infura
POLYGONSCAN_API_KEY=XXXXXXX              # Per verifica source
STO_TOKEN_NAME=NeoNoble Revenue Share Token
STO_TOKEN_SYMBOL=NNRS
SETTLEMENT_TOKEN_POLYGON=0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359  # USDC nativo Polygon
INITIAL_NAV=250000000                    # 250 USDC (6 dec) per token
MAX_HOLDERS=149                          # < 150 per esenzione art. 100-bis TUF
LOCKUP_UNTIL=<timestamp 12 mesi>
TREASURY_ADDRESS=0x...                   # Wallet tesoreria segregato
EOF

# 3. Simulazione dry-run su fork Polygon (OPZIONALE ma consigliato)
#    Hardhat network fork per testare il deploy senza spendere MATIC reali.

# 4. Deploy effettivo
yarn deploy:polygon

# Output atteso: 6 indirizzi Polygon mainnet.
# Annotarli su documento sicuro (password manager condiviso team).

# 5. Verifica sorgente Polygonscan (obbligatorio)
export REGISTRY=0x...
export COMPLIANCE=0x...
export TOKEN=0x...
export ORACLE=0x...
export REDEMPTION=0x...
export REVSHARE=0x...
yarn verify:polygon

# 6. Country allowlist (eseguire in Remix o script separato)
#    Country codes ISO 3166-1 numeric:
#    IT=380, DE=276, FR=250, ES=724, NL=528, BE=056, AT=040,
#    LU=442, IE=372, PT=620, FI=246, SE=752, DK=208, CH=756
#    Chiamare compliance.setCountryAllowed(code, true) per ciascuno.

# 7. Configurazione backend NeoNoble
#    Aggiungere a /app/backend/.env (o Railway env):
cat <<EOF
POLYGON_RPC_URL=https://polygon-rpc.com
POLYGON_CHAIN_ID=137
STO_TOKEN_ADDRESS=0x...
STO_REGISTRY_ADDRESS=0x...
STO_NAV_ORACLE=0x...
STO_REDEMPTION_VAULT=0x...
STO_REVSHARE_VAULT=0x...
STO_SETTLEMENT_TOKEN=0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359
STO_TOKEN_NAME=NeoNoble Revenue Share Token
STO_TOKEN_SYMBOL=NNRS
STO_NOMINAL_EUR=250
RESEND_API_KEY=re_xxxxx                  # Per broadcast email lead
EOF
#    Poi: sudo supervisorctl restart backend

# 8. Smoke test produzione
curl https://<tuo-dominio>/api/sto/health    # atteso: deployed=true
curl https://<tuo-dominio>/api/sto/public-info  # atteso: phase="live"
```

### Costo deploy stimato

| Voce | Costo MATIC | Costo EUR (MATIC ~€0.50) |
|---|---|---|
| IdentityRegistry | ~0.15 | €0.08 |
| DefaultCompliance | ~0.20 | €0.10 |
| NenoSecurityToken | ~0.50 | €0.25 |
| NAVOracle | ~0.15 | €0.08 |
| RedemptionVault | ~0.25 | €0.13 |
| RevenueShareVault | ~0.20 | €0.10 |
| Wiring (6 tx) | ~0.10 | €0.05 |
| Country allowlist (~10 tx) | ~0.15 | €0.08 |
| **TOTALE** | **~1.70 MATIC** | **~€0.85** |

Prevedere 3-5 MATIC nel wallet deployer per margine.

### Post-deploy checklist

- [ ] Indirizzi salvati su documento sicuro (password manager condiviso)
- [ ] Polygonscan verification OK per tutti e 6 i contratti
- [ ] Country allowlist configurata
- [ ] Frontend `/sto/public-info` ritorna `phase=live`
- [ ] Backend admin può chiamare `/api/sto/admin/whitelist/add` con successo
- [ ] Treasury alimenta riserva con 100 USDC test → `RedemptionVault.fund()`
- [ ] Test dry-run con 1 investitore pilota (amico whitelisted) subscription 100 USDC → mint 0.4 token → richiesta redemption → claim
- [ ] Email broadcast ai lead (`/admin/sto/leads`) per annunciare go-live

---

## Verifica contratti su Polygonscan

Dopo il deploy:

```bash
export REGISTRY=0x...
export COMPLIANCE=0x...
export TOKEN=0x...
export ORACLE=0x...
export REDEMPTION=0x...
export REVSHARE=0x...
yarn verify:polygon
```

Questo pubblica il sorgente Solidity su Polygonscan, permettendo agli
investitori e all'avvocato di audit-are il codice. **Obbligatorio per
compliance**.

---

## Operazioni continue

Una volta deployato, le attività periodiche sono:

| Attività | Frequenza | Chi | Come |
|---|---|---|---|
| Aggiungere investitori alla whitelist | on-demand post-KYC | Backoffice | `yarn whitelist:add` (env: `REGISTRY_ADDRESS`, `INVESTOR_ADDRESS`, `EXPIRES_UNIX`) o endpoint backend `/api/sto/whitelist/add` |
| Mint dopo bonifico fiat ricevuto | on-demand | Backoffice | `token.mint(investor, amount)` |
| Aggiornare NAV | trimestrale | Tesoreria + revisore | `yarn nav:update` |
| Distribuire revenue share | trimestrale | Tesoreria | `revShareVault.distribute(amount)` |
| Alimentare riserva redemption | mensile/trimestrale | Tesoreria | `redemptionVault.fund(amount)` |
| Approvare redemption requests | quotidiano/settimanale | Operator | `redemptionVault.approve(requestId)` |

---

## Checklist pre-emissione

- [ ] Tutti i test locali passano (`yarn test`)
- [ ] Deploy su Amoy completato
- [ ] Flow end-to-end testato su Amoy con 3 wallet di test (investitore + tesoreria + operator)
- [ ] Audit smart contract esterno completato, findings risolti
- [ ] Avvocato ha approvato:
  - [ ] Prospetto informativo (o esenzione art. 100-bis TUF <€8M)
  - [ ] Informativa MiCA
  - [ ] Testo del contratto di sottoscrizione
  - [ ] Informativa privacy GDPR
  - [ ] Regole KYC/AML con Sumsub
- [ ] Registrazione CONSOB / comunicazione preventiva
- [ ] Registro OAM se richiesto per VASP activity
- [ ] Treasury account bancario segregato creato (conto dedicato alla riserva redemption)
- [ ] Procedura di revisione NAV trimestrale firmata con revisore
- [ ] Disclosure rischi pubblicata sul sito NeoNoble Ramp
- [ ] Deploy mainnet eseguito + verifica Polygonscan
- [ ] Wiring compliance rules finali (maxHolders, lockup, country allowlist)
- [ ] Dry-run con 1 investitore pilota (friend-and-family) prima del go-live pubblico

---

## Integrazione con l'avvocato

Lo studio legale ti fornirà, tipicamente:

1. **Parametri di compliance** → da applicare al deploy:
   - `MAX_HOLDERS` (es. 149 per esenzione art. 100-bis)
   - `LOCKUP_UNTIL` (es. 12 mesi da first issuance)
   - Country allowlist iniziale (tipicamente EU + CH + UK + spesso esclusi US/CN/RU)
2. **Prospetto informativo** in PDF — `reportHash` del prospetto va caricato su IPFS e il suo CID messo come primo `NAVOracle.reportHash`
3. **KYC SLA** con Sumsub — tempo di verifica, documenti, paesi supportati
4. **Procedura di redemption** — timeline (es. request entro T-5, approvazione entro T-3, payout entro T), tetti mensili, casi di sospensione

Queste informazioni guidano sia gli script di deploy sia le policy del
backend Neno. Il codice Solidity è **già predisposto** per ricevere tutti
questi parametri senza modifiche strutturali.

---

## Supporto

Per dubbi tecnici: apri issue su GitHub con label `sto`. Per dubbi legali:
rivolgersi all'avvocato dello studio fintech nominato.
