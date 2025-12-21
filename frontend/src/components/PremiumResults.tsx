import React from 'react';
import { PremiumQueryResponse, PremiumResult } from '../types/api';

interface PremiumResultsProps {
  response: PremiumQueryResponse | null;
  loading?: boolean;
  error?: string | null;
}

const PremiumResults: React.FC<PremiumResultsProps> = ({ response, loading, error }) => {
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
              </tr>
            </thead>
            <tbody>
              {response.results.map((result: PremiumResult, index: number) => (
                <tr key={index}>
                  <td className="numeric">{formatNumber(result.strike_price)}</td>
                  <td className="numeric">{result.duration_days}</td>
                  <td className="numeric">{result.data_points}</td>
                  <td className="numeric highlight">{formatNumber(result.min_premium)}</td>
                  <td className="numeric highlight-primary">{formatNumber(result.avg_premium)}</td>
                  <td className="numeric highlight">{formatNumber(result.max_premium)}</td>
                  <td className="numeric">{formatNumber(result.latest_premium)}</td>
                  <td className="greeks">{formatGreeks(result.greeks_avg)}</td>
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
    </div>
  );
};

export default PremiumResults;
