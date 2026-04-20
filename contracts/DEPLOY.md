# NeoNoble Launchpad — Guida di Deploy

Questa guida ti porta da zero a un **Launchpad operativo su BSC Mainnet**.

## Cosa hai nel repo

```
/app/contracts/
├── BondingCurveToken.sol    # ERC20 con bonding curve virtual AMM
└── Launchpad.sol             # Factory che deploya i token
```

## Flow di deploy (15 minuti, con Remix IDE)

### 1) Apri Remix
Vai su [remix.ethereum.org](https://remix.ethereum.org).

### 2) Carica i contract
Crea due file nel file explorer di Remix:
- `BondingCurveToken.sol` → copia il contenuto di `/app/contracts/BondingCurveToken.sol`
- `Launchpad.sol` → copia il contenuto di `/app/contracts/Launchpad.sol`

### 3) Compila
- Compiler version: **0.8.20** o superiore
- Optimizer: **ON**, runs = **200**
- Compila prima `BondingCurveToken.sol`, poi `Launchpad.sol`.

### 4) Collega MetaMask a BSC Mainnet
Metti il wallet su BSC Mainnet (chainId 56). Serve un minimo di BNB per il gas (~0.03 BNB dovrebbe bastare per deployare entrambi i contract... in realtà serve solo deployare il Factory perché i BondingCurveToken vengono deployati *dal* factory runtime).

### 5) Deploy del factory
Nella sezione **Deploy & Run Transactions** di Remix:
- Seleziona **Environment: "Injected Provider - MetaMask"**
- Seleziona **Contract: Launchpad**
- Nel campo del constructor **`_platformFeeRecipient`** inserisci l'**indirizzo del wallet** dove vuoi ricevere le fee della piattaforma (es. il wallet treasury di NeoNoble).
- Premi **Deploy**. Firma in MetaMask.

### 6) Copia l'indirizzo del Factory
Dopo la conferma, copia l'indirizzo del contratto deployato (lo trovi nella sezione "Deployed Contracts" di Remix).

### 7) Imposta l'env var nel backend
Aggiungi a `/app/backend/.env` (o nelle env di Railway):

```bash
LAUNCHPAD_FACTORY_ADDRESS=0x...il_tuo_factory
```

### 8) Riavvia il backend
```bash
sudo supervisorctl restart backend
```

### 9) Verifica
```bash
curl https://<tuo-dominio>/api/launchpad/health
```
Dovresti vedere `"factory_deployed": true`.

## Come funziona

### Creazione di un token
Un utente qualunque chiama `createToken(name, symbol, metadataURI)` sul factory pagando la **deployFee** (default 0.05 BNB). Il factory:
1. Deploya una nuova istanza di `BondingCurveToken`
2. Registra il token negli array `allTokens` e `tokensByCreator[creator]`
3. Inoltra la deploy fee al `platformFeeRecipient`

### Buy (chi compra)
L'utente manda BNB al metodo `buy(minTokensOut)`. Il contratto:
1. Preleva 1% platform fee + 1% creator fee
2. Applica la formula `x*y=k` con reserve virtuali
3. Minta i token al buyer
4. Aggiorna `realBnbReserve`
5. Se `realBnbReserve >= 85 BNB` → **graduation**: la curva si chiude, 200M token vengono mintati al factory per creare l'LP PancakeSwap (migrazione manuale v1, automatica v2).

### Sell (chi vende)
L'utente chiama `sell(tokensIn, minBnbOut)`. Il contratto:
1. Brucia i token del seller
2. Calcola BNB da restituire con la formula `x*y=k`
3. Preleva 1% platform + 1% creator fee sul BNB out
4. Invia il netto al seller

## Parametri economici

| Parametro | Valore | Modificabile |
|---|---|---|
| Deploy fee | 0.05 BNB | ✅ `setDeployFee(n)` owner-only |
| Platform fee | 1% per trade | ❌ hardcoded |
| Creator fee | 1% per trade | ❌ hardcoded |
| Virtual BNB reserve iniziale | 30 BNB | ❌ hardcoded |
| Virtual token reserve iniziale | 1.073.000.000 | ❌ hardcoded |
| Graduation threshold | 85 BNB raccolti | ❌ hardcoded |
| Token on curve | 800M | ❌ hardcoded |
| Token per LP post-graduation | 200M | ❌ hardcoded |

## Sicurezza

- ✅ Nessun backdoor: il contract non ha funzioni `pause`, `rescue`, `mint` admin
- ✅ ReentrancyGuard su `buy` e `sell`
- ✅ Nessun owner su `BondingCurveToken` (il factory non può toccare i token deployati)
- ⚠️ **Non auditato**: consigliata audit formale prima di volumi > €100k

## Domande frequenti

**Q: Quanto capitale deve mettere un creator?**
A: Solo 0.05 BNB di deploy fee (~25€). Zero collateral aggiuntivo.

**Q: E se nessuno compra il token?**
A: Il token esiste ma la curva è a prezzo iniziale. Il creator ha perso la deploy fee, nient'altro.

**Q: Un utente può uscire con tutto il BNB?**
A: Sì, finché c'è `realBnbReserve`. La curva è matematicamente simmetrica: se metti 10 BNB e nessun altro trade il prezzo, puoi anche uscire con ~10 BNB (meno fee 2%+2% = 4% round-trip).

**Q: Cosa succede alla graduation (85 BNB)?**
A: La curva si chiude (niente più buy/sell sul contract). 200M token vengono riservati nel factory per creare un LP iniziale PancakeSwap. La migrazione LP è manuale in v1 (un operatore chiama PancakeSwap Factory + pairs + addLiquidity con i 200M token + il BNB accumulato); v2 sarà automatica.
