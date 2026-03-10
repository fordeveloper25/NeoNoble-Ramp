/**
 * Token Creation Page
 * Enterprise-grade token creation interface for NeoNoble Ramp
 */

import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import {
  Coins, ArrowLeft, Upload, Globe, FileText, 
  Twitter, Send, MessageCircle, Check, AlertCircle, Loader2
} from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || '';

const CHAINS = [
  { id: 'ethereum', name: 'Ethereum', icon: '⟠', color: '#627EEA' },
  { id: 'bsc', name: 'BNB Smart Chain', icon: '🔶', color: '#F3BA2F' },
  { id: 'polygon', name: 'Polygon', icon: '🟣', color: '#8247E5' },
  { id: 'arbitrum', name: 'Arbitrum', icon: '🔵', color: '#28A0F0' },
  { id: 'base', name: 'Base', icon: '🔷', color: '#0052FF' },
];

export default function TokenCreation() {
  const navigate = useNavigate();
  const { token } = useAuth();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  const [createdToken, setCreatedToken] = useState(null);

  const [formData, setFormData] = useState({
    name: '',
    symbol: '',
    description: '',
    total_supply: '',
    initial_price: '',
    chain: 'bsc',
    decimals: 18,
    logo_url: '',
    website_url: '',
    whitepaper_url: '',
    social_links: {
      twitter: '',
      telegram: '',
      discord: ''
    }
  });

  const handleChange = (e) => {
    const { name, value } = e.target;
    if (name.startsWith('social_')) {
      const socialKey = name.replace('social_', '');
      setFormData(prev => ({
        ...prev,
        social_links: { ...prev.social_links, [socialKey]: value }
      }));
    } else {
      setFormData(prev => ({ ...prev, [name]: value }));
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const payload = {
        ...formData,
        total_supply: parseFloat(formData.total_supply),
        initial_price: parseFloat(formData.initial_price),
        decimals: parseInt(formData.decimals),
      };

      const response = await fetch(`${BACKEND_URL}/api/tokens/create`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(payload)
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Errore nella creazione del token');
      }

      setCreatedToken(data);
      setSuccess(true);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  if (success && createdToken) {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center p-4">
        <div className="bg-gray-900 border border-gray-800 rounded-2xl p-8 max-w-md w-full text-center">
          <div className="w-16 h-16 bg-green-500/20 rounded-full flex items-center justify-center mx-auto mb-6">
            <Check className="w-8 h-8 text-green-400" />
          </div>
          <h2 className="text-2xl font-bold text-white mb-2">Token Creato!</h2>
          <p className="text-gray-400 mb-6">
            Il tuo token <span className="text-purple-400 font-bold">${createdToken.symbol}</span> è stato creato con successo ed è in attesa di approvazione.
          </p>
          
          <div className="bg-gray-800/50 rounded-xl p-4 mb-6 text-left">
            <div className="flex justify-between mb-2">
              <span className="text-gray-400">Nome</span>
              <span className="text-white">{createdToken.name}</span>
            </div>
            <div className="flex justify-between mb-2">
              <span className="text-gray-400">Simbolo</span>
              <span className="text-white">{createdToken.symbol}</span>
            </div>
            <div className="flex justify-between mb-2">
              <span className="text-gray-400">Supply</span>
              <span className="text-white">{createdToken.total_supply.toLocaleString()}</span>
            </div>
            <div className="flex justify-between mb-2">
              <span className="text-gray-400">Prezzo Iniziale</span>
              <span className="text-white">€{createdToken.initial_price}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Stato</span>
              <span className="text-yellow-400">In attesa di approvazione</span>
            </div>
          </div>

          <div className="bg-purple-500/10 border border-purple-500/30 rounded-lg p-4 mb-6">
            <p className="text-purple-300 text-sm">
              <strong>Fee di creazione:</strong> €{createdToken.creation_fee}
            </p>
            <p className="text-gray-400 text-xs mt-1">
              Il pagamento sarà richiesto dopo l'approvazione admin.
            </p>
          </div>

          <div className="flex gap-3">
            <button
              onClick={() => navigate('/dashboard')}
              className="flex-1 px-4 py-2 bg-gray-800 hover:bg-gray-700 text-white rounded-lg transition-colors"
            >
              Dashboard
            </button>
            <button
              onClick={() => navigate('/tokens/list')}
              className="flex-1 px-4 py-2 bg-purple-500 hover:bg-purple-600 text-white rounded-lg transition-colors"
            >
              I Miei Token
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-950">
      {/* Header */}
      <header className="border-b border-gray-800 bg-gray-900/50 backdrop-blur-lg sticky top-0 z-10">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center gap-4">
          <button
            onClick={() => navigate(-1)}
            className="p-2 hover:bg-gray-800 rounded-lg transition-colors"
          >
            <ArrowLeft className="w-5 h-5 text-gray-400" />
          </button>
          <div className="flex items-center gap-3">
            <div className="p-2 bg-purple-500/20 rounded-lg">
              <Coins className="w-6 h-6 text-purple-400" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-white">Crea Token</h1>
              <p className="text-gray-400 text-sm">Lancia il tuo token su NeoNoble Ramp</p>
            </div>
          </div>
        </div>
      </header>

      {/* Form */}
      <main className="max-w-4xl mx-auto px-4 py-8">
        <form onSubmit={handleSubmit} className="space-y-8">
          {error && (
            <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 flex items-center gap-3">
              <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0" />
              <p className="text-red-400">{error}</p>
            </div>
          )}

          {/* Basic Info */}
          <section className="bg-gray-900 border border-gray-800 rounded-xl p-6">
            <h2 className="text-lg font-semibold text-white mb-4">Informazioni Base</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm text-gray-400 mb-2">Nome Token *</label>
                <input
                  type="text"
                  name="name"
                  value={formData.name}
                  onChange={handleChange}
                  required
                  placeholder="Es. MyToken"
                  className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg text-white focus:border-purple-500 focus:outline-none"
                  data-testid="token-name-input"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-2">Simbolo *</label>
                <input
                  type="text"
                  name="symbol"
                  value={formData.symbol}
                  onChange={handleChange}
                  required
                  maxLength={10}
                  placeholder="Es. MTK"
                  className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg text-white uppercase focus:border-purple-500 focus:outline-none"
                  data-testid="token-symbol-input"
                />
              </div>
              <div className="md:col-span-2">
                <label className="block text-sm text-gray-400 mb-2">Descrizione</label>
                <textarea
                  name="description"
                  value={formData.description}
                  onChange={handleChange}
                  rows={3}
                  placeholder="Descrivi il tuo token e il suo caso d'uso..."
                  className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg text-white focus:border-purple-500 focus:outline-none resize-none"
                />
              </div>
            </div>
          </section>

          {/* Token Economics */}
          <section className="bg-gray-900 border border-gray-800 rounded-xl p-6">
            <h2 className="text-lg font-semibold text-white mb-4">Token Economics</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-sm text-gray-400 mb-2">Total Supply *</label>
                <input
                  type="number"
                  name="total_supply"
                  value={formData.total_supply}
                  onChange={handleChange}
                  required
                  min="1"
                  placeholder="1000000"
                  className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg text-white focus:border-purple-500 focus:outline-none"
                  data-testid="token-supply-input"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-2">Prezzo Iniziale (EUR) *</label>
                <input
                  type="number"
                  name="initial_price"
                  value={formData.initial_price}
                  onChange={handleChange}
                  required
                  min="0.000001"
                  step="0.000001"
                  placeholder="1.00"
                  className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg text-white focus:border-purple-500 focus:outline-none"
                  data-testid="token-price-input"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-2">Decimali</label>
                <select
                  name="decimals"
                  value={formData.decimals}
                  onChange={handleChange}
                  className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg text-white focus:border-purple-500 focus:outline-none"
                >
                  <option value={18}>18 (Standard)</option>
                  <option value={8}>8</option>
                  <option value={6}>6</option>
                </select>
              </div>
            </div>
          </section>

          {/* Blockchain */}
          <section className="bg-gray-900 border border-gray-800 rounded-xl p-6">
            <h2 className="text-lg font-semibold text-white mb-4">Blockchain</h2>
            <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
              {CHAINS.map((chain) => (
                <button
                  key={chain.id}
                  type="button"
                  onClick={() => setFormData(prev => ({ ...prev, chain: chain.id }))}
                  className={`p-4 rounded-xl border-2 transition-all ${
                    formData.chain === chain.id
                      ? 'border-purple-500 bg-purple-500/10'
                      : 'border-gray-700 bg-gray-800/50 hover:border-gray-600'
                  }`}
                  data-testid={`chain-${chain.id}`}
                >
                  <div className="text-2xl mb-2">{chain.icon}</div>
                  <div className="text-white text-sm font-medium">{chain.name}</div>
                </button>
              ))}
            </div>
          </section>

          {/* Links */}
          <section className="bg-gray-900 border border-gray-800 rounded-xl p-6">
            <h2 className="text-lg font-semibold text-white mb-4">Link & Social</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="flex items-center gap-3">
                <Globe className="w-5 h-5 text-gray-400" />
                <input
                  type="url"
                  name="website_url"
                  value={formData.website_url}
                  onChange={handleChange}
                  placeholder="https://mytoken.com"
                  className="flex-1 px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg text-white focus:border-purple-500 focus:outline-none"
                />
              </div>
              <div className="flex items-center gap-3">
                <FileText className="w-5 h-5 text-gray-400" />
                <input
                  type="url"
                  name="whitepaper_url"
                  value={formData.whitepaper_url}
                  onChange={handleChange}
                  placeholder="https://mytoken.com/whitepaper.pdf"
                  className="flex-1 px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg text-white focus:border-purple-500 focus:outline-none"
                />
              </div>
              <div className="flex items-center gap-3">
                <Twitter className="w-5 h-5 text-gray-400" />
                <input
                  type="text"
                  name="social_twitter"
                  value={formData.social_links.twitter}
                  onChange={handleChange}
                  placeholder="@mytoken"
                  className="flex-1 px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg text-white focus:border-purple-500 focus:outline-none"
                />
              </div>
              <div className="flex items-center gap-3">
                <Send className="w-5 h-5 text-gray-400" />
                <input
                  type="text"
                  name="social_telegram"
                  value={formData.social_links.telegram}
                  onChange={handleChange}
                  placeholder="t.me/mytoken"
                  className="flex-1 px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg text-white focus:border-purple-500 focus:outline-none"
                />
              </div>
            </div>
          </section>

          {/* Fee Info */}
          <div className="bg-purple-500/10 border border-purple-500/30 rounded-xl p-6">
            <div className="flex items-start gap-4">
              <div className="p-2 bg-purple-500/20 rounded-lg">
                <Coins className="w-6 h-6 text-purple-400" />
              </div>
              <div>
                <h3 className="text-white font-semibold mb-1">Fee di Creazione Token</h3>
                <p className="text-gray-400 text-sm mb-2">
                  La creazione di un token richiede una fee di <span className="text-purple-400 font-bold">€100</span>.
                  Il pagamento sarà richiesto dopo l'approvazione da parte dell'admin.
                </p>
                <p className="text-gray-500 text-xs">
                  Dopo l'approvazione, potrai richiedere il listing e creare trading pairs.
                </p>
              </div>
            </div>
          </div>

          {/* Submit */}
          <button
            type="submit"
            disabled={loading}
            className="w-full py-4 bg-gradient-to-r from-purple-500 to-pink-500 hover:from-purple-600 hover:to-pink-600 text-white font-semibold rounded-xl transition-all disabled:opacity-50 flex items-center justify-center gap-2"
            data-testid="create-token-btn"
          >
            {loading ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                Creazione in corso...
              </>
            ) : (
              <>
                <Coins className="w-5 h-5" />
                Crea Token
              </>
            )}
          </button>
        </form>
      </main>
    </div>
  );
}
