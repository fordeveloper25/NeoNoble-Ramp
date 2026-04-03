import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ArrowLeft, ArrowRightLeft, Loader2, CreditCard, Building,
  Clock, TrendingUp, TrendingDown, Plus, Repeat,
  Wallet, CheckCircle, ExternalLink, Copy, Check, AlertTriangle, Shield,
  QrCode, ArrowDownToLine
} from 'lucide-react';
import { QRCodeSVG } from 'qrcode.react';
import { useWeb3 } from '../context/Web3Context';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || '';

/* ── HTTP helpers using XMLHttpRequest (bypasses fetch body interception) ── */

function xhrGet(url, options = {}) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open('GET', url, true);
    if (options.headers) {
      Object.entries(options.headers).forEach(([k, v]) => xhr.setRequestHeader(k, v));
    }
    if (options.signal) {
      options.signal.addEventListener('abort', () => { xhr.abort(); reject(new DOMException('Aborted', 'AbortError')); });
    }
    xhr.onload = () => {
      try { resolve(JSON.parse(xhr.responseText)); } catch { resolve({ detail: `Errore ${xhr.status}` }); }
    };
    xhr.onerror = () => resolve({ detail: 'Connessione di rete fallita' });
    xhr.send();
  });
}

function xhrPost(url, body, token) {
  return new Promise((resolve) => {
    const xhr = new XMLHttpRequest();
    xhr.open('POST', url, true);
    xhr.setRequestHeader('Content-Type', 'application/json');
    if (token) xhr.setRequestHeader('Authorization', `Bearer ${token}`);
    xhr.onload = () => {
      let data;
      try { data = JSON.parse(xhr.responseText); } catch { data = { detail: `Errore ${xhr.status}` }; }
      resolve({ ok: xhr.status >= 200 && xhr.status < 300, status: xhr.status, data });
    };
    xhr.onerror = () => resolve({ ok: false, status: 0, data: { detail: 'Connessione di rete fallita' } });
    xhr.send(JSON.stringify(body));
  });
}

function xhrFetch(url, options = {}) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open(options.method || 'GET', url, true);
    if (options.headers) {
      Object.entries(options.headers).forEach(([k, v]) => xhr.setRequestHeader(k, v));
    }
    if (options.signal) {
      options.signal.addEventListener('abort', () => { xhr.abort(); reject(new DOMException('Aborted', 'AbortError')); });
    }
    xhr.onload = () => {
      try { resolve(JSON.parse(xhr.responseText)); } catch { resolve({}); }
    };
    xhr.onerror = () => resolve({});
    xhr.send(options.body || null);
  });
}

const BUILTIN_ASSETS = ['EUR', 'BNB', 'ETH', 'USDT', 'BTC', 'USDC', 'MATIC', 'USD'];

export default function NenoExchange() {
  const navigate = useNavigate();
  const {
    address, isConnected, balance: onChainBalance, currentChain, formatAddress,
    nenoOnChainBalance, refetchNenoBalance,
    transferNeno, isTxPending, isWaitingReceipt, txHash, resetTx,
  } = useWeb3();

  const [tab, setTab] = useState('buy');
  const [asset, setAsset] = useState('EUR');
  const [nenoAmount, setNenoAmount] = useState('1');
  const [quote, setQuote] = useState(null);
  const [marketInfo, setMarketInfo] = useState(null);
  const [priceData, setPriceData] = useState(null);
  const [txs, setTxs] = useState([]);
  const [balances, setBalances] = useState({});
  const [cards, setCards] = useState([]);
  const [ibans, setIbans] = useState([]);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [customTokens, setCustomTokens] = useState([]);
  const [allAssets, setAllAssets] = useState(BUILTIN_ASSETS);
  const [copiedHash, setCopiedHash] = useState(null);
  const [platformWallet, setPlatformWallet] = useState(null);
  const [txStep, setTxStep] = useState(null); // 'signing' | 'confirming' | 'verifying' | null

  // Off-ramp
  const [offrampDest, setOfframpDest] = useState('card');
  const [selectedCard, setSelectedCard] = useState('');
  const [offrampIban, setOfframpIban] = useState('');
  const [offrampName, setOfframpName] = useState('');
  const [copiedAddr, setCopiedAddr] = useState(false);

  // Swap
  const [swapFrom, setSwapFrom] = useState('NENO');
  const [swapTo, setSwapTo] = useState('ETH');
  const [swapAmt, setSwapAmt] = useState('1');
  const [swapQuote, setSwapQuote] = useState(null);

  // Create Token
  const [newSym, setNewSym] = useState('');
  const [newName, setNewName] = useState('');
  const [newPrice, setNewPrice] = useState('');
  const [newSupply, setNewSupply] = useState('1000000');

  const abortRef = useRef(null);

  const fetchData = useCallback(async () => {
    try {
      const token = localStorage.getItem('token');
      const authHdr = { Authorization: `Bearer ${token}` };
      const [mData, pData, tData, bData, cData, iData, pwData] = await Promise.all([
        xhrFetch(`${BACKEND_URL}/api/neno-exchange/market`),
        xhrFetch(`${BACKEND_URL}/api/neno-exchange/price`),
        xhrFetch(`${BACKEND_URL}/api/neno-exchange/transactions`, { headers: authHdr }),
        xhrFetch(`${BACKEND_URL}/api/wallet/balances`, { headers: authHdr }),
        xhrFetch(`${BACKEND_URL}/api/cards/my-cards`, { headers: authHdr }),
        xhrFetch(`${BACKEND_URL}/api/banking/iban`, { headers: authHdr }),
        xhrFetch(`${BACKEND_URL}/api/neno-exchange/platform-wallet`),
      ]);
      setMarketInfo(mData);
      setPriceData(pData);
      setTxs(tData.transactions || []);
      const bMap = {};
      (bData.wallets || []).forEach(w => { bMap[w.asset] = w.balance; });
      setBalances(bMap);
      setCards((cData.cards || []).filter(c => c.status === 'active'));
      setIbans(iData.ibans || []);
      if (cData.cards?.length > 0) setSelectedCard(cData.cards[0].id);
      setCustomTokens(mData.custom_tokens || []);
      setAllAssets([...BUILTIN_ASSETS, ...(mData.custom_tokens || []).map(t => t.symbol)]);
      if (pwData.address) setPlatformWallet(pwData.address);
    } catch (e) { console.error('fetchData error:', e); }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  // Live NENO quote
  useEffect(() => {
    if (!nenoAmount || parseFloat(nenoAmount) <= 0 || tab === 'swap' || tab === 'create' || tab === 'deposit') { setQuote(null); return; }
    if (abortRef.current) abortRef.current.abort();
    const ctrl = new AbortController();
    abortRef.current = ctrl;
    const dir = tab === 'offramp' ? 'sell' : tab;
    xhrGet(`${BACKEND_URL}/api/neno-exchange/quote?direction=${dir}&asset=${tab === 'offramp' ? 'EUR' : asset}&neno_amount=${nenoAmount}`, { signal: ctrl.signal })
      .then(data => { if (!ctrl.signal.aborted) setQuote(data.detail ? null : data); })
      .catch(() => {});
    return () => ctrl.abort();
  }, [tab, asset, nenoAmount]);

  // Live swap quote
  useEffect(() => {
    if (tab !== 'swap' || !swapAmt || parseFloat(swapAmt) <= 0) { setSwapQuote(null); return; }
    const ctrl = new AbortController();
    xhrGet(`${BACKEND_URL}/api/neno-exchange/swap-quote?from_asset=${swapFrom}&to_asset=${swapTo}&amount=${swapAmt}`, { signal: ctrl.signal })
      .then(data => { if (!ctrl.signal.aborted) setSwapQuote(data.detail ? null : data); })
      .catch(() => {});
    return () => ctrl.abort();
  }, [tab, swapFrom, swapTo, swapAmt]);

  /* ── On-chain transaction flow (MetaMask signing) ─────────────── */
  const executeOnChain = async (nenoAmt, backendUrl, backendBody) => {
    if (!isConnected || !address || !platformWallet) {
      throw new Error('Connetti il tuo wallet MetaMask per eseguire operazioni on-chain');
    }
    const amt = parseFloat(nenoAmt);
    if (nenoOnChainBalance < amt) {
      throw new Error(`Saldo NENO on-chain insufficiente: ${nenoOnChainBalance.toFixed(4)} disponibile, ${amt} necessario`);
    }

    // Step 1: Sign & send ERC-20 transfer via MetaMask
    setTxStep('signing');
    let hash;
    try {
      hash = await transferNeno(platformWallet, amt);
    } catch (e) {
      const msg = e?.shortMessage || e?.message || 'Firma rifiutata';
      throw new Error(`MetaMask: ${msg}`);
    }

    // Step 2: Wait for block confirmation
    setTxStep('confirming');
    const maxWait = 120000;
    const start = Date.now();
    let confirmed = false;
    while (Date.now() - start < maxWait) {
      await new Promise(r => setTimeout(r, 3000));
      try {
        const checkResult = await xhrPost(`${BACKEND_URL}/api/neno-exchange/verify-deposit`,
          { tx_hash: hash, expected_amount: amt, operation: tab },
          localStorage.getItem('token')
        );
        if (checkResult.ok && checkResult.data.verified) {
          confirmed = true;
          break;
        }
        if (checkResult.data.detail && checkResult.data.detail.includes('non trovata on-chain')) continue;
        if (!checkResult.ok && !checkResult.data.detail?.includes('non trovata')) {
          throw new Error(checkResult.data.detail || 'Verifica fallita');
        }
      } catch (e) {
        if (e.message.includes('Verifica fallita')) throw e;
      }
    }
    if (!confirmed) {
      throw new Error('Timeout: la transazione non e\' stata confermata entro 120 secondi. Controlla su BscScan: ' + hash);
    }

    // Step 3: Execute backend operation with tx_hash
    setTxStep('verifying');
    const { ok, data } = await xhrPost(`${BACKEND_URL}${backendUrl}`, { ...backendBody, tx_hash: hash }, localStorage.getItem('token'));
    if (!ok) throw new Error(data.detail || 'Errore backend');

    // Refresh balances
    if (refetchNenoBalance) refetchNenoBalance();
    return { data, hash };
  };

  /* ── Standard execution (internal or on-chain) ────────────────── */
  const exec = async (url, body, requiresNeno = false) => {
    setLoading(true); setResult(null); setTxStep(null);
    try {
      let data, onchainHash;

      if (requiresNeno && isConnected && platformWallet && nenoOnChainBalance > 0) {
        // Real on-chain execution via MetaMask
        const nenoAmt = body.neno_amount || body.amount || 0;
        const res = await executeOnChain(nenoAmt, url, body);
        data = res.data;
        onchainHash = res.hash;
      } else {
        // Internal ledger execution
        const token = localStorage.getItem('token');
        const { ok, data: d } = await xhrPost(`${BACKEND_URL}${url}`, body, token);
        if (!ok) throw new Error(d.detail || JSON.stringify(d));
        data = d;
      }

      const tx = data.transaction || {};
      setResult({
        ok: true,
        msg: data.message || 'Operazione completata',
        balances: data.balances,
        settlementHash: onchainHash || tx.settlement_hash,
        blockNumber: tx.settlement_block_number,
        blockExplorer: onchainHash ? `https://bscscan.com/tx/${onchainHash}` : tx.settlement_explorer,
        contractExplorer: tx.settlement_contract_explorer,
        network: tx.settlement_network || 'BSC Mainnet',
        isOnChain: !!onchainHash,
        onchainExplorer: data.onchain_explorer,
      });
      fetchData();
    } catch (e) {
      setResult({ ok: false, msg: e.message });
    } finally {
      setLoading(false); setTxStep(null);
      if (resetTx) resetTx();
    }
  };

  const handleBuy = () => exec('/api/neno-exchange/buy', { pay_asset: asset, neno_amount: parseFloat(nenoAmount) });
  const handleSell = () => exec('/api/neno-exchange/sell', { receive_asset: asset, neno_amount: parseFloat(nenoAmount) }, true);
  const handleSwap = () => {
    const isFromNeno = swapFrom.toUpperCase() === 'NENO';
    exec('/api/neno-exchange/swap', { from_asset: swapFrom, to_asset: swapTo, amount: parseFloat(swapAmt) }, isFromNeno);
  };
  const handleOfframp = () => {
    const body = { neno_amount: parseFloat(nenoAmount), destination: offrampDest };
    if (offrampDest === 'card') body.card_id = selectedCard;
    if (offrampDest === 'bank') { body.destination_iban = offrampIban; body.beneficiary_name = offrampName; }
    exec('/api/neno-exchange/offramp', body, true);
  };
  const handleCreateToken = () => exec('/api/neno-exchange/create-token', {
    symbol: newSym, name: newName, price_eur: parseFloat(newPrice), total_supply: parseFloat(newSupply) || 1000000,
  });

  const TABS = [
    { id: 'buy', label: 'Compra', icon: TrendingUp },
    { id: 'sell', label: 'Vendi', icon: TrendingDown },
    { id: 'swap', label: 'Swap', icon: Repeat },
    { id: 'deposit', label: 'Deposita', icon: ArrowDownToLine },
    { id: 'offramp', label: 'Off-Ramp', icon: Building },
    { id: 'create', label: 'Crea Token', icon: Plus },
  ];

  // Determine if current operation will use on-chain
  const willUseOnChain = (requiresNeno) => requiresNeno && isConnected && platformWallet && nenoOnChainBalance > 0;
  const showOnChainBadge = willUseOnChain(tab === 'sell' || tab === 'offramp' || (tab === 'swap' && swapFrom.toUpperCase() === 'NENO')) && tab !== 'deposit';

  // Transaction step labels
  const stepLabel = txStep === 'signing' ? 'Firma con MetaMask...'
    : txStep === 'confirming' ? 'Attesa conferma BSC...'
    : txStep === 'verifying' ? 'Verifica on-chain...'
    : null;

  return (
    <div className="min-h-screen bg-zinc-950" data-testid="neno-exchange-page">
      {/* Header */}
      <div className="border-b border-zinc-800 bg-zinc-900/80 backdrop-blur-sm">
        <div className="max-w-5xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button onClick={() => navigate('/dashboard')} className="p-1.5 hover:bg-zinc-800 rounded-lg" data-testid="exchange-back-btn">
              <ArrowLeft className="w-4 h-4 text-zinc-400" />
            </button>
            <div>
              <h1 className="text-white font-bold text-lg">$NENO Exchange</h1>
              <span className="text-zinc-500 text-xs">
                {priceData ? `EUR ${priceData.neno_eur_price?.toLocaleString()} ${priceData.shift_pct > 0 ? '+' : ''}${priceData.shift_pct}%` : '...'}
              </span>
            </div>
          </div>
          <div className="flex items-center gap-4">
            {isConnected && address && (
              <div className="flex items-center gap-1.5 px-2.5 py-1.5 bg-emerald-500/10 border border-emerald-500/30 rounded-lg" data-testid="wallet-connected-status">
                <CheckCircle className="w-3.5 h-3.5 text-emerald-400" />
                <span className="text-emerald-400 text-[10px] font-mono">{formatAddress(address)}</span>
                {onChainBalance && <span className="text-zinc-500 text-[10px]">({parseFloat(onChainBalance.formatted).toFixed(4)} {onChainBalance.symbol})</span>}
              </div>
            )}
            <div className="text-right" data-testid="neno-balance-section">
              {isConnected && nenoOnChainBalance > 0 ? (
                <>
                  <div className="text-zinc-500 text-[10px]">NENO On-Chain (BSC)</div>
                  <div className="text-emerald-400 font-mono font-bold" data-testid="neno-onchain-balance">{nenoOnChainBalance.toFixed(4)}</div>
                </>
              ) : (
                <>
                  <div className="text-zinc-500 text-[10px]">NENO Balance</div>
                  <div className="text-white font-mono font-bold" data-testid="neno-balance">{(balances.NENO || 0).toFixed(4)}</div>
                </>
              )}
              {isConnected && (
                <div className="text-zinc-600 text-[9px]">
                  Interno: {(balances.NENO || 0).toFixed(4)}
                  {nenoOnChainBalance > 0 && ` | On-chain: ${nenoOnChainBalance.toFixed(4)}`}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-5xl mx-auto px-4 py-4 space-y-4">
        {/* Tabs */}
        <div className="flex gap-1 bg-zinc-900 rounded-lg p-1 overflow-x-auto">
          {TABS.map(t => (
            <button key={t.id} onClick={() => setTab(t.id)} data-testid={`tab-${t.id}`}
              className={`flex items-center gap-1.5 px-3 py-2 rounded-md text-xs font-medium whitespace-nowrap transition-colors ${tab === t.id ? 'bg-purple-600 text-white' : 'text-zinc-400 hover:text-white hover:bg-zinc-800'}`}>
              <t.icon className="w-3.5 h-3.5" /> {t.label}
            </button>
          ))}
        </div>

        {/* On-chain execution indicator */}
        {showOnChainBadge && (
          <div className="flex items-center gap-2 px-3 py-2 bg-emerald-500/10 border border-emerald-500/20 rounded-lg" data-testid="onchain-mode-badge">
            <Shield className="w-4 h-4 text-emerald-400" />
            <span className="text-emerald-400 text-xs font-medium">Esecuzione On-Chain</span>
            <span className="text-emerald-500/60 text-[10px]">MetaMask firmera' il trasferimento NENO verso il hot wallet della piattaforma</span>
          </div>
        )}

        {/* Transaction step progress */}
        {stepLabel && (
          <div className="flex items-center gap-2 px-3 py-2 bg-amber-500/10 border border-amber-500/20 rounded-lg animate-pulse" data-testid="tx-step-indicator">
            <Loader2 className="w-4 h-4 text-amber-400 animate-spin" />
            <span className="text-amber-400 text-xs font-medium">{stepLabel}</span>
            {txHash && <span className="text-amber-500/60 text-[10px] font-mono">{txHash.slice(0, 14)}...</span>}
          </div>
        )}

        {/* Result banner */}
        {result && (
          <div className={`rounded-lg px-4 py-3 text-sm ${result.ok ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-red-500/20 text-red-400 border border-red-500/30'}`} data-testid="result-banner">
            <div className="font-medium">{result.msg}</div>
            {result.isOnChain && result.settlementHash && (
              <div className="mt-2 space-y-1 text-[11px]">
                <div className="flex items-center gap-1.5">
                  <Shield className="w-3 h-3 text-emerald-500" />
                  <span className="text-emerald-500 font-bold">Transazione reale on-chain</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="text-emerald-600">TX Hash:</span>
                  <span className="font-mono text-emerald-500/80">{result.settlementHash.slice(0, 14)}...{result.settlementHash.slice(-8)}</span>
                  <button onClick={() => { navigator.clipboard.writeText(result.settlementHash); setCopiedHash(result.settlementHash); setTimeout(() => setCopiedHash(null), 2000); }}
                    className="p-0.5 hover:bg-emerald-500/20 rounded" data-testid="copy-settlement-hash">
                    {copiedHash === result.settlementHash ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3 opacity-60" />}
                  </button>
                </div>
                <div className="flex items-center gap-3 text-emerald-600/60">
                  <span>BSC Mainnet</span>
                  <a href={result.onchainExplorer || result.blockExplorer} target="_blank" rel="noopener noreferrer" className="flex items-center gap-0.5 text-emerald-500 hover:text-emerald-400" data-testid="bscscan-link">
                    <ExternalLink className="w-2.5 h-2.5" /> Verifica su BscScan
                  </a>
                </div>
              </div>
            )}
            {!result.isOnChain && result.ok && result.settlementHash && (
              <div className="mt-2 space-y-1 text-[11px]">
                <div className="flex items-center gap-1.5">
                  <span className="text-emerald-600">Settlement:</span>
                  <span className="font-mono text-emerald-500/80">{result.settlementHash.slice(0, 14)}...{result.settlementHash.slice(-8)}</span>
                </div>
                <div className="flex items-center gap-3 text-emerald-600/60">
                  {result.blockNumber > 0 && <span>Block #{result.blockNumber?.toLocaleString()}</span>}
                  {result.blockExplorer && (
                    <a href={result.blockExplorer} target="_blank" rel="noopener noreferrer" className="flex items-center gap-0.5 text-emerald-500 hover:text-emerald-400">
                      <ExternalLink className="w-2.5 h-2.5" /> BSCScan
                    </a>
                  )}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Buy / Sell */}
        {(tab === 'buy' || tab === 'sell') && (
          <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-5 space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-zinc-500 text-xs mb-1 block">{tab === 'buy' ? 'Paga con' : 'Ricevi in'}</label>
                <select value={asset} onChange={e => setAsset(e.target.value)} data-testid="asset-select"
                  className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2.5 text-white text-sm">
                  {allAssets.map(a => <option key={a} value={a}>{a}{balances[a] ? ` (${balances[a].toFixed(4)})` : ''}</option>)}
                </select>
              </div>
              <div>
                <label className="text-zinc-500 text-xs mb-1 block">Quantita NENO</label>
                <input type="number" value={nenoAmount} onChange={e => setNenoAmount(e.target.value)} min="0" step="any" data-testid="neno-amount-input"
                  className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2.5 text-white text-sm font-mono" placeholder="0.001" />
              </div>
            </div>
            {quote && (
              <div className="bg-zinc-800/50 rounded-lg p-3 text-xs space-y-1" data-testid="quote-info">
                <div className="flex justify-between"><span className="text-zinc-500">Prezzo NENO</span><span className="text-white">EUR {quote.neno_eur_price?.toLocaleString()}</span></div>
                <div className="flex justify-between"><span className="text-zinc-500">Rate</span><span className="text-white">1 NENO = {quote.rate?.toFixed(6)} {asset}</span></div>
                <div className="flex justify-between"><span className="text-zinc-500">Fee ({quote.fee_percent}%)</span><span className="text-amber-400">{quote.fee?.toFixed(8)} {asset}</span></div>
                <div className="flex justify-between font-bold"><span className="text-zinc-300">{tab === 'buy' ? 'Costo Totale' : 'Ricevi Netto'}</span>
                  <span className="text-emerald-400">{(tab === 'buy' ? quote.total_cost : quote.net_receive)?.toFixed(8)} {asset}</span>
                </div>
              </div>
            )}
            {/* Sell: warn if no on-chain balance but wallet connected */}
            {tab === 'sell' && isConnected && nenoOnChainBalance === 0 && (
              <div className="flex items-center gap-2 px-3 py-2 bg-amber-500/10 border border-amber-500/20 rounded-lg text-xs" data-testid="no-onchain-balance-warning">
                <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
                <span className="text-amber-400">Nessun NENO on-chain nel wallet connesso. Verra' usato il saldo interno.</span>
              </div>
            )}
            <button onClick={tab === 'buy' ? handleBuy : handleSell} disabled={loading || !nenoAmount || parseFloat(nenoAmount) <= 0} data-testid={`${tab}-btn`}
              className={`w-full py-3 rounded-lg font-bold text-sm transition-colors disabled:opacity-50 ${tab === 'buy' ? 'bg-emerald-600 hover:bg-emerald-500 text-white' : 'bg-red-600 hover:bg-red-500 text-white'}`}>
              {loading ? <Loader2 className="w-4 h-4 animate-spin mx-auto" /> : tab === 'buy' ? `Compra ${nenoAmount} NENO` : `Vendi ${nenoAmount} NENO`}
            </button>
          </div>
        )}

        {/* Swap */}
        {tab === 'swap' && (
          <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-5 space-y-4">
            <div className="grid grid-cols-5 gap-2 items-end">
              <div className="col-span-2">
                <label className="text-zinc-500 text-xs mb-1 block">Da</label>
                <select value={swapFrom} onChange={e => setSwapFrom(e.target.value)} data-testid="swap-from-select"
                  className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2.5 text-white text-sm">
                  {['NENO', ...allAssets].filter((v,i,a) => a.indexOf(v)===i).map(a => <option key={a} value={a}>{a}{balances[a] ? ` (${balances[a].toFixed(4)})` : ''}</option>)}
                </select>
              </div>
              <div className="flex justify-center">
                <button onClick={() => { setSwapFrom(swapTo); setSwapTo(swapFrom); }} className="p-2 bg-zinc-800 rounded-full hover:bg-zinc-700">
                  <ArrowRightLeft className="w-4 h-4 text-purple-400" />
                </button>
              </div>
              <div className="col-span-2">
                <label className="text-zinc-500 text-xs mb-1 block">A</label>
                <select value={swapTo} onChange={e => setSwapTo(e.target.value)} data-testid="swap-to-select"
                  className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2.5 text-white text-sm">
                  {['NENO', ...allAssets].filter((v,i,a) => a.indexOf(v)===i).map(a => <option key={a} value={a}>{a}</option>)}
                </select>
              </div>
            </div>
            <div>
              <label className="text-zinc-500 text-xs mb-1 block">Quantita {swapFrom}</label>
              <input type="number" value={swapAmt} onChange={e => setSwapAmt(e.target.value)} min="0" step="any" data-testid="swap-amount-input"
                className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2.5 text-white text-sm font-mono" />
            </div>
            {swapQuote && (
              <div className="bg-zinc-800/50 rounded-lg p-3 text-xs space-y-1" data-testid="swap-quote">
                <div className="flex justify-between"><span className="text-zinc-500">Rate</span><span className="text-white">1 {swapFrom} = {swapQuote.rate?.toFixed(8)} {swapTo}</span></div>
                <div className="flex justify-between"><span className="text-zinc-500">Fee ({swapQuote.fee_pct}%)</span><span className="text-amber-400">EUR {swapQuote.fee_eur}</span></div>
                <div className="flex justify-between font-bold"><span className="text-zinc-300">Ricevi</span><span className="text-emerald-400">{swapQuote.receive_amount?.toFixed(8)} {swapTo}</span></div>
              </div>
            )}
            <button onClick={handleSwap} disabled={loading || !swapAmt || parseFloat(swapAmt) <= 0 || swapFrom === swapTo} data-testid="swap-btn"
              className="w-full py-3 bg-purple-600 hover:bg-purple-500 rounded-lg font-bold text-sm text-white transition-colors disabled:opacity-50">
              {loading ? <Loader2 className="w-4 h-4 animate-spin mx-auto" /> : `Swap ${swapAmt} ${swapFrom} → ${swapTo}`}
            </button>
          </div>
        )}


        {/* Deposit NENO Widget */}
        {tab === 'deposit' && platformWallet && (
          <div className="bg-zinc-900 border border-zinc-800 rounded-xl overflow-hidden" data-testid="deposit-neno-widget">
            {/* Header */}
            <div className="bg-gradient-to-r from-emerald-600/20 to-teal-600/20 border-b border-emerald-500/20 px-5 py-3">
              <div className="flex items-center gap-2">
                <ArrowDownToLine className="w-4.5 h-4.5 text-emerald-400" />
                <h3 className="text-white font-bold text-sm">Deposita $NENO</h3>
              </div>
              <p className="text-emerald-400/70 text-[11px] mt-0.5">Invia NENO dal tuo wallet al hot wallet della piattaforma per operazioni di vendita e off-ramp</p>
            </div>

            <div className="p-5 space-y-5">
              {/* QR Code + Address */}
              <div className="flex flex-col items-center space-y-4">
                <div className="bg-white p-4 rounded-2xl shadow-lg shadow-emerald-500/10" data-testid="deposit-qr-code">
                  <QRCodeSVG
                    value={platformWallet}
                    size={180}
                    bgColor="#ffffff"
                    fgColor="#0a0a0a"
                    level="H"
                    includeMargin={false}
                  />
                </div>

                {/* Address with copy */}
                <div className="w-full max-w-md">
                  <label className="text-zinc-500 text-[10px] uppercase tracking-wider block mb-1.5 text-center">Indirizzo Hot Wallet (BSC)</label>
                  <div className="flex items-center gap-2 bg-zinc-800/80 border border-zinc-700 rounded-lg px-3 py-2.5">
                    <span className="text-emerald-400 font-mono text-[11px] break-all flex-1 select-all" data-testid="deposit-wallet-address">
                      {platformWallet}
                    </span>
                    <button
                      onClick={() => { navigator.clipboard.writeText(platformWallet); setCopiedAddr(true); setTimeout(() => setCopiedAddr(false), 2500); }}
                      className="flex-shrink-0 p-1.5 rounded-md hover:bg-zinc-700 transition-colors"
                      data-testid="copy-deposit-address-btn"
                    >
                      {copiedAddr
                        ? <Check className="w-4 h-4 text-emerald-400" />
                        : <Copy className="w-4 h-4 text-zinc-500 hover:text-white" />
                      }
                    </button>
                  </div>
                  {copiedAddr && (
                    <p className="text-emerald-400 text-[10px] text-center mt-1 animate-pulse">Indirizzo copiato!</p>
                  )}
                </div>
              </div>

              {/* Instructions */}
              <div className="space-y-2.5">
                <div className="flex items-start gap-3 bg-zinc-800/40 rounded-lg px-3 py-2.5">
                  <div className="w-5 h-5 rounded-full bg-emerald-500/20 flex items-center justify-center flex-shrink-0 mt-0.5">
                    <span className="text-emerald-400 text-[10px] font-bold">1</span>
                  </div>
                  <div>
                    <p className="text-white text-xs font-medium">Apri MetaMask o il tuo wallet BSC</p>
                    <p className="text-zinc-500 text-[10px]">Assicurati di essere sulla rete BNB Smart Chain (Chain ID 56)</p>
                  </div>
                </div>
                <div className="flex items-start gap-3 bg-zinc-800/40 rounded-lg px-3 py-2.5">
                  <div className="w-5 h-5 rounded-full bg-emerald-500/20 flex items-center justify-center flex-shrink-0 mt-0.5">
                    <span className="text-emerald-400 text-[10px] font-bold">2</span>
                  </div>
                  <div>
                    <p className="text-white text-xs font-medium">Invia i token $NENO all'indirizzo sopra</p>
                    <p className="text-zinc-500 text-[10px]">Copia l'indirizzo o scansiona il QR code dal tuo wallet mobile</p>
                  </div>
                </div>
                <div className="flex items-start gap-3 bg-zinc-800/40 rounded-lg px-3 py-2.5">
                  <div className="w-5 h-5 rounded-full bg-emerald-500/20 flex items-center justify-center flex-shrink-0 mt-0.5">
                    <span className="text-emerald-400 text-[10px] font-bold">3</span>
                  </div>
                  <div>
                    <p className="text-white text-xs font-medium">Il deposito viene verificato automaticamente</p>
                    <p className="text-zinc-500 text-[10px]">Dopo la conferma on-chain, il saldo sara' aggiornato e potrai vendere/scambiare/off-ramp</p>
                  </div>
                </div>
              </div>

              {/* Token contract info */}
              <div className="bg-zinc-800/30 border border-zinc-700/50 rounded-lg p-3 space-y-1.5">
                <div className="flex items-center justify-between text-[10px]">
                  <span className="text-zinc-500">Token</span>
                  <span className="text-white font-mono">$NENO (ERC-20)</span>
                </div>
                <div className="flex items-center justify-between text-[10px]">
                  <span className="text-zinc-500">Network</span>
                  <span className="text-white font-mono">BNB Smart Chain (BSC)</span>
                </div>
                <div className="flex items-center justify-between text-[10px]">
                  <span className="text-zinc-500">Contratto</span>
                  <a href="https://bscscan.com/token/0xeF3F5C1892A8d7A3304E4A15959E124402d69974" target="_blank" rel="noopener noreferrer"
                    className="text-emerald-400 hover:text-emerald-300 font-mono flex items-center gap-1" data-testid="deposit-contract-link">
                    0xeF3F...d69974 <ExternalLink className="w-2.5 h-2.5" />
                  </a>
                </div>
                <div className="flex items-center justify-between text-[10px]">
                  <span className="text-zinc-500">Decimali</span>
                  <span className="text-white font-mono">18</span>
                </div>
              </div>

              {/* Warning */}
              <div className="flex items-start gap-2 bg-amber-500/10 border border-amber-500/20 rounded-lg px-3 py-2">
                <AlertTriangle className="w-3.5 h-3.5 text-amber-400 flex-shrink-0 mt-0.5" />
                <p className="text-amber-400/80 text-[10px] leading-relaxed">
                  Invia solo token <strong>$NENO</strong> su rete <strong>BSC Mainnet</strong> a questo indirizzo.
                  Inviare altri token o su altre reti puo' causare la perdita dei fondi.
                </p>
              </div>
            </div>
          </div>
        )}


        {/* Off-Ramp */}
        {tab === 'offramp' && (
          <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-5 space-y-4">
            <div>
              <label className="text-zinc-500 text-xs mb-1 block">Quantita NENO da convertire</label>
              <input type="number" value={nenoAmount} onChange={e => setNenoAmount(e.target.value)} min="0" step="any" data-testid="offramp-amount-input"
                className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2.5 text-white text-sm font-mono" />
            </div>
            <div className="flex gap-2">
              {[{ id: 'card', label: 'Carta', icon: CreditCard }, { id: 'bank', label: 'Banca SEPA', icon: Building }].map(d => (
                <button key={d.id} onClick={() => setOfframpDest(d.id)} data-testid={`offramp-dest-${d.id}`}
                  className={`flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg text-xs font-medium border transition-colors ${offrampDest === d.id ? 'bg-purple-600/20 border-purple-500 text-purple-400' : 'bg-zinc-800 border-zinc-700 text-zinc-400'}`}>
                  <d.icon className="w-3.5 h-3.5" /> {d.label}
                </button>
              ))}
            </div>
            {offrampDest === 'card' && cards.length > 0 && (
              <select value={selectedCard} onChange={e => setSelectedCard(e.target.value)} className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2.5 text-white text-sm">
                {cards.map(c => <option key={c.id} value={c.id}>{c.card_number_masked} ({c.card_type})</option>)}
              </select>
            )}
            {offrampDest === 'bank' && (
              <div className="space-y-2">
                <input value={offrampIban} onChange={e => setOfframpIban(e.target.value)} placeholder="IBAN destinazione" data-testid="offramp-iban-input"
                  className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2.5 text-white text-sm" />
                <input value={offrampName} onChange={e => setOfframpName(e.target.value)} placeholder="Nome beneficiario" data-testid="offramp-name-input"
                  className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2.5 text-white text-sm" />
              </div>
            )}
            {quote && (
              <div className="bg-zinc-800/50 rounded-lg p-3 text-xs space-y-1">
                <div className="flex justify-between"><span className="text-zinc-500">Valore lordo</span><span className="text-white">EUR {quote.gross_value?.toFixed(2)}</span></div>
                <div className="flex justify-between"><span className="text-zinc-500">Fee</span><span className="text-amber-400">EUR {quote.fee?.toFixed(2)}</span></div>
                <div className="flex justify-between font-bold"><span className="text-zinc-300">Ricevi</span><span className="text-emerald-400">EUR {quote.net_receive?.toFixed(2)}</span></div>
              </div>
            )}
            <button onClick={handleOfframp} disabled={loading || !nenoAmount || parseFloat(nenoAmount) <= 0} data-testid="offramp-btn"
              className="w-full py-3 bg-blue-600 hover:bg-blue-500 rounded-lg font-bold text-sm text-white transition-colors disabled:opacity-50">
              {loading ? <Loader2 className="w-4 h-4 animate-spin mx-auto" /> : `Off-Ramp ${nenoAmount} NENO → ${offrampDest === 'card' ? 'Carta' : 'Banca'}`}
            </button>
          </div>
        )}

        {/* Create Token */}
        {tab === 'create' && (
          <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-5 space-y-4">
            <h3 className="text-white font-medium text-sm">Crea il tuo Token</h3>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-zinc-500 text-xs mb-1 block">Simbolo (ticker)</label>
                <input value={newSym} onChange={e => setNewSym(e.target.value.toUpperCase())} placeholder="MYTOKEN" maxLength={10} data-testid="create-symbol-input"
                  className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2.5 text-white text-sm font-mono" />
              </div>
              <div>
                <label className="text-zinc-500 text-xs mb-1 block">Nome</label>
                <input value={newName} onChange={e => setNewName(e.target.value)} placeholder="My Token" maxLength={50} data-testid="create-name-input"
                  className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2.5 text-white text-sm" />
              </div>
              <div>
                <label className="text-zinc-500 text-xs mb-1 block">Prezzo (EUR)</label>
                <input type="number" value={newPrice} onChange={e => setNewPrice(e.target.value)} placeholder="0.01" min="0" step="any" data-testid="create-price-input"
                  className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2.5 text-white text-sm font-mono" />
              </div>
              <div>
                <label className="text-zinc-500 text-xs mb-1 block">Supply totale</label>
                <input type="number" value={newSupply} onChange={e => setNewSupply(e.target.value)} placeholder="1000000" min="1" data-testid="create-supply-input"
                  className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2.5 text-white text-sm font-mono" />
              </div>
            </div>
            <button onClick={handleCreateToken} disabled={loading || !newSym || !newName || !newPrice} data-testid="create-token-btn"
              className="w-full py-3 bg-amber-600 hover:bg-amber-500 rounded-lg font-bold text-sm text-white transition-colors disabled:opacity-50">
              {loading ? <Loader2 className="w-4 h-4 animate-spin mx-auto" /> : `Crea ${newSym || 'Token'} @ EUR ${newPrice || '?'}`}
            </button>
          </div>
        )}

        {/* Custom Tokens List */}
        {customTokens.length > 0 && (
          <div className="bg-zinc-900 border border-zinc-800 rounded-xl overflow-hidden">
            <div className="px-4 py-2 border-b border-zinc-800"><span className="text-white font-medium text-xs">Token Custom ({customTokens.length})</span></div>
            <div className="divide-y divide-zinc-800/50">
              {customTokens.map(t => (
                <div key={t.symbol} className="px-4 py-2 flex items-center justify-between text-xs">
                  <div><span className="text-white font-mono font-bold">{t.symbol}</span> <span className="text-zinc-500">{t.name}</span></div>
                  <div className="text-right"><span className="text-emerald-400 font-mono">EUR {t.price_eur}</span> <span className="text-zinc-600 ml-2">Supply: {t.total_supply?.toLocaleString()}</span></div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Transaction History */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl overflow-hidden">
          <div className="px-4 py-2 border-b border-zinc-800 flex items-center gap-2">
            <Clock className="w-3.5 h-3.5 text-zinc-500" />
            <span className="text-white font-medium text-xs">Transazioni Recenti</span>
          </div>
          <div className="divide-y divide-zinc-800/50 max-h-60 overflow-y-auto">
            {txs.length === 0 && <div className="py-6 text-center text-zinc-500 text-xs">Nessuna transazione</div>}
            {txs.map(t => (
              <div key={t.id} className="px-4 py-2 space-y-0.5">
                <div className="flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2">
                    <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${t.type === 'buy_neno' ? 'bg-emerald-500/20 text-emerald-400' : t.type === 'swap' ? 'bg-purple-500/20 text-purple-400' : t.type === 'neno_offramp' ? 'bg-blue-500/20 text-blue-400' : 'bg-red-500/20 text-red-400'}`}>
                      {t.type === 'buy_neno' ? 'BUY' : t.type === 'sell_neno' ? 'SELL' : t.type === 'swap' ? 'SWAP' : 'OFFRAMP'}
                    </span>
                    <span className="text-zinc-300">{t.neno_amount ? `${t.neno_amount} NENO` : t.from_amount ? `${t.from_amount} ${t.from_asset}` : ''}</span>
                    {t.eur_value && <span className="text-zinc-600 text-[10px]">(EUR {t.eur_value})</span>}
                    {t.execution_mode === 'onchain' && <Shield className="w-3 h-3 text-emerald-500" />}
                  </div>
                  <div className="flex items-center gap-2">
                    {t.settlement_status === 'settled' && <CheckCircle className="w-3 h-3 text-emerald-500" />}
                    <span className="text-zinc-500">{t.created_at?.slice(0, 16).replace('T', ' ')}</span>
                  </div>
                </div>
                {(t.onchain_tx_hash || t.settlement_hash) && (
                  <div className="flex items-center gap-2">
                    <span className="text-zinc-700 text-[9px] font-mono">{(t.onchain_tx_hash || t.settlement_hash).slice(0, 14)}...{(t.onchain_tx_hash || t.settlement_hash).slice(-6)}</span>
                    {t.onchain_tx_hash && (
                      <a href={`https://bscscan.com/tx/${t.onchain_tx_hash}`} target="_blank" rel="noopener noreferrer" className="text-emerald-500 hover:text-emerald-400">
                        <ExternalLink className="w-2.5 h-2.5" />
                      </a>
                    )}
                    {!t.onchain_tx_hash && t.settlement_explorer && (
                      <a href={t.settlement_explorer} target="_blank" rel="noopener noreferrer" className="text-blue-500 hover:text-blue-400">
                        <ExternalLink className="w-2.5 h-2.5" />
                      </a>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Platform Wallet + Contract Info */}
        <div className="bg-zinc-900/50 border border-zinc-800/50 rounded-xl p-3" data-testid="contract-info-footer">
          <div className="flex items-center justify-between text-[10px]">
            <div className="flex items-center gap-2 text-zinc-600">
              <Wallet className="w-3 h-3" />
              <span>$NENO Contract (BSC)</span>
            </div>
            <a href="https://bscscan.com/token/0xeF3F5C1892A8d7A3304E4A15959E124402d69974" target="_blank" rel="noopener noreferrer"
              className="flex items-center gap-1 text-zinc-500 hover:text-emerald-400 font-mono transition-colors" data-testid="contract-bscscan-link">
              0xeF3F5C18...d69974 <ExternalLink className="w-2.5 h-2.5" />
            </a>
          </div>
          {platformWallet && (
            <div className="flex items-center justify-between text-[10px] mt-1">
              <span className="text-zinc-600">Hot Wallet (depositi)</span>
              <span className="text-zinc-500 font-mono" data-testid="platform-wallet-address">{platformWallet.slice(0, 8)}...{platformWallet.slice(-6)}</span>
            </div>
          )}
          <div className="flex items-center gap-3 mt-1 text-[9px] text-zinc-700">
            <span>Chain: BSC Mainnet (56)</span>
            <span>Supply: 999.8M $NENO</span>
            <span>Decimals: 18</span>
          </div>
        </div>
      </div>
    </div>
  );
}
