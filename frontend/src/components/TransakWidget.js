import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';
import { 
  CreditCard, 
  ArrowUpRight, 
  ArrowDownRight, 
  X,
  ExternalLink,
  Loader2,
  CheckCircle,
  AlertCircle,
  RefreshCw
} from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

// Supported currencies
const FIAT_CURRENCIES = [
  { code: 'EUR', name: 'Euro', symbol: '€' },
  { code: 'USD', name: 'US Dollar', symbol: '$' },
  { code: 'GBP', name: 'British Pound', symbol: '£' }
];

const CRYPTO_CURRENCIES = [
  { code: 'USDT', name: 'Tether USD', network: 'bsc' },
  { code: 'USDC', name: 'USD Coin', network: 'bsc' },
  { code: 'BNB', name: 'Binance Coin', network: 'bsc' },
  { code: 'NENO', name: 'NeoNoble Token', network: 'bsc' }
];

export default function TransakWidget({ isOpen, onClose, initialMode = 'BUY' }) {
  const { user } = useAuth();
  
  const [mode, setMode] = useState(initialMode); // BUY or SELL
  const [fiatCurrency, setFiatCurrency] = useState('EUR');
  const [cryptoCurrency, setCryptoCurrency] = useState('USDT');
  const [amount, setAmount] = useState('');
  const [walletAddress, setWalletAddress] = useState('');
  const [loading, setLoading] = useState(false);
  const [widgetUrl, setWidgetUrl] = useState(null);
  const [showWidget, setShowWidget] = useState(false);
  const [status, setStatus] = useState(null);
  const [orderId, setOrderId] = useState(null);

  // Generate widget URL
  const generateWidgetUrl = async () => {
    if (!amount || parseFloat(amount) <= 0) {
      setStatus({ type: 'error', message: 'Please enter a valid amount' });
      return;
    }

    if (mode === 'BUY' && !walletAddress) {
      setStatus({ type: 'error', message: 'Please enter your wallet address' });
      return;
    }

    setLoading(true);
    setStatus(null);

    try {
      // Create order record first
      const orderResponse = await fetch(`${BACKEND_URL}/api/transak/orders`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({
          user_id: user?.id || 'guest',
          product_type: mode,
          fiat_currency: fiatCurrency,
          crypto_currency: cryptoCurrency,
          fiat_amount: mode === 'BUY' ? parseFloat(amount) : null,
          crypto_amount: mode === 'SELL' ? parseFloat(amount) : null,
          wallet_address: walletAddress
        })
      });

      if (!orderResponse.ok) {
        throw new Error('Failed to create order');
      }

      const order = await orderResponse.json();
      setOrderId(order.order_id);

      // Generate widget URL
      const widgetResponse = await fetch(`${BACKEND_URL}/api/transak/widget-url`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({
          product_type: mode,
          fiat_currency: fiatCurrency,
          crypto_currency: cryptoCurrency,
          network: 'bsc',
          wallet_address: walletAddress,
          email: user?.email,
          fiat_amount: mode === 'BUY' ? parseFloat(amount) : null,
          crypto_amount: mode === 'SELL' ? parseFloat(amount) : null,
          redirect_url: window.location.origin + '/dashboard?transak=complete'
        })
      });

      if (!widgetResponse.ok) {
        const error = await widgetResponse.json();
        throw new Error(error.detail || 'Failed to generate widget URL');
      }

      const data = await widgetResponse.json();
      setWidgetUrl(data.widget_url);
      setShowWidget(true);
      setStatus({ type: 'success', message: 'Widget ready! Opening Transak...' });

    } catch (err) {
      console.error('Widget generation error:', err);
      setStatus({ type: 'error', message: err.message || 'Failed to open widget' });
    } finally {
      setLoading(false);
    }
  };

  // Handle iframe messages from Transak
  const handleTransakMessage = useCallback((event) => {
    // Verify origin
    if (!event.origin.includes('transak.com')) return;

    try {
      const data = typeof event.data === 'string' ? JSON.parse(event.data) : event.data;
      
      if (data.event_id === 'TRANSAK_ORDER_CREATED') {
        setStatus({ type: 'info', message: 'Order created! Processing...' });
        // Link the Transak order ID
        if (orderId && data.data?.id) {
          fetch(`${BACKEND_URL}/api/transak/orders/link`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${localStorage.getItem('token')}`
            },
            body: JSON.stringify({
              order_id: orderId,
              transak_order_id: data.data.id
            })
          }).catch(console.error);
        }
      }
      
      if (data.event_id === 'TRANSAK_ORDER_SUCCESSFUL') {
        setStatus({ type: 'success', message: 'Transaction completed successfully!' });
        setTimeout(() => {
          setShowWidget(false);
          onClose?.();
        }, 2000);
      }
      
      if (data.event_id === 'TRANSAK_ORDER_FAILED') {
        setStatus({ type: 'error', message: 'Transaction failed. Please try again.' });
      }
      
      if (data.event_id === 'TRANSAK_WIDGET_CLOSE') {
        setShowWidget(false);
      }
    } catch (e) {
      // Not a JSON message, ignore
    }
  }, [orderId, onClose]);

  useEffect(() => {
    window.addEventListener('message', handleTransakMessage);
    return () => window.removeEventListener('message', handleTransakMessage);
  }, [handleTransakMessage]);

  // Reset when modal closes
  useEffect(() => {
    if (!isOpen) {
      setShowWidget(false);
      setWidgetUrl(null);
      setStatus(null);
      setAmount('');
    }
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
      <div className="relative w-full max-w-lg bg-white dark:bg-gray-900 rounded-2xl shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-2">
            <CreditCard className="w-5 h-5 text-blue-500" />
            <h2 className="text-lg font-semibold">
              {mode === 'BUY' ? 'Buy Crypto' : 'Sell Crypto'}
            </h2>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-full hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Widget iframe or Form */}
        {showWidget && widgetUrl ? (
          <div className="relative">
            <iframe
              src={widgetUrl}
              title="Transak Widget"
              className="w-full h-[600px] border-0"
              allow="camera;microphone;payment"
              sandbox="allow-scripts allow-same-origin allow-popups allow-forms allow-modals"
            />
            <button
              onClick={() => setShowWidget(false)}
              className="absolute top-2 right-2 p-2 bg-white/90 rounded-full shadow hover:bg-white transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        ) : (
          <div className="p-6 space-y-6">
            {/* Mode Toggle */}
            <div className="flex gap-2 p-1 bg-gray-100 dark:bg-gray-800 rounded-lg">
              <button
                onClick={() => setMode('BUY')}
                className={`flex-1 flex items-center justify-center gap-2 py-2 px-4 rounded-md font-medium transition-colors ${
                  mode === 'BUY'
                    ? 'bg-green-500 text-white'
                    : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
                }`}
              >
                <ArrowDownRight className="w-4 h-4" />
                Buy
              </button>
              <button
                onClick={() => setMode('SELL')}
                className={`flex-1 flex items-center justify-center gap-2 py-2 px-4 rounded-md font-medium transition-colors ${
                  mode === 'SELL'
                    ? 'bg-orange-500 text-white'
                    : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
                }`}
              >
                <ArrowUpRight className="w-4 h-4" />
                Sell
              </button>
            </div>

            {/* Amount Input */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                {mode === 'BUY' ? 'You Pay' : 'You Sell'}
              </label>
              <div className="flex gap-2">
                <input
                  type="number"
                  value={amount}
                  onChange={(e) => setAmount(e.target.value)}
                  placeholder="0.00"
                  className="flex-1 px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
                <select
                  value={mode === 'BUY' ? fiatCurrency : cryptoCurrency}
                  onChange={(e) => mode === 'BUY' ? setFiatCurrency(e.target.value) : setCryptoCurrency(e.target.value)}
                  className="px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 focus:ring-2 focus:ring-blue-500"
                >
                  {mode === 'BUY' 
                    ? FIAT_CURRENCIES.map(c => (
                        <option key={c.code} value={c.code}>{c.code}</option>
                      ))
                    : CRYPTO_CURRENCIES.map(c => (
                        <option key={c.code} value={c.code}>{c.code}</option>
                      ))
                  }
                </select>
              </div>
            </div>

            {/* Receive Currency */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                {mode === 'BUY' ? 'You Receive' : 'You Receive'}
              </label>
              <select
                value={mode === 'BUY' ? cryptoCurrency : fiatCurrency}
                onChange={(e) => mode === 'BUY' ? setCryptoCurrency(e.target.value) : setFiatCurrency(e.target.value)}
                className="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 focus:ring-2 focus:ring-blue-500"
              >
                {mode === 'BUY'
                  ? CRYPTO_CURRENCIES.map(c => (
                      <option key={c.code} value={c.code}>{c.code} - {c.name}</option>
                    ))
                  : FIAT_CURRENCIES.map(c => (
                      <option key={c.code} value={c.code}>{c.code} - {c.name}</option>
                    ))
                }
              </select>
            </div>

            {/* Wallet Address (for BUY) */}
            {mode === 'BUY' && (
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Your BSC Wallet Address
                </label>
                <input
                  type="text"
                  value={walletAddress}
                  onChange={(e) => setWalletAddress(e.target.value)}
                  placeholder="0x..."
                  className="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 focus:ring-2 focus:ring-blue-500"
                />
              </div>
            )}

            {/* Status Messages */}
            {status && (
              <div className={`flex items-center gap-2 p-3 rounded-lg ${
                status.type === 'error' ? 'bg-red-50 text-red-700 dark:bg-red-900/30 dark:text-red-400' :
                status.type === 'success' ? 'bg-green-50 text-green-700 dark:bg-green-900/30 dark:text-green-400' :
                'bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400'
              }`}>
                {status.type === 'error' && <AlertCircle className="w-5 h-5" />}
                {status.type === 'success' && <CheckCircle className="w-5 h-5" />}
                {status.type === 'info' && <RefreshCw className="w-5 h-5 animate-spin" />}
                <span className="text-sm">{status.message}</span>
              </div>
            )}

            {/* Action Button */}
            <button
              onClick={generateWidgetUrl}
              disabled={loading || !amount}
              className={`w-full flex items-center justify-center gap-2 py-3 px-4 rounded-lg font-medium transition-colors ${
                mode === 'BUY'
                  ? 'bg-green-500 hover:bg-green-600 text-white'
                  : 'bg-orange-500 hover:bg-orange-600 text-white'
              } disabled:opacity-50 disabled:cursor-not-allowed`}
            >
              {loading ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  Loading...
                </>
              ) : (
                <>
                  <ExternalLink className="w-5 h-5" />
                  {mode === 'BUY' ? 'Buy with Transak' : 'Sell with Transak'}
                </>
              )}
            </button>

            {/* Info */}
            <p className="text-xs text-center text-gray-500 dark:text-gray-400">
              Powered by Transak • Secure & Compliant
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
