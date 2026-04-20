import React, { useEffect, useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAccount, useChainId, useSwitchChain, useSendTransaction } from 'wagmi';
import { useAuth } from '../context/AuthContext';
import { useWeb3 } from '../context/Web3Context';
import { launchpadApi } from '../api/launchpad';

const BSC_CHAIN_ID = 56;

export default function LaunchpadCreate() {
  const { user } = useAuth();
  const { openWalletModal } = useWeb3();
  const { address, isConnected } = useAccount();
  const chainId = useChainId();
  const { switchChain } = useSwitchChain();
  const { sendTransactionAsync, isPending } = useSendTransaction();
  const navigate = useNavigate();

  const [name, setName] = useState('');
  const [symbol, setSymbol] = useState('');
  const [metadataUri, setMetadataUri] = useState('');
  const [config, setConfig] = useState(null);
  const [error, setError] = useState(null);
  const [flow, setFlow] = useState('idle'); // idle|building|signing|confirming|done|error
  const [txHash, setTxHash] = useState(null);

  useEffect(() => {
    (async () => {
      try {
        setConfig(await launchpadApi.config());
      } catch (e) {
        setError(e?.response?.data?.detail || e.message);
      }
    })();
  }, []);

  const canSubmit =
    user &&
    name.trim().length > 0 &&
    symbol.trim().length > 0 &&
    symbol.trim().length <= 12 &&
    flow === 'idle';

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    if (!user) {
      setError('Effettua il login prima.');
      return;
    }
    if (!isConnected || !address) {
      openWalletModal();
      return;
    }
    if (chainId !== BSC_CHAIN_ID) {
      try { await switchChain({ chainId: BSC_CHAIN_ID }); }
      catch { setError('Passa a BSC Mainnet nel wallet.'); return; }
    }

    try {
      setFlow('building');
      const built = await launchpadApi.buildCreate({
        name: name.trim(),
        symbol: symbol.trim().toUpperCase(),
        metadataUri: metadataUri.trim(),
        userWalletAddress: address,
      });

      setFlow('signing');
      const hash = await sendTransactionAsync({
        to: built.to,
        data: built.data,
        value: BigInt(built.value || '0x0'),
      });
      setTxHash(hash);
      setFlow('confirming');
      // Poll per ~2min per trovare il token nell'elenco factory
      let newToken = null;
      for (let i = 0; i < 40; i++) {
        await new Promise((r) => setTimeout(r, 3000));
        try {
          const res = await launchpadApi.list(100, 0);
          const mine = (res.tokens || []).filter((t) => t.creator?.toLowerCase() === address.toLowerCase());
          if (mine.length > 0) {
            // ultimo creato dall'utente
            newToken = mine[mine.length - 1];
            break;
          }
        } catch (_) {}
      }
      setFlow('done');
      if (newToken) {
        setTimeout(() => navigate(`/launchpad/${newToken.address}`), 1500);
      }
    } catch (err) {
      setError(err?.shortMessage || err?.response?.data?.detail || err?.message || 'Errore');
      setFlow('error');
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-purple-950 to-slate-950 text-white">
      <div className="max-w-3xl mx-auto px-4 py-8">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-3xl md:text-4xl font-bold flex items-center gap-3">
            <span>✨</span> Crea Token
          </h1>
          <Link to="/launchpad" className="text-sm text-slate-300 hover:text-white underline">
            ← Launchpad
          </Link>
        </div>

        <div className="bg-slate-900/70 backdrop-blur border border-slate-800 rounded-2xl p-6 shadow-2xl">
          {config && (
            <div className="mb-5 p-3 rounded-lg bg-slate-800/70 border border-slate-700 text-xs text-slate-300">
              <div>Deploy fee: <span className="text-white font-semibold">{config.deploy_fee_bnb} BNB</span></div>
              <div>Platform fee on each trade: <span className="text-white">{config.platform_fee_bps / 100}%</span></div>
              <div>Creator fee on each trade: <span className="text-white">{config.creator_fee_bps / 100}%</span> (va al tuo wallet automaticamente)</div>
              <div>Graduation: <span className="text-white">{config.graduation_bnb} BNB raccolti</span></div>
              <div className="text-emerald-300 mt-2">✓ Zero collateral richiesto</div>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs text-slate-400 uppercase tracking-wide mb-1">Nome</label>
              <input
                data-testid="launchpad-create-name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                maxLength={50}
                placeholder="My Awesome Token"
                className="w-full px-3 py-2 rounded-lg bg-slate-800 border border-slate-700 focus:border-purple-500 outline-none"
              />
            </div>
            <div>
              <label className="block text-xs text-slate-400 uppercase tracking-wide mb-1">Symbol</label>
              <input
                data-testid="launchpad-create-symbol"
                value={symbol}
                onChange={(e) => setSymbol(e.target.value.toUpperCase())}
                maxLength={12}
                placeholder="MAT"
                className="w-full px-3 py-2 rounded-lg bg-slate-800 border border-slate-700 focus:border-purple-500 outline-none font-mono"
              />
            </div>
            <div>
              <label className="block text-xs text-slate-400 uppercase tracking-wide mb-1">
                Metadata URI <span className="text-slate-600">(opzionale — IPFS/HTTPS con logo + descrizione)</span>
              </label>
              <input
                data-testid="launchpad-create-metadata"
                value={metadataUri}
                onChange={(e) => setMetadataUri(e.target.value)}
                maxLength={500}
                placeholder="ipfs://... or https://..."
                className="w-full px-3 py-2 rounded-lg bg-slate-800 border border-slate-700 focus:border-purple-500 outline-none text-sm"
              />
            </div>

            <button
              type="submit"
              disabled={!canSubmit || isPending}
              data-testid="launchpad-create-submit"
              className="w-full py-3 rounded-xl font-semibold text-white bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-500 hover:to-pink-500 disabled:opacity-40 disabled:cursor-not-allowed transition"
            >
              {!user ? 'Login per continuare'
                : !isConnected ? 'Connetti wallet'
                : flow === 'building' ? 'Preparo tx…'
                : flow === 'signing' ? 'Firma nel wallet…'
                : flow === 'confirming' ? 'Attendo conferma on-chain…'
                : flow === 'done' ? '✔ Token creato!'
                : `🚀 Crea Token (${config?.deploy_fee_bnb || '?'} BNB)`}
            </button>

            {error && (
              <div className="p-3 rounded bg-rose-950/50 border border-rose-800 text-sm text-rose-300">
                ⚠ {error}
              </div>
            )}
            {txHash && (
              <div className="p-3 rounded bg-emerald-950/40 border border-emerald-700 text-sm">
                <a
                  href={`https://bscscan.com/tx/${txHash}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-emerald-300 underline break-all"
                >
                  View tx {txHash.slice(0, 16)}…{txHash.slice(-8)} ↗
                </a>
              </div>
            )}
          </form>

          <p className="mt-5 text-xs text-slate-500 leading-relaxed">
            Il prezzo iniziale del token parte molto basso e sale man mano che gli utenti comprano.
            Nessun utente (incluso te) puo' stampare token senza pagare. Quando il contratto raccoglie{' '}
            <strong>{config?.graduation_bnb || 85} BNB</strong>, la curva si chiude e 200M token vengono
            riservati per la creazione di un LP su PancakeSwap.
          </p>
        </div>
      </div>
    </div>
  );
}
