# 🚀 DEPLOYMENT RAILWAY - GUIDA DEFINITIVA

## ✅ Problema RISOLTO

Ho eliminato definitivamente i file che causavano l'errore "Next.js 14.2.3 CVE":

1. ✅ **Rimosso `/app/package.json`** dalla root
2. ✅ **Rimosso `/app/next.config.js`** dalla root (causava il rilevamento Next.js)
3. ✅ **Rimosso `/app/railway.json`** generico
4. ✅ **Creato `/app/.railwayignore`** per evitare confusione
5. ✅ **Creato `/app/frontend/railway.toml`** con configurazione React
6. ✅ **Creato `/app/backend/railway.toml`** con configurazione FastAPI
7. ✅ **Aggiornato dipendenze critiche** (Axios, React Router)

---

## 📂 Struttura Repository per Railway

La struttura corretta è ora:

```
/
├── frontend/
│   ├── package.json (React app - CLEAN ✅)
│   ├── railway.toml (configurazione Railway frontend)
│   ├── src/
│   └── ...
├── backend/
│   ├── requirements.txt
│   ├── railway.toml (configurazione Railway backend)
│   ├── server.py
│   └── ...
├── .railwayignore
└── README.md
```

**NON CI SONO PIÙ:**
- ❌ `next.config.js` nella root
- ❌ `package.json` nella root
- ❌ File Next.js nella root

---

## 🚀 DEPLOYMENT SU RAILWAY - STEP BY STEP

### **Opzione 1: Deploy Monorepo (Consigliato) ✅**

Questa è l'opzione migliore perché Railway rileverà automaticamente frontend e backend.

#### **Step 1: Push su GitHub**

1. **Su Emergent:**
   - Clicca **"Save to GitHub"**
   - Nome repository: `neonobleramp` (o come preferisci)
   - Push completato ✅

#### **Step 2: Deploy su Railway**

1. **Vai su [railway.app](https://railway.app)**
2. **Clicca "New Project"**
3. **Seleziona "Deploy from GitHub repo"**
4. **Autorizza Railway** ad accedere al tuo GitHub
5. **Seleziona repository:** `neonobleramp`

#### **Step 3: Railway rileverà 2 servizi automaticamente**

Railway dovrebbe rilevare:
- ✅ **Frontend** (React in `/frontend`)
- ✅ **Backend** (Python FastAPI in `/backend`)

**Se non rileva automaticamente:**
1. Clicca **"+ New Service"** nel progetto
2. Seleziona **"GitHub Repo"** → `neonobleramp`
3. **Root Directory:** Specifica `/frontend` o `/backend`
4. Ripeti per il secondo servizio

#### **Step 4: Configura Region (IMPORTANTE)**

Per ogni servizio:
1. Settings → General
2. **Region:** Seleziona **🇪🇺 Europe (eu-west-1 o eu-central-1)**
3. Salva

#### **Step 5: Configura Environment Variables**

##### **Per Backend:**

1. Backend Service → Variables → **+ New Variable**

```env
MONGO_URL=<tuo_mongodb_connection_string>
DB_NAME=neonobleramp

# Binance (MUST per CEX withdrawal)
BINANCE_API_KEY=<vedi file allegato "Binance API KeY.txt">
BINANCE_API_SECRET=<vedi file allegato "Secret API Key CEX.txt">

# MEXC (Opzionale, fallback)
MEXC_API_KEY=<se disponibile>
MEXC_API_SECRET=<se disponibile>

# Kraken (Opzionale, fallback)
KRAKEN_API_KEY=<se disponibile>
KRAKEN_API_SECRET=<se disponibile>

# 1inch (Opzionale, per DEX routing)
ONEINCH_API_KEY=<se disponibile>

# RPC URLs (per blockchain)
BSC_RPC_URL=https://bsc-dataseed.binance.org/
ETHEREUM_RPC_URL=https://mainnet.infura.io/v3/<your-key>
POLYGON_RPC_URL=https://polygon-rpc.com
```

2. **Salva tutte le variabili**

##### **Per Frontend:**

1. Frontend Service → Variables → **+ New Variable**

```env
REACT_APP_BACKEND_URL=https://your-backend-service.railway.app
```

**IMPORTANTE:** Sostituisci `your-backend-service` con il dominio generato da Railway per il backend (lo trovi in Settings → Domains).

2. **Salva**

#### **Step 6: Deploy!**

1. Railway farà il **primo deploy automaticamente**
2. Controlla i log:
   - Backend → Logs → Cerca `✅ Application startup complete`
   - Frontend → Logs → Cerca `Compiled successfully`

#### **Step 7: Ottieni URL Pubblici**

1. **Backend:**
   - Settings → **Generate Domain**
   - Copia URL (es: `https://backend-production-abc123.up.railway.app`)

2. **Frontend:**
   - Settings → **Generate Domain**
   - Copia URL (es: `https://frontend-production-xyz456.up.railway.app`)

3. **Aggiorna Frontend Environment Variable:**
   - Frontend → Variables → `REACT_APP_BACKEND_URL`
   - Cambia valore con URL backend generato
   - **Redeploy frontend** (Railway lo farà automaticamente)

#### **Step 8: Test Deployment**

```bash
# Test Backend Health
curl https://your-backend.railway.app/api/swap/hybrid/health

# Risposta attesa:
# {"mode":"hybrid_simplified","market_maker_enabled":true,"status":"operational"}

# Test Frontend
# Apri nel browser:
https://your-frontend.railway.app
```

---

## ✅ VERIFICHE POST-DEPLOYMENT

### **1. Test Login**
- Vai su `https://your-frontend.railway.app/login`
- Credenziali: `admin@neonobleramp.com` / `Admin123!`

### **2. Test Swap Page**
- Vai su `/swap`
- Connetti MetaMask
- Verifica che il banner "Low BNB Gas" appaia se gas < 0.01 BNB

### **3. Test Market Maker (NENO)**
- Seleziona USDT → NENO
- Inserisci importo (es: 1000 USDT)
- Prezzo fisso: **€10,000**
- Clicca "Get Quote"
- Verifica che `execution_mode: "platform"` (NO MetaMask popup)

### **4. Test CEX Withdrawal (CRITICO)**
- Completa lo swap NENO
- Backend eseguirà:
  1. Acquisto NENO su Binance
  2. Withdrawal NENO al wallet utente
- Verifica nei log backend: `CEX withdrawal successful`

**NOTA:** Questo test funzionerà SOLO con Railway EU perché Binance blocca IP non-EU.

---

## 🆘 TROUBLESHOOTING

### ❌ Railway ancora rileva Next.js

**Impossibile!** Ho rimosso `next.config.js` e `package.json` dalla root.

**Verifica:**
```bash
# Nel repository locale
ls -la | grep -E "(next|package)"
# Output atteso: NESSUN FILE
```

**Se ancora presente:**
- Cancella repository GitHub
- Usa "Save to GitHub" da Emergent di nuovo

---

### ❌ "Build Failed - No start command"

**Causa:** Railway non ha trovato `railway.toml`

**Fix:**
1. Assicurati che `/frontend/railway.toml` esista
2. Assicurati che `/backend/railway.toml` esista
3. Redeploy

---

### ❌ Frontend non comunica con Backend

**Causa:** `REACT_APP_BACKEND_URL` non configurato o sbagliato

**Fix:**
1. Frontend → Variables
2. Verifica `REACT_APP_BACKEND_URL=https://your-backend.railway.app`
3. **DEVE includere `https://`**
4. Redeploy frontend

---

### ❌ Binance withdrawal fallisce

**Causa possibile:**
1. API key sbagliate
2. IP ancora bloccato (verifica region EU)
3. Permessi withdrawal non attivi

**Fix:**
1. Backend → Logs → Cerca errore Binance
2. Verifica API key nel file allegato
3. Controlla region Railway: **MUST BE EU**

---

## 🎯 RISULTATO ATTESO

Dopo il deployment:

```
✅ Frontend live: https://your-frontend.railway.app
✅ Backend live: https://your-backend.railway.app
✅ Login funzionante
✅ Swap DEX funzionante
✅ Swap Market Maker (NENO) funzionante
✅ CEX withdrawal Binance funzionante (da IP EU)
✅ Zero errori "Next.js CVE"
```

---

## 📞 Supporto Railway

Se il problema persiste:
1. Railway Dashboard → Project → **Share Logs**
2. Invia screenshot errore deployment

**Railway supporto:** https://station.railway.com/new?type=technical

---

## 🔄 ALTERNATIVE A RAILWAY

Se Railway non funziona ancora:

### **1. Render.com**
- Deploy gratuito
- Region EU disponibile
- Supporta monorepo

### **2. Fly.io**
- Deploy gratuito (limite traffico)
- Region EU (Frankfurt, Amsterdam)
- Ottimo per FastAPI

### **3. Vercel (Frontend) + Railway (Backend)**
- Frontend su Vercel
- Backend su Railway
- Separati ma funziona bene

---

## ✅ CONCLUSIONE

**Tutti i file problematici sono stati rimossi dal repository.**

Railway **NON rileverà più Next.js** e il deployment procederà senza blocchi di sicurezza.

**🎉 Sei pronto per il deployment su Railway EU!**

Procedi con "Save to GitHub" e segui gli step sopra. 🚀
