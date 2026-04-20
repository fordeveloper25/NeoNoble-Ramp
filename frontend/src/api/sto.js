import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const BASE = `${BACKEND_URL}/api/sto`;

const api = axios.create({
  baseURL: BASE,
  headers: { 'Content-Type': 'application/json' },
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

export const stoApi = {
  health: async () => (await api.get('/health')).data,
  publicInfo: async () => (await api.get('/public-info')).data,
  lead: async (payload) => (await api.post('/lead', payload)).data,

  kycSubmit: async (payload) => (await api.post('/kyc/submit', payload)).data,
  kycStatus: async () => (await api.get('/kyc/status')).data,

  portfolio: async (wallet) => (await api.get(`/portfolio?wallet=${wallet}`)).data,
  buildRedemption: async (payload) => (await api.post('/redemption/request', payload)).data,
  buildRevClaim: async (payload) => (await api.post('/revenue/claim-build', payload)).data,

  adminLeads: async () => (await api.get('/admin/leads')).data,
};

export default stoApi;
