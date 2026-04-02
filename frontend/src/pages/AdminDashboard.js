import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import {
  LayoutDashboard, Users, Coins, CreditCard,
  Shield, Globe, LogOut, ChevronRight, Loader2,
  Check, X, Eye, ArrowUpRight, ArrowDownRight,
  Activity, Clock, ListChecks, BarChart3, TrendingUp,
  FileText
} from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || '';

function getAuthHeaders() {
  return {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${localStorage.getItem('token')}`
  };
}

const STATUS_COLORS = {
  pending: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
  approved: 'bg-green-500/20 text-green-400 border-green-500/30',
  rejected: 'bg-red-500/20 text-red-400 border-red-500/30',
  live: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
  paused: 'bg-gray-500/20 text-gray-400 border-gray-500/30',
  active: 'bg-green-500/20 text-green-400 border-green-500/30',
  cancelled: 'bg-red-500/20 text-red-400 border-red-500/30',
};

// Overview Section
function OverviewSection({ tokenStats, subStats, usersCount }) {
  const cards = [
    { title: 'Utenti Totali', value: usersCount, icon: Users, color: 'from-blue-500/20 to-blue-600/10 border-blue-500/30' },
    { title: 'Token Creati', value: tokenStats?.tokens?.total || 0, icon: Coins, color: 'from-purple-500/20 to-purple-600/10 border-purple-500/30' },
    { title: 'Token in Attesa', value: tokenStats?.tokens?.pending || 0, icon: Clock, color: 'from-yellow-500/20 to-yellow-600/10 border-yellow-500/30' },
    { title: 'Token Live', value: tokenStats?.tokens?.live || 0, icon: Activity, color: 'from-green-500/20 to-green-600/10 border-green-500/30' },
    { title: 'Listing Pendenti', value: tokenStats?.listings?.pending || 0, icon: ListChecks, color: 'from-orange-500/20 to-orange-600/10 border-orange-500/30' },
    { title: 'Trading Pairs', value: tokenStats?.trading_pairs?.total || 0, icon: BarChart3, color: 'from-cyan-500/20 to-cyan-600/10 border-cyan-500/30' },
    { title: 'Abbonamenti Attivi', value: subStats?.by_status?.active || 0, icon: CreditCard, color: 'from-pink-500/20 to-pink-600/10 border-pink-500/30' },
    { title: 'MRR', value: `€${(subStats?.monthly_recurring_revenue || 0).toLocaleString()}`, icon: ArrowUpRight, color: 'from-emerald-500/20 to-emerald-600/10 border-emerald-500/30' },
  ];

  return (
    <div data-testid="admin-overview">
      <h2 className="text-2xl font-bold text-white mb-6">Dashboard Overview</h2>
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {cards.map((card, i) => (
          <div key={i} className={`bg-gradient-to-br ${card.color} border rounded-xl p-5`}>
            <div className="flex items-center justify-between mb-3">
              <span className="text-gray-400 text-sm">{card.title}</span>
              <card.icon className="w-4 h-4 text-gray-500" />
            </div>
            <div className="text-2xl font-bold text-white">{card.value}</div>
          </div>
        ))}
      </div>
      <div className="mt-6 bg-gray-800/50 border border-gray-700 rounded-xl p-6">
        <h3 className="text-lg font-semibold text-white mb-3">Fee Structure</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          <div><span className="text-gray-400">Token Creation:</span> <span className="text-white ml-1">€{tokenStats?.fees?.token_creation}</span></div>
          <div><span className="text-gray-400">Listing Standard:</span> <span className="text-white ml-1">€{tokenStats?.fees?.listing_standard}</span></div>
          <div><span className="text-gray-400">Listing Premium:</span> <span className="text-white ml-1">€{tokenStats?.fees?.listing_premium}</span></div>
          <div><span className="text-gray-400">Trading Pair:</span> <span className="text-white ml-1">€{tokenStats?.fees?.trading_pair}</span></div>
        </div>
      </div>
    </div>
  );
}

// Token Management Section
function TokenManagement() {
  const [tokens, setTokens] = useState([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(null);
  const [filter, setFilter] = useState('all');

  const fetchTokens = useCallback(async () => {
    setLoading(true);
    try {
      let url = `${BACKEND_URL}/api/tokens/list?page_size=100`;
      if (filter !== 'all') url += `&status=${filter}`;
      const res = await fetch(url, { headers: getAuthHeaders() });
      const data = await res.json();
      setTokens(data.tokens || []);
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  }, [filter]);

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { fetchTokens(); }, [filter]);

  const handleAction = async (tokenId, action) => {
    setActionLoading(tokenId);
    try {
      await fetch(`${BACKEND_URL}/api/tokens/${tokenId}/admin-action`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({ action })
      });
      await fetchTokens();
    } catch (e) { console.error(e); }
    finally { setActionLoading(null); }
  };

  return (
    <div data-testid="admin-tokens">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold text-white">Gestione Token</h2>
        <div className="flex gap-2">
          {['all', 'pending', 'approved', 'live', 'rejected'].map(f => (
            <button key={f} onClick={() => setFilter(f)}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${filter === f ? 'bg-purple-500 text-white' : 'bg-gray-800 text-gray-400 hover:text-white'}`}>
              {f === 'all' ? 'Tutti' : f.charAt(0).toUpperCase() + f.slice(1)}
            </button>
          ))}
        </div>
      </div>
      {loading ? (
        <div className="flex justify-center py-12"><Loader2 className="w-8 h-8 text-purple-500 animate-spin" /></div>
      ) : tokens.length === 0 ? (
        <div className="text-center py-12 text-gray-400">Nessun token trovato</div>
      ) : (
        <div className="bg-gray-800/50 border border-gray-700 rounded-xl overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-800">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase">Token</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase">Chain</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase">Supply</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase">Prezzo</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase">Stato</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase">Azioni</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-700">
              {tokens.map(t => (
                <tr key={t.id} className="hover:bg-gray-800/50">
                  <td className="px-4 py-3">
                    <div className="text-white font-medium">{t.name}</div>
                    <div className="text-gray-500 text-xs">${t.symbol}</div>
                  </td>
                  <td className="px-4 py-3 text-gray-300 text-sm">{t.chain}</td>
                  <td className="px-4 py-3 text-gray-300 text-sm">{t.total_supply?.toLocaleString()}</td>
                  <td className="px-4 py-3 text-gray-300 text-sm">€{t.current_price}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-1 rounded text-xs font-medium border ${STATUS_COLORS[t.status] || STATUS_COLORS.pending}`}>
                      {t.status}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex gap-2">
                      {t.status === 'pending' && (
                        <>
                          <button onClick={() => handleAction(t.id, 'approve')} disabled={actionLoading === t.id}
                            data-testid={`approve-token-${t.symbol}`}
                            className="p-1.5 bg-green-500/20 hover:bg-green-500/30 text-green-400 rounded-lg transition-colors" title="Approva">
                            {actionLoading === t.id ? <Loader2 className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />}
                          </button>
                          <button onClick={() => handleAction(t.id, 'reject')} disabled={actionLoading === t.id}
                            data-testid={`reject-token-${t.symbol}`}
                            className="p-1.5 bg-red-500/20 hover:bg-red-500/30 text-red-400 rounded-lg transition-colors" title="Rifiuta">
                            <X className="w-4 h-4" />
                          </button>
                        </>
                      )}
                      {t.status === 'approved' && (
                        <button onClick={() => handleAction(t.id, 'go_live')} disabled={actionLoading === t.id}
                          data-testid={`golive-token-${t.symbol}`}
                          className="px-2 py-1 bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-400 rounded-lg text-xs transition-colors">
                          Go Live
                        </button>
                      )}
                      {t.status === 'live' && (
                        <button onClick={() => handleAction(t.id, 'pause')} disabled={actionLoading === t.id}
                          className="px-2 py-1 bg-yellow-500/20 hover:bg-yellow-500/30 text-yellow-400 rounded-lg text-xs transition-colors">
                          Pausa
                        </button>
                      )}
                      {t.status === 'paused' && (
                        <button onClick={() => handleAction(t.id, 'unpause')} disabled={actionLoading === t.id}
                          className="px-2 py-1 bg-blue-500/20 hover:bg-blue-500/30 text-blue-400 rounded-lg text-xs transition-colors">
                          Riattiva
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// Listing Management Section
function ListingManagement() {
  const [listings, setListings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(null);

  const fetchListings = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`${BACKEND_URL}/api/tokens/listings/list?page_size=100`, { headers: getAuthHeaders() });
      const data = await res.json();
      setListings(data.listings || []);
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  }, []);

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { fetchListings(); }, []);

  const handleAction = async (listingId, action) => {
    setActionLoading(listingId);
    try {
      await fetch(`${BACKEND_URL}/api/tokens/listings/${listingId}/admin-action?action=${action}`, {
        method: 'POST', headers: getAuthHeaders()
      });
      await fetchListings();
    } catch (e) { console.error(e); }
    finally { setActionLoading(null); }
  };

  return (
    <div data-testid="admin-listings">
      <h2 className="text-2xl font-bold text-white mb-6">Gestione Listing</h2>
      {loading ? (
        <div className="flex justify-center py-12"><Loader2 className="w-8 h-8 text-purple-500 animate-spin" /></div>
      ) : listings.length === 0 ? (
        <div className="text-center py-12">
          <ListChecks className="w-12 h-12 text-gray-600 mx-auto mb-3" />
          <p className="text-gray-400">Nessuna richiesta di listing</p>
        </div>
      ) : (
        <div className="space-y-4">
          {listings.map(l => (
            <div key={l.id} className="bg-gray-800/50 border border-gray-700 rounded-xl p-5">
              <div className="flex items-center justify-between">
                <div>
                  <div className="flex items-center gap-3 mb-1">
                    <span className="text-white font-semibold">${l.token_symbol}</span>
                    <span className={`px-2 py-0.5 rounded text-xs font-medium border ${STATUS_COLORS[l.status] || STATUS_COLORS.pending}`}>
                      {l.status}
                    </span>
                    <span className="text-gray-500 text-xs">{l.listing_type}</span>
                  </div>
                  <div className="text-gray-400 text-sm">Fee: €{l.listing_fee} | Pairs: {(l.requested_pairs || []).join(', ')}</div>
                </div>
                <div className="flex gap-2">
                  {l.status === 'pending' && (
                    <>
                      <button onClick={() => handleAction(l.id, 'approve')} disabled={actionLoading === l.id}
                        data-testid={`approve-listing-${l.token_symbol}`}
                        className="px-3 py-1.5 bg-green-500/20 hover:bg-green-500/30 text-green-400 rounded-lg text-sm transition-colors flex items-center gap-1">
                        {actionLoading === l.id ? <Loader2 className="w-3 h-3 animate-spin" /> : <Check className="w-3 h-3" />}
                        Approva
                      </button>
                      <button onClick={() => handleAction(l.id, 'reject')} disabled={actionLoading === l.id}
                        className="px-3 py-1.5 bg-red-500/20 hover:bg-red-500/30 text-red-400 rounded-lg text-sm transition-colors flex items-center gap-1">
                        <X className="w-3 h-3" /> Rifiuta
                      </button>
                    </>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// Users Section
function UsersSection() {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const res = await fetch(`${BACKEND_URL}/api/auth/admin/users`, { headers: getAuthHeaders() });
        const data = await res.json();
        setUsers(data.users || []);
      } catch (e) { console.error(e); }
      finally { setLoading(false); }
    })();
  }, []);

  return (
    <div data-testid="admin-users">
      <h2 className="text-2xl font-bold text-white mb-6">Gestione Utenti</h2>
      {loading ? (
        <div className="flex justify-center py-12"><Loader2 className="w-8 h-8 text-purple-500 animate-spin" /></div>
      ) : (
        <div className="bg-gray-800/50 border border-gray-700 rounded-xl overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-800">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase">Email</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase">Ruolo</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase">Registrato</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-700">
              {users.map((u, i) => (
                <tr key={i} className="hover:bg-gray-800/50">
                  <td className="px-4 py-3 text-white">{u.email}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-1 rounded text-xs font-medium ${
                      u.role === 'ADMIN' ? 'bg-red-500/20 text-red-400' :
                      u.role === 'DEVELOPER' ? 'bg-blue-500/20 text-blue-400' :
                      'bg-gray-500/20 text-gray-400'
                    }`}>{u.role}</span>
                  </td>
                  <td className="px-4 py-3 text-gray-400 text-sm">
                    {u.created_at ? new Date(u.created_at).toLocaleDateString('it-IT') : 'N/A'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// Subscriptions Management
function SubscriptionsSection() {
  const [subs, setSubs] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const res = await fetch(`${BACKEND_URL}/api/subscriptions/admin/list?page_size=100`, { headers: getAuthHeaders() });
        const data = await res.json();
        setSubs(data.subscriptions || []);
      } catch (e) { console.error(e); }
      finally { setLoading(false); }
    })();
  }, []);

  return (
    <div data-testid="admin-subscriptions">
      <h2 className="text-2xl font-bold text-white mb-6">Gestione Abbonamenti</h2>
      {loading ? (
        <div className="flex justify-center py-12"><Loader2 className="w-8 h-8 text-purple-500 animate-spin" /></div>
      ) : subs.length === 0 ? (
        <div className="text-center py-12">
          <CreditCard className="w-12 h-12 text-gray-600 mx-auto mb-3" />
          <p className="text-gray-400">Nessun abbonamento attivo</p>
        </div>
      ) : (
        <div className="bg-gray-800/50 border border-gray-700 rounded-xl overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-800">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase">Utente</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase">Piano</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase">Ciclo</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase">Importo</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase">Stato</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-700">
              {subs.map(s => (
                <tr key={s.id} className="hover:bg-gray-800/50">
                  <td className="px-4 py-3 text-gray-300 text-sm">{s.user_id?.substring(0, 8)}...</td>
                  <td className="px-4 py-3 text-white font-medium">{s.plan_name}</td>
                  <td className="px-4 py-3 text-gray-300 text-sm">{s.billing_cycle}</td>
                  <td className="px-4 py-3 text-gray-300 text-sm">€{s.amount_paid}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-1 rounded text-xs font-medium border ${STATUS_COLORS[s.status] || STATUS_COLORS.active}`}>
                      {s.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// Analytics Section
function AnalyticsSection() {
  const [loading, setLoading] = useState(true);
  const [overview, setOverview] = useState(null);
  const [engagement, setEngagement] = useState(null);
  const [days, setDays] = useState(30);

  useEffect(() => {
    (async () => {
      setLoading(true);
      try {
        const headers = getAuthHeaders();
        const [ovRes, engRes] = await Promise.all([
          fetch(`${BACKEND_URL}/api/analytics/admin/overview?days=${days}`, { headers }),
          fetch(`${BACKEND_URL}/api/analytics/admin/engagement?days=${Math.min(days, 90)}`, { headers })
        ]);
        if (ovRes.ok) setOverview(await ovRes.json());
        if (engRes.ok) setEngagement(await engRes.json());
      } catch (e) { console.error(e); }
      finally { setLoading(false); }
    })();
  }, [days]);

  if (loading) return <div className="flex justify-center py-12"><Loader2 className="w-8 h-8 text-purple-500 animate-spin" /></div>;

  return (
    <div data-testid="admin-analytics">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold text-white">Analytics & Traffico</h2>
        <div className="flex gap-2">
          {[7, 30, 90].map(d => (
            <button key={d} onClick={() => setDays(d)}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${days === d ? 'bg-purple-500 text-white' : 'bg-gray-800 text-gray-400 hover:text-white'}`}>
              {d}g
            </button>
          ))}
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <div className="bg-gradient-to-br from-blue-500/20 to-blue-600/10 border border-blue-500/30 rounded-xl p-5">
          <div className="text-gray-400 text-sm mb-1">Page Views</div>
          <div className="text-2xl font-bold text-white">{overview?.page_views?.total || 0}</div>
        </div>
        <div className="bg-gradient-to-br from-green-500/20 to-green-600/10 border border-green-500/30 rounded-xl p-5">
          <div className="text-gray-400 text-sm mb-1">Utenti Attivi</div>
          <div className="text-2xl font-bold text-white">{overview?.users?.active || 0}</div>
        </div>
        <div className="bg-gradient-to-br from-purple-500/20 to-purple-600/10 border border-purple-500/30 rounded-xl p-5">
          <div className="text-gray-400 text-sm mb-1">Nuovi Utenti</div>
          <div className="text-2xl font-bold text-white">{overview?.users?.new || 0}</div>
        </div>
        <div className="bg-gradient-to-br from-cyan-500/20 to-cyan-600/10 border border-cyan-500/30 rounded-xl p-5">
          <div className="text-gray-400 text-sm mb-1">Sessioni</div>
          <div className="text-2xl font-bold text-white">{engagement?.sessions || 0}</div>
        </div>
      </div>

      {/* Engagement */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-6">
          <h3 className="text-lg font-semibold text-white mb-4">Engagement</h3>
          <div className="space-y-3">
            <div className="flex justify-between"><span className="text-gray-400">Pagine/Sessione</span><span className="text-white font-medium">{engagement?.avg_pages_per_session || 0}</span></div>
            <div className="flex justify-between"><span className="text-gray-400">Durata Media (sec)</span><span className="text-white font-medium">{engagement?.avg_session_duration_seconds || 0}</span></div>
            <div className="flex justify-between"><span className="text-gray-400">Token Creati</span><span className="text-white font-medium">{engagement?.recent_activity?.tokens_created || 0}</span></div>
            <div className="flex justify-between"><span className="text-gray-400">Nuovi Abbonamenti</span><span className="text-white font-medium">{engagement?.recent_activity?.subscriptions || 0}</span></div>
            <div className="flex justify-between"><span className="text-gray-400">Listing Richiesti</span><span className="text-white font-medium">{engagement?.recent_activity?.listings || 0}</span></div>
          </div>
        </div>

        <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-6">
          <h3 className="text-lg font-semibold text-white mb-4">Top Pagine</h3>
          {(overview?.page_views?.by_page || []).length === 0 ? (
            <div className="text-gray-500 text-sm py-4 text-center">Nessun dato di traffico ancora</div>
          ) : (
            <div className="space-y-2">
              {(overview?.page_views?.by_page || []).slice(0, 8).map((p, i) => (
                <div key={i} className="flex items-center justify-between">
                  <span className="text-gray-300 text-sm truncate max-w-[200px]">{p.page}</span>
                  <span className="text-white font-medium text-sm">{p.views}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Daily Traffic */}
      {(overview?.daily_traffic || []).length > 0 && (
        <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-6">
          <h3 className="text-lg font-semibold text-white mb-4">Traffico Giornaliero</h3>
          <div className="flex gap-1 items-end h-32">
            {overview.daily_traffic.map((d, i) => {
              const maxViews = Math.max(...overview.daily_traffic.map(x => x.views));
              const height = maxViews > 0 ? (d.views / maxViews) * 100 : 0;
              return (
                <div key={i} className="flex-1 flex flex-col items-center gap-1" title={`${d.date}: ${d.views} views`}>
                  <div className="w-full bg-purple-500/60 rounded-t" style={{ height: `${Math.max(height, 2)}%` }} />
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

// Sidebar
const NAV_ITEMS = [
  { id: 'overview', label: 'Overview', icon: LayoutDashboard },
  { id: 'tokens', label: 'Token', icon: Coins },
  { id: 'listings', label: 'Listing', icon: ListChecks },
  { id: 'users', label: 'Utenti', icon: Users },
  { id: 'subscriptions', label: 'Abbonamenti', icon: CreditCard },
  { id: 'analytics', label: 'Analytics', icon: TrendingUp },
];

export default function AdminDashboard() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [activeSection, setActiveSection] = useState('overview');
  const [loading, setLoading] = useState(true);
  const [tokenStats, setTokenStats] = useState(null);
  const [subStats, setSubStats] = useState(null);
  const [usersCount, setUsersCount] = useState(0);

  useEffect(() => {
    (async () => {
      try {
        const headers = getAuthHeaders();
        const [tsRes, ssRes, uRes] = await Promise.all([
          fetch(`${BACKEND_URL}/api/tokens/stats/overview`, { headers }),
          fetch(`${BACKEND_URL}/api/subscriptions/admin/stats`, { headers }),
          fetch(`${BACKEND_URL}/api/auth/admin/users`, { headers })
        ]);
        setTokenStats(await tsRes.json());
        setSubStats(await ssRes.json());
        const uData = await uRes.json();
        setUsersCount(uData.total || 0);
      } catch (e) { console.error(e); }
      finally { setLoading(false); }
    })();
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-purple-500 animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-950 flex" data-testid="admin-dashboard">
      {/* Sidebar */}
      <div className="w-60 bg-gray-900 border-r border-gray-800 min-h-screen p-4 flex flex-col">
        <div className="flex items-center gap-3 mb-8 px-2">
          <div className="w-9 h-9 bg-gradient-to-r from-purple-500 to-pink-500 rounded-lg flex items-center justify-center">
            <Shield className="w-5 h-5 text-white" />
          </div>
          <div>
            <div className="text-white font-bold text-sm">Admin Panel</div>
            <div className="text-gray-500 text-xs">NeoNoble Ramp</div>
          </div>
        </div>
        <nav className="flex-1 space-y-1">
          {NAV_ITEMS.map(item => (
            <button key={item.id} onClick={() => setActiveSection(item.id)}
              data-testid={`admin-nav-${item.id}`}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors ${
                activeSection === item.id ? 'bg-purple-500/20 text-purple-400' : 'text-gray-400 hover:bg-gray-800 hover:text-white'
              }`}>
              <item.icon className="w-4 h-4" />
              {item.label}
            </button>
          ))}
        </nav>
        <div className="pt-4 border-t border-gray-800 space-y-1">
          <button onClick={() => navigate('/audit')}
            className="w-full flex items-center gap-3 px-3 py-2.5 text-gray-400 hover:bg-gray-800 hover:text-white rounded-lg text-sm transition-colors"
            data-testid="admin-nav-audit">
            <FileText className="w-4 h-4" /> Registro Audit
          </button>
          <button onClick={() => navigate('/dashboard')}
            className="w-full flex items-center gap-3 px-3 py-2.5 text-gray-400 hover:bg-gray-800 hover:text-white rounded-lg text-sm transition-colors">
            <Globe className="w-4 h-4" /> Dashboard
          </button>
          <button onClick={logout}
            className="w-full flex items-center gap-3 px-3 py-2.5 text-red-400 hover:bg-red-500/10 rounded-lg text-sm transition-colors">
            <LogOut className="w-4 h-4" /> Logout
          </button>
        </div>
      </div>

      {/* Main Content */}
      <main className="flex-1 p-8">
        <div className="max-w-6xl mx-auto">
          {activeSection === 'overview' && <OverviewSection tokenStats={tokenStats} subStats={subStats} usersCount={usersCount} />}
          {activeSection === 'tokens' && <TokenManagement />}
          {activeSection === 'listings' && <ListingManagement />}
          {activeSection === 'users' && <UsersSection />}
          {activeSection === 'subscriptions' && <SubscriptionsSection />}
          {activeSection === 'analytics' && <AnalyticsSection />}
        </div>
      </main>
    </div>
  );
}
