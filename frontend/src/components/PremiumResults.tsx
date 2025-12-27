import React, { useState } from 'react';
import { PremiumQueryResponse, PremiumResult, PremiumQueryRequest } from '../types/api';
import PremiumHistogram from './PremiumHistogram';
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

const PremiumResults: React.FC<PremiumResultsProps> = ({ response, loading, error, queryRequest }) => {
  const [histogramData, setHistogramData] = useState<HistogramData | null>(null);
  const [histogramLoading, setHistogramLoading] = useState(false);
  const [histogramError, setHistogramError] = useState<string | null>(null);
  const [selectedStrike, setSelectedStrike] = useState<number | null>(null);

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
        <h3>Premium Statistics</h3>
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
                  className={selectedStrike === result.strike_price ? 'selected-row' : ''}
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
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          <div className="results-summary">
            <p><strong>Total Results:</strong> {response.results.length} strike/duration combinations</p>
            <p><strong>Total Data Points:</strong> {response.results.reduce((sum, r) => sum + r.data_points, 0)}</p>
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
    </div>
  );
};

export default PremiumResults;
