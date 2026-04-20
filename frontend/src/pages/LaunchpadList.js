import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { launchpadApi } from '../api/launchpad';

export default function LaunchpadList() {
  const [tokens, setTokens] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [health, setHealth] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    (async () => {
      try {
        const h = await launchpadApi.health();
        setHealth(h);
        if (!h.factory_deployed) {
          setLoading(false);
          return;
        }
        const res = await launchpadApi.list(50, 0);
        setTokens(res.tokens || []);
        setTotal(res.total || 0);
      } catch (e) {
        setError(e?.response?.data?.detail || e.message);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-purple-950 to-slate-950 text-white">
      <div className="max-w-7xl mx-auto px-4 py-8">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-3xl md:text-4xl font-bold flex items-center gap-3">
              <span>🚀</span> Launchpad
            </h1>
            <p className="text-slate-400 mt-1">
              Crea il tuo token con bonding curve — zero collateral, solo una fee di deploy.
              Gli utenti comprano/vendono direttamente dalla curva.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <Link
              to="/launchpad/create"
              data-testid="launchpad-create-btn"
              className="px-4 py-2 rounded-xl font-semibold text-white bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-500 hover:to-pink-500 transition"
            >
              + Crea Token
            </Link>
            <Link to="/dashboard" className="text-sm text-slate-300 hover:text-white underline">
              ← Dashboard
            </Link>
          </div>
        </div>

        {/* Health */}
        {health && !health.factory_deployed && (
          <div data-testid="launchpad-awaiting-deploy" className="mb-6 p-4 rounded-xl bg-amber-900/30 border border-amber-600/50">
            <h3 className="font-semibold text-amber-200 mb-1">
              Factory non ancora deployato
            </h3>
            <p className="text-sm text-amber-100/90">
              Per attivare il Launchpad devi deployare i contract Solidity in{' '}
              <code className="px-1 bg-slate-800 rounded">/app/contracts/</code> su BSC Mainnet e
              impostare <code className="px-1 bg-slate-800 rounded">LAUNCHPAD_FACTORY_ADDRESS</code>{' '}
              nelle variabili d'ambiente del backend. Vedi la guida{' '}
              <code className="px-1 bg-slate-800 rounded">DEPLOY.md</code>.
            </p>
          </div>
        )}

        {health && health.factory_deployed && (
          <div className="mb-6 flex flex-wrap gap-2 text-xs">
            <span className="px-3 py-1 rounded bg-emerald-900/50 text-emerald-300">
              ● Factory attivo
            </span>
            <span className="px-3 py-1 rounded bg-slate-800 text-slate-300">
              BSC chain 56 · {total} token creati
            </span>
            <span className="px-3 py-1 rounded bg-slate-800 text-slate-300">
              Modello: virtual AMM · zero capitale piattaforma
            </span>
          </div>
        )}

        {loading && (
          <div className="text-slate-400">Caricamento token…</div>
        )}

        {error && (
          <div className="p-4 rounded bg-rose-950/50 border border-rose-800 text-rose-300">
            ⚠ {error}
          </div>
        )}

        {!loading && !error && tokens.length === 0 && health?.factory_deployed && (
          <div className="text-center py-16 text-slate-400">
            <p className="mb-4">Nessun token ancora lanciato.</p>
            <Link
              to="/launchpad/create"
              className="inline-block px-6 py-3 rounded-xl font-semibold bg-purple-600 hover:bg-purple-500"
            >
              Crea il primo token 🚀
            </Link>
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {tokens.map((t) => (
            <TokenCard key={t.address} token={t} />
          ))}
        </div>
      </div>
    </div>
  );
}

function TokenCard({ token }) {
  if (token.error) {
    return (
      <div className="p-4 rounded-xl bg-slate-900/50 border border-rose-800 text-rose-300 text-xs">
        {token.address.slice(0, 10)}… — {token.error}
      </div>
    );
  }
  const progress = Math.min(100, token.graduation_progress_pct || 0);
  return (
    <Link
      to={`/launchpad/${token.address}`}
      data-testid={`launchpad-token-${token.symbol}`}
      className="block p-5 rounded-2xl bg-slate-900/70 backdrop-blur border border-slate-800 hover:border-purple-500 transition"
    >
      <div className="flex items-start justify-between mb-3">
        <div>
          <h3 className="text-lg font-bold">{token.name}</h3>
          <p className="text-xs text-slate-400 font-mono">${token.symbol}</p>
        </div>
        {token.graduated && (
          <span className="text-[10px] px-2 py-1 rounded bg-emerald-700 uppercase">
            Graduated
          </span>
        )}
      </div>
      <div className="space-y-1 text-sm text-slate-300">
        <div className="flex justify-between">
          <span className="text-slate-500">Price</span>
          <span>{token.price_bnb.toExponential(4)} BNB</span>
        </div>
        <div className="flex justify-between">
          <span className="text-slate-500">Raised</span>
          <span>{token.real_bnb_reserve_human.toFixed(4)} / {token.graduation_bnb} BNB</span>
        </div>
      </div>
      <div className="mt-3 h-2 rounded-full bg-slate-800 overflow-hidden">
        <div
          className="h-full bg-gradient-to-r from-purple-500 to-pink-500 transition-all"
          style={{ width: `${progress}%` }}
        />
      </div>
      <p className="mt-2 text-xs text-slate-500">
        {progress.toFixed(1)}% verso graduation su PancakeSwap
      </p>
    </Link>
  );
}
