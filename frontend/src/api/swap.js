/**
 * NeoNoble Swap API client.
 * Talks to the /api/swap/* endpoints.
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
  execute: async ({ fromToken, toToken, amountIn, userWalletAddress, slippage }) => {
    const { data } = await swap.post('/execute', {
      from_token: fromToken,
      to_token: toToken,
      amount_in: amountIn,
      user_wallet_address: userWalletAddress,
      ...(slippage ? { slippage } : {}),
    });
    return data;
  },
  history: async (limit = 50) => (await swap.get(`/history?limit=${limit}`)).data,
};

export default swapApi;
