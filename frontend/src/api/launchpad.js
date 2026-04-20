/**
 * NeoNoble Launchpad API client.
 * Tutti gli endpoint sono user-signed: il backend ritorna solo calldata,
 * l'utente firma con MetaMask.
 */
import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const BASE = `${BACKEND_URL}/api/launchpad`;

const api = axios.create({
  baseURL: BASE,
  headers: { 'Content-Type': 'application/json' },
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

export const launchpadApi = {
  health: async () => (await api.get('/health')).data,
  config: async () => (await api.get('/config')).data,
  list: async (limit = 50, offset = 0) =>
    (await api.get(`/tokens?limit=${limit}&offset=${offset}`)).data,
  detail: async (address) => (await api.get(`/tokens/${address}`)).data,

  quoteBuy: async (tokenAddress, bnbIn) =>
    (await api.get(`/quote-buy?token=${tokenAddress}&bnb_in=${bnbIn}`)).data,
  quoteSell: async (tokenAddress, tokensIn) =>
    (await api.get(`/quote-sell?token=${tokenAddress}&tokens_in=${tokensIn}`)).data,

  buildCreate: async ({ name, symbol, metadataUri, userWalletAddress }) =>
    (await api.post('/build-create', {
      name,
      symbol,
      metadata_uri: metadataUri || '',
      user_wallet_address: userWalletAddress,
    })).data,

  buildBuy: async ({ tokenAddress, bnbIn, userWalletAddress, slippagePct = 3 }) =>
    (await api.post('/build-buy', {
      token_address: tokenAddress,
      bnb_in: bnbIn,
      user_wallet_address: userWalletAddress,
      slippage_pct: slippagePct,
    })).data,

  buildSell: async ({ tokenAddress, tokensIn, userWalletAddress, slippagePct = 3 }) =>
    (await api.post('/build-sell', {
      token_address: tokenAddress,
      tokens_in: tokensIn,
      user_wallet_address: userWalletAddress,
      slippage_pct: slippagePct,
    })).data,
};

export default launchpadApi;
