import React, { useEffect, useState } from 'react';
import Plot from 'react-plotly.js';
import apiClient from '../services/api';
import './IntradayStockChart.css';

interface IntradayDataPoint {
  timestamp: string;
  price: number;
  volume?: number;
}

interface IntradayStockChartProps {
  ticker: string;
  companyName?: string;
}

const IntradayStockChart: React.FC<IntradayStockChartProps> = ({ ticker, companyName }) => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<IntradayDataPoint[]>([]);
  const [source, setSource] = useState<string>('');
  const [date, setDate] = useState<string>('');
  const [refreshing, setRefreshing] = useState(false);

  const fetchIntradayData = async () => {
    const isRefresh = !loading; // If not initial load, it's a refresh
    if (isRefresh) {
      setRefreshing(true);
    } else {
      setLoading(true);
    }
    setError(null);

    try {
      const response = await apiClient.getIntradayPrices(ticker);
      setData(response.data_points);
      setSource(response.source);
      setDate(response.date);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('Failed to fetch intraday data');
      }
      console.error('Intraday data fetch error:', err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    if (ticker) {
      fetchIntradayData();
    }
  }, [ticker]);

  const handleRefresh = () => {
    fetchIntradayData();
  };

  if (loading) {
    return (
      <div className="intraday-chart-container">
        <div className="intraday-loading">
          <div className="spinner"></div>
          <p>Loading intraday chart...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="intraday-chart-container">
        <div className="intraday-error">
          <p>⚠️ Intraday Chart Unavailable</p>
          <p className="error-details">{error}</p>
          <p className="error-hint">
            <strong>Common reasons:</strong>
          </p>
          <ul className="error-reasons">
            <li>Market is currently closed (weekends, holidays, after-hours)</li>
            <li>API rate limits reached (Alpha Vantage: 25 calls/day free tier)</li>
            <li>No trading data available yet for today</li>
            <li>Backend needs restart after adding API keys to .env file</li>
          </ul>
        </div>
      </div>
    );
  }

  if (!data || data.length === 0) {
    return (
      <div className="intraday-chart-container">
        <div className="intraday-empty">
          <p>No intraday data available for {ticker}</p>
        </div>
      </div>
    );
  }

  // Prepare chart data
  const timestamps = data.map(d => new Date(d.timestamp));
  const prices = data.map(d => d.price);

  const minPrice = Math.min(...prices);
  const maxPrice = Math.max(...prices);
  const priceRange = maxPrice - minPrice;
  const latestPrice = prices[prices.length - 1];
  const firstPrice = prices[0];
  const priceChange = latestPrice - firstPrice;
  const priceChangePercent = ((priceChange / firstPrice) * 100);

  const isHistorical = source.includes('Historical');
  const displayDate = new Date(date).toLocaleDateString(undefined, {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  });

  return (
    <div className={`intraday-chart-container ${isHistorical ? 'historical-fallback' : ''}`}>
      <div className="intraday-header">
        <div className="chart-title-row">
          <h3>
            {isHistorical ? 'Previous Day Stock Price' : 'Intraday Stock Price'} - {ticker}
          </h3>
          <div className="price-info">
            <button
              className={`refresh-btn ${refreshing ? 'refreshing' : ''}`}
              onClick={handleRefresh}
              disabled={refreshing}
              title="Refresh data"
            >
              🔄
            </button>
            <span className="current-price">${latestPrice.toFixed(2)}</span>
            <span className={`price-change ${priceChange >= 0 ? 'positive' : 'negative'}`}>
              {priceChange >= 0 ? '+' : ''}{priceChange.toFixed(2)} ({priceChangePercent >= 0 ? '+' : ''}{priceChangePercent.toFixed(2)}%)
            </span>
          </div>
        </div>
        {isHistorical && (
          <div className="fallback-notice">
            ⚠️ Intraday data for today is unavailable. Showing data from {displayDate}.
          </div>
        )}
        <div className="chart-info">
          {companyName && <span className="company-name">{companyName}</span>}
          <span className="data-date">Date: {date}</span>
          <span className="data-source">Source: {source}</span>
          <span className="data-points">{data.length} data points</span>
          <span className="interval">5-minute intervals</span>
        </div>
      </div>

      <div className="chart-wrapper">
        <Plot
          data={[
            {
              type: 'scatter',
              mode: 'lines',
              x: timestamps,
              y: prices,
              line: {
                color: priceChange >= 0 ? '#22c55e' : '#ef4444',
                width: 2
              },
              fill: 'tonexty',
              fillcolor: priceChange >= 0 ? 'rgba(34, 197, 94, 0.1)' : 'rgba(239, 68, 68, 0.1)',
              hovertemplate: '<b>%{x|%H:%M}</b><br>$%{y:.2f}<extra></extra>'
            }
          ]}
          layout={{
            autosize: true,
            margin: { l: 60, r: 30, t: 20, b: 60 },
            xaxis: {
              title: 'Time',
              type: 'date',
              tickformat: '%H:%M',
              gridcolor: '#e5e7eb',
              showgrid: true
            },
            yaxis: {
              title: 'Price ($)',
              gridcolor: '#e5e7eb',
              showgrid: true,
              range: [
                minPrice - (priceRange * 0.1),
                maxPrice + (priceRange * 0.1)
              ]
            },
            hovermode: 'x unified',
            plot_bgcolor: '#ffffff',
            paper_bgcolor: '#ffffff',
            font: {
              family: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
              size: 12,
              color: '#374151'
            }
          }}
          config={{
            responsive: true,
            displayModeBar: true,
            displaylogo: false,
            modeBarButtonsToRemove: ['lasso2d', 'select2d']
          }}
          style={{ width: '100%', height: '400px' }}
        />
      </div>

      <div className="chart-stats">
        <div className="stat-item">
          <span className="stat-label">Open:</span>
          <span className="stat-value">${firstPrice.toFixed(2)}</span>
        </div>
        <div className="stat-item">
          <span className="stat-label">Current:</span>
          <span className="stat-value">${latestPrice.toFixed(2)}</span>
        </div>
        <div className="stat-item">
          <span className="stat-label">Day Range:</span>
          <span className="stat-value">${minPrice.toFixed(2)} - ${maxPrice.toFixed(2)}</span>
        </div>
        <div className="stat-item">
          <span className="stat-label">Change:</span>
          <span className={`stat-value ${priceChange >= 0 ? 'positive' : 'negative'}`}>
            {priceChange >= 0 ? '+' : ''}{priceChange.toFixed(2)} ({priceChangePercent >= 0 ? '+' : ''}{priceChangePercent.toFixed(2)}%)
          </span>
        </div>
      </div>
    </div>
  );
};

export default IntradayStockChart;
