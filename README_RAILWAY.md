# NeoNoble Ramp - Crypto Trading Platform

## 🏗️ Architecture

This is a **monorepo** containing:

### **Backend** (`/backend`)
- **Tech:** Python FastAPI
- **Features:** Hybrid Swap Engine (DEX + Market Maker + CEX Fallback)
- **Deploy:** Railway EU (Python/Nixpacks)
- **Start:** `uvicorn server:app --host 0.0.0.0 --port $PORT`

### **Frontend** (`/frontend`)
- **Tech:** React (Create React App)
- **Features:** Swap UI, Wallet Connection, Market Maker Interface
- **Deploy:** Railway EU (Node.js/Nixpacks)
- **Start:** `yarn start`

---

## 🚀 Railway Deployment

### **Automatic Detection:**
Railway should automatically detect 2 services:
1. **Backend** (Python in `/backend`)
2. **Frontend** (React in `/frontend`)

### **Manual Setup:**
If auto-detection fails:

#### **Backend Service:**
- **Root Directory:** `/backend`
- **Builder:** Nixpacks
- **Start Command:** `uvicorn server:app --host 0.0.0.0 --port $PORT`
- **Region:** Europe West (eu-west-1)

#### **Frontend Service:**
- **Root Directory:** `/frontend`
- **Builder:** Nixpacks
- **Start Command:** `yarn start`
- **Region:** Europe West (eu-west-1)

---

## ⚠️ Important Notes

- **DO NOT use Dockerfile** (obsolete, use Nixpacks)
- **Root directory** contains only config files
- **Actual services** are in `/backend` and `/frontend`
- **Railway must deploy each service separately** with correct root directory

---

## 📄 Documentation

See `/GUIDA_RAILWAY_DEFINITIVA.md` for complete deployment guide (Italian).
