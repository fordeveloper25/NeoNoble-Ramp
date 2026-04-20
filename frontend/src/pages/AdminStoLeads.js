import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { stoApi } from '../api/sto';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

export default function AdminStoLeads() {
  const [leads, setLeads] = useState([]);
  const [count, setCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [subject, setSubject] = useState('');
  const [html, setHtml] = useState('<p>Ciao!</p>');
  const [onlyMarketing, setOnlyMarketing] = useState(true);
  const [broadcasting, setBroadcasting] = useState(false);
  const [broadcastResult, setBroadcastResult] = useState(null);

  const load = async () => {
    try {
      setLoading(true);
      const r = await stoApi.adminLeads();
      setLeads(r.leads || []);
      setCount(r.count || 0);
    } catch (e) {
      setError(e?.response?.data?.detail || e.message);
    } finally { setLoading(false); }
  };

  useEffect(() => { load(); }, []);

  const downloadCsv = () => {
    const token = localStorage.getItem('token');
    fetch(`${BACKEND_URL}/api/sto/admin/leads/export`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.blob();
      })
      .then((blob) => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'sto_leads.csv';
        a.click();
        URL.revokeObjectURL(url);
      })
      .catch((e) => setError(e.message));
  };

  const sendBroadcast = async () => {
    if (!subject || !html || subject.length < 3 || html.length < 10) {
      setError('Compila subject e html'); return;
    }
    if (!window.confirm(`Inviare email a ${onlyMarketing ? 'solo opt-in marketing' : 'TUTTI'} i ${count} lead?`)) return;
    setBroadcasting(true); setError(null); setBroadcastResult(null);
    try {
      const token = localStorage.getItem('token');
      const r = await fetch(`${BACKEND_URL}/api/sto/admin/leads/broadcast`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ subject, html, only_accepts_marketing: onlyMarketing }),
      });
      const data = await r.json();
      if (!r.ok) throw new Error(data.detail || `HTTP ${r.status}`);
      setBroadcastResult(data);
    } catch (e) {
      setError(e.message);
    } finally { setBroadcasting(false); }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-indigo-950 to-slate-950 text-white">
      <div className="max-w-6xl mx-auto px-4 py-8">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-3xl md:text-4xl font-bold">📥 STO Leads</h1>
            <p className="text-slate-400 mt-1">{count} pre-registrazioni raccolte</p>
          </div>
          <Link to="/admin" className="text-sm text-slate-300 hover:text-white underline">
            ← Admin
          </Link>
        </div>

        {/* Actions */}
        <div className="mb-6 flex flex-wrap gap-3">
          <button
            onClick={downloadCsv}
            data-testid="sto-leads-csv"
            className="px-4 py-2 rounded-lg bg-emerald-700 hover:bg-emerald-600 font-medium text-sm"
          >
            ⬇ Export CSV
          </button>
          <button
            onClick={load}
            className="px-4 py-2 rounded-lg bg-slate-700 hover:bg-slate-600 font-medium text-sm"
          >
            ↻ Refresh
          </button>
        </div>

        {/* Broadcast box */}
        <div className="mb-6 p-5 rounded-2xl bg-slate-900/70 border border-slate-800">
          <h2 className="text-xl font-bold mb-3">📢 Email broadcast</h2>
          <p className="text-xs text-slate-500 mb-3">
            Invia un'email a tutti i lead. Richiede <code>RESEND_API_KEY</code> configurata sul backend
            (in assenza le email vengono solo loggate in console).
          </p>

          <div className="space-y-3">
            <input
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              placeholder="Subject"
              data-testid="sto-broadcast-subject"
              className="w-full px-3 py-2 rounded-lg bg-slate-800 border border-slate-700 focus:border-indigo-500 outline-none"
            />
            <textarea
              value={html}
              onChange={(e) => setHtml(e.target.value)}
              rows={6}
              placeholder="<p>HTML content</p>"
              data-testid="sto-broadcast-html"
              className="w-full px-3 py-2 rounded-lg bg-slate-800 border border-slate-700 focus:border-indigo-500 outline-none font-mono text-sm"
            />
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={onlyMarketing}
                onChange={(e) => setOnlyMarketing(e.target.checked)}
              />
              Solo chi ha dato consenso marketing (GDPR)
            </label>
            <button
              onClick={sendBroadcast}
              disabled={broadcasting || !subject}
              data-testid="sto-broadcast-send"
              className="px-6 py-2 rounded-lg bg-gradient-to-r from-indigo-600 to-pink-600 hover:from-indigo-500 hover:to-pink-500 font-semibold disabled:opacity-40"
            >
              {broadcasting ? 'Invio…' : 'Invia broadcast'}
            </button>
          </div>

          {broadcastResult && (
            <div className="mt-4 p-3 rounded bg-emerald-950/40 border border-emerald-800 text-sm">
              ✔ Inviato: <strong>{broadcastResult.sent}</strong> · Falliti: <strong>{broadcastResult.failed}</strong> · Totale recipient: <strong>{broadcastResult.recipients}</strong>
            </div>
          )}
          {error && (
            <div className="mt-4 p-3 rounded bg-rose-950/40 border border-rose-800 text-sm text-rose-300">
              ⚠ {error}
            </div>
          )}
        </div>

        {/* Leads table */}
        <div className="p-5 rounded-2xl bg-slate-900/70 border border-slate-800 overflow-x-auto">
          {loading ? (
            <p className="text-slate-400">Caricamento…</p>
          ) : leads.length === 0 ? (
            <p className="text-slate-500">Nessun lead registrato.</p>
          ) : (
            <table className="w-full text-sm">
              <thead className="text-xs text-slate-500 uppercase border-b border-slate-800">
                <tr>
                  <th className="text-left py-2">Email</th>
                  <th className="text-left py-2">Nome</th>
                  <th className="text-left py-2">Paese</th>
                  <th className="text-left py-2">Importo</th>
                  <th className="text-left py-2">Wallet</th>
                  <th className="text-left py-2">MKT</th>
                  <th className="text-left py-2">Data</th>
                </tr>
              </thead>
              <tbody>
                {leads.map((l, i) => (
                  <tr key={i} className="border-b border-slate-800/50 hover:bg-slate-800/30">
                    <td className="py-2">{l.email}</td>
                    <td className="py-2">{l.full_name}</td>
                    <td className="py-2 font-mono">{l.country}</td>
                    <td className="py-2">{l.amount_range}</td>
                    <td className="py-2 font-mono text-xs">{l.wallet_address ? `${l.wallet_address.slice(0,8)}…${l.wallet_address.slice(-4)}` : '—'}</td>
                    <td className="py-2">{l.accepts_marketing ? '✔' : '—'}</td>
                    <td className="py-2 text-xs text-slate-500">{l.created_at?.slice(0, 10)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
