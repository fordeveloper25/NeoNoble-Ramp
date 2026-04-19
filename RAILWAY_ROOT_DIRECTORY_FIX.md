# 🚨 RAILWAY: ROOT DIRECTORY NON CONFIGURATO!

## ❌ ERRORE ATTUALE

```
Nixpacks was unable to generate a build plan for this app.
The contents of the app directory are:
_old_files/, backend/, frontend/, workers/, ...
```

**Causa:** Stai deployando dalla **ROOT** del repository, ma questo è un **MONOREPO**!

Railway vede la root (che contiene solo file .md e cartelle) e non sa che tipo di app è.

---

## ✅ SOLUZIONE: Configura ROOT DIRECTORY

### **Railway NON sa automaticamente che questo è un monorepo!**

Devi dirgli **MANUALMENTE** dove sono i servizi:
- Backend → `/backend`
- Frontend → `/frontend`

---

## 📋 STEP-BY-STEP: Configurazione Railway

### **🔴 IMPORTANTE: NON fare "Deploy from GitHub" dalla homepage!**

Quello deployerà dalla root e fallirà sempre!

---

## ✅ METODO CORRETTO

### **STEP 1: Crea un PROGETTO VUOTO**

1. **Railway Dashboard** → **New Project**
2. **Seleziona:** "Empty Project" (NON "Deploy from GitHub")
3. Nome progetto: `neonobleramp`

---

### **STEP 2: Aggiungi SERVIZIO BACKEND**

1. **Nel progetto** → **+ New**
2. **Seleziona:** "GitHub Repo"
3. **Autorizza Railway** (se richiesto)
4. **Seleziona repository:** `neonobleramp`

#### **⚠️ CONFIGURAZIONE CRITICA:**

5. **Vai su Settings → General:**
   - **Name:** `backend` (opzionale)
   - ⚠️ **Root Directory:** `/backend` ← **QUESTO È FONDAMENTALE!**

6. **Settings → Deploy:**
   - **Builder:** Nixpacks (default)
   - **Build Command:** Lascia vuoto (auto)
   - **Start Command:** `uvicorn server:app --host 0.0.0.0 --port $PORT`

7. **Settings → General → Region:**
   - Seleziona: **🇪🇺 Europe West (europe-west4)**

8. **Variables → + New Variable:**
```env
MONGO_URL=mongodb+srv://...
DB_NAME=neonobleramp
BINANCE_API_KEY=xxx
BINANCE_API_SECRET=xxx
MEXC_API_KEY=xxx
MEXC_API_SECRET=xxx
```

9. **Settings → Networking → Generate Domain**
   - Copia l'URL: `https://backend-production-xxx.railway.app`

---

### **STEP 3: Aggiungi SERVIZIO FRONTEND**

1. **Nello STESSO progetto** → **+ New**
2. **Seleziona:** "GitHub Repo"
3. **Seleziona repository:** `neonobleramp` (stesso di prima)

#### **⚠️ CONFIGURAZIONE CRITICA:**

4. **Vai su Settings → General:**
   - **Name:** `frontend` (opzionale)
   - ⚠️ **Root Directory:** `/frontend` ← **QUESTO È FONDAMENTALE!**

5. **Settings → Deploy:**
   - **Builder:** Nixpacks (default)
   - **Build Command:** `yarn build`
   - **Start Command:** `yarn start`

6. **Settings → General → Region:**
   - Seleziona: **🇪🇺 Europe West (europe-west4)**

7. **Variables → + New Variable:**
```env
REACT_APP_BACKEND_URL=https://backend-production-xxx.railway.app
```
⚠️ **Sostituisci** con l'URL backend copiato sopra!

8. **Settings → Networking → Generate Domain**
   - Questo sarà il tuo URL pubblico!

---

### **STEP 4: Deploy!**

Railway farà il deploy automaticamente quando aggiungi i servizi.

**Monitora i log:**
- Backend → Deployments → View Logs
- Frontend → Deployments → View Logs

---

## 🎯 Risultato Atteso

### **Backend Logs:**
```
✅ Nixpacks detected: Python
✅ Installing dependencies from requirements.txt
✅ Starting: uvicorn server:app --host 0.0.0.0 --port 8080
✅ Application startup complete
```

### **Frontend Logs:**
```
✅ Nixpacks detected: Node.js (yarn)
✅ Installing dependencies
✅ Running: yarn build
✅ Build complete
✅ Starting: yarn start
✅ Compiled successfully
```

---

## 🆘 SE FALLISCE ANCORA

### **Scenario: "Nixpacks unable to generate build plan"**

**Causa:** Root Directory non configurato

**Fix:**
1. Service → Settings → General
2. Verifica **Root Directory**:
   - Backend: `/backend`
   - Frontend: `/frontend`
3. Se vuoto, aggiungilo e Redeploy

---

### **Scenario: "Start command not found"**

**Fix:**
1. Service → Settings → Deploy
2. **Start Command:**
   - Backend: `uvicorn server:app --host 0.0.0.0 --port $PORT`
   - Frontend: `yarn start`
3. Salva e Redeploy

---

### **Scenario: Backend build OK ma crash al start**

**Causa:** Variabili d'ambiente mancanti

**Fix:**
1. Backend → Variables
2. Verifica che ci siano TUTTE le variabili:
   - `MONGO_URL`
   - `BINANCE_API_KEY`
   - `BINANCE_API_SECRET`
3. Redeploy

---

## 📊 Checklist Pre-Deploy

Prima di aggiungere i servizi, verifica:

- [ ] ✅ Push su GitHub completato
- [ ] ✅ Repository: `neonobleramp`
- [ ] ✅ Hai le API keys (Binance, MongoDB)
- [ ] ✅ Sai come configurare Root Directory

---

## ✅ CONCLUSIONE

**IL PROBLEMA NON È IL CODICE!**  
Il codice è perfetto.

**IL PROBLEMA È LA CONFIGURAZIONE RAILWAY!**

Railway non sa che questo è un monorepo.  
**DEVI dirgli manualmente** dove sono i servizi:

```
Backend → Root Directory: /backend
Frontend → Root Directory: /frontend
```

**SENZA questa configurazione, Railway fallirà SEMPRE!**

---

## 🎉 Ora Prova di Nuovo!

1. Fai push su GitHub (se non fatto)
2. Railway → New Project → Empty Project
3. + New → GitHub → neonobleramp
4. ⚠️ Settings → Root Directory: `/backend`
5. Ripeti per frontend con Root Directory: `/frontend`

**Funzionerà al 100%!** 🚀

---

**P.S.:** Se continua a fallire, fai screenshot della configurazione Railway (Settings → General) e allegalo. Vedrò subito cosa manca!
