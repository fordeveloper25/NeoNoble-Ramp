import React, { useEffect, useRef, useState, useCallback } from 'react';
import { Transak } from '@transak/transak-sdk';
import { useAuth } from '../context/AuthContext';
import { X, Loader2, CheckCircle, AlertCircle } from 'lucide-react';

const TRANSAK_STAGING = 'https://global-stg.transak.com';
const TRANSAK_API_KEY = process.env.REACT_APP_TRANSAK_API_KEY || '5911d9ec-46b5-48b0-a4c8-0b67aa60baae';
const REFERRER = typeof window !== 'undefined' ? window.location.origin : 'https://neonobleramp.com';

function buildWidgetUrl(mode, email) {
  const params = new URLSearchParams({
    apiKey: TRANSAK_API_KEY,
    productsAvailed: mode,
    defaultCryptoCurrency: 'NENO',
    cryptoCurrencyList: 'NENO,BNB,ETH,USDT,USDC,BTC',
    network: 'bsc',
    defaultNetwork: 'bsc',
    networks: 'bsc,ethereum,polygon',
    defaultFiatCurrency: 'EUR',
    themeColor: '7c3aed',
    colorMode: 'DARK',
    hideMenu: 'true',
    exchangeScreenTitle: mode === 'BUY' ? 'Acquista $NENO' : 'Vendi $NENO',
    referrerDomain: REFERRER,
  });
  if (email) params.set('email', email);
  return `${TRANSAK_STAGING}?${params.toString()}`;
}

/**
 * Official Transak SDK widget for $NENO on/off-ramp.
 */
export default function TransakWidget({ isOpen, onClose, initialMode = 'BUY' }) {
  const { user } = useAuth();
  const transakRef = useRef(null);
  const [status, setStatus] = useState(null);
  const [ready, setReady] = useState(false);

  const cleanup = useCallback(() => {
    try { transakRef.current?.close(); } catch (_) {}
    transakRef.current = null;
    setReady(false);
    setStatus(null);
  }, []);

  useEffect(() => {
    if (!isOpen) { cleanup(); return; }

    const url = buildWidgetUrl(initialMode, user?.email);
    try {
      transakRef.current = new Transak({
        widgetUrl: url,
        referrer: REFERRER,
        containerId: 'transak-mount',
        themeColor: '#7c3aed',
      });

      transakRef.current.init();
      setReady(true);

      Transak.on(Transak.EVENTS.TRANSAK_ORDER_CREATED, () => {
        setStatus({ type: 'info', msg: 'Ordine creato, elaborazione in corso...' });
      });

      Transak.on(Transak.EVENTS.TRANSAK_ORDER_SUCCESSFUL, () => {
        setStatus({ type: 'success', msg: 'Transazione completata!' });
        setTimeout(() => { cleanup(); onClose?.(); }, 2500);
      });

      Transak.on(Transak.EVENTS.TRANSAK_ORDER_FAILED, () => {
        setStatus({ type: 'error', msg: 'Transazione fallita. Riprova.' });
      });

      Transak.on(Transak.EVENTS.TRANSAK_WIDGET_CLOSE, () => {
        cleanup();
        onClose?.();
      });
    } catch (err) {
      console.error('[Transak] init error', err);
      setStatus({ type: 'error', msg: "Errore nell'inizializzazione del widget." });
    }

    return cleanup;
  }, [isOpen, initialMode, user, onClose, cleanup]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="relative w-full max-w-[480px] bg-gray-900 border border-gray-700 rounded-2xl overflow-hidden shadow-2xl"
        data-testid="transak-widget-modal">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-800">
          <span className="text-white font-semibold text-sm">
            {initialMode === 'BUY' ? 'Acquista $NENO' : 'Vendi $NENO'} — Transak
          </span>
          <button onClick={() => { cleanup(); onClose?.(); }} data-testid="transak-close-btn"
            className="p-1.5 hover:bg-gray-800 rounded-lg transition-colors">
            <X className="w-4 h-4 text-gray-400" />
          </button>
        </div>

        {/* Status bar */}
        {status && (
          <div className={`flex items-center gap-2 px-4 py-2 text-xs ${
            status.type === 'error'   ? 'bg-red-500/10 text-red-400' :
            status.type === 'success' ? 'bg-green-500/10 text-green-400' :
            'bg-blue-500/10 text-blue-400'
          }`}>
            {status.type === 'success' && <CheckCircle className="w-3.5 h-3.5" />}
            {status.type === 'error' && <AlertCircle className="w-3.5 h-3.5" />}
            {status.type === 'info' && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
            {status.msg}
          </div>
        )}

        {/* SDK mount point */}
        <div id="transak-mount"
          className="w-full bg-gray-950"
          style={{ minHeight: 560 }}
          data-testid="transak-sdk-container"
        >
          {!ready && (
            <div className="flex flex-col items-center justify-center h-[560px] gap-3">
              <Loader2 className="w-8 h-8 text-purple-500 animate-spin" />
              <span className="text-gray-400 text-sm">Caricamento Transak...</span>
            </div>
          )}
        </div>

        <div className="px-4 py-2 border-t border-gray-800 text-center">
          <span className="text-gray-500 text-[10px]">
            Powered by Transak — Sicuro & Regolamentato
          </span>
        </div>
      </div>
    </div>
  );
}
