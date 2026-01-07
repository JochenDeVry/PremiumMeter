import React, { useState } from 'react';
import { PremiumQueryResponse, PremiumResult, PremiumQueryRequest } from '../types/api';
import PremiumHistogram from './PremiumHistogram';
import PremiumBoxPlot from './PremiumBoxPlot';
import PremiumSurface3D from './PremiumSurface3D';
import apiClient from '../services/api';

interface PremiumResultsProps {
  response: PremiumQueryResponse | null;
  loading?: boolean;
  error?: string | null;
  queryRequest?: PremiumQueryRequest | null;
}

interface HistogramData {
  premiums: number[];
  ticker: string;
  optionType: string;
  strikePrice: number;
  durationDays: number;
  dataPoints: number;
}

interface BoxPlotData {
  dataPoints: Array<{
    stock_price: number;
    premium: number;
    timestamp: string;
  }>;
  ticker: string;
  optionType: string;
  strikePrice: number;
  durationDays: number;
  stockPriceRange: {
    min: number;
    max: number;
    mean: number;
  };
  totalPoints: number;
}

const PremiumResults: React.FC<PremiumResultsProps> = ({ response, loading, error, queryRequest }) => {
  const [histogramData, setHistogramData] = useState<HistogramData | null>(null);
  const [histogramLoading, setHistogramLoading] = useState(false);
  const [histogramError, setHistogramError] = useState<string | null>(null);
  const [selectedStrike, setSelectedStrike] = useState<number | null>(null);

  const [boxPlotData, setBoxPlotData] = useState<BoxPlotData | null>(null);
  const [boxPlotLoading, setBoxPlotLoading] = useState(false);
  const [boxPlotError, setBoxPlotError] = useState<string | null>(null);
  const [selectedBoxPlotStrike, setSelectedBoxPlotStrike] = useState<number | null>(null);

  const [show3DSurface, setShow3DSurface] = useState(false);

  const fetchHistogramData = async (result: PremiumResult) => {
    if (!response || !queryRequest) return;

    setHistogramLoading(true);
    setHistogramError(null);
    setSelectedStrike(result.strike_price);

    console.log('Result object:', result);
    console.log('Query request:', queryRequest);

    try {
      // Extract the actual string value from the enum
      const optionTypeValue = typeof response.option_type === 'string' 
        ? response.option_type 
        : response.option_type.valueOf();

      // Use the original query's parameters
      const durationDays = queryRequest.duration_days || 30;
      const durationTolerance = queryRequest.duration_tolerance_days ?? 0;  // Use 0 if not specified
      const lookback = queryRequest.lookback_days || 30;

      const requestData = {
        ticker: response.ticker,
        option_type: optionTypeValue,
        strike_price: result.strike_price,
        duration_days: durationDays,
        duration_tolerance_days: durationTolerance,
        lookback_days: lookback,
      };

      console.log('Histogram request:', requestData);

      const data = await apiClient.queryPremiumDistribution(requestData);

      setHistogramData({
        premiums: data.premiums,
        ticker: data.ticker,
        optionType: data.option_type,
        strikePrice: data.strike_price,
        durationDays: data.duration_days,
        dataPoints: data.data_points,
      });
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to load histogram data';
      setHistogramError(errorMsg);
      console.error('Histogram error:', err);
    } finally {
      setHistogramLoading(false);
    }
  };

  const fetchBoxPlotData = async (result: PremiumResult) => {
    if (!response || !queryRequest) return;

    setBoxPlotLoading(true);
    setBoxPlotError(null);
    setSelectedBoxPlotStrike(result.strike_price);

    try {
      const optionTypeValue = typeof response.option_type === 'string' 
        ? response.option_type 
        : response.option_type.valueOf();

      const durationDays = queryRequest.duration_days || 30;
      const durationTolerance = queryRequest.duration_tolerance_days ?? 0;
      const lookback = queryRequest.lookback_days || 30;

      const requestData = {
        ticker: response.ticker,
        option_type: optionTypeValue,
        strike_price: result.strike_price,
        duration_days: durationDays,
        duration_tolerance_days: durationTolerance,
        lookback_days: lookback,
      };

      console.log('Box plot request:', requestData);

      const data = await apiClient.queryPremiumBoxPlot(requestData);

      setBoxPlotData({
        dataPoints: data.data_points,
        ticker: data.ticker,
        optionType: data.option_type,
        strikePrice: data.strike_price,
        durationDays: data.duration_days,
        stockPriceRange: data.stock_price_range,
        totalPoints: data.total_points,
      });
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to load box plot data';
      setBoxPlotError(errorMsg);
      console.error('Box plot error:', err);
    } finally {
      setBoxPlotLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="results-container">
        <div className="loading">
          <div className="spinner"></div>
          <p>Querying premium data...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="results-container">
        <div className="error">
          <h3>Error</h3>
          <p>{error}</p>
        </div>
      </div>
    );
  }

  if (!response) {
    return (
      <div className="results-container">
        <div className="placeholder">
          <p>Submit a query to see premium statistics</p>
        </div>
      </div>
    );
  }

  const formatNumber = (num: number | undefined, decimals: number = 2): string => {
    if (num === undefined || num === null) return 'N/A';
    return num.toFixed(decimals);
  };

  const formatGreeks = (greeks: PremiumResult['greeks_avg']): string => {
    if (!greeks) return 'N/A';
    const parts: string[] = [];
    if (greeks.delta !== undefined) parts.push(`Δ ${formatNumber(greeks.delta, 4)}`);
    if (greeks.gamma !== undefined) parts.push(`Γ ${formatNumber(greeks.gamma, 4)}`);
    if (greeks.theta !== undefined) parts.push(`Θ ${formatNumber(greeks.theta, 4)}`);
    if (greeks.vega !== undefined) parts.push(`V ${formatNumber(greeks.vega, 4)}`);
    return parts.length > 0 ? parts.join(', ') : 'N/A';
  };

  return (
    <div className="results-container">
      <div className="results-header">
        <div className="results-title-row">
          <h3>Premium Statistics</h3>
          {response.current_stock_price && (
            <div className="current-price-badge">
              <span className="price-label">Current Price</span>
              <span className="price-value">${response.current_stock_price.toFixed(2)}</span>
            </div>
          )}
        </div>
        <div className="results-meta">
          <span><strong>Ticker:</strong> {response.ticker}</span>
          <span><strong>Type:</strong> {response.option_type.toUpperCase()}</span>
          <span><strong>Query Time:</strong> {new Date(response.query_timestamp).toLocaleString()}</span>
        </div>
      </div>

      {response.results.length === 0 ? (
        <div className="no-results">
          <p>No premium data found for the specified criteria.</p>
          <p className="help-text">
            Try adjusting the strike price, duration tolerance, or lookback period.
          </p>
        </div>
      ) : (
        <div className="results-table-container">
          <table className="results-table">
            <thead>
              <tr>
                <th>Strike ($)</th>
                <th>Duration (days)</th>
                <th>Data Points</th>
                <th>Min Premium ($)</th>
                <th>Avg Premium ($)</th>
                <th>Max Premium ($)</th>
                <th>Latest ($)</th>
                <th>Greeks (Avg)</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {response.results.map((result: PremiumResult, index: number) => (
                <tr 
                  key={index}
                  className={
                    selectedStrike === result.strike_price || selectedBoxPlotStrike === result.strike_price
                      ? 'selected-row'
                      : ''
                  }
                >
                  <td className="numeric">{formatNumber(result.strike_price)}</td>
                  <td className="numeric">{result.duration_days}</td>
                  <td className="numeric">{result.data_points}</td>
                  <td className="numeric highlight">{formatNumber(result.min_premium)}</td>
                  <td className="numeric highlight-primary">{formatNumber(result.avg_premium)}</td>
                  <td className="numeric highlight">{formatNumber(result.max_premium)}</td>
                  <td className="numeric">{formatNumber(result.latest_premium)}</td>
                  <td className="greeks">{formatGreeks(result.greeks_avg)}</td>
                  <td className="actions">
                    <button
                      className="histogram-btn"
                      onClick={() => fetchHistogramData(result)}
                      disabled={histogramLoading}
                      title="View premium distribution histogram"
                    >
                      📊 Histogram
                    </button>
                    <button
                      className="boxplot-btn"
                      onClick={() => fetchBoxPlotData(result)}
                      disabled={boxPlotLoading}
                      title="View premium vs stock price box plot"
                    >
                      📦 Box Plot
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          <div className="results-summary">
            <p><strong>Total Results:</strong> {response.results.length} strike/duration combinations</p>
            <p><strong>Total Data Points:</strong> {response.results.reduce((sum, r) => sum + r.data_points, 0)}</p>
            <button
              className="surface-3d-toggle-btn"
              onClick={() => setShow3DSurface(!show3DSurface)}
            >
              {show3DSurface ? '✕ Hide' : '🎲 View'} 3D Premium Surface
            </button>
          </div>
        </div>
      )}

      {/* Histogram Section */}
      {histogramLoading && (
        <div className="histogram-loading">
          <div className="spinner"></div>
          <p>Loading histogram data...</p>
        </div>
      )}

      {histogramError && (
        <div className="histogram-error">
          <p>Error loading histogram: {histogramError}</p>
        </div>
      )}

      {histogramData && !histogramLoading && !histogramError && (
        <PremiumHistogram
          premiums={histogramData.premiums}
          ticker={histogramData.ticker}
          optionType={histogramData.optionType}
          strikePrice={histogramData.strikePrice}
          durationDays={histogramData.durationDays}
          dataPoints={histogramData.dataPoints}
        />
      )}

      {/* Box Plot Section */}
      {boxPlotLoading && (
        <div className="histogram-loading">
          <div className="spinner"></div>
          <p>Loading box plot data...</p>
        </div>
      )}

      {boxPlotError && (
        <div className="histogram-error">
          <p>Error loading box plot: {boxPlotError}</p>
        </div>
      )}

      {boxPlotData && !boxPlotLoading && !boxPlotError && (
        <PremiumBoxPlot
          ticker={boxPlotData.ticker}
          optionType={boxPlotData.optionType}
          strikePrice={boxPlotData.strikePrice}
          durationDays={boxPlotData.durationDays}
          currentStockPrice={response?.current_stock_price}
          dataPoints={boxPlotData.dataPoints}
          stockPriceRange={boxPlotData.stockPriceRange}
        />
      )}

      {/* 3D Surface Section */}
      {show3DSurface && response && queryRequest && (
        <PremiumSurface3D
          ticker={response.ticker}
          optionType={
            typeof response.option_type === 'string'
              ? response.option_type
              : response.option_type.valueOf()
          }
          initialDuration={queryRequest.duration_days || 30}
          lookbackDays={queryRequest.lookback_days || 30}
          toleranceDays={queryRequest.duration_tolerance_days ?? 3}
          queryStrikePrices={response.results.map(r => r.strike_price)}
        />
      )}
    </div>
  );
};

export default PremiumResults;
