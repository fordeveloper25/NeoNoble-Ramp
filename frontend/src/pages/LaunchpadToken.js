import React, { useEffect, useState, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useAccount, useChainId, useSwitchChain, useSendTransaction, useWaitForTransactionReceipt } from 'wagmi';
import { useAuth } from '../context/AuthContext';
import { useWeb3 } from '../context/Web3Context';
import { launchpadApi } from '../api/launchpad';

const BSC_CHAIN_ID = 56;

export default function LaunchpadToken() {
  const { address: tokenAddress } = useParams();
  const { user } = useAuth();
  const { openWalletModal } = useWeb3();
  const { address: userAddress, isConnected } = useAccount();
  const chainId = useChainId();
  const { switchChain } = useSwitchChain();
  const { sendTransactionAsync } = useSendTransaction();

  const [token, setToken] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [mode, setMode] = useState('buy'); // buy | sell
  const [amount, setAmount] = useState('');
  const [slippage, setSlippage] = useState(3);
  const [quote, setQuote] = useState(null);
  const [quoteLoading, setQuoteLoading] = useState(false);
  const [quoteError, setQuoteError] = useState(null);

  const [flow, setFlow] = useState('idle'); // idle | building | signing | confirming | done | error
  const [txHash, setTxHash] = useState(null);
  const [flowMsg, setFlowMsg] = useState('');

  const { data: receipt } = useWaitForTransactionReceipt({
    hash: txHash,
    query: { enabled: !!txHash },
  });

  const refresh = useCallback(async () => {
    try {
      const t = await launchpadApi.detail(tokenAddress);
      setToken(t);
    } catch (e) {
      setError(e?.response?.data?.detail || e.message);
    } finally {
      setLoading(false);
    }
  }, [tokenAddress]);

  useEffect(() => { refresh(); }, [refresh]);

  // refresh dopo conferma tx
  useEffect(() => {
    if (receipt) {
      setFlow('done');
      setFlowMsg('✔ Transazione confermata.');
      refresh();
    }
  }, [receipt, refresh]);

  // auto-quote
  useEffect(() => {
    const n = parseFloat(amount);
    if (!n || n <= 0) { setQuote(null); setQuoteError(null); return; }
    setQuoteLoading(true); setQuoteError(null);
    const h = setTimeout(async () => {
      try {
        const q = mode === 'buy'
          ? await launchpadApi.quoteBuy(tokenAddress, n)
          : await launchpadApi.quoteSell(tokenAddress, n);
        setQuote(q);
      } catch (e) {
        setQuote(null);
        setQuoteError(e?.response?.data?.detail || e.message);
      } finally { setQuoteLoading(false); }
    }, 400);
    return () => clearTimeout(h);
  }, [amount, mode, tokenAddress]);

  const handleTrade = async () => {
    setError(null); setFlowMsg(''); setTxHash(null);
    if (!user) { setError('Login richiesto.'); return; }
    if (!isConnected || !userAddress) { openWalletModal(); return; }
    if (chainId !== BSC_CHAIN_ID) {
      try { await switchChain({ chainId: BSC_CHAIN_ID }); }
      catch { setError('Passa a BSC Mainnet.'); return; }
    }
    const n = parseFloat(amount);
    if (!n || n <= 0) { setError('Importo non valido.'); return; }

    try {
      setFlow('building');
      setFlowMsg(mode === 'buy' ? 'Preparazione buy tx…' : 'Preparazione sell tx…');
      const built = mode === 'buy'
        ? await launchpadApi.buildBuy({
            tokenAddress, bnbIn: n, userWalletAddress: userAddress, slippagePct: Number(slippage),
          })
        : await launchpadApi.buildSell({
            tokenAddress, tokensIn: n, userWalletAddress: userAddress, slippagePct: Number(slippage),
          });

      setFlow('signing');
      setFlowMsg('Firma nel wallet…');
      const hash = await sendTransactionAsync({
        to: built.to,
        data: built.data,
        value: BigInt(built.value || '0x0'),
      });
      setTxHash(hash);
      setFlow('confirming');
      setFlowMsg('In attesa di conferma on-chain…');
    } catch (err) {
      setError(err?.shortMessage || err?.response?.data?.detail || err?.message || 'Errore');
      setFlow('error');
    }
  };

  if (loading) return (
    <Center><div className="text-slate-400">Caricamento token…</div></Center>
  );
  if (error && !token) return (
    <Center><div className="text-rose-400">⚠ {error}</div></Center>
  );
  if (!token) return null;

  const priceStr = token.price_bnb.toExponential(4);
  const progress = Math.min(100, token.graduation_progress_pct || 0);

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-purple-950 to-slate-950 text-white">
      <div className="max-w-6xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-3xl md:text-4xl font-bold">
              {token.name} <span className="text-slate-500 font-mono text-2xl">${token.symbol}</span>
            </h1>
            <a
              href={token.explorer_url}
              target="_blank" rel="noopener noreferrer"
              className="text-xs text-slate-400 hover:text-white underline break-all"
            >
              {token.address}
            </a>
          </div>
          <Link to="/launchpad" className="text-sm text-slate-300 hover:text-white underline">
            ← Launchpad
          </Link>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
          <Stat label="Price" value={`${priceStr} BNB`} />
          <Stat label="Market Cap" value={`${token.market_cap_bnb.toFixed(4)} BNB`} />
          <Stat label="Raised" value={`${token.real_bnb_reserve_human.toFixed(4)} BNB`} />
          <Stat label="Supply" value={`${token.total_supply_human.toLocaleString()} ${token.symbol}`} />
        </div>

        {/* Graduation progress */}
        <div className="mb-6 p-4 rounded-2xl bg-slate-900/70 backdrop-blur border border-slate-800">
          <div className="flex justify-between text-sm mb-2">
            <span className="text-slate-400">Graduation progress</span>
            <span className="text-white font-semibold">
              {token.real_bnb_reserve_human.toFixed(4)} / {token.graduation_bnb} BNB ({progress.toFixed(1)}%)
            </span>
          </div>
          <div className="h-3 rounded-full bg-slate-800 overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-purple-500 via-pink-500 to-amber-400 transition-all"
              style={{ width: `${progress}%` }}
            />
          </div>
          {token.graduated && (
            <p className="mt-2 text-emerald-300 text-sm" data-testid="token-graduated">
              🎓 Questo token si e' graduato. La curva e' chiusa — 200M token sono stati riservati per la creazione del LP PancakeSwap.
            </p>
          )}
        </div>

        {/* Trade card */}
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
          <div className="lg:col-span-3">
            <div className="bg-slate-900/70 backdrop-blur border border-slate-800 rounded-2xl p-6 shadow-2xl">
              {/* Mode tabs */}
              <div className="flex gap-2 mb-4 bg-slate-800/50 p-1 rounded-lg">
                <button
                  data-testid="launchpad-tab-buy"
                  onClick={() => { setMode('buy'); setAmount(''); setQuote(null); }}
                  className={`flex-1 py-2 rounded ${mode === 'buy' ? 'bg-emerald-600 text-white' : 'text-slate-400 hover:text-white'}`}
                >Buy</button>
                <button
                  data-testid="launchpad-tab-sell"
                  onClick={() => { setMode('sell'); setAmount(''); setQuote(null); }}
                  disabled={token.graduated}
                  className={`flex-1 py-2 rounded ${mode === 'sell' ? 'bg-rose-600 text-white' : 'text-slate-400 hover:text-white'} disabled:opacity-40`}
                >Sell</button>
              </div>

              <label className="block text-xs text-slate-400 uppercase tracking-wide mb-1">
                {mode === 'buy' ? 'BNB da spendere' : `${token.symbol} da vendere`}
              </label>
              <input
                type="number"
                step="any"
                min="0"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                placeholder="0.0"
                data-testid={`launchpad-amount-${mode}`}
                className="w-full px-4 py-3 rounded-lg bg-slate-800 border border-slate-700 focus:border-purple-500 outline-none text-2xl font-semibold"
              />

              {/* Quote */}
              <div className="mt-4 min-h-[60px] text-sm">
                {quoteLoading && <span className="text-slate-400">Quoting…</span>}
                {quoteError && <div className="text-rose-400">⚠ {quoteError}</div>}
                {quote && mode === 'buy' && (
                  <div className="space-y-1 text-slate-300">
                    <div>Ricevi: <strong className="text-white">{quote.tokens_out_human.toLocaleString(undefined, { maximumFractionDigits: 4 })} {token.symbol}</strong></div>
                    <div className="text-xs text-slate-500">
                      Prezzo effettivo: {quote.effective_price_bnb_per_token.toExponential(4)} BNB per {token.symbol}
                    </div>
                  </div>
                )}
                {quote && mode === 'sell' && (
                  <div className="space-y-1 text-slate-300">
                    <div>Ricevi: <strong className="text-white">{quote.user_receives_human.toFixed(8)} BNB</strong></div>
                    <div className="text-xs text-slate-500">
                      Lordo curva: {quote.bnb_out_gross_human.toFixed(8)} BNB (fees platform+creator 2% sottratte)
                    </div>
                  </div>
                )}
              </div>

              {/* Slippage */}
              <div className="mt-4 flex items-center gap-2 text-xs">
                <span className="text-slate-400">Slippage:</span>
                {[1, 3, 5, 10].map((s) => (
                  <button
                    key={s}
                    onClick={() => setSlippage(s)}
                    className={`px-2 py-1 rounded border ${
                      Number(slippage) === s
                        ? 'border-purple-500 bg-purple-900/40 text-white'
                        : 'border-slate-700 text-slate-300 hover:border-slate-500'
                    }`}
                  >{s}%</button>
                ))}
                <input
                  type="number" step="0.1" min="0.1" max="50" value={slippage}
                  onChange={(e) => setSlippage(e.target.value)}
                  className="w-20 px-2 py-1 rounded border border-slate-700 bg-slate-800"
                />
              </div>

              <button
                onClick={handleTrade}
                disabled={!amount || parseFloat(amount) <= 0 || flow === 'building' || flow === 'signing' || flow === 'confirming' || (mode === 'sell' && token.graduated)}
                data-testid={`launchpad-${mode}-submit`}
                className={`mt-6 w-full py-3 rounded-xl font-semibold text-white ${
                  mode === 'buy'
                    ? 'bg-gradient-to-r from-emerald-600 to-green-600 hover:from-emerald-500 hover:to-green-500'
                    : 'bg-gradient-to-r from-rose-600 to-red-600 hover:from-rose-500 hover:to-red-500'
                } disabled:opacity-40 disabled:cursor-not-allowed transition`}
              >
                {!user ? 'Login'
                  : !isConnected ? 'Connetti wallet'
                  : flow === 'building' ? 'Preparo…'
                  : flow === 'signing' ? 'Firma nel wallet…'
                  : flow === 'confirming' ? 'Attendo conferma…'
                  : mode === 'buy' ? `Buy ${token.symbol}` : `Sell ${token.symbol}`}
              </button>

              {flowMsg && flow !== 'done' && (
                <div className="mt-3 p-3 rounded bg-slate-800/70 border border-slate-700 text-sm text-slate-200">
                  {flowMsg}
                </div>
              )}
              {error && (
                <div className="mt-3 p-3 rounded bg-rose-950/50 border border-rose-800 text-sm text-rose-300">
                  ⚠ {error}
                </div>
              )}
              {txHash && (
                <div className="mt-3 p-3 rounded bg-emerald-950/40 border border-emerald-700 text-sm">
                  <a href={`https://bscscan.com/tx/${txHash}`} target="_blank" rel="noopener noreferrer"
                     className="text-emerald-300 underline break-all">
                    {txHash} ↗
                  </a>
                </div>
              )}
            </div>
          </div>

          <div className="lg:col-span-2">
            <div className="bg-slate-900/70 backdrop-blur border border-slate-800 rounded-2xl p-6 shadow-xl space-y-3 text-sm">
              <h3 className="font-semibold text-lg mb-2">Info</h3>
              <InfoRow label="Creator" value={<MonoAddr a={token.creator} />} />
              <InfoRow label="Contract" value={<MonoAddr a={token.address} />} />
              {token.metadata_uri && (
                <InfoRow label="Metadata" value={
                  <a href={token.metadata_uri} target="_blank" rel="noopener noreferrer"
                     className="text-purple-400 underline break-all">{token.metadata_uri}</a>
                } />
              )}
              <InfoRow label="Graduated" value={token.graduated ? 'Sì' : 'No'} />
              <InfoRow label="Total Supply" value={`${token.total_supply_human.toLocaleString()} ${token.symbol}`} />
              <InfoRow label="Virtual BNB" value={`${(Number(token.virtual_bnb_reserve) / 1e18).toFixed(4)}`} />
              <InfoRow label="Real BNB in curve" value={`${token.real_bnb_reserve_human.toFixed(6)}`} />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function Center({ children }) {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-purple-950 to-slate-950 text-white flex items-center justify-center">
      {children}
    </div>
  );
}
function Stat({ label, value }) {
  return (
    <div className="p-4 rounded-xl bg-slate-900/70 backdrop-blur border border-slate-800">
      <div className="text-xs text-slate-500 uppercase tracking-wide">{label}</div>
      <div className="text-lg font-semibold mt-1">{value}</div>
    </div>
  );
}
function InfoRow({ label, value }) {
  return (
    <div className="flex justify-between items-start gap-3">
      <span className="text-slate-500">{label}</span>
      <span className="text-right">{value}</span>
    </div>
  );
}
function MonoAddr({ a }) {
  if (!a) return null;
  return (
    <a href={`https://bscscan.com/address/${a}`} target="_blank" rel="noopener noreferrer"
       className="font-mono text-xs text-purple-400 underline break-all">
      {a.slice(0, 8)}…{a.slice(-6)}
    </a>
  );
}
