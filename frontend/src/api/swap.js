/**
 * NeoNoble Swap API client (USER-SIGNED mode).
 */
import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const SWAP_BASE = `${BACKEND_URL}/api/swap`;

const swap = axios.create({
  baseURL: SWAP_BASE,
  headers: { 'Content-Type': 'application/json' },
});

swap.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

export const swapApi = {
  // Standard endpoints (DEX only)
  health: async () => (await swap.get('/health')).data,
  tokens: async () => (await swap.get('/tokens')).data,
  quote: async (fromToken, toToken, amountIn) => {
    const { data } = await swap.post('/quote', {
      from_token: fromToken,
      to_token: toToken,
      amount_in: amountIn,
    });
    return data;
  },
  build: async ({ fromToken, toToken, amountIn, userWalletAddress, slippage }) => {
    const { data } = await swap.post('/build', {
      from_token: fromToken,
      to_token: toToken,
      amount_in: amountIn,
      user_wallet_address: userWalletAddress,
      ...(slippage != null ? { slippage: Number(slippage) } : {}),
    });
    return data;
  },
  track: async (swapId, txHash) => {
    const { data } = await swap.post('/track', { swap_id: swapId, tx_hash: txHash });
    return data;
  },
  history: async (limit = 50) => (await swap.get(`/history?limit=${limit}`)).data,
  
  // HYBRID endpoints (DEX → Market Maker → CEX Fallback)
  hybrid: {
    health: async () => (await swap.get('/hybrid/health')).data,
    quote: async (fromToken, toToken, amountIn) => {
      const { data } = await swap.post('/hybrid/quote', {
        from_token: fromToken,
        to_token: toToken,
        amount_in: amountIn,
      });
      return data;
    },
    build: async ({ fromToken, toToken, amountIn, userWalletAddress, slippage }) => {
      const { data } = await swap.post('/hybrid/build', {
        from_token: fromToken,
        to_token: toToken,
        amount_in: amountIn,
        user_wallet_address: userWalletAddress,
        ...(slippage != null ? { slippage: Number(slippage) } : {}),
      });
      return data;
    },
  },
};

export default swapApi;
