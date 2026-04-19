# 🚀 GUIDA POST-DEPLOYMENT - NEONOBLE RAMP

## 📍 URL DI PRODUZIONE

Una volta completato il deployment su Railway, avrai **2 URL pubblici**:

### **Frontend URL** (ancora da ottenere da Railway)
```
https://[il-tuo-dominio-railway].railway.app
```

### **Backend URL** (ancora da ottenere da Railway)
```
https://[il-tuo-backend-railway].railway.app
```

> **IMPORTANTE:** Railway genera automaticamente gli URL dopo il deployment. Li trovi su:
> - Railway Dashboard → Seleziona il servizio → Tab "Settings" → Sezione "Domains"

---

## ⚙️ STEP 1: CONFIGURAZIONE VARIABILI D'AMBIENTE SU RAILWAY

### **1.1 Configurazione Backend**

Vai su **Railway Dashboard → Backend Service → Variables** e aggiungi:

#### **Obbligatorie:**
```
MONGO_URL=mongodb://[tuo-mongodb-url]
DB_NAME=neonoble_ramp
```

**Opzioni per MongoDB:**
- **Opzione A:** Usa Railway MongoDB Plugin (consigliato)
  - Vai su Railway → Add New → Database → MongoDB
  - Railway creerà automaticamente la variabile `MONGOURL`
  - Il backend la leggerà automaticamente

- **Opzione B:** Usa MongoDB Atlas (gratuito)
  - Vai su https://www.mongodb.com/cloud/atlas
  - Crea un cluster gratuito
  - Ottieni la connection string
  - Aggiungi `MONGO_URL` su Railway

#### **Raccomandate (per funzionalità complete):**
```
API_SECRET_ENCRYPTION_KEY=[genera una stringa casuale lunga]
BSC_RPC_URL=https://bsc-dataseed.binance.org/
STRIPE_SECRET_KEY=[tua Stripe key per pagamenti]
CIRCLE_API_KEY=[tua Circle key per USDC]
```

#### **Opzionali (per liquidità CEX):**
```
BINANCE_API_KEY=[tua key]
BINANCE_API_SECRET=[tuo secret]
MEXC_API_KEY=[tua key]
MEXC_API_SECRET=[tuo secret]
ONEINCH_API_KEY=[tua key 1inch]
```

### **1.2 Configurazione Frontend**

Vai su **Railway Dashboard → Frontend Service → Variables** e aggiungi:

```
REACT_APP_BACKEND_URL=https://[il-tuo-backend-railway].railway.app
```

> **NOTA:** Sostituisci `[il-tuo-backend-railway]` con l'URL effettivo del backend che trovi su Railway

---

## 🔐 STEP 2: PRIMO ACCESSO E CONFIGURAZIONE

### **2.1 Accedi come Admin**

Una volta deployato il frontend, vai su:
```
https://[il-tuo-dominio-railway].railway.app
```

**Credenziali Admin di default:**
```
Email: admin@neonobleramp.com
Password: Admin123!
```

### **2.2 Verifica Dashboard Admin**

Dopo il login come admin, avrai accesso a:
- ✅ **Pipeline Autonomo** - Gestione fondi e payout automatici
- ✅ **Growth Dashboard** - Analytics utenti e revenue
- ✅ **Card Monetization Engine** - Metriche carte virtuali
- ✅ **Revenue Cashout** - Prelievi revenue in crypto o SEPA
- ✅ **Stripe Balance Management** - Gestione balance Stripe

---

## 👥 STEP 3: ACCESSO UTENTI NORMALI

### **3.1 Registrazione Nuovo Utente**

Gli utenti possono:
1. Andare su `https://[il-tuo-dominio-railway].railway.app`
2. Cliccare su **"Get Started"** o **"Register"**
3. Compilare il form di registrazione:
   - Email
   - Password
   - Nome completo
4. Confermare l'account (se hai configurato email verification)

### **3.2 Utente di Test (già esistente)**

Puoi usare questo account di test:
```
Email: test@example.com
Password: Test1234!
```

---

## 💰 STEP 4: UTILIZZO DELLA PIATTAFORMA

### **4.1 Funzionalità Principali per Utenti**

#### **A) Swap Crypto (Hybrid Engine)**
1. Connetti wallet MetaMask o Coinbase
2. Vai su **"Swap"** nella navbar
3. Seleziona token FROM e TO
4. Inserisci l'importo
5. Clicca **"Get Quote"** per vedere il prezzo
6. Clicca **"Swap"** per eseguire
7. Conferma la transazione nel wallet

**Modalità supportate:**
- 🔵 **DEX Routing** (1inch → PancakeSwap)
- 🟢 **Market Maker** (NENO @ 10,000€ fixed)
- 🔴 **CEX Fallback** (Binance, MEXC, Kraken, Coinbase)

#### **B) Buy/Sell con EUR**
1. Vai su **"Ramp"**
2. Scegli **"Buy"** o **"Sell"**
3. Inserisci l'importo in EUR
4. Seleziona il token crypto
5. Conferma l'operazione
6. Completa il pagamento (Stripe o bonifico)

#### **C) Carte Virtuali (Card Engine)**
1. Vai su **"Cards"**
2. Clicca **"Create New Card"**
3. Scegli il tipo:
   - Single-use (usa e getta)
   - Multi-use (riutilizzabile)
4. Carica fondi sulla carta
5. Usa la carta per acquisti online

#### **D) Wallet & History**
1. Vai su **"Wallet"** per vedere:
   - Balance crypto
   - Balance EUR
   - Indirizzi di deposito
2. Vai su **"History"** per vedere:
   - Swap eseguiti
   - Transazioni ramp
   - Carte create

---

## 🔧 STEP 5: FUNZIONALITÀ AVANZATE (Solo Admin)

### **5.1 Pipeline Autonomo**

**Dashboard:** `/admin` → Tab "Pipeline Autonomo"

**Funzioni:**
- **Auto-Fund:** Ricarica automatica degli hot wallet
- **Auto-Payout Check:** Verifica e processa payout automatici
- **Status Monitoring:** Monitoraggio real-time del pipeline

**Come usare:**
1. Vai su Admin Dashboard
2. Clicca su tab **"Pipeline Autonomo"**
3. Visualizza lo status corrente
4. Clicca **"Trigger Auto-Fund"** per ricaricare wallet
5. Clicca **"Trigger Auto-Payout"** per processare payout

### **5.2 Revenue Cashout**

**Dashboard:** `/admin` → Tab "Revenue Cashout"

**Funzioni:**
- **Crypto Withdrawal:** Preleva revenue in USDT/BTC/ETH
- **SEPA Payout:** Preleva revenue tramite bonifico bancario
- **History:** Storico di tutti i prelievi

**Come prelevare in Crypto:**
1. Inserisci l'importo in EUR
2. Seleziona **"Crypto"** come destination
3. Inserisci il wallet address
4. Clicca **"Withdraw Revenue"**
5. Conferma la transazione

**Come prelevare via SEPA:**
1. Inserisci l'importo in EUR
2. Seleziona **"SEPA"** come destination
3. Inserisci IBAN e nome beneficiario
4. Clicca **"Withdraw Revenue"**
5. Il bonifico sarà processato entro 1-2 giorni lavorativi

### **5.3 Stripe Balance Management**

**Dashboard:** `/admin` → Tab "Stripe Balance"

**Funzioni:**
- **Top-up Stripe:** Ricarica il balance Stripe per payout
- **SEPA Payout from Stripe:** Preleva fondi da Stripe a conto bancario
- **Balance Monitoring:** Visualizza balance Stripe real-time

### **5.4 Growth & Analytics**

**Dashboard:** `/admin` → Tab "Growth Dashboard"

**Metriche disponibili:**
- **User Funnel:** Conversione da registrazione a primo swap
- **Retention:** Tasso di ritorno utenti
- **ARPU:** Revenue medio per utente
- **Daily Revenue:** Grafico revenue giornaliero ultimi 7 giorni

---

## 🎯 STEP 6: CONFIGURAZIONE AVANZATA (Opzionale)

### **6.1 Configurare Liquidità CEX**

Per abilitare il fallback CEX nel Hybrid Swap Engine:

1. **Ottieni API Keys dagli exchange:**
   - Binance: https://www.binance.com/en/support/faq/how-to-create-api-360002502072
   - MEXC: https://www.mexc.com/user/openapi
   - Kraken: https://support.kraken.com/hc/en-us/articles/360000919966
   - Coinbase: https://www.coinbase.com/settings/api

2. **Aggiungi le keys su Railway Backend Variables:**
   ```
   BINANCE_API_KEY=...
   BINANCE_API_SECRET=...
   MEXC_API_KEY=...
   MEXC_API_SECRET=...
   ```

3. **Testa il fallback CEX:**
   - Vai su Swap
   - Prova uno swap di grandi dimensioni (>10,000€)
   - Il sistema userà automaticamente CEX se DEX non ha liquidità

### **6.2 Configurare 1inch Aggregator**

Per abilitare il routing DEX ottimizzato:

1. Vai su https://portal.1inch.dev/
2. Registrati e ottieni un API key
3. Aggiungi su Railway Backend Variables:
   ```
   ONEINCH_API_KEY=your_key_here
   ```

### **6.3 Configurare Stripe (per Ramp EUR)**

Per abilitare pagamenti con carta e SEPA:

1. Vai su https://dashboard.stripe.com/register
2. Completa la registrazione e verifica l'account
3. Ottieni le API keys (Test e Live)
4. Aggiungi su Railway Backend Variables:
   ```
   STRIPE_SECRET_KEY=sk_live_...
   ```

### **6.4 Configurare Circle USDC**

Per abilitare USDC stablecoin payments:

1. Vai su https://www.circle.com/en/circle-account
2. Registrati per un Circle Account
3. Ottieni le API keys
4. Aggiungi su Railway Backend Variables:
   ```
   CIRCLE_API_KEY=your_key_here
   ```

---

## 📊 STEP 7: MONITORING E MANUTENZIONE

### **7.1 Controllare i Log su Railway**

1. Vai su Railway Dashboard
2. Seleziona il servizio (Frontend o Backend)
3. Clicca su **"View Logs"**
4. Filtra per:
   - ✅ Info logs (operazioni normali)
   - ⚠️ Warning logs (attenzione richiesta)
   - ❌ Error logs (problemi da risolvere)

### **7.2 Metriche da Monitorare**

**Backend:**
- ✅ Healthcheck status (deve essere "healthy")
- ✅ Response time API (<500ms ideale)
- ✅ Database connections (stabile)
- ⚠️ Error rate (<1% ideale)

**Frontend:**
- ✅ Page load time (<3s ideale)
- ✅ Build size (<5MB ideale)
- ✅ User sessions (crescente)

### **7.3 Backup Database**

**Importante:** Configura backup automatici MongoDB:

**Se usi Railway MongoDB Plugin:**
- Railway fa backup automatici ogni 24h
- Retention: 7 giorni

**Se usi MongoDB Atlas:**
- Vai su Atlas Dashboard → Backup
- Configura backup automatici
- Scegli retention policy (gratuito: 2 giorni)

---

## 🆘 TROUBLESHOOTING COMUNE

### **Problema 1: "Backend connection failed"**

**Causa:** Frontend non raggiunge il backend

**Soluzione:**
1. Verifica che `REACT_APP_BACKEND_URL` sia configurato correttamente
2. Controlla che il backend sia "Active" su Railway
3. Testa il backend direttamente: `curl https://[backend-url]/api/health`

### **Problema 2: "Database connection error"**

**Causa:** MongoDB non configurato o non raggiungibile

**Soluzione:**
1. Verifica `MONGO_URL` su Railway Backend Variables
2. Controlla che MongoDB sia attivo (Railway Plugin o Atlas)
3. Testa la connessione dal backend logs

### **Problema 3: "Swap failed - No liquidity"**

**Causa:** Nessuna liquidità disponibile (DEX, Market Maker, CEX)

**Soluzione:**
1. Verifica che almeno un'opzione di liquidità sia configurata:
   - **DEX:** Funziona sempre (PancakeSwap BSC)
   - **Market Maker:** Funziona solo per NENO token
   - **CEX:** Richiede API keys configurate
2. Prova con un importo più piccolo
3. Controlla i log backend per errori specifici

### **Problema 4: "Payment failed - Stripe"**

**Causa:** Stripe non configurato o chiavi sbagliate

**Soluzione:**
1. Verifica `STRIPE_SECRET_KEY` su Railway
2. Assicurati di usare chiavi **Live** (non Test) in produzione
3. Controlla il Stripe Dashboard per errori

---

## 🎉 RIEPILOGO: COME INIZIARE SUBITO

### **Per Te (Owner/Admin):**
1. ✅ Fai il deployment su Railway
2. ✅ Configura `MONGO_URL` (minimo richiesto)
3. ✅ Ottieni gli URL Railway (Frontend + Backend)
4. ✅ Aggiorna `REACT_APP_BACKEND_URL` nel frontend
5. ✅ Accedi con `admin@neonobleramp.com` / `Admin123!`
6. ✅ Esplora la dashboard admin e testa le funzionalità

### **Per gli Utenti:**
1. ✅ Vanno su `https://[tuo-frontend-url].railway.app`
2. ✅ Si registrano con email e password
3. ✅ Connettono il wallet (MetaMask/Coinbase)
4. ✅ Iniziano a fare swap, buy/sell, creare carte

### **Funzionalità Disponibili da Subito (anche senza configurazioni avanzate):**
- ✅ **Swap DEX** (via PancakeSwap BSC) - **FUNZIONA SEMPRE**
- ✅ **Market Maker NENO** (prezzo fisso 10,000€) - **FUNZIONA SEMPRE**
- ✅ **User Authentication** (JWT) - **FUNZIONA SEMPRE**
- ✅ **Wallet Management** - **FUNZIONA SEMPRE**
- ✅ **Transaction History** - **FUNZIONA SEMPRE**

### **Funzionalità che Richiedono Configurazione Aggiuntiva:**
- 🔒 **CEX Fallback** → Richiede API keys Binance/MEXC/etc
- 🔒 **Ramp EUR** → Richiede Stripe API key
- 🔒 **Circle USDC** → Richiede Circle API key
- 🔒 **Carte Virtuali** → Richiede Stripe + Circle

---

## 📞 SUPPORTO

Se hai problemi o domande:
1. Controlla i **log Railway** per errori specifici
2. Verifica che tutte le **variabili d'ambiente** siano configurate
3. Consulta questa guida per troubleshooting

**Buon deployment! 🚀**
