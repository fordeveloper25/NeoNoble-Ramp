import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { useAccount, useChainId, useSwitchChain, useSendTransaction, useWaitForTransactionReceipt } from 'wagmi';
import { useAuth } from '../context/AuthContext';
import { useWeb3 } from '../context/Web3Context';
import { swapApi } from '../api/swap';
import { parseUnits } from 'viem';

const BSC_CHAIN_ID = 56;
const LOW_GAS_THRESHOLD = parseUnits('0.002', 18); // 0.002 BNB in wei

function explorerTx(hash) {
  return hash ? `https://bscscan.com/tx/${hash}` : null;
}

export default function Swap() {
  const { user } = useAuth();
  const { openWalletModal, formatAddress, balance } = useWeb3();
  const { address, isConnected } = useAccount();
  const chainId = useChainId();
  const { switchChain } = useSwitchChain();

  const {
    sendTransactionAsync,
    isPending: isSending,
    reset: resetSend,
  } = useSendTransaction();

  const [tokens, setTokens] = useState([]);
  const [fromToken, setFromToken] = useState('NENO');
  const [toToken, setToToken] = useState('USDT');
  const [amount, setAmount] = useState('');
  const [slippage, setSlippage] = useState(0.8);

  const [quote, setQuote] = useState(null);
  const [loadingQuote, setLoadingQuote] = useState(false);
  const [quoteError, setQuoteError] = useState(null);

  // flow state machine: idle | building | approving | swapping | tracking | done | error
  const [flow, setFlow] = useState('idle');
  const [flowMessage, setFlowMessage] = useState('');
  const [lastSwap, setLastSwap] = useState(null);
  const [txHash, setTxHash] = useState(null);
  const [error, setError] = useState(null);

  const [history, setHistory] = useState([]);
  const [health, setHealth] = useState(null);

  // Wait for the swap tx receipt when we have a hash
  const { data: receipt, isLoading: waitingReceipt } = useWaitForTransactionReceipt({
    hash: txHash,
    query: { enabled: !!txHash },
  });

  // --- load tokens + health -----------------------------------------------
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

  // --- history ------------------------------------------------------------
  const refreshHistory = useCallback(async () => {
    if (!user) return;
    try {
      const h = await swapApi.history(20);
      setHistory(h.history || []);
    } catch (_) {}
  }, [user]);
  useEffect(() => { refreshHistory(); }, [refreshHistory]);

  // --- auto-quote ---------------------------------------------------------
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

  // --- when receipt arrives, finalize the swap ----------------------------
  useEffect(() => {
    if (!receipt || !lastSwap) return;
    (async () => {
      try {
        setFlow('tracking');
        setFlowMessage('Confirming on BscScan…');
        const tracked = await swapApi.track(lastSwap.swap_id, receipt.transactionHash);
        setFlow(tracked.status === 'success' ? 'done' : 'error');
        setFlowMessage(
          tracked.status === 'success'
            ? '✔ Swap confirmed on-chain.'
            : '✗ Transaction reverted on-chain.'
        );
        refreshHistory();
      } catch (err) {
        setFlow('error');
        setError(err?.response?.data?.detail || err.message);
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [receipt]);

  // --- the real action ----------------------------------------------------
  const swapDirection = () => {
    setFromToken(toToken);
    setToToken(fromToken);
    setQuote(null);
    setTxHash(null);
    setLastSwap(null);
    setFlow('idle');
    setFlowMessage('');
    setError(null);
    resetSend && resetSend();
  };

  const ensureBsc = async () => {
    if (chainId !== BSC_CHAIN_ID) {
      try {
        await switchChain({ chainId: BSC_CHAIN_ID });
      } catch (err) {
        throw new Error('Please switch your wallet to BSC Mainnet.');
      }
    }
  };

  const handleSwap = async () => {
    setError(null);
    setTxHash(null);
    setLastSwap(null);
    setFlow('idle');
    setFlowMessage('');

    if (!user) {
      setError('Please log in first.');
      return;
    }
    if (!isConnected || !address) {
      openWalletModal();
      return;
    }
    const amt = parseFloat(amount);
    if (!amt || amt <= 0) {
      setError('Enter a valid amount.');
      return;
    }

    try {
      await ensureBsc();

      // 1) Build calldata from backend
      setFlow('building');
      setFlowMessage('Fetching best route…');
      const built = await swapApi.build({
        fromToken,
        toToken,
        amountIn: amt,
        userWalletAddress: address,
        slippage: Number(slippage),
      });
      setLastSwap(built);

      // 2) If ERC-20 approval is required, ask the user to sign it first
      if (built.needs_approve && built.approve_calldata) {
        setFlow('approving');
        setFlowMessage(`Sign the approval for ${built.from_token} in your wallet…`);
        const approveHash = await sendTransactionAsync({
          to: built.approve_calldata.to,
          data: built.approve_calldata.data,
          value: BigInt(built.approve_calldata.value || '0x0'),
        });
        // We don't strictly need to wait here — most RPCs will surface the
        // updated allowance quickly.  Give it 3s for safety.
        await new Promise((r) => setTimeout(r, 3000));
        setFlowMessage(`Approval sent (${approveHash.slice(0, 10)}…). Now sign the swap…`);
      }

      // 3) Send the actual swap tx
      setFlow('swapping');
      setFlowMessage('Sign the swap transaction in your wallet…');
      const hash = await sendTransactionAsync({
        to: built.to,
        data: built.data,
        value: BigInt(built.value || '0x0'),
      });
      setTxHash(hash);
      setFlowMessage('Swap submitted. Waiting for confirmation…');
      // The useWaitForTransactionReceipt effect above will handle tracking.
    } catch (err) {
      const msg =
        err?.shortMessage ||
        err?.response?.data?.detail ||
        err?.message ||
        'Unknown error';
      setError(msg);
      setFlow('error');
    }
  };

  const sortedTokens = useMemo(
    () => [...tokens].sort((a, b) => (a.symbol === 'NENO' ? -1 : a.symbol.localeCompare(b.symbol))),
    [tokens]
  );

  const estimatedOut = quote?.estimated_amount_out;
  const quoteSource = quote?.source;
  const buttonDisabled =
    !amount ||
    parseFloat(amount) <= 0 ||
    fromToken === toToken ||
    flow === 'building' ||
    flow === 'approving' ||
    flow === 'swapping' ||
    flow === 'tracking' ||
    isSending ||
    waitingReceipt;

  // Check if user has low BNB balance for gas
  const hasLowGas = isConnected && balance?.value && BigInt(balance.value) < LOW_GAS_THRESHOLD;

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
              Real user-signed swaps on BSC • 1inch + PancakeSwap • funds go straight to your wallet
            </p>
          </div>
          <div className="flex items-center gap-3">
            <Link to="/help" className="text-sm text-slate-300 hover:text-white underline">
              ❓ Aiuto
            </Link>
            <Link to="/dashboard" className="text-sm text-slate-300 hover:text-white underline">
              ← Dashboard
            </Link>
          </div>
        </div>

        {/* Low BNB Gas Warning Banner */}
        {hasLowGas && (
          <div className="mb-6 p-4 rounded-xl bg-gradient-to-r from-amber-900/40 to-orange-900/40 border border-amber-600/50 backdrop-blur">
            <div className="flex items-start gap-3">
              <span className="text-2xl">⚠️</span>
              <div className="flex-1">
                <h3 className="font-semibold text-amber-200 mb-1">
                  Saldo BNB Basso
                </h3>
                <p className="text-sm text-amber-100/90 leading-relaxed">
                  Il tuo wallet ha meno di 0.002 BNB. Hai bisogno di BNB per pagare le commissioni gas delle transazioni su BSC.
                  {' '}
                  <span className="font-medium">
                    Ti consigliamo di aggiungere almeno 0.005-0.01 BNB
                  </span>
                  {' '}
                  al tuo wallet prima di effettuare swap.
                </p>
                <p className="text-xs text-amber-200/70 mt-2">
                  💡 Saldo attuale: {balance?.formatted ? `${parseFloat(balance.formatted).toFixed(6)} ${balance.symbol}` : '—'}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Health badges */}
        {health && (
          <div className="mb-6 flex flex-wrap gap-2 text-xs">
            <Badge ok={health.rpc_connected}>
              RPC {health.rpc_connected ? 'connected' : 'down'}
            </Badge>
            <Badge ok={health.oneinch_configured}>
              1inch {health.oneinch_configured ? 'enabled' : 'disabled'}
            </Badge>
            <span className="px-2 py-1 rounded bg-slate-800 text-slate-300">
              BSC chain {health.chain_id} • max {health.max_slippage_pct}% slippage
            </span>
            <span className="px-2 py-1 rounded bg-slate-800 text-slate-300">
              User-signed mode (you pay gas)
            </span>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
          {/* Swap card */}
          <div className="lg:col-span-3">
            <div className="bg-slate-900/70 backdrop-blur border border-slate-800 rounded-2xl p-6 shadow-2xl">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold">Swap</h2>
                {isConnected ? (
                  <span className="text-xs px-3 py-1 rounded-full bg-emerald-900/60 text-emerald-300">
                    {formatAddress ? formatAddress(address) : address}
                    {chainId === BSC_CHAIN_ID ? ' • BSC' : ` • chain ${chainId}`}
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

              <TokenField
                label="You receive (estimated)"
                tokens={sortedTokens}
                token={toToken}
                onTokenChange={setToToken}
                amount={
                  loadingQuote
                    ? '…'
                    : estimatedOut != null
                    ? Number(estimatedOut).toLocaleString(undefined, { maximumFractionDigits: 8 })
                    : ''
                }
                readOnly
              />

              <div className="mt-4 min-h-[52px]">
                {quoteError && <div className="text-sm text-rose-400">⚠ {quoteError}</div>}
                {quote && (
                  <div className="text-xs text-slate-400 space-y-1">
                    <div>
                      Rate: 1 {fromToken} ≈{' '}
                      <span className="text-slate-200">
                        {Number(quote.rate).toLocaleString(undefined, { maximumFractionDigits: 8 })}{' '}
                        {toToken}
                      </span>
                    </div>
                    <div>
                      Route: <span className="text-slate-200 uppercase">{quoteSource}</span>
                      {quote.note && <span className="ml-2 text-amber-400">({quote.note})</span>}
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
                onClick={handleSwap}
                disabled={buttonDisabled}
                className="mt-6 w-full py-3 rounded-xl font-semibold text-white bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-500 hover:to-pink-500 disabled:opacity-40 disabled:cursor-not-allowed transition"
              >
                {!user
                  ? 'Login to swap'
                  : !isConnected
                  ? 'Connect wallet to swap'
                  : flow === 'building'
                  ? 'Fetching best route…'
                  : flow === 'approving'
                  ? 'Waiting for approval signature…'
                  : flow === 'swapping'
                  ? 'Waiting for swap signature…'
                  : flow === 'tracking' || waitingReceipt
                  ? 'Confirming on-chain…'
                  : `Swap ${fromToken} → ${toToken}`}
              </button>

              {/* Flow status */}
              {flowMessage && flow !== 'done' && (
                <div className="mt-4 p-3 rounded bg-slate-800/70 border border-slate-700 text-sm text-slate-200 flex items-center gap-2">
                  <Spinner /> {flowMessage}
                </div>
              )}

              {/* Error */}
              {error && (
                <div className="mt-4 p-3 rounded bg-rose-950/50 border border-rose-800 text-sm text-rose-300">
                  ⚠ {error}
                </div>
              )}

              {/* Success */}
              {flow === 'done' && receipt && (
                <div className="mt-4 p-4 rounded bg-emerald-950/40 border border-emerald-700 text-sm space-y-2">
                  <div className="text-emerald-300 font-medium">✔ Swap confirmed on BSC</div>
                  <div className="text-slate-200">
                    {lastSwap?.amount_in_human} {lastSwap?.from_token} →{' '}
                    <strong>
                      ≈{' '}
                      {Number(lastSwap?.estimated_amount_out_human).toLocaleString(undefined, {
                        maximumFractionDigits: 8,
                      })}{' '}
                      {lastSwap?.to_token}
                    </strong>
                  </div>
                  <a
                    href={explorerTx(receipt.transactionHash)}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-block text-emerald-400 underline text-xs break-all"
                  >
                    View on BscScan ↗ {receipt.transactionHash}
                  </a>
                </div>
              )}

              <p className="mt-4 text-xs text-slate-500">
                ℹ You sign the transaction with your own wallet; output tokens arrive directly in your wallet. You need a small amount of BNB for gas.
              </p>
            </div>
          </div>

          {/* History */}
          <div className="lg:col-span-2">
            <div className="bg-slate-900/70 backdrop-blur border border-slate-800 rounded-2xl p-6 shadow-xl h-full">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold">Recent swaps</h2>
                <button onClick={refreshHistory} className="text-xs text-slate-400 hover:text-white">
                  Refresh
                </button>
              </div>
              {!user && <p className="text-sm text-slate-400">Login to view your swap history.</p>}
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
                      <StatusBadge status={h.status} source={h.source} />
                    </div>
                    <div className="text-slate-400">
                      {h.amount_in} {h.from_token}
                      {h.amount_out_estimate && (
                        <>
                          {' '}
                          →{' '}
                          <span className="text-slate-200">
                            ≈{' '}
                            {Number(h.amount_out_estimate).toLocaleString(undefined, {
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
        <span className="text-xs text-slate-400 uppercase tracking-wide">{label}</span>
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
        ok ? 'bg-emerald-900/50 text-emerald-300' : 'bg-rose-900/50 text-rose-300'
      }`}
    >
      {ok ? '●' : '○'} {children}
    </span>
  );
}

function Spinner() {
  return (
    <span className="inline-block w-3 h-3 border-2 border-slate-500 border-t-white rounded-full animate-spin" />
  );
}

function StatusBadge({ status, source }) {
  const map = {
    success: 'bg-emerald-700',
    built: 'bg-blue-700',
    pending: 'bg-slate-600',
    failed: 'bg-rose-700',
  };
  const cls = map[status] || 'bg-slate-600';
  return (
    <span className={`text-[10px] px-2 py-0.5 rounded ${cls}`}>
      {status}
      {source ? ` • ${source}` : ''}
    </span>
  );
}
