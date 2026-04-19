import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useWeb3 } from '../context/Web3Context';
import { swapApi } from '../api/swap';

const TIER_STYLES = {
  tier1: 'bg-emerald-600',
  tier2: 'bg-blue-600',
  tier3: 'bg-amber-600',
  tier4: 'bg-purple-600',
};

const TIER_HINT = {
  tier1: 'Best price via 1inch aggregator',
  tier2: 'On-chain via PancakeSwap V2',
  tier3: 'Direct transfer from platform reserves',
  tier4: 'Queued for on-chain delivery when liquidity is available',
};

function explorerTx(hash) {
  return hash ? `https://bscscan.com/tx/${hash}` : null;
}

export default function Swap() {
  const { user } = useAuth();
  const {
    address,
    isConnected,
    openWalletModal,
    formatAddress,
    chainId,
    refetchNenoBalance,
  } = useWeb3();

  const [tokens, setTokens] = useState([]);
  const [fromToken, setFromToken] = useState('NENO');
  const [toToken, setToToken] = useState('USDT');
  const [amount, setAmount] = useState('');
  const [slippage, setSlippage] = useState(0.8);

  const [quote, setQuote] = useState(null);
  const [loadingQuote, setLoadingQuote] = useState(false);
  const [quoteError, setQuoteError] = useState(null);

  const [executing, setExecuting] = useState(false);
  const [lastResult, setLastResult] = useState(null);
  const [executeError, setExecuteError] = useState(null);

  const [history, setHistory] = useState([]);
  const [health, setHealth] = useState(null);

  // Bootstrap: load tokens, health, history
  useEffect(() => {
    (async () => {
      try {
        const t = await swapApi.tokens();
        setTokens(t.tokens || []);
      } catch (_) {}
      try {
        setHealth(await swapApi.health());
      } catch (_) {}
    })();
  }, []);

  const refreshHistory = useCallback(async () => {
    if (!user) return;
    try {
      const h = await swapApi.history(20);
      setHistory(h.history || []);
    } catch (_) {}
  }, [user]);

  useEffect(() => {
    refreshHistory();
  }, [refreshHistory]);

  // Auto-quote as user types (debounced)
  useEffect(() => {
    const amt = parseFloat(amount);
    if (!fromToken || !toToken || fromToken === toToken || !amt || amt <= 0) {
      setQuote(null);
      setQuoteError(null);
      return;
    }
    setLoadingQuote(true);
    setQuoteError(null);
    const h = setTimeout(async () => {
      try {
        const q = await swapApi.quote(fromToken, toToken, amt);
        setQuote(q);
      } catch (err) {
        setQuoteError(err?.response?.data?.detail || err.message);
        setQuote(null);
      } finally {
        setLoadingQuote(false);
      }
    }, 500);
    return () => clearTimeout(h);
  }, [fromToken, toToken, amount]);

  const swapDirection = () => {
    setFromToken(toToken);
    setToToken(fromToken);
    setQuote(null);
  };

  const handleExecute = async () => {
    setExecuteError(null);
    setLastResult(null);

    if (!user) {
      setExecuteError('Devi essere loggato per effettuare uno swap.');
      return;
    }
    if (!isConnected || !address) {
      openWalletModal();
      return;
    }
    if (chainId !== 56) {
      setExecuteError('Passa al network BSC Mainnet (chain 56) nel tuo wallet.');
      return;
    }
    const amt = parseFloat(amount);
    if (!amt || amt <= 0) {
      setExecuteError('Inserisci un importo valido.');
      return;
    }

    setExecuting(true);
    try {
      const res = await swapApi.execute({
        fromToken,
        toToken,
        amountIn: amt,
        userWalletAddress: address,
        slippage: Number(slippage),
      });
      setLastResult(res);
      if (!res.success) setExecuteError(res.error || res.message || 'Swap failed');
      // Refresh balances + history
      refetchNenoBalance && refetchNenoBalance();
      refreshHistory();
    } catch (err) {
      setExecuteError(err?.response?.data?.detail || err.message);
    } finally {
      setExecuting(false);
    }
  };

  const sortedTokens = useMemo(
    () => [...tokens].sort((a, b) => (a.symbol === 'NENO' ? -1 : a.symbol.localeCompare(b.symbol))),
    [tokens]
  );

  const estimatedOut = quote?.estimated_amount_out;
  const quoteSource = quote?.source;

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-purple-950 to-slate-950 text-white">
      <div className="max-w-6xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-3xl md:text-4xl font-bold flex items-center gap-3">
              <span>⚡</span> Swap On-Chain
            </h1>
            <p className="text-slate-400 mt-1">
              Real BSC swaps • 1inch + PancakeSwap + platform reserves fallback
            </p>
          </div>
          <Link
            to="/dashboard"
            className="text-sm text-slate-300 hover:text-white underline"
          >
            ← Dashboard
          </Link>
        </div>

        {/* Health badge */}
        {health && (
          <div className="mb-6 flex flex-wrap gap-2 text-xs">
            <Badge ok={health.rpc_connected}>
              RPC {health.rpc_connected ? 'connected' : 'down'}
            </Badge>
            <Badge ok={health.hot_wallet_configured}>
              Hot wallet {health.hot_wallet_configured ? 'ready' : 'missing'}
            </Badge>
            <Badge ok={health.oneinch_configured}>
              1inch {health.oneinch_configured ? 'enabled' : 'disabled'}
            </Badge>
            <span className="px-2 py-1 rounded bg-slate-800 text-slate-300">
              Max {health.max_neno_per_tx} NENO/tx • {health.max_slippage_pct}% slippage max
            </span>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
          {/* Swap card */}
          <div className="lg:col-span-3">
            <div className="bg-slate-900/70 backdrop-blur border border-slate-800 rounded-2xl p-6 shadow-2xl">
              {/* Wallet status */}
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold">Swap</h2>
                {isConnected ? (
                  <span className="text-xs px-3 py-1 rounded-full bg-emerald-900/60 text-emerald-300">
                    {formatAddress(address)} {chainId === 56 ? '• BSC' : `• chain ${chainId}`}
                  </span>
                ) : (
                  <button
                    onClick={openWalletModal}
                    className="text-xs px-3 py-1 rounded-full bg-purple-600 hover:bg-purple-500"
                  >
                    Connect wallet
                  </button>
                )}
              </div>

              {/* FROM */}
              <TokenField
                label="You pay"
                tokens={sortedTokens}
                token={fromToken}
                onTokenChange={setFromToken}
                amount={amount}
                onAmountChange={setAmount}
              />

              <div className="flex justify-center my-2">
                <button
                  onClick={swapDirection}
                  className="w-10 h-10 rounded-full bg-slate-800 hover:bg-slate-700 border border-slate-700 transition text-xl"
                  title="Invert"
                >
                  ⇅
                </button>
              </div>

              {/* TO */}
              <TokenField
                label="You receive"
                tokens={sortedTokens}
                token={toToken}
                onTokenChange={setToToken}
                amount={
                  loadingQuote
                    ? '…'
                    : estimatedOut != null
                    ? Number(estimatedOut).toLocaleString(undefined, {
                        maximumFractionDigits: 8,
                      })
                    : ''
                }
                readOnly
              />

              {/* Quote info */}
              <div className="mt-4 min-h-[52px]">
                {quoteError && (
                  <div className="text-sm text-rose-400">⚠ {quoteError}</div>
                )}
                {quote && (
                  <div className="text-xs text-slate-400 space-y-1">
                    <div>
                      Rate: 1 {fromToken} ≈{' '}
                      <span className="text-slate-200">
                        {Number(quote.rate).toLocaleString(undefined, {
                          maximumFractionDigits: 8,
                        })}{' '}
                        {toToken}
                      </span>
                    </div>
                    <div>
                      Source:{' '}
                      <span className="text-slate-200 uppercase">
                        {quoteSource}
                      </span>
                      {quote.note && (
                        <span className="ml-2 text-amber-400">({quote.note})</span>
                      )}
                    </div>
                  </div>
                )}
              </div>

              {/* Slippage */}
              <div className="mt-4 flex items-center gap-2 text-xs">
                <span className="text-slate-400">Slippage:</span>
                {[0.5, 0.8, 1.0, 2.0].map((s) => (
                  <button
                    key={s}
                    onClick={() => setSlippage(s)}
                    className={`px-2 py-1 rounded border ${
                      Number(slippage) === s
                        ? 'border-purple-500 bg-purple-900/40 text-white'
                        : 'border-slate-700 text-slate-300 hover:border-slate-500'
                    }`}
                  >
                    {s}%
                  </button>
                ))}
                <input
                  type="number"
                  step="0.1"
                  min="0.1"
                  max="5"
                  value={slippage}
                  onChange={(e) => setSlippage(e.target.value)}
                  className="w-20 px-2 py-1 rounded border border-slate-700 bg-slate-800 text-white"
                />
              </div>

              {/* Action */}
              <button
                onClick={handleExecute}
                disabled={
                  executing ||
                  !amount ||
                  parseFloat(amount) <= 0 ||
                  fromToken === toToken
                }
                className="mt-6 w-full py-3 rounded-xl font-semibold text-white bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-500 hover:to-pink-500 disabled:opacity-40 disabled:cursor-not-allowed transition"
              >
                {!user
                  ? 'Login to swap'
                  : !isConnected
                  ? 'Connect wallet to swap'
                  : executing
                  ? 'Processing on-chain…'
                  : `Swap ${fromToken} → ${toToken}`}
              </button>

              {executeError && (
                <div className="mt-4 p-3 rounded bg-rose-950/50 border border-rose-800 text-sm text-rose-300">
                  ⚠ {executeError}
                </div>
              )}

              {lastResult && lastResult.success && (
                <div className="mt-4 p-4 rounded bg-emerald-950/40 border border-emerald-700 text-sm space-y-2">
                  <div className="flex items-center gap-2">
                    <span
                      className={`inline-block text-[10px] px-2 py-0.5 rounded ${
                        TIER_STYLES[lastResult.tier] || 'bg-slate-700'
                      }`}
                    >
                      {lastResult.tier_label}
                    </span>
                    <span className="text-emerald-300">✔ Swap confirmed</span>
                  </div>
                  <div className="text-slate-200">
                    {lastResult.amount_in} {lastResult.from_token} →{' '}
                    <strong>
                      {Number(lastResult.amount_out).toLocaleString(undefined, {
                        maximumFractionDigits: 8,
                      })}{' '}
                      {lastResult.to_token}
                    </strong>
                  </div>
                  {lastResult.tx_hash && (
                    <a
                      href={explorerTx(lastResult.tx_hash)}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-block text-emerald-400 underline text-xs break-all"
                    >
                      View on BscScan ↗ {lastResult.tx_hash}
                    </a>
                  )}
                  {lastResult.queued && (
                    <div className="text-amber-300 text-xs">
                      ⏳ On-chain delivery queued — your platform balance has been
                      credited instantly.
                    </div>
                  )}
                  <div className="text-xs text-slate-400">
                    {TIER_HINT[lastResult.tier]}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* History */}
          <div className="lg:col-span-2">
            <div className="bg-slate-900/70 backdrop-blur border border-slate-800 rounded-2xl p-6 shadow-xl h-full">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold">Recent swaps</h2>
                <button
                  onClick={refreshHistory}
                  className="text-xs text-slate-400 hover:text-white"
                >
                  Refresh
                </button>
              </div>
              {!user && (
                <p className="text-sm text-slate-400">
                  Login to view your swap history.
                </p>
              )}
              {user && history.length === 0 && (
                <p className="text-sm text-slate-400">
                  No swaps yet. Your transactions will appear here.
                </p>
              )}
              <ul className="space-y-2">
                {history.map((h) => (
                  <li
                    key={h.swap_id}
                    className="p-3 rounded bg-slate-800/70 border border-slate-700 text-xs"
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-mono text-slate-300">
                        {h.from_token} → {h.to_token}
                      </span>
                      <StatusBadge status={h.status} tier={h.tier} />
                    </div>
                    <div className="text-slate-400">
                      {h.amount_in} {h.from_token}
                      {h.amount_out && (
                        <>
                          {' '}
                          →{' '}
                          <span className="text-slate-200">
                            {Number(h.amount_out).toLocaleString(undefined, {
                              maximumFractionDigits: 6,
                            })}{' '}
                            {h.to_token}
                          </span>
                        </>
                      )}
                    </div>
                    {h.tx_hash && (
                      <a
                        href={explorerTx(h.tx_hash)}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-purple-400 underline break-all"
                      >
                        {h.tx_hash.slice(0, 14)}…{h.tx_hash.slice(-6)}
                      </a>
                    )}
                    <div className="text-[10px] text-slate-500 mt-1">
                      {h.created_at?.slice(0, 19).replace('T', ' ')}
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function TokenField({ label, tokens, token, onTokenChange, amount, onAmountChange, readOnly }) {
  return (
    <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-4">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs text-slate-400 uppercase tracking-wide">
          {label}
        </span>
      </div>
      <div className="flex items-center gap-3">
        <input
          type={readOnly ? 'text' : 'number'}
          placeholder="0.0"
          step="any"
          min="0"
          readOnly={readOnly}
          value={amount}
          onChange={onAmountChange ? (e) => onAmountChange(e.target.value) : undefined}
          className="flex-1 bg-transparent text-2xl font-semibold outline-none placeholder-slate-600"
        />
        <select
          value={token}
          onChange={(e) => onTokenChange(e.target.value)}
          className="bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-purple-500"
        >
          {tokens.map((t) => (
            <option key={t.symbol} value={t.symbol}>
              {t.logo} {t.symbol} — {t.name}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}

function Badge({ ok, children }) {
  return (
    <span
      className={`px-2 py-1 rounded ${
        ok
          ? 'bg-emerald-900/50 text-emerald-300'
          : 'bg-rose-900/50 text-rose-300'
      }`}
    >
      {ok ? '●' : '○'} {children}
    </span>
  );
}

function StatusBadge({ status, tier }) {
  const map = {
    completed: 'bg-emerald-700',
    queued: 'bg-amber-700',
    pending: 'bg-slate-600',
    failed: 'bg-rose-700',
  };
  const cls = map[status] || 'bg-slate-600';
  return (
    <span className={`text-[10px] px-2 py-0.5 rounded ${cls}`}>
      {status}
      {tier ? ` • ${tier}` : ''}
    </span>
  );
}
