import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, ArrowRightLeft, Loader2, CreditCard, Building, ArrowRight, Clock, ChevronDown, TrendingUp, TrendingDown } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || '';
const headers = () => ({ 'Content-Type': 'application/json', Authorization: `Bearer ${localStorage.getItem('token')}` });

const ASSETS = ['EUR', 'BNB', 'ETH', 'USDT', 'BTC', 'USDC', 'MATIC', 'USD'];

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

  // Off-ramp state
  const [offrampDest, setOfframpDest] = useState('card');
  const [selectedCard, setSelectedCard] = useState('');
  const [offrampIban, setOfframpIban] = useState('');
  const [offrampName, setOfframpName] = useState('');

  const fetchData = useCallback(async () => {
    try {
      const [mRes, pRes, tRes, bRes, cRes, iRes] = await Promise.all([
        fetch(`${BACKEND_URL}/api/neno-exchange/market`),
        fetch(`${BACKEND_URL}/api/neno-exchange/price`),
        fetch(`${BACKEND_URL}/api/neno-exchange/transactions`, { headers: headers() }),
        fetch(`${BACKEND_URL}/api/wallet/balances`, { headers: headers() }),
        fetch(`${BACKEND_URL}/api/cards/my-cards`, { headers: headers() }),
        fetch(`${BACKEND_URL}/api/banking/iban`, { headers: headers() }),
      ]);
      const [mData, pData, tData, bData, cData, iData] = await Promise.all([mRes.json(), pRes.json(), tRes.json(), bRes.json(), cRes.json(), iRes.json()]);
      setMarketInfo(mData);
      setPriceData(pData);
      setTxs(tData.transactions || []);
      const bMap = {};
      (bData.wallets || []).forEach(w => { bMap[w.asset] = w.balance; });
      setBalances(bMap);
      setCards((cData.cards || []).filter(c => c.status === 'active'));
      setIbans(iData.ibans || []);
      if (cData.cards?.length > 0) setSelectedCard(cData.cards[0].id);
    } catch (e) { console.error(e); }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  // Live quote
  useEffect(() => {
    if (!nenoAmount || parseFloat(nenoAmount) <= 0) { setQuote(null); return; }
    const dir = tab === 'offramp' ? 'sell' : tab;
    fetch(`${BACKEND_URL}/api/neno-exchange/quote?direction=${dir}&asset=${tab === 'offramp' ? 'EUR' : asset}&neno_amount=${nenoAmount}`)
      .then(r => r.json()).then(setQuote).catch(() => setQuote(null));
  }, [tab, asset, nenoAmount]);

  const handleBuy = async () => {
    setLoading(true); setResult(null);
    try {
      const res = await fetch(`${BACKEND_URL}/api/neno-exchange/buy`, {
        method: 'POST', headers: headers(),
        body: JSON.stringify({ pay_asset: asset, neno_amount: parseFloat(nenoAmount) }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail);
      setResult({ ok: true, msg: data.message, balances: data.balances });
      fetchData();
    } catch (e) { setResult({ ok: false, msg: e.message }); }
    finally { setLoading(false); }
  };

  const handleSell = async () => {
    setLoading(true); setResult(null);
    try {
      const res = await fetch(`${BACKEND_URL}/api/neno-exchange/sell`, {
        method: 'POST', headers: headers(),
        body: JSON.stringify({ receive_asset: asset, neno_amount: parseFloat(nenoAmount) }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail);
      setResult({ ok: true, msg: data.message, balances: data.balances });
      fetchData();
    } catch (e) { setResult({ ok: false, msg: e.message }); }
    finally { setLoading(false); }
  };

  const handleOfframp = async () => {
    setLoading(true); setResult(null);
    try {
      const body = { neno_amount: parseFloat(nenoAmount), destination: offrampDest };
      if (offrampDest === 'card') body.card_id = selectedCard;
      if (offrampDest === 'bank') { body.destination_iban = offrampIban; body.beneficiary_name = offrampName; }
      const res = await fetch(`${BACKEND_URL}/api/neno-exchange/offramp`, {
        method: 'POST', headers: headers(), body: JSON.stringify(body),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail);
      setResult({ ok: true, msg: data.message });
      fetchData();
    } catch (e) { setResult({ ok: false, msg: e.message }); }
    finally { setLoading(false); }
  };

  return (
    <div className="min-h-screen bg-gray-950" data-testid="neno-exchange-page">
      {/* Header */}
      <div className="border-b border-gray-800 bg-gray-900/50">
        <div className="max-w-5xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button onClick={() => navigate('/dashboard')} className="p-1.5 hover:bg-gray-800 rounded-lg">
              <ArrowLeft className="w-4 h-4 text-gray-400" />
            </button>
            <div>
              <h1 className="text-white font-bold text-lg">NeoNoble Exchange</h1>
              <p className="text-gray-500 text-xs">Acquista, vendi e converti $NENO — On/Off-Ramp interno</p>
            </div>
          </div>
          <div className="text-right">
            <div className="text-gray-400 text-xs">Prezzo $NENO</div>
            <div className="text-white font-bold text-xl" data-testid="neno-price">
              {(priceData?.neno_eur_price || marketInfo?.neno_eur_price || 10000).toLocaleString('it-IT', { style: 'currency', currency: 'EUR' })}
            </div>
            {priceData && priceData.shift_pct !== 0 && (
              <div className={`flex items-center justify-end gap-1 text-xs ${priceData.shift_pct > 0 ? 'text-emerald-400' : 'text-red-400'}`} data-testid="neno-shift">
                {priceData.shift_pct > 0 ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
                {priceData.shift_pct > 0 ? '+' : ''}{priceData.shift_pct}% vs base
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="max-w-5xl mx-auto px-4 pt-6">
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
          {/* Left — Exchange Panel */}
          <div className="lg:col-span-3 space-y-4">
            {/* Tabs */}
            <div className="flex gap-1 bg-gray-900 rounded-xl p-1 w-fit">
              {[
                { id: 'buy', label: 'Acquista', color: 'green' },
                { id: 'sell', label: 'Vendi', color: 'orange' },
                { id: 'offramp', label: 'Off-Ramp', color: 'blue' },
              ].map(t => (
                <button key={t.id} onClick={() => { setTab(t.id); setResult(null); }} data-testid={`tab-${t.id}`}
                  className={`px-5 py-2 rounded-lg text-sm font-medium transition-colors ${
                    tab === t.id
                      ? t.color === 'green' ? 'bg-green-500/20 text-green-400'
                        : t.color === 'orange' ? 'bg-orange-500/20 text-orange-400'
                        : 'bg-blue-500/20 text-blue-400'
                      : 'text-gray-400 hover:text-white'
                  }`}>
                  {t.label}
                </button>
              ))}
            </div>

            {/* Exchange Form */}
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 space-y-4">
              {/* NENO Amount */}
              <div>
                <label className="text-gray-400 text-xs mb-1.5 block">Quantita' $NENO</label>
                <div className="flex items-center gap-3">
                  <input type="number" step="any" min="0.001" value={nenoAmount}
                    onChange={e => setNenoAmount(e.target.value)} data-testid="neno-amount-input"
                    className="flex-1 px-4 py-3 bg-gray-800 border border-gray-700 rounded-xl text-white text-lg font-mono focus:border-purple-500 focus:outline-none" />
                  <div className="px-4 py-3 bg-purple-500/20 border border-purple-500/30 rounded-xl text-purple-400 font-bold text-sm">
                    $NENO
                  </div>
                </div>
              </div>

              {/* Asset Selection (buy/sell only) */}
              {tab !== 'offramp' && (
                <div>
                  <label className="text-gray-400 text-xs mb-1.5 block">
                    {tab === 'buy' ? 'Paga con' : 'Ricevi in'}
                  </label>
                  <div className="grid grid-cols-4 gap-2">
                    {ASSETS.map(a => (
                      <button key={a} onClick={() => setAsset(a)} data-testid={`asset-${a}`}
                        className={`py-2.5 rounded-xl text-sm font-medium transition-all ${
                          asset === a
                            ? 'bg-purple-500/20 text-purple-400 border border-purple-500/40'
                            : 'bg-gray-800 text-gray-400 border border-gray-700 hover:border-gray-600'
                        }`}>
                        {a}
                        {balances[a] !== undefined && (
                          <div className="text-[10px] text-gray-500 mt-0.5">{balances[a]?.toFixed(a === 'EUR' || a === 'USD' ? 2 : 4)}</div>
                        )}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Off-Ramp Destination */}
              {tab === 'offramp' && (
                <div className="space-y-3">
                  <label className="text-gray-400 text-xs block">Destinazione</label>
                  <div className="grid grid-cols-2 gap-3">
                    <button onClick={() => setOfframpDest('card')} data-testid="offramp-card"
                      className={`p-3 rounded-xl border flex items-center gap-2 ${
                        offrampDest === 'card' ? 'border-blue-500 bg-blue-500/10' : 'border-gray-700 bg-gray-800'
                      }`}>
                      <CreditCard className="w-5 h-5 text-blue-400" />
                      <div className="text-left">
                        <div className="text-white text-sm font-medium">Carta</div>
                        <div className="text-gray-400 text-xs">Visa/Mastercard</div>
                      </div>
                    </button>
                    <button onClick={() => setOfframpDest('bank')} data-testid="offramp-bank"
                      className={`p-3 rounded-xl border flex items-center gap-2 ${
                        offrampDest === 'bank' ? 'border-blue-500 bg-blue-500/10' : 'border-gray-700 bg-gray-800'
                      }`}>
                      <Building className="w-5 h-5 text-teal-400" />
                      <div className="text-left">
                        <div className="text-white text-sm font-medium">Conto Bancario</div>
                        <div className="text-gray-400 text-xs">Bonifico SEPA</div>
                      </div>
                    </button>
                  </div>

                  {offrampDest === 'card' && cards.length > 0 && (
                    <select value={selectedCard} onChange={e => setSelectedCard(e.target.value)} data-testid="offramp-card-select"
                      className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white text-sm">
                      {cards.map(c => (
                        <option key={c.id} value={c.id}>{c.card_network?.toUpperCase()} {c.card_number_masked} — EUR {c.balance?.toFixed(2)}</option>
                      ))}
                    </select>
                  )}
                  {offrampDest === 'card' && cards.length === 0 && (
                    <div className="text-yellow-400 text-xs p-2 bg-yellow-500/10 rounded-lg">Nessuna carta attiva. Crea una carta dalla sezione Carte.</div>
                  )}

                  {offrampDest === 'bank' && (
                    <div className="space-y-2">
                      <input type="text" value={offrampIban} onChange={e => setOfframpIban(e.target.value)}
                        placeholder="IBAN destinazione" data-testid="offramp-iban"
                        className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white text-sm font-mono" />
                      <input type="text" value={offrampName} onChange={e => setOfframpName(e.target.value)}
                        placeholder="Nome beneficiario" data-testid="offramp-name"
                        className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white text-sm" />
                    </div>
                  )}
                </div>
              )}

              {/* Quote Preview */}
              {quote && nenoAmount && parseFloat(nenoAmount) > 0 && (
                <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-4 space-y-2" data-testid="quote-preview">
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-400">Prezzo NENO</span>
                    <span className="text-white font-mono">{ASSETS.includes(quote.pay_asset || quote.receive_asset || 'EUR') ? '' : ''}{(marketInfo?.neno_eur_price || 10000).toLocaleString('it-IT', { style: 'currency', currency: 'EUR' })}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-400">Tasso</span>
                    <span className="text-white font-mono">1 NENO = {quote.rate?.toFixed(6)} {quote.pay_asset || quote.receive_asset || 'EUR'}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-400">Fee ({quote.fee_percent}%)</span>
                    <span className="text-yellow-400 font-mono">{quote.fee?.toFixed(6)} {quote.pay_asset || quote.receive_asset || 'EUR'}</span>
                  </div>
                  <div className="border-t border-gray-700 pt-2 flex justify-between text-sm font-medium">
                    <span className="text-gray-300">{tab === 'buy' ? 'Costo totale' : 'Riceverai'}</span>
                    <span className={`font-mono ${tab === 'buy' ? 'text-orange-400' : 'text-green-400'}`}>
                      {(tab === 'buy' ? quote.total_cost : (quote.net_receive || quote.eur_net))?.toFixed(6)} {quote.pay_asset || quote.receive_asset || 'EUR'}
                    </span>
                  </div>
                </div>
              )}

              {/* Action Button */}
              <button
                onClick={tab === 'buy' ? handleBuy : tab === 'sell' ? handleSell : handleOfframp}
                disabled={loading || !nenoAmount || parseFloat(nenoAmount) <= 0}
                data-testid="exchange-submit"
                className={`w-full py-3 rounded-xl font-bold text-sm transition-all flex items-center justify-center gap-2 disabled:opacity-50 ${
                  tab === 'buy' ? 'bg-green-500 hover:bg-green-600 text-white' :
                  tab === 'sell' ? 'bg-orange-500 hover:bg-orange-600 text-white' :
                  'bg-blue-500 hover:bg-blue-600 text-white'
                }`}>
                {loading ? <Loader2 className="w-4 h-4 animate-spin" /> :
                  tab === 'buy' ? `Acquista ${nenoAmount || 0} NENO` :
                  tab === 'sell' ? `Vendi ${nenoAmount || 0} NENO` :
                  `Off-Ramp ${nenoAmount || 0} NENO → ${offrampDest === 'card' ? 'Carta' : 'Conto'}`
                }
              </button>

              {/* Result */}
              {result && (
                <div className={`p-3 rounded-xl text-sm ${result.ok ? 'bg-green-500/10 text-green-400 border border-green-500/20' : 'bg-red-500/10 text-red-400 border border-red-500/20'}`}
                  data-testid="exchange-result">
                  {result.msg}
                  {result.balances && (
                    <div className="mt-1 text-xs text-gray-400">
                      {Object.entries(result.balances).map(([k, v]) => (
                        <span key={k} className="mr-3">{k}: {typeof v === 'number' ? v.toFixed(k === 'EUR' ? 2 : 6) : v}</span>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* Right — Info & History */}
          <div className="lg:col-span-2 space-y-4">
            {/* Balances */}
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
              <h3 className="text-white font-medium text-sm mb-3">I tuoi saldi</h3>
              <div className="space-y-2">
                <div className="flex justify-between items-center p-2 bg-purple-500/10 border border-purple-500/20 rounded-lg">
                  <span className="text-purple-400 font-bold text-sm">$NENO</span>
                  <span className="text-white font-mono text-sm" data-testid="neno-balance">{(balances['NENO'] || 0).toFixed(4)}</span>
                </div>
                {ASSETS.filter(a => balances[a] > 0).map(a => (
                  <div key={a} className="flex justify-between items-center px-2 py-1.5 text-xs">
                    <span className="text-gray-400">{a}</span>
                    <span className="text-gray-300 font-mono">{balances[a]?.toFixed(a === 'EUR' || a === 'USD' ? 2 : 6)}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Conversion Rates */}
            {marketInfo && (
              <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
                <h3 className="text-white font-medium text-sm mb-3">Tassi di conversione</h3>
                <div className="space-y-1.5">
                  {Object.entries(marketInfo.pairs || {}).slice(0, 8).map(([pair, info]) => (
                    <div key={pair} className="flex justify-between text-xs">
                      <span className="text-gray-400">{pair}</span>
                      <span className="text-gray-300 font-mono">{info.rate?.toFixed(4)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Transaction History */}
            <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
              <div className="px-4 py-3 border-b border-gray-800 flex items-center gap-2">
                <Clock className="w-4 h-4 text-gray-400" />
                <span className="text-white font-medium text-sm">Storico Transazioni</span>
              </div>
              <div className="divide-y divide-gray-800/50 max-h-80 overflow-y-auto">
                {txs.length === 0 && (
                  <div className="px-4 py-6 text-center text-gray-500 text-xs">Nessuna transazione</div>
                )}
                {txs.map(t => (
                  <div key={t.id} className="px-4 py-2.5 text-xs">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-1.5">
                        <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${
                          t.type === 'buy_neno' ? 'bg-green-500/20 text-green-400' :
                          t.type === 'sell_neno' ? 'bg-orange-500/20 text-orange-400' :
                          'bg-blue-500/20 text-blue-400'
                        }`}>
                          {t.type === 'buy_neno' ? 'BUY' : t.type === 'sell_neno' ? 'SELL' : 'OFF-RAMP'}
                        </span>
                        <span className="text-gray-300">{t.neno_amount} NENO</span>
                      </div>
                      <span className={`${t.status === 'completed' ? 'text-green-400' : 'text-yellow-400'}`}>{t.status}</span>
                    </div>
                    <div className="text-gray-500 mt-0.5">
                      {t.type === 'buy_neno' && `Pagato ${t.pay_amount?.toFixed(4)} ${t.pay_asset}`}
                      {t.type === 'sell_neno' && `Ricevuto ${t.receive_amount?.toFixed(4)} ${t.receive_asset}`}
                      {t.type === 'neno_offramp' && `EUR ${t.eur_net?.toFixed(2)} → ${t.destination_info}`}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
