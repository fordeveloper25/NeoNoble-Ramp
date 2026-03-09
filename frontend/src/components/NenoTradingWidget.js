import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';
import toast from 'react-hot-toast';
import NenoCandlestickChart from './NenoCandlestickChart';
import { PriceAlertCreator, showNotificationToast } from './NotificationSystem';
import {
  TrendingUp,
  TrendingDown,
  ArrowUpRight,
  ArrowDownRight,
  RefreshCw,
  DollarSign,
  Activity,
  BarChart3,
  Wifi,
  WifiOff,
  ChevronDown,
  ChevronUp,
  Clock,
  Zap,
  LineChart,
  Bell
} from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || '';

// Available trading pairs for NENO
const NENO_PAIRS = [
  { symbol: 'NENO-EUR', display: 'NENO/EUR', quote: 'EUR' },
  { symbol: 'NENO-USD', display: 'NENO/USD', quote: 'USD' },
  { symbol: 'NENO-USDT', display: 'NENO/USDT', quote: 'USDT' }
];

// Available exchanges
const EXCHANGES = [
  { id: 'neno_exchange', name: 'NeoNoble', icon: '🏛️' },
  { id: 'kraken', name: 'Kraken', icon: '🐙' },
  { id: 'coinbase', name: 'Coinbase', icon: '🪙' },
  { id: 'binance', name: 'Binance', icon: '💎' }
];

export default function NenoTradingWidget({ compact = false }) {
  const { user } = useAuth();
  const wsRef = useRef(null);
  
  // State
  const [selectedPair, setSelectedPair] = useState(NENO_PAIRS[0]);
  const [selectedExchange, setSelectedExchange] = useState(EXCHANGES[0]);
  const [ticker, setTicker] = useState(null);
  const [orderSide, setOrderSide] = useState('buy');
  const [orderType, setOrderType] = useState('market');
  const [quantity, setQuantity] = useState('');
  const [limitPrice, setLimitPrice] = useState('');
  const [loading, setLoading] = useState(false);
  const [wsConnected, setWsConnected] = useState(false);
  const [orders, setOrders] = useState([]);
  const [showOrders, setShowOrders] = useState(false);
  const [status, setStatus] = useState(null);
  const [balance, setBalance] = useState({ neno: 0, eur: 0 });

  // WebSocket connection for real-time ticker
  const connectWebSocket = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const wsUrl = BACKEND_URL.replace('https://', 'wss://').replace('http://', 'ws://');
    const ws = new WebSocket(`${wsUrl}/api/ws/ticker/${selectedPair.symbol}`);
    
    ws.onopen = () => {
      console.log('[WS] Connected');
      setWsConnected(true);
    };
    
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'ticker') {
          setTicker(data.data);
        }
      } catch (e) {
        console.error('[WS] Parse error:', e);
      }
    };
    
    ws.onerror = (error) => {
      console.error('[WS] Error:', error);
      setWsConnected(false);
    };
    
    ws.onclose = () => {
      console.log('[WS] Disconnected');
      setWsConnected(false);
      // Reconnect after 3 seconds
      setTimeout(connectWebSocket, 3000);
    };
    
    wsRef.current = ws;
  }, [selectedPair.symbol]);

  // Fetch ticker via REST (fallback)
  const fetchTicker = useCallback(async () => {
    try {
      const response = await fetch(
        `${BACKEND_URL}/api/exchanges/ticker/${selectedPair.symbol}?venue=${selectedExchange.id}`
      );
      if (response.ok) {
        const data = await response.json();
        setTicker(data);
      }
    } catch (error) {
      console.error('Ticker fetch error:', error);
    }
  }, [selectedPair.symbol, selectedExchange.id]);

  // Fetch orders
  const fetchOrders = useCallback(async () => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/exchanges/orders?symbol=${selectedPair.symbol}&limit=10`);
      if (response.ok) {
        const data = await response.json();
        setOrders(data.orders || []);
      }
    } catch (error) {
      console.error('Orders fetch error:', error);
    }
  }, [selectedPair.symbol]);

  // Fetch balance
  const fetchBalance = useCallback(async () => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/exchanges/balances`);
      if (response.ok) {
        const data = await response.json();
        const nenoBalance = data.balances?.neno_exchange?.find(b => b.currency === 'NENO');
        setBalance({
          neno: nenoBalance?.available || 0,
          eur: 100000 // Default EUR balance
        });
      }
    } catch (error) {
      console.error('Balance fetch error:', error);
    }
  }, []);

  // Initialize
  useEffect(() => {
    fetchTicker();
    fetchOrders();
    fetchBalance();
    connectWebSocket();

    // Polling fallback if WS not connected
    const interval = setInterval(() => {
      if (!wsConnected) {
        fetchTicker();
      }
    }, 2000);

    return () => {
      clearInterval(interval);
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [fetchTicker, fetchOrders, fetchBalance, connectWebSocket, wsConnected]);

  // Update WebSocket when pair changes
  useEffect(() => {
    if (wsRef.current) {
      wsRef.current.close();
    }
    connectWebSocket();
    fetchTicker();
  }, [selectedPair, connectWebSocket, fetchTicker]);

  // Place order
  const placeOrder = async () => {
    if (!quantity || parseFloat(quantity) <= 0) {
      setStatus({ type: 'error', message: 'Inserisci una quantità valida' });
      return;
    }

    setLoading(true);
    setStatus(null);

    try {
      const orderData = {
        symbol: selectedPair.symbol,
        side: orderSide,
        quantity: parseFloat(quantity),
        order_type: orderType
      };

      if (orderType === 'limit' && limitPrice) {
        orderData.price = parseFloat(limitPrice);
      }

      const response = await fetch(`${BACKEND_URL}/api/exchanges/orders`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify(orderData)
      });

      const result = await response.json();

      if (response.ok) {
        const order = result.order;
        setStatus({
          type: 'success',
          message: `Ordine ${order.status === 'filled' ? 'eseguito' : 'piazzato'}: ${orderSide.toUpperCase()} ${quantity} NENO @ €${order.price?.toLocaleString()}`
        });
        setQuantity('');
        setLimitPrice('');
        fetchOrders();
        fetchBalance();
      } else {
        setStatus({ type: 'error', message: result.detail || 'Errore nell\'ordine' });
      }
    } catch (error) {
      setStatus({ type: 'error', message: 'Errore di connessione' });
    } finally {
      setLoading(false);
    }
  };

  // Calculate total
  const calculateTotal = () => {
    const qty = parseFloat(quantity) || 0;
    const price = orderType === 'limit' 
      ? parseFloat(limitPrice) || 0 
      : (orderSide === 'buy' ? ticker?.ask : ticker?.bid) || 0;
    return qty * price;
  };

  // Price change indicator
  const priceChange = ticker ? ((ticker.last - ticker.low_24h) / ticker.low_24h * 100).toFixed(2) : 0;
  const isPositive = parseFloat(priceChange) >= 0;

  if (compact) {
    // Compact version for dashboard
    return (
      <div className="bg-gradient-to-br from-purple-900/30 to-indigo-900/30 rounded-xl p-4 border border-purple-500/20" data-testid="neno-widget-compact">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-full bg-gradient-to-r from-purple-500 to-pink-500 flex items-center justify-center text-white font-bold text-sm">
              N
            </div>
            <div>
              <span className="text-white font-semibold">$NENO</span>
              <span className="text-gray-400 text-sm ml-2">/ EUR</span>
            </div>
          </div>
          <div className={`flex items-center gap-1 text-sm ${isPositive ? 'text-green-400' : 'text-red-400'}`}>
            {isPositive ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
            {priceChange}%
          </div>
        </div>
        
        <div className="text-2xl font-bold text-white mb-2">
          €{ticker?.last?.toLocaleString() || '10,000'}
        </div>
        
        <div className="flex gap-2 text-xs">
          <span className="text-green-400">Bid: €{ticker?.bid?.toLocaleString() || '-'}</span>
          <span className="text-red-400">Ask: €{ticker?.ask?.toLocaleString() || '-'}</span>
        </div>
        
        <div className="flex items-center gap-1 mt-2 text-xs text-gray-400">
          {wsConnected ? (
            <><Wifi className="w-3 h-3 text-green-400" /> Live</>
          ) : (
            <><WifiOff className="w-3 h-3 text-yellow-400" /> Polling</>
          )}
        </div>
      </div>
    );
  }

  // Full trading widget
  return (
    <div className="bg-gray-900 rounded-2xl border border-gray-800 overflow-hidden" data-testid="neno-trading-widget">
      {/* Header */}
      <div className="bg-gradient-to-r from-purple-900/50 to-indigo-900/50 p-4 border-b border-gray-800">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-full bg-gradient-to-r from-purple-500 to-pink-500 flex items-center justify-center text-white font-bold text-xl shadow-lg shadow-purple-500/30">
              N
            </div>
            <div>
              <h2 className="text-xl font-bold text-white">$NENO Trading</h2>
              <p className="text-gray-400 text-sm">NeoNoble Token</p>
            </div>
          </div>
          
          <div className="flex items-center gap-2">
            <div className={`px-2 py-1 rounded-full text-xs flex items-center gap-1 ${
              wsConnected ? 'bg-green-500/20 text-green-400' : 'bg-yellow-500/20 text-yellow-400'
            }`}>
              {wsConnected ? <Wifi className="w-3 h-3" /> : <WifiOff className="w-3 h-3" />}
              {wsConnected ? 'Live' : 'Polling'}
            </div>
            <button
              onClick={fetchTicker}
              className="p-2 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-400 hover:text-white transition-colors"
              data-testid="refresh-ticker-btn"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      <div className="p-4 space-y-4">
        {/* Price Display */}
        <div className="bg-gray-800/50 rounded-xl p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-gray-400 text-sm">Prezzo Corrente</span>
            <div className={`flex items-center gap-1 text-sm ${isPositive ? 'text-green-400' : 'text-red-400'}`}>
              {isPositive ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
              {priceChange}%
            </div>
          </div>
          <div className="text-3xl font-bold text-white mb-3">
            €{ticker?.last?.toLocaleString() || '10,000'}
          </div>
          <div className="grid grid-cols-3 gap-4 text-sm">
            <div>
              <span className="text-gray-500 block">Bid</span>
              <span className="text-green-400 font-medium">€{ticker?.bid?.toLocaleString() || '-'}</span>
            </div>
            <div>
              <span className="text-gray-500 block">Ask</span>
              <span className="text-red-400 font-medium">€{ticker?.ask?.toLocaleString() || '-'}</span>
            </div>
            <div>
              <span className="text-gray-500 block">Volume 24h</span>
              <span className="text-white font-medium">{ticker?.volume_24h?.toLocaleString() || '-'}</span>
            </div>
          </div>
        </div>

        {/* Exchange & Pair Selection */}
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-gray-400 text-xs mb-1 block">Exchange</label>
            <select
              value={selectedExchange.id}
              onChange={(e) => setSelectedExchange(EXCHANGES.find(ex => ex.id === e.target.value))}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:border-purple-500 focus:outline-none"
              data-testid="exchange-select"
            >
              {EXCHANGES.map(ex => (
                <option key={ex.id} value={ex.id}>{ex.icon} {ex.name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-gray-400 text-xs mb-1 block">Coppia</label>
            <select
              value={selectedPair.symbol}
              onChange={(e) => setSelectedPair(NENO_PAIRS.find(p => p.symbol === e.target.value))}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:border-purple-500 focus:outline-none"
              data-testid="pair-select"
            >
              {NENO_PAIRS.map(pair => (
                <option key={pair.symbol} value={pair.symbol}>{pair.display}</option>
              ))}
            </select>
          </div>
        </div>

        {/* Buy/Sell Toggle */}
        <div className="grid grid-cols-2 gap-2">
          <button
            onClick={() => setOrderSide('buy')}
            className={`py-3 rounded-lg font-medium transition-all ${
              orderSide === 'buy'
                ? 'bg-green-500 text-white shadow-lg shadow-green-500/30'
                : 'bg-gray-800 text-gray-400 hover:text-white'
            }`}
            data-testid="buy-btn"
          >
            <ArrowUpRight className="w-4 h-4 inline mr-1" />
            Compra
          </button>
          <button
            onClick={() => setOrderSide('sell')}
            className={`py-3 rounded-lg font-medium transition-all ${
              orderSide === 'sell'
                ? 'bg-red-500 text-white shadow-lg shadow-red-500/30'
                : 'bg-gray-800 text-gray-400 hover:text-white'
            }`}
            data-testid="sell-btn"
          >
            <ArrowDownRight className="w-4 h-4 inline mr-1" />
            Vendi
          </button>
        </div>

        {/* Order Type */}
        <div className="flex gap-2">
          <button
            onClick={() => setOrderType('market')}
            className={`flex-1 py-2 rounded-lg text-sm font-medium transition-colors ${
              orderType === 'market'
                ? 'bg-purple-500/20 text-purple-400 border border-purple-500/50'
                : 'bg-gray-800 text-gray-400'
            }`}
            data-testid="market-order-btn"
          >
            <Zap className="w-4 h-4 inline mr-1" />
            Market
          </button>
          <button
            onClick={() => setOrderType('limit')}
            className={`flex-1 py-2 rounded-lg text-sm font-medium transition-colors ${
              orderType === 'limit'
                ? 'bg-purple-500/20 text-purple-400 border border-purple-500/50'
                : 'bg-gray-800 text-gray-400'
            }`}
            data-testid="limit-order-btn"
          >
            <Clock className="w-4 h-4 inline mr-1" />
            Limit
          </button>
        </div>

        {/* Order Form */}
        <div className="space-y-3">
          <div>
            <label className="text-gray-400 text-xs mb-1 block">Quantità (NENO)</label>
            <input
              type="number"
              value={quantity}
              onChange={(e) => setQuantity(e.target.value)}
              placeholder="0.00"
              step="0.01"
              min="0"
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-3 text-white focus:border-purple-500 focus:outline-none"
              data-testid="quantity-input"
            />
          </div>

          {orderType === 'limit' && (
            <div>
              <label className="text-gray-400 text-xs mb-1 block">Prezzo Limite (€)</label>
              <input
                type="number"
                value={limitPrice}
                onChange={(e) => setLimitPrice(e.target.value)}
                placeholder={ticker?.last?.toString() || '10000'}
                step="1"
                min="0"
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-3 text-white focus:border-purple-500 focus:outline-none"
                data-testid="limit-price-input"
              />
            </div>
          )}

          {/* Total */}
          <div className="bg-gray-800/50 rounded-lg p-3 flex justify-between items-center">
            <span className="text-gray-400">Totale</span>
            <span className="text-xl font-bold text-white">
              €{calculateTotal().toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </span>
          </div>

          {/* Balance Info */}
          <div className="flex justify-between text-sm text-gray-400">
            <span>NENO disponibili: {balance.neno.toFixed(4)}</span>
            <span>EUR disponibili: €{balance.eur.toLocaleString()}</span>
          </div>
        </div>

        {/* Status Message */}
        {status && (
          <div className={`p-3 rounded-lg text-sm ${
            status.type === 'success' 
              ? 'bg-green-500/20 text-green-400 border border-green-500/30'
              : 'bg-red-500/20 text-red-400 border border-red-500/30'
          }`} data-testid="status-message">
            {status.message}
          </div>
        )}

        {/* Submit Button */}
        <button
          onClick={placeOrder}
          disabled={loading || !quantity}
          className={`w-full py-4 rounded-xl font-bold text-lg transition-all ${
            orderSide === 'buy'
              ? 'bg-gradient-to-r from-green-500 to-emerald-500 hover:from-green-600 hover:to-emerald-600 text-white shadow-lg shadow-green-500/30'
              : 'bg-gradient-to-r from-red-500 to-rose-500 hover:from-red-600 hover:to-rose-600 text-white shadow-lg shadow-red-500/30'
          } disabled:opacity-50 disabled:cursor-not-allowed`}
          data-testid="place-order-btn"
        >
          {loading ? (
            <RefreshCw className="w-5 h-5 animate-spin inline" />
          ) : (
            <>
              {orderSide === 'buy' ? 'Compra' : 'Vendi'} NENO
            </>
          )}
        </button>

        {/* Recent Orders */}
        <div className="border-t border-gray-800 pt-4">
          <button
            onClick={() => setShowOrders(!showOrders)}
            className="w-full flex items-center justify-between text-gray-400 hover:text-white transition-colors"
            data-testid="toggle-orders-btn"
          >
            <span className="flex items-center gap-2">
              <BarChart3 className="w-4 h-4" />
              Ordini Recenti ({orders.length})
            </span>
            {showOrders ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>

          {showOrders && (
            <div className="mt-3 space-y-2 max-h-48 overflow-y-auto">
              {orders.length === 0 ? (
                <p className="text-gray-500 text-sm text-center py-4">Nessun ordine recente</p>
              ) : (
                orders.map((order, idx) => (
                  <div
                    key={order.order_id || idx}
                    className="bg-gray-800/50 rounded-lg p-3 flex justify-between items-center text-sm"
                  >
                    <div>
                      <span className={`font-medium ${order.side === 'buy' ? 'text-green-400' : 'text-red-400'}`}>
                        {order.side?.toUpperCase()}
                      </span>
                      <span className="text-white ml-2">{order.quantity} NENO</span>
                    </div>
                    <div className="text-right">
                      <div className="text-white">€{order.price?.toLocaleString()}</div>
                      <div className={`text-xs ${
                        order.status === 'filled' ? 'text-green-400' : 
                        order.status === 'open' ? 'text-yellow-400' : 'text-gray-400'
                      }`}>
                        {order.status}
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
