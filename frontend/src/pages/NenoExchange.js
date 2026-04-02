import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ArrowLeft, ArrowRightLeft, Loader2, CreditCard, Building, ArrowRight,
  Clock, ChevronDown, TrendingUp, TrendingDown, Plus, Repeat
} from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || '';
const hdrs = () => ({ 'Content-Type': 'application/json', Authorization: `Bearer ${localStorage.getItem('token')}` });

async function safeJson(res) {
  const text = await res.text();
  try { return JSON.parse(text); } catch { return { detail: text }; }
}

const BUILTIN_ASSETS = ['EUR', 'BNB', 'ETH', 'USDT', 'BTC', 'USDC', 'MATIC', 'USD'];

export default function NenoExchange() {
  const navigate = useNavigate();
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

  // Off-ramp
  const [offrampDest, setOfframpDest] = useState('card');
  const [selectedCard, setSelectedCard] = useState('');
  const [offrampIban, setOfframpIban] = useState('');
  const [offrampName, setOfframpName] = useState('');

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
      const [mRes, pRes, tRes, bRes, cRes, iRes] = await Promise.all([
        fetch(`${BACKEND_URL}/api/neno-exchange/market`),
        fetch(`${BACKEND_URL}/api/neno-exchange/price`),
        fetch(`${BACKEND_URL}/api/neno-exchange/transactions`, { headers: hdrs() }),
        fetch(`${BACKEND_URL}/api/wallet/balances`, { headers: hdrs() }),
        fetch(`${BACKEND_URL}/api/cards/my-cards`, { headers: hdrs() }),
        fetch(`${BACKEND_URL}/api/banking/iban`, { headers: hdrs() }),
      ]);
      const [mData, pData, tData, bData, cData, iData] = await Promise.all([
        safeJson(mRes), safeJson(pRes), safeJson(tRes), safeJson(bRes), safeJson(cRes), safeJson(iRes),
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
    } catch (e) { console.error(e); }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  // Live NENO quote with AbortController
  useEffect(() => {
    if (!nenoAmount || parseFloat(nenoAmount) <= 0 || tab === 'swap' || tab === 'create') { setQuote(null); return; }
    if (abortRef.current) abortRef.current.abort();
    const ctrl = new AbortController();
    abortRef.current = ctrl;
    const dir = tab === 'offramp' ? 'sell' : tab;
    fetch(`${BACKEND_URL}/api/neno-exchange/quote?direction=${dir}&asset=${tab === 'offramp' ? 'EUR' : asset}&neno_amount=${nenoAmount}`, { signal: ctrl.signal })
      .then(r => r.text())
      .then(t => { try { setQuote(JSON.parse(t)); } catch { setQuote(null); } })
      .catch(() => {});
    return () => ctrl.abort();
  }, [tab, asset, nenoAmount]);

  // Live swap quote
  useEffect(() => {
    if (tab !== 'swap' || !swapAmt || parseFloat(swapAmt) <= 0) { setSwapQuote(null); return; }
    const ctrl = new AbortController();
    fetch(`${BACKEND_URL}/api/neno-exchange/swap-quote?from_asset=${swapFrom}&to_asset=${swapTo}&amount=${swapAmt}`, { signal: ctrl.signal })
      .then(r => r.text())
      .then(t => { try { setSwapQuote(JSON.parse(t)); } catch { setSwapQuote(null); } })
      .catch(() => {});
    return () => ctrl.abort();
  }, [tab, swapFrom, swapTo, swapAmt]);

  const exec = async (url, body) => {
    setLoading(true); setResult(null);
    try {
      const res = await fetch(`${BACKEND_URL}${url}`, { method: 'POST', headers: hdrs(), body: JSON.stringify(body) });
      const data = await safeJson(res);
      if (!res.ok) throw new Error(data.detail || 'Errore');
      setResult({ ok: true, msg: data.message, balances: data.balances });
      fetchData();
    } catch (e) { setResult({ ok: false, msg: e.message }); }
    finally { setLoading(false); }
  };

  const handleBuy = () => exec('/api/neno-exchange/buy', { pay_asset: asset, neno_amount: parseFloat(nenoAmount) });
  const handleSell = () => exec('/api/neno-exchange/sell', { receive_asset: asset, neno_amount: parseFloat(nenoAmount) });
  const handleSwap = () => exec('/api/neno-exchange/swap', { from_asset: swapFrom, to_asset: swapTo, amount: parseFloat(swapAmt) });
  const handleOfframp = () => {
    const body = { neno_amount: parseFloat(nenoAmount), destination: offrampDest };
    if (offrampDest === 'card') body.card_id = selectedCard;
    if (offrampDest === 'bank') { body.destination_iban = offrampIban; body.beneficiary_name = offrampName; }
    exec('/api/neno-exchange/offramp', body);
  };
  const handleCreateToken = () => exec('/api/neno-exchange/create-token', {
    symbol: newSym, name: newName, price_eur: parseFloat(newPrice), total_supply: parseFloat(newSupply) || 1000000,
  });

  const TABS = [
    { id: 'buy', label: 'Compra', icon: TrendingUp },
    { id: 'sell', label: 'Vendi', icon: TrendingDown },
    { id: 'swap', label: 'Swap', icon: Repeat },
    { id: 'offramp', label: 'Off-Ramp', icon: Building },
    { id: 'create', label: 'Crea Token', icon: Plus },
  ];

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
          <div className="text-right">
            <div className="text-zinc-500 text-[10px]">NENO Balance</div>
            <div className="text-white font-mono font-bold" data-testid="neno-balance">{(balances.NENO || 0).toFixed(4)}</div>
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

        {/* Result banner */}
        {result && (
          <div className={`rounded-lg px-4 py-3 text-sm ${result.ok ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' : 'bg-red-500/20 text-red-400 border border-red-500/30'}`} data-testid="result-banner">
            {result.msg}
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
              <div key={t.id} className="px-4 py-2 flex items-center justify-between text-xs">
                <div className="flex items-center gap-2">
                  <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${t.type === 'buy_neno' ? 'bg-emerald-500/20 text-emerald-400' : t.type === 'swap' ? 'bg-purple-500/20 text-purple-400' : 'bg-red-500/20 text-red-400'}`}>
                    {t.type === 'buy_neno' ? 'BUY' : t.type === 'sell_neno' ? 'SELL' : t.type === 'swap' ? 'SWAP' : 'OFFRAMP'}
                  </span>
                  <span className="text-zinc-300">{t.neno_amount ? `${t.neno_amount} NENO` : t.from_amount ? `${t.from_amount} ${t.from_asset}` : ''}</span>
                </div>
                <div className="text-zinc-500">{t.created_at?.slice(0, 16).replace('T', ' ')}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
