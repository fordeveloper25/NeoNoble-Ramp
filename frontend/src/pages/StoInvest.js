import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { stoApi } from '../api/sto';

export default function StoInvest() {
  const [info, setInfo] = useState(null);
  const [health, setHealth] = useState(null);
  const [form, setForm] = useState({
    email: '', full_name: '', country: 'IT', amount_range: '10k-50k',
    wallet_address: '', accepts_marketing: false,
  });
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    (async () => {
      try { setInfo(await stoApi.publicInfo()); } catch (_) {}
      try { setHealth(await stoApi.health()); } catch (_) {}
    })();
  }, []);

  const canSubmit = form.email && form.full_name.length >= 2 && form.country.length === 2 && !submitting;

  const submit = async (e) => {
    e.preventDefault();
    setError(null); setSubmitting(true);
    try {
      await stoApi.lead(form);
      setSubmitted(true);
    } catch (err) {
      setError(err?.response?.data?.detail || err.message);
    } finally {
      setSubmitting(false);
    }
  };

  const isLive = info?.phase === 'live';

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-indigo-950 to-slate-950 text-white">
      <div className="max-w-5xl mx-auto px-4 py-12">

        {/* Hero */}
        <div className="text-center mb-12">
          <span className="inline-block px-3 py-1 rounded-full bg-indigo-900/60 text-indigo-200 text-xs uppercase tracking-widest mb-4">
            Security Token Offering · Polygon PoS
          </span>
          <h1 className="text-4xl md:text-6xl font-bold bg-gradient-to-r from-indigo-300 to-pink-300 bg-clip-text text-transparent mb-4">
            {info?.name || 'NeoNoble Revenue Share Token'}
          </h1>
          <p className="text-lg text-slate-300 max-w-2xl mx-auto">
            Un security token regolamentato che dà diritto a una <strong>quota pro-rata dei ricavi</strong> della
            piattaforma NeoNoble Ramp (swap, carte, banking, launchpad), con <strong>redemption trimestrale a NAV</strong> in USDC.
          </p>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-10">
          <Stat label="Simbolo" value={info?.symbol || '—'} />
          <Stat label="Prezzo nominale" value={info?.nominal_price_eur ? `€${info.nominal_price_eur}` : '—'} />
          <Stat label="Target raise" value={info ? `€${(info.target_raise_eur_min/1e6)}M – €${(info.target_raise_eur_max/1e6)}M` : '—'} />
          <Stat label="Chain" value={info?.chain || 'Polygon PoS'} />
        </div>

        {/* Phase banner */}
        <div className="mb-10 p-4 rounded-xl bg-indigo-900/30 border border-indigo-700/50 text-center">
          {isLive ? (
            <p className="text-indigo-100">
              <strong>🟢 LIVE</strong> — subscription aperta agli investitori KYC-verificati.{' '}
              <Link to="/sto/portfolio" className="underline">Vai al tuo portfolio →</Link>
            </p>
          ) : (
            <p className="text-amber-200">
              <strong>⏳ PRE-LAUNCH</strong> — siamo in fase di prospetto legale + audit smart contract.
              Lascia la tua email sotto per essere avvisato al go-live (stimato: 6 mesi).
            </p>
          )}
        </div>

        {/* Lead form */}
        <div className="bg-slate-900/70 backdrop-blur border border-slate-800 rounded-2xl p-8 shadow-2xl">
          {submitted ? (
            <div className="text-center py-8">
              <div className="text-5xl mb-4">✅</div>
              <h2 className="text-2xl font-bold mb-2">Pre-registrazione ricevuta</h2>
              <p className="text-slate-400">Ti contatteremo via email al go-live con le istruzioni KYC.</p>
              <Link to="/dashboard" className="inline-block mt-6 px-6 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 transition">
                Torna alla Dashboard
              </Link>
            </div>
          ) : (
            <form onSubmit={submit} className="space-y-4">
              <h2 className="text-2xl font-bold mb-4">Pre-registrati per il go-live</h2>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs text-slate-400 uppercase mb-1">Email *</label>
                  <input
                    type="email" required data-testid="sto-lead-email"
                    value={form.email}
                    onChange={(e) => setForm({ ...form, email: e.target.value })}
                    className="w-full px-3 py-2 rounded-lg bg-slate-800 border border-slate-700 focus:border-indigo-500 outline-none"
                  />
                </div>
                <div>
                  <label className="block text-xs text-slate-400 uppercase mb-1">Nome completo *</label>
                  <input
                    required data-testid="sto-lead-name"
                    value={form.full_name}
                    onChange={(e) => setForm({ ...form, full_name: e.target.value })}
                    className="w-full px-3 py-2 rounded-lg bg-slate-800 border border-slate-700 focus:border-indigo-500 outline-none"
                  />
                </div>
                <div>
                  <label className="block text-xs text-slate-400 uppercase mb-1">Paese residenza (ISO-2)</label>
                  <input
                    maxLength={2} minLength={2} required data-testid="sto-lead-country"
                    value={form.country}
                    onChange={(e) => setForm({ ...form, country: e.target.value.toUpperCase() })}
                    className="w-full px-3 py-2 rounded-lg bg-slate-800 border border-slate-700 focus:border-indigo-500 outline-none font-mono"
                  />
                </div>
                <div>
                  <label className="block text-xs text-slate-400 uppercase mb-1">Importo indicativo</label>
                  <select
                    data-testid="sto-lead-amount"
                    value={form.amount_range}
                    onChange={(e) => setForm({ ...form, amount_range: e.target.value })}
                    className="w-full px-3 py-2 rounded-lg bg-slate-800 border border-slate-700 focus:border-indigo-500 outline-none"
                  >
                    <option value="<1k">&lt; €1.000</option>
                    <option value="1k-10k">€1.000 – €10.000</option>
                    <option value="10k-50k">€10.000 – €50.000</option>
                    <option value="50k+">&gt; €50.000</option>
                  </select>
                </div>
                <div className="md:col-span-2">
                  <label className="block text-xs text-slate-400 uppercase mb-1">
                    Wallet EVM (opzionale — aggiungi dopo se non lo hai)
                  </label>
                  <input
                    data-testid="sto-lead-wallet"
                    placeholder="0x..."
                    value={form.wallet_address}
                    onChange={(e) => setForm({ ...form, wallet_address: e.target.value })}
                    className="w-full px-3 py-2 rounded-lg bg-slate-800 border border-slate-700 focus:border-indigo-500 outline-none font-mono text-sm"
                  />
                </div>
              </div>

              <label className="flex items-center gap-2 text-sm text-slate-300">
                <input
                  type="checkbox"
                  checked={form.accepts_marketing}
                  onChange={(e) => setForm({ ...form, accepts_marketing: e.target.checked })}
                />
                Accetto di ricevere aggiornamenti via email (facoltativo)
              </label>

              <button
                type="submit"
                disabled={!canSubmit}
                data-testid="sto-lead-submit"
                className="w-full py-3 rounded-xl font-semibold text-white bg-gradient-to-r from-indigo-600 to-pink-600 hover:from-indigo-500 hover:to-pink-500 disabled:opacity-40 transition"
              >
                {submitting ? 'Invio…' : 'Pre-registrati'}
              </button>

              {error && <div className="p-3 rounded bg-rose-950/50 border border-rose-800 text-rose-300 text-sm">⚠ {error}</div>}
            </form>
          )}
        </div>

        {/* Compliance footer */}
        <div className="mt-10 p-5 rounded-xl bg-slate-900/40 border border-slate-800 text-xs text-slate-400 leading-relaxed">
          <p className="mb-2"><strong className="text-slate-300">Informativa</strong></p>
          <p>
            Questa pre-registrazione NON costituisce offerta al pubblico ai sensi dell'art. 94 TUF.
            L'emissione effettiva del security token e` subordinata all'approvazione del prospetto
            (o all'esenzione ai sensi dell'art. 100-bis TUF per offerte &lt; €8M) e all'audit degli smart
            contract. I token saranno distribuiti solo a investitori KYC-verificati conformi alle
            regole MiCA / direttiva AIFM. Gli investimenti in security token comportano rischi, inclusa
            possibile perdita del capitale. Leggere il prospetto prima di investire.
          </p>
          <p className="mt-3">
            Health contratti on-chain: <strong className={health?.deployed ? 'text-emerald-300' : 'text-amber-300'}>
              {health?.deployed ? 'LIVE Polygon' : 'Awaiting deploy'}
            </strong>
            {' · '}
            RPC: <strong className={health?.rpc_connected ? 'text-emerald-300' : 'text-rose-300'}>
              {health?.rpc_connected ? 'connected' : 'down'}
            </strong>
          </p>
        </div>
      </div>
    </div>
  );
}

function Stat({ label, value }) {
  return (
    <div className="p-4 rounded-xl bg-slate-900/60 backdrop-blur border border-slate-800 text-center">
      <div className="text-xs text-slate-500 uppercase tracking-wide">{label}</div>
      <div className="text-lg font-semibold mt-1">{value}</div>
    </div>
  );
}
