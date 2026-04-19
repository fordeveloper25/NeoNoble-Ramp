# NeoNoble Ramp - Production Deployment Guide

## 🚀 Deploy to Railway (EU Region)

### Prerequisites
- GitHub account
- Railway account (https://railway.app)
- API Keys (Binance, MEXC, Kraken, etc.)

### Step 1: GitHub Export (from Emergent)
1. Click your profile icon in Emergent
2. Connect GitHub account if not already connected
3. Click "Save to GitHub" button in the chat interface
4. Select branch (e.g., `main`)
5. Click "PUSH TO GITHUB"

### Step 2: Railway Setup
1. Go to https://railway.app
2. Sign up/Login with GitHub
3. Click "New Project"
4. Select "Deploy from GitHub repo"
5. Choose your NeoNoble Ramp repository
6. **IMPORTANT: Select EU West region in project settings**

### Step 3: Configure Environment Variables

Go to Railway project → Variables and add:

#### MongoDB
```
MONGO_URL=<your_mongodb_connection_string>
DB_NAME=neonobleramp
```

#### Backend API
```
JWT_SECRET=<generate_random_secret>
BACKEND_URL=https://your-app.railway.app
```

#### Binance (with withdrawal permissions)
```
BINANCE_API_KEY=ejcUlNhrKcT8exTK8cKBgV1zTCevFVQi2lLYk3q8QzPDNvcdyf2xPkEkKMYDmFh2
BINANCE_API_SECRET=ejcUlNhrKcT8exTK8cKBgV1zTCevFVQi2lLYk3q8QzPDNvcdyf2xPkEkKMYDmFh2
BINANCE_TESTNET=false
```

#### MEXC
```
MEXC_API_KEY=7a5c421154154a7f8ce050562490f499
MEXC_API_SECRET=z5LOgApbiFiuzPjvWHrcgmqr0DbezyyGsUp5mAMgUnbNgzSAvhBGfqC9dvv3hhIU
```

#### Kraken
```
KRAKEN_API_KEY=6KT2QOXodt3BVl9e1IkH7kQ0EwM8X35T8N9qJFrexk4izFY0kH/903O8
KRAKEN_API_SECRET=gvFA2y9siWdkpFp1YonZ1BlI+/p8diY8SNR+1PedGiKttWxsPj5CDPjMg7COPfLCO6YInNQ/W7zXA6zgj+/CCQ==
```

#### Coinbase
```
COINBASE_API_KEY=abc81dfd-4cea-428f-aa2f-373cb439b08f
COINBASE_API_SECRET=rJFA5mRjeCwq7E/hQvGQSqXOEh1i71FrGkYps+QB6yB0K/ngruxj0VNRDqqNqnvkvFWSF51SX7spXtt3jxmFqQ==
```

#### Market Maker Settings
```
NENO_PRICE_EUR=10000
MARKET_MAKER_ENABLED=true
CEX_FALLBACK_ENABLED=true
```

#### RPC Endpoints (Multi-Chain)
```
BSC_RPC_URL=https://bsc-dataseed1.binance.org
ETHEREUM_RPC_URL=https://eth-mainnet.g.alchemy.com/v2/DcratgiD511rxPvR-RI3pSSDVMvXDAIi
POLYGON_RPC_URL=https://polygon-mainnet.g.alchemy.com/v2/DcratgiD511rxPvR-RI3pSSDVMvXDAIi
ARBITRUM_RPC_URL=https://arb-mainnet.g.alchemy.com/v2/DcratgiD511rxPvR-RI3pSSDVMvXDAIi
BASE_RPC_URL=https://base-mainnet.g.alchemy.com/v2/DcratgiD511rxPvR-RI3pSSDVMvXDAIi
```

### Step 4: Deploy Services

Railway will auto-detect:
- Backend: Python FastAPI (port 8001)
- Frontend: React (port 3000)

**Make sure to:**
1. Set `REACT_APP_BACKEND_URL` to your Railway backend URL
2. Enable public networking for both services
3. Set custom domains if needed

### Step 5: Database Setup

**Option A: Use Railway MongoDB**
1. Add MongoDB service in Railway
2. Copy connection string to `MONGO_URL`

**Option B: Use MongoDB Atlas**
1. Create cluster on MongoDB Atlas
2. Whitelist Railway IP addresses
3. Copy connection string

### Step 6: Verify Deployment

After deployment:
1. Check backend: `https://your-backend.railway.app/api/swap/hybrid/health`
2. Check frontend: `https://your-frontend.railway.app`
3. Test NENO swap with real Binance withdrawal

### 🎯 Expected Result

With EU deployment:
- ✅ Binance API will work (no geo-restriction)
- ✅ Real withdrawals will execute
- ✅ Tokens delivered to user wallet in 5-30 minutes
- ✅ Production-ready swap system

### 🆘 Troubleshooting

**Binance still geo-restricted?**
- Verify Railway project region is set to EU West
- Check in Railway dashboard → Settings → Region

**Environment variables not working?**
- Make sure there are no quotes around values
- Restart services after changing variables

**MongoDB connection failed?**
- Check connection string format
- Verify IP whitelist includes Railway IPs

### 📞 Support

- Railway docs: https://docs.railway.app
- Emergent support: support@emergent.sh
