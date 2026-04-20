import React, { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useAccount, useSendTransaction, useChainId, useSwitchChain } from 'wagmi';
import { useAuth } from '../context/AuthContext';
import { useWeb3 } from '../context/Web3Context';
import { stoApi } from '../api/sto';

const POLYGON_CHAIN_ID = 137;

export default function StoPortfolio() {
  const { user } = useAuth();
  const { openWalletModal } = useWeb3();
  const { address, isConnected } = useAccount();
  const chainId = useChainId();
  const { switchChain } = useSwitchChain();
  const { sendTransactionAsync } = useSendTransaction();

  const [portfolio, setPortfolio] = useState(null);
  const [health, setHealth] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [redeemAmount, setRedeemAmount] = useState('');
  const [flow, setFlow] = useState('idle');

  const load = useCallback(async () => {
    if (!address) return;
    setLoading(true);
    try {
      const h = await stoApi.health();
      setHealth(h);
      const p = await stoApi.portfolio(address);
      setPortfolio(p);
    } catch (e) {
      setError(e?.response?.data?.detail || e.message);
    } finally { setLoading(false); }
  }, [address]);

  useEffect(() => { load(); }, [load]);

  const ensurePolygon = async () => {
    if (chainId !== POLYGON_CHAIN_ID) {
      try { await switchChain({ chainId: POLYGON_CHAIN_ID }); }
      catch { throw new Error('Passa a Polygon Mainnet nel wallet'); }
    }
  };

  const handleRedeem = async () => {
    setError(null);
    const n = parseFloat(redeemAmount);
    if (!n || n <= 0) { setError('Importo non valido'); return; }
    if (!isConnected) { openWalletModal(); return; }
    try {
      await ensurePolygon();
      setFlow('building');
      const wei = BigInt(Math.floor(n * 1e18)).toString();
      const built = await stoApi.buildRedemption({ amount_token_wei: wei, user_wallet: address });
      setFlow('signing');
      const hash = await sendTransactionAsync({
        to: built.to, data: built.data, value: BigInt(built.value || '0x0'),
      });
      setFlow('done');
      setTimeout(load, 5000);
      window.open(`https://polygonscan.com/tx/${hash}`, '_blank');
    } catch (e) {
      setError(e?.shortMessage || e?.response?.data?.detail || e.message);
      setFlow('idle');
    }
  };

  const handleClaim = async (distId) => {
    setError(null);
    if (!isConnected) { openWalletModal(); return; }
    try {
      await ensurePolygon();
      const built = await stoApi.buildRevClaim({ user_wallet: address, distribution_id: distId });
      const hash = await sendTransactionAsync({
        to: built.to, data: built.data, value: BigInt(built.value || '0x0'),
      });
      setTimeout(load, 5000);
      window.open(`https://polygonscan.com/tx/${hash}`, '_blank');
    } catch (e) {
      setError(e?.shortMessage || e?.response?.data?.detail || e.message);
    }
  };

  if (!user) return <Msg>Effettua il login per accedere al portfolio STO.</Msg>;

  const deployed = health?.deployed;

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-indigo-950 to-slate-950 text-white">
      <div className="max-w-5xl mx-auto px-4 py-10">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-3xl md:text-4xl font-bold">📊 STO Portfolio</h1>
            <p className="text-slate-400 mt-1">Bilancio, revenue share e richieste di redemption</p>
          </div>
          <div className="flex gap-3">
            <Link to="/sto/invest" className="text-sm text-indigo-300 hover:text-indigo-200 underline">
              → Info offerta
            </Link>
            <Link to="/dashboard" className="text-sm text-slate-300 hover:text-white underline">
              ← Dashboard
            </Link>
          </div>
        </div>

        {!deployed && (
          <div className="mb-6 p-4 rounded-xl bg-amber-900/30 border border-amber-700/50 text-amber-100">
            ⏳ I contratti STO non sono ancora deployati su Polygon. Il portfolio sara` disponibile al go-live.{' '}
            <Link to="/sto/invest" className="underline">Pre-registrati qui</Link>.
          </div>
        )}

        {!isConnected ? (
          <div className="p-8 rounded-2xl bg-slate-900/70 border border-slate-800 text-center">
            <p className="text-slate-300 mb-4">Connetti il tuo wallet whitelisted per visualizzare il portfolio.</p>
            <button onClick={openWalletModal} data-testid="sto-connect-wallet"
              className="px-6 py-3 rounded-xl bg-gradient-to-r from-indigo-600 to-pink-600 hover:from-indigo-500 hover:to-pink-500 font-semibold">
              Connetti wallet
            </button>
          </div>
        ) : loading ? (
          <Msg>Caricamento portfolio…</Msg>
        ) : (
          <>
            {/* Balance card */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
              <Stat label="Saldo token" value={portfolio?.balance_human ? `${portfolio.balance_human.toLocaleString()}` : '0'} />
              <Stat label="NAV corrente" value={portfolio?.nav_per_token_wei ? `${Number(BigInt(portfolio.nav_per_token_wei)) / 1e6} USDC` : '—'} />
              <Stat label="Valore stimato" value={portfolio?.estimated_value_settlement_wei ? `${(Number(BigInt(portfolio.estimated_value_settlement_wei)) / 1e6).toFixed(2)} USDC` : '—'} />
            </div>

            {/* Redemption */}
            <div className="mb-6 p-6 rounded-2xl bg-slate-900/70 border border-slate-800">
              <h2 className="text-xl font-bold mb-3">💶 Redemption a NAV</h2>
              <p className="text-xs text-slate-500 mb-4">
                Richiedi il rimborso dei tuoi token al NAV corrente. La richiesta viene approvata dall'operator
                entro 5 giorni lavorativi e il payout in USDC e` disponibile dopo ulteriori 2 giorni.
              </p>
              <div className="flex gap-2">
                <input
                  type="number" step="any" min="0"
                  placeholder="Quantita` token"
                  value={redeemAmount}
                  onChange={(e) => setRedeemAmount(e.target.value)}
                  data-testid="sto-redeem-amount"
                  disabled={!deployed}
                  className="flex-1 px-3 py-2 rounded-lg bg-slate-800 border border-slate-700 focus:border-indigo-500 outline-none disabled:opacity-40"
                />
                <button
                  onClick={handleRedeem}
                  disabled={!deployed || flow !== 'idle' || !redeemAmount}
                  data-testid="sto-redeem-submit"
                  className="px-5 py-2 rounded-lg bg-gradient-to-r from-rose-600 to-red-600 hover:from-rose-500 hover:to-red-500 font-semibold disabled:opacity-40"
                >
                  {flow === 'building' ? 'Preparo…' : flow === 'signing' ? 'Firma…' : flow === 'done' ? '✔' : 'Richiedi redemption'}
                </button>
              </div>
            </div>

            {/* Claimable revenue */}
            <div className="mb-6 p-6 rounded-2xl bg-slate-900/70 border border-slate-800">
              <h2 className="text-xl font-bold mb-3">💰 Revenue share claimabile</h2>
              {(!portfolio?.claimable_revenue || portfolio.claimable_revenue.length === 0) ? (
                <p className="text-slate-500 text-sm">Nessuna distribuzione da claimare al momento.</p>
              ) : (
                <ul className="space-y-2">
                  {portfolio.claimable_revenue.map((c) => (
                    <li key={c.distribution_id} className="flex items-center justify-between p-3 rounded bg-slate-800/50 border border-slate-700">
                      <div>
                        <div className="text-sm">Distribuzione #{c.distribution_id}</div>
                        <div className="text-xs text-slate-500">{new Date(c.timestamp * 1000).toLocaleDateString()}</div>
                      </div>
                      <div className="flex items-center gap-3">
                        <span className="font-mono text-emerald-300">
                          {(Number(BigInt(c.share_wei)) / 1e6).toFixed(4)} USDC
                        </span>
                        <button
                          onClick={() => handleClaim(c.distribution_id)}
                          className="px-3 py-1 rounded bg-emerald-600 hover:bg-emerald-500 text-sm"
                        >
                          Claim
                        </button>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            {/* Redemption history */}
            <div className="p-6 rounded-2xl bg-slate-900/70 border border-slate-800">
              <h2 className="text-xl font-bold mb-3">📋 Le mie richieste</h2>
              {(!portfolio?.my_redemptions || portfolio.my_redemptions.length === 0) ? (
                <p className="text-slate-500 text-sm">Nessuna richiesta di redemption.</p>
              ) : (
                <ul className="space-y-2">
                  {portfolio.my_redemptions.map((r, i) => (
                    <li key={i} className="flex items-center justify-between p-3 rounded bg-slate-800/50 border border-slate-700 text-sm">
                      <div>
                        <div>Request · {new Date(r.created_at).toLocaleDateString()}</div>
                        <div className="text-xs text-slate-500">{(Number(BigInt(r.amount_token_wei)) / 1e18).toLocaleString()} token</div>
                      </div>
                      <span className="text-xs px-2 py-0.5 rounded bg-slate-700 uppercase">{r.status}</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </>
        )}

        {error && (
          <div className="mt-6 p-3 rounded bg-rose-950/50 border border-rose-800 text-rose-300 text-sm">
            ⚠ {error}
          </div>
        )}
      </div>
    </div>
  );
}

function Msg({ children }) {
  return (
    <div className="min-h-[60vh] flex items-center justify-center text-slate-400">
      {children}
    </div>
  );
}
function Stat({ label, value }) {
  return (
    <div className="p-4 rounded-xl bg-slate-900/60 backdrop-blur border border-slate-800 text-center">
      <div className="text-xs text-slate-500 uppercase tracking-wide">{label}</div>
      <div className="text-xl font-semibold mt-1">{value}</div>
    </div>
  );
}
