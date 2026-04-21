# 🚀 NeoNoble Ramp - Guida Deployment Railway EU

## 📋 Panoramica

Questa guida ti aiuta a deployare **NeoNoble Ramp** su **Railway** in region **EU** per abilitare i withdrawal reali da Binance (senza geo-restriction).

---

## 🎯 Passo 1: Esporta su GitHub da Emergent

### 1.1 Connetti GitHub
1. Nell'interfaccia Emergent, clicca sull'**icona profilo** in alto
2. Cerca e clicca **"Connect GitHub"**
3. Autorizza Emergent ad accedere ai tuoi repository GitHub

### 1.2 Esporta il codice
1. Nella chat di Emergent, trova il pulsante **"Save to GitHub"**
2. Seleziona il branch (es. `main`)
3. Clicca **"PUSH TO GITHUB"**
4. Attendi conferma dell'export (30-60 secondi)

✅ **Risultato:** Il codice completo è ora sul tuo GitHub!

---

## 🚂 Passo 2: Setup Railway

### 2.1 Crea account Railway
1. Vai su [https://railway.app](https://railway.app)
2. Clicca **"Login with GitHub"**
3. Autorizza Railway

### 2.2 Crea nuovo progetto
1. Click **"New Project"**
2. Seleziona **"Deploy from GitHub repo"**
3. Trova e seleziona **neonobleramp** (o il nome del tuo repo)
4. Railway inizierà il deployment automatico

### 2.3 Configura Region EU (IMPORTANTE!)
1. Vai su **Project Settings** (⚙️ in alto a destra)
2. Cerca **"Region"**
3. Seleziona **"Europe West (eu-west-1)"**
4. Salva le modifiche
5. **Rideploy** il progetto per applicare la nuova region

---

## ⚙️ Passo 3: Configura Variabili d'Ambiente

### 3.1 Accedi alle Variables
1. Nel tuo progetto Railway, vai su **"Variables"** tab
2. Clicca **"Raw Editor"** per inserire tutte le variabili insieme

### 3.2 Copia e incolla queste variabili

```env
# MongoDB
MONGO_URL=mongodb+srv://<user>:<password>@cluster.mongodb.net/neonobleramp
DB_NAME=neonobleramp

# Backend
JWT_SECRET=<genera_un_secret_casuale_qui>
PORT=8001

# Frontend
REACT_APP_BACKEND_URL=https://your-backend.up.railway.app

# Market Maker
NENO_PRICE_EUR=10000
MARKET_MAKER_ENABLED=true
CEX_FALLBACK_ENABLED=true

# Binance (con permessi withdrawal)
BINANCE_API_KEY=ejcUlNhrKcT8exTK8cKBgV1zTCevFVQi2lLYk3q8QzPDNvcdyf2xPkEkKMYDmFh2
BINANCE_API_SECRET=ejcUlNhrKcT8exTK8cKBgV1zTCevFVQi2lLYk3q8QzPDNvcdyf2xPkEkKMYDmFh2
BINANCE_TESTNET=false

# MEXC
MEXC_API_KEY=7a5c421154154a7f8ce050562490f499
MEXC_API_SECRET=z5LOgApbiFiuzPjvWHrcgmqr0DbezyyGsUp5mAMgUnbNgzSAvhBGfqC9dvv3hhIU

# Kraken
KRAKEN_API_KEY=6KT2QOXodt3BVl9e1IkH7kQ0EwM8X35T8N9qJFrexk4izFY0kH/903O8
KRAKEN_API_SECRET=gvFA2y9siWdkpFp1YonZ1BlI+/p8diY8SNR+1PedGiKttWxsPj5CDPjMg7COPfLCO6YInNQ/W7zXA6zgj+/CCQ==

# Coinbase
COINBASE_API_KEY=sto-deployment-full
COINBASE_API_SECRET=rJFA5mRjeCwq7E/hQvGQSqXOEh1i71FrGkYps+QB6yB0K/ngruxj0VNRDqqNqnvkvFWSF51SX7spXtt3jxmFqQ==

# RPC Endpoints
BSC_RPC_URL=https://bsc-dataseed1.binance.org
ETHEREUM_RPC_URL=https://eth-mainnet.g.alchemy.com/v2/DcratgiD511rxPvR-RI3pSSDVMvXDAIi
POLYGON_RPC_URL=https://polygon-mainnet.g.alchemy.com/v2/DcratgiD511rxPvR-RI3pSSDVMvXDAIi
ARBITRUM_RPC_URL=https://arb-mainnet.g.alchemy.com/v2/DcratgiD511rxPvR-RI3pSSDVMvXDAIi
BASE_RPC_URL=https://base-mainnet.g.alchemy.com/v2/DcratgiD511rxPvR-RI3pSSDVMvXDAIi
```

### 3.3 Genera JWT Secret
Usa questo comando per generare un secret sicuro:
```bash
openssl rand -base64 32
```
O usa un generatore online: https://generate-secret.vercel.app

---

## 💾 Passo 4: Setup MongoDB

### Opzione A: MongoDB Atlas (Consigliato)
1. Vai su [https://www.mongodb.com/cloud/atlas](https://www.mongodb.com/cloud/atlas)
2. Crea un **cluster gratuito** in region **EU**
3. Crea database user e password
4. **Whitelist IP:** Aggiungi `0.0.0.0/0` (permetti tutti gli IP)
5. Copia la **connection string**
6. Sostituisci `<password>` con la tua password
7. Incolla in `MONGO_URL` su Railway

### Opzione B: Railway MongoDB Plugin
1. Nel progetto Railway, clicca **"+ New"**
2. Seleziona **"MongoDB"**
3. Railway creerà automaticamente il database
4. Copia `MONGO_URL` generato automaticamente
5. Incollalo nelle variables del backend

---

## 🌐 Passo 5: Configura Networking

### 5.1 Abilita Public Networking
1. Per ogni servizio (backend/frontend), vai su **Settings**
2. Trova **"Networking"**
3. Clicca **"Generate Domain"**
4. Copia l'URL generato

### 5.2 Aggiorna REACT_APP_BACKEND_URL
1. Copia l'URL del **backend** (es. `https://neonobleramp-backend.up.railway.app`)
2. Vai su **Variables** del **frontend**
3. Aggiorna `REACT_APP_BACKEND_URL` con l'URL del backend
4. Salva e attendi il redeploy

---

## ✅ Passo 6: Verifica Deployment

### 6.1 Test Backend
Apri nel browser:
```
https://your-backend.up.railway.app/api/swap/hybrid/health
```

Dovresti vedere:
```json
{
  "mode": "hybrid_simplified",
  "market_maker_enabled": true,
  "neno_price_eur": 10000.0,
  "status": "operational"
}
```

### 6.2 Test Frontend
Apri:
```
https://your-frontend.up.railway.app
```

Dovresti vedere la homepage di NeoNoble Ramp.

### 6.3 Test NENO Swap con Binance Reale
1. Fai login nell'app
2. Vai su `/swap`
3. Inserisci 1 NENO → USDT
4. Clicca "Swap"
5. **Controlla i logs del backend su Railway**
6. Dovresti vedere: `✅ Binance withdrawal successful` (non più geo-restriction!)

---

## 🎯 Risultato Atteso

Con deployment in **EU region**, Binance funzionerà senza geo-restriction:

```
✅ Binance exchange loaded
✅ Attempting withdrawal from Binance...
✅ Binance withdrawal successful!
✅ TX Hash: 0xabc123...
✅ Tokens will arrive in 5-30 minutes
```

---

## 🐛 Troubleshooting

### Problema: Binance ancora geo-restricted
**Soluzione:**
- Verifica che la region del progetto Railway sia **EU West**
- Vai su Project Settings → Region
- Se necessario, cambia region e rideploy

### Problema: MongoDB connection failed
**Soluzione:**
- Verifica connection string in `MONGO_URL`
- Controlla che IP `0.0.0.0/0` sia whitelisted su MongoDB Atlas
- Test connection string localmente con `mongosh`

### Problema: Frontend non si connette al backend
**Soluzione:**
- Verifica che `REACT_APP_BACKEND_URL` punti all'URL corretto del backend
- Controlla CORS settings nel backend
- Verifica che entrambi i servizi abbiano public domain

### Problema: Environment variables non caricate
**Soluzione:**
- Riavvia il servizio dopo aver modificato le variables
- Controlla che non ci siano caratteri speciali non escaped
- Usa "Raw Editor" invece di aggiungere una per una

---

## 📞 Supporto

- **Railway Docs:** https://docs.railway.app
- **Railway Discord:** https://discord.gg/railway
- **MongoDB Atlas Support:** https://www.mongodb.com/support

---

## 🚀 Next Steps Dopo Deployment

1. **Custom Domain:** Aggiungi dominio personalizzato (es. `neonobleramp.com`)
2. **SSL Certificate:** Railway gestisce automaticamente
3. **Monitoring:** Abilita logs e metrics su Railway dashboard
4. **Backup Database:** Setup backup automatici MongoDB
5. **Scaling:** Railway scala automaticamente in base al traffico

---

## 🎉 Congratulazioni!

Hai deployato con successo **NeoNoble Ramp** in production su Railway EU!

Ora il sistema supporta:
- ✅ Swap NENO @ 10.000€
- ✅ Withdrawal reali da Binance (no geo-restriction)
- ✅ Multi-chain support (BSC, ETH, Polygon, Arbitrum, Base)
- ✅ CEX liquidity (Binance, MEXC, Kraken, Coinbase)
- ✅ Production-ready architecture

**Happy swapping! 🎯**
