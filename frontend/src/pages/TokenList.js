/**
 * Token List Page
 * Displays user's tokens and marketplace
 */

import React, { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import {
  Coins, Plus, Search, Filter, ArrowUpRight, Clock,
  CheckCircle, XCircle, Loader2, ChevronRight, TrendingUp
} from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || '';

const STATUS_BADGES = {
  pending: { color: 'bg-yellow-500/20 text-yellow-400', label: 'In Attesa' },
  approved: { color: 'bg-green-500/20 text-green-400', label: 'Approvato' },
  rejected: { color: 'bg-red-500/20 text-red-400', label: 'Rifiutato' },
  live: { color: 'bg-purple-500/20 text-purple-400', label: 'Live' },
  paused: { color: 'bg-gray-500/20 text-gray-400', label: 'In Pausa' },
};

const CHAIN_ICONS = {
  ethereum: '⟠',
  bsc: '🔶',
  polygon: '🟣',
  arbitrum: '🔵',
  base: '🔷',
};

export default function TokenList() {
  const navigate = useNavigate();
  const { token, user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [tokens, setTokens] = useState([]);
  const [filter, setFilter] = useState('all'); // all, my, pending, live
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    fetchTokens();
  }, [filter]);

  const fetchTokens = async () => {
    setLoading(true);
    try {
      let url = `${BACKEND_URL}/api/tokens/list?page_size=50`;
      
      if (filter === 'my') {
        url += `&creator_id=${user?.id}`;
      } else if (filter !== 'all') {
        url += `&status=${filter}`;
      }

      const response = await fetch(url, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      const data = await response.json();
      setTokens(data.tokens || []);
    } catch (error) {
      console.error('Error fetching tokens:', error);
    } finally {
      setLoading(false);
    }
  };

  const filteredTokens = tokens.filter(t => 
    t.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    t.symbol.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="min-h-screen bg-gray-950">
      {/* Header */}
      <header className="border-b border-gray-800 bg-gray-900/50 backdrop-blur-lg sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-purple-500/20 rounded-lg">
                <Coins className="w-6 h-6 text-purple-400" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-white">Token Marketplace</h1>
                <p className="text-gray-400 text-sm">Esplora e gestisci token</p>
              </div>
            </div>
            <button
              onClick={() => navigate('/tokens/create')}
              className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-purple-500 to-pink-500 hover:from-purple-600 hover:to-pink-600 text-white rounded-lg font-medium transition-all"
              data-testid="create-token-nav-btn"
            >
              <Plus className="w-4 h-4" />
              Crea Token
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 py-6">
        {/* Filters */}
        <div className="flex flex-col md:flex-row gap-4 mb-6">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
            <input
              type="text"
              placeholder="Cerca token..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-3 bg-gray-800 border border-gray-700 rounded-lg text-white focus:border-purple-500 focus:outline-none"
            />
          </div>
          <div className="flex gap-2">
            {[
              { id: 'all', label: 'Tutti' },
              { id: 'my', label: 'I Miei' },
              { id: 'live', label: 'Live' },
              { id: 'pending', label: 'In Attesa' },
            ].map((f) => (
              <button
                key={f.id}
                onClick={() => setFilter(f.id)}
                className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                  filter === f.id
                    ? 'bg-purple-500 text-white'
                    : 'bg-gray-800 text-gray-400 hover:text-white'
                }`}
              >
                {f.label}
              </button>
            ))}
          </div>
        </div>

        {/* Token Grid */}
        {loading ? (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="w-8 h-8 text-purple-500 animate-spin" />
          </div>
        ) : filteredTokens.length === 0 ? (
          <div className="text-center py-20">
            <Coins className="w-16 h-16 text-gray-600 mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-white mb-2">Nessun Token</h3>
            <p className="text-gray-400 mb-6">
              {filter === 'my' 
                ? "Non hai ancora creato nessun token."
                : "Nessun token trovato con questi filtri."}
            </p>
            <button
              onClick={() => navigate('/tokens/create')}
              className="px-6 py-3 bg-purple-500 hover:bg-purple-600 text-white rounded-lg font-medium transition-colors"
            >
              Crea il tuo primo Token
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredTokens.map((t) => (
              <TokenCard key={t.id} token={t} />
            ))}
          </div>
        )}
      </main>
    </div>
  );
}

function TokenCard({ token }) {
  const navigate = useNavigate();
  const status = STATUS_BADGES[token.status] || STATUS_BADGES.pending;
  const chainIcon = CHAIN_ICONS[token.chain] || '🔗';

  return (
    <div
      className="bg-gray-900 border border-gray-800 rounded-xl p-5 hover:border-purple-500/50 transition-all cursor-pointer group"
      onClick={() => navigate(`/tokens/${token.id}`)}
      data-testid={`token-card-${token.symbol}`}
    >
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 bg-gradient-to-br from-purple-500/20 to-pink-500/20 rounded-xl flex items-center justify-center text-2xl">
            {token.logo_url ? (
              <img src={token.logo_url} alt={token.symbol} className="w-8 h-8 rounded-full" />
            ) : (
              <span>{token.symbol.charAt(0)}</span>
            )}
          </div>
          <div>
            <h3 className="text-white font-semibold">{token.name}</h3>
            <p className="text-gray-400 text-sm">${token.symbol}</p>
          </div>
        </div>
        <span className={`px-2 py-1 rounded text-xs font-medium ${status.color}`}>
          {status.label}
        </span>
      </div>

      <div className="space-y-2 mb-4">
        <div className="flex justify-between text-sm">
          <span className="text-gray-400">Prezzo</span>
          <span className="text-white font-medium">€{token.current_price.toLocaleString()}</span>
        </div>
        <div className="flex justify-between text-sm">
          <span className="text-gray-400">Supply</span>
          <span className="text-white">{token.total_supply.toLocaleString()}</span>
        </div>
        <div className="flex justify-between text-sm">
          <span className="text-gray-400">Chain</span>
          <span className="text-white flex items-center gap-1">
            {chainIcon} {token.chain}
          </span>
        </div>
        <div className="flex justify-between text-sm">
          <span className="text-gray-400">Trading Pairs</span>
          <span className="text-white">{token.trading_pairs_count || 0}</span>
        </div>
      </div>

      <div className="flex items-center justify-between pt-4 border-t border-gray-800">
        <span className="text-gray-500 text-xs">
          Creato {new Date(token.created_at).toLocaleDateString('it-IT')}
        </span>
        <ChevronRight className="w-5 h-5 text-gray-500 group-hover:text-purple-400 transition-colors" />
      </div>
    </div>
  );
}
