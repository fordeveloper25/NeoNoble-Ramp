import React, { useEffect, useRef, useState, useCallback } from 'react';
import { createChart, ColorType, CrosshairMode } from 'lightweight-charts';
import {
  TrendingUp,
  TrendingDown,
  BarChart3,
  Clock,
  RefreshCw,
  Maximize2,
  Minimize2
} from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || '';

// Available timeframes
const TIMEFRAMES = [
  { value: '1m', label: '1M' },
  { value: '5m', label: '5M' },
  { value: '15m', label: '15M' },
  { value: '1h', label: '1H' },
  { value: '4h', label: '4H' },
  { value: '1d', label: '1D' }
];

export default function NenoCandlestickChart({ 
  symbol = 'NENO-EUR',
  height = 400,
  showControls = true,
  compact = false
}) {
  const chartContainerRef = useRef(null);
  const chartRef = useRef(null);
  const candlestickSeriesRef = useRef(null);
  const volumeSeriesRef = useRef(null);
  
  const [timeframe, setTimeframe] = useState('1h');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [priceStats, setPriceStats] = useState(null);
  const [isFullscreen, setIsFullscreen] = useState(false);

  // Fetch candlestick data
  const fetchCandles = useCallback(async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch(
        `${BACKEND_URL}/api/price-history/candles/${symbol}?timeframe=${timeframe}&limit=200`
      );
      
      if (!response.ok) throw new Error('Failed to fetch candles');
      
      const data = await response.json();
      
      // Transform data for lightweight-charts
      const candles = data.candles.map(c => ({
        time: Math.floor(c.timestamp / 1000), // Convert to seconds
        open: c.open,
        high: c.high,
        low: c.low,
        close: c.close
      }));
      
      const volumes = data.candles.map(c => ({
        time: Math.floor(c.timestamp / 1000),
        value: c.volume,
        color: c.close >= c.open ? 'rgba(34, 197, 94, 0.5)' : 'rgba(239, 68, 68, 0.5)'
      }));
      
      // Update chart
      if (candlestickSeriesRef.current) {
        candlestickSeriesRef.current.setData(candles);
      }
      if (volumeSeriesRef.current) {
        volumeSeriesRef.current.setData(volumes);
      }
      
      // Fit content
      if (chartRef.current) {
        chartRef.current.timeScale().fitContent();
      }
      
    } catch (err) {
      console.error('Candle fetch error:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [symbol, timeframe]);

  // Fetch price stats
  const fetchStats = useCallback(async () => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/price-history/current/${symbol}`);
      if (response.ok) {
        const data = await response.json();
        setPriceStats(data);
      }
    } catch (err) {
      console.error('Stats fetch error:', err);
    }
  }, [symbol]);

  // Initialize chart
  useEffect(() => {
    if (!chartContainerRef.current) return;

    // Chart options
    const chartOptions = {
      layout: {
        background: { type: ColorType.Solid, color: 'transparent' },
        textColor: '#9CA3AF'
      },
      grid: {
        vertLines: { color: 'rgba(55, 65, 81, 0.3)' },
        horzLines: { color: 'rgba(55, 65, 81, 0.3)' }
      },
      crosshair: {
        mode: CrosshairMode.Normal,
        vertLine: {
          color: '#6366F1',
          width: 1,
          style: 2,
          labelBackgroundColor: '#6366F1'
        },
        horzLine: {
          color: '#6366F1',
          width: 1,
          style: 2,
          labelBackgroundColor: '#6366F1'
        }
      },
      timeScale: {
        borderColor: 'rgba(55, 65, 81, 0.5)',
        timeVisible: true,
        secondsVisible: false
      },
      rightPriceScale: {
        borderColor: 'rgba(55, 65, 81, 0.5)',
        scaleMargins: {
          top: 0.1,
          bottom: 0.2
        }
      },
      handleScroll: {
        mouseWheel: true,
        pressedMouseMove: true
      },
      handleScale: {
        axisPressedMouseMove: true,
        mouseWheel: true,
        pinch: true
      }
    };

    // Create chart
    const chart = createChart(chartContainerRef.current, {
      ...chartOptions,
      width: chartContainerRef.current.clientWidth,
      height: compact ? 200 : height
    });
    chartRef.current = chart;

    // Candlestick series
    const candlestickSeries = chart.addCandlestickSeries({
      upColor: '#22C55E',
      downColor: '#EF4444',
      borderUpColor: '#22C55E',
      borderDownColor: '#EF4444',
      wickUpColor: '#22C55E',
      wickDownColor: '#EF4444'
    });
    candlestickSeriesRef.current = candlestickSeries;

    // Volume series
    const volumeSeries = chart.addHistogramSeries({
      priceFormat: {
        type: 'volume'
      },
      priceScaleId: '',
      scaleMargins: {
        top: 0.85,
        bottom: 0
      }
    });
    volumeSeriesRef.current = volumeSeries;

    // Resize handler
    const handleResize = () => {
      if (chartContainerRef.current && chart) {
        chart.applyOptions({
          width: chartContainerRef.current.clientWidth
        });
      }
    };
    window.addEventListener('resize', handleResize);

    // Cleanup
    return () => {
      window.removeEventListener('resize', handleResize);
      chart.remove();
    };
  }, [height, compact]);

  // Fetch data when timeframe changes
  useEffect(() => {
    fetchCandles();
    fetchStats();

    // Auto-refresh every 30 seconds
    const interval = setInterval(() => {
      fetchCandles();
      fetchStats();
    }, 30000);

    return () => clearInterval(interval);
  }, [fetchCandles, fetchStats]);

  // Toggle fullscreen
  const toggleFullscreen = () => {
    setIsFullscreen(!isFullscreen);
    if (chartRef.current && chartContainerRef.current) {
      chartRef.current.applyOptions({
        height: isFullscreen ? (compact ? 200 : height) : window.innerHeight - 200
      });
    }
  };

  const priceChange = priceStats?.change_pct_24h || 0;
  const isPositive = priceChange >= 0;

  return (
    <div 
      className={`bg-gray-900 rounded-xl border border-gray-800 overflow-hidden ${
        isFullscreen ? 'fixed inset-4 z-50' : ''
      }`}
      data-testid="neno-candlestick-chart"
    >
      {/* Header */}
      {showControls && (
        <div className="p-4 border-b border-gray-800 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-gradient-to-r from-purple-500 to-pink-500 flex items-center justify-center text-white font-bold">
              N
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-white font-semibold text-lg">{symbol}</span>
                {priceStats && (
                  <span className="text-2xl font-bold text-white">
                    €{priceStats.price?.toLocaleString()}
                  </span>
                )}
              </div>
              {priceStats && (
                <div className={`flex items-center gap-2 text-sm ${
                  isPositive ? 'text-green-400' : 'text-red-400'
                }`}>
                  {isPositive ? (
                    <TrendingUp className="w-4 h-4" />
                  ) : (
                    <TrendingDown className="w-4 h-4" />
                  )}
                  <span>
                    {isPositive ? '+' : ''}{priceChange.toFixed(2)}% (24h)
                  </span>
                  <span className="text-gray-500">|</span>
                  <span className="text-gray-400">
                    H: €{priceStats.high_24h?.toLocaleString()}
                  </span>
                  <span className="text-gray-400">
                    L: €{priceStats.low_24h?.toLocaleString()}
                  </span>
                </div>
              )}
            </div>
          </div>
          
          <div className="flex items-center gap-2">
            {/* Timeframe selector */}
            <div className="flex bg-gray-800 rounded-lg p-1">
              {TIMEFRAMES.map(tf => (
                <button
                  key={tf.value}
                  onClick={() => setTimeframe(tf.value)}
                  className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
                    timeframe === tf.value
                      ? 'bg-purple-500 text-white'
                      : 'text-gray-400 hover:text-white'
                  }`}
                  data-testid={`timeframe-${tf.value}`}
                >
                  {tf.label}
                </button>
              ))}
            </div>
            
            <button
              onClick={fetchCandles}
              disabled={loading}
              className="p-2 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-400 hover:text-white transition-colors"
              data-testid="refresh-chart-btn"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            </button>
            
            <button
              onClick={toggleFullscreen}
              className="p-2 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-400 hover:text-white transition-colors"
              data-testid="fullscreen-btn"
            >
              {isFullscreen ? (
                <Minimize2 className="w-4 h-4" />
              ) : (
                <Maximize2 className="w-4 h-4" />
              )}
            </button>
          </div>
        </div>
      )}

      {/* Chart */}
      <div className="relative">
        {loading && (
          <div className="absolute inset-0 bg-gray-900/80 flex items-center justify-center z-10">
            <RefreshCw className="w-8 h-8 text-purple-500 animate-spin" />
          </div>
        )}
        
        {error && (
          <div className="absolute inset-0 bg-gray-900/80 flex items-center justify-center z-10">
            <div className="text-center">
              <p className="text-red-400 mb-2">Errore nel caricamento</p>
              <button
                onClick={fetchCandles}
                className="px-4 py-2 bg-purple-500 text-white rounded-lg hover:bg-purple-600"
              >
                Riprova
              </button>
            </div>
          </div>
        )}
        
        <div 
          ref={chartContainerRef} 
          className="w-full"
          style={{ height: compact ? 200 : height }}
        />
      </div>

      {/* Footer stats */}
      {showControls && priceStats && (
        <div className="p-3 border-t border-gray-800 grid grid-cols-4 gap-4 text-sm">
          <div>
            <span className="text-gray-500 block">Volume 24h</span>
            <span className="text-white font-medium">
              {priceStats.volume_24h?.toLocaleString()} NENO
            </span>
          </div>
          <div>
            <span className="text-gray-500 block">Variazione 24h</span>
            <span className={`font-medium ${isPositive ? 'text-green-400' : 'text-red-400'}`}>
              {isPositive ? '+' : ''}€{priceStats.change_24h?.toLocaleString()}
            </span>
          </div>
          <div>
            <span className="text-gray-500 block">Timeframe</span>
            <span className="text-white font-medium flex items-center gap-1">
              <Clock className="w-3 h-3" />
              {TIMEFRAMES.find(t => t.value === timeframe)?.label}
            </span>
          </div>
          <div>
            <span className="text-gray-500 block">Ultimo aggiornamento</span>
            <span className="text-white font-medium">
              {new Date().toLocaleTimeString('it-IT')}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
