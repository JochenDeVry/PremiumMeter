import React, { useState, useEffect } from 'react';
import type { SchedulerConfig, SchedulerConfigRequest, RateLimitCalculation } from '../types/api';
import apiClient from '../services/api';
import './SchedulerConfigPanel.css';

interface Props {
  initialConfig: SchedulerConfig;
  onConfigUpdated: (config: SchedulerConfig) => void;
  onPause: () => Promise<void>;
  onResume: () => Promise<void>;
}

export const SchedulerConfigPanel: React.FC<Props> = ({
  initialConfig,
  onConfigUpdated,
  onPause,
  onResume,
}) => {
  const [isEditing, setIsEditing] = useState(false);
  const [config, setConfig] = useState(initialConfig);
  const [rateCalc, setRateCalc] = useState<RateLimitCalculation | null>(null);
  const [showInfoModal, setShowInfoModal] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Recalculate rates when config changes
  useEffect(() => {
    loadRateCalculation();
  }, [config.polling_interval_minutes, config.stock_delay_seconds, config.max_expirations]);

  useEffect(() => {
    setConfig(initialConfig);
  }, [initialConfig]);

  const loadRateCalculation = async () => {
    try {
      // Pass current config values for real-time calculation
      const calc = await apiClient.getRateLimitCalculation(
        config.polling_interval_minutes,
        config.stock_delay_seconds,
        config.max_expirations
      );
      setRateCalc(calc);
    } catch (err) {
      console.error('Failed to load rate calculation:', err);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    setError(null);

    try {
      const request: SchedulerConfigRequest = {
        polling_interval_minutes: config.polling_interval_minutes,
        stock_delay_seconds: config.stock_delay_seconds,
        max_expirations: config.max_expirations,
      };

      const updatedConfig = await apiClient.updateSchedulerConfig(request);
      onConfigUpdated(updatedConfig);
      setIsEditing(false);
      await loadRateCalculation();
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to save configuration');
    } finally {
      setSaving(false);
    }
  };

  const handleCancel = () => {
    setConfig(initialConfig);
    setIsEditing(false);
    setError(null);
  };

  const getRateLimitStatus = (within: boolean) => {
    return within ? '✓' : '⚠';
  };

  const getRateLimitClass = (within: boolean) => {
    return within ? 'rate-ok' : 'rate-warning';
  };

  return (
    <div className="scheduler-config-panel">
      <div className="panel-header">
        <h2>Scheduler Configuration</h2>
        <button
          onClick={() => setShowInfoModal(true)}
          className="button button-info"
          title="View rate limit information"
        >
          ℹ Info
        </button>
      </div>

      {error && <div className="error-message">{error}</div>}

      <div className="config-sections">
        {/* Status Section */}
        <div className="config-section">
          <h3>Status</h3>
          <div className="config-row">
            <span className="config-label">Current Status:</span>
            <span className={`status-badge ${config.status}`}>
              {config.status.toUpperCase()}
            </span>
          </div>
          <div className="button-group">
            {config.status === 'active' ? (
              <button onClick={onPause} className="button button-warning">
                Pause Scheduler
              </button>
            ) : (
              <button onClick={onResume} className="button button-success">
                Start Scheduler
              </button>
            )}
          </div>
        </div>

        {/* Scraper Settings */}
        <div className="config-section">
          <h3>Scraper Settings</h3>
          
          <div className="config-row">
            <label className="config-label">
              Polling Interval (minutes):
              <span className="hint">How often to scrape (1-1440)</span>
            </label>
            {isEditing ? (
              <input
                type="number"
                min="1"
                max="1440"
                value={config.polling_interval_minutes}
                onChange={(e) =>
                  setConfig({
                    ...config,
                    polling_interval_minutes: parseInt(e.target.value) || 1,
                  })
                }
                className="config-input"
              />
            ) : (
              <span className="config-value">{config.polling_interval_minutes} min</span>
            )}
          </div>

          <div className="config-row">
            <label className="config-label">
              Stock Delay (seconds):
              <span className="hint">Delay between stocks (0-300)</span>
            </label>
            {isEditing ? (
              <input
                type="number"
                min="0"
                max="300"
                value={config.stock_delay_seconds}
                onChange={(e) =>
                  setConfig({
                    ...config,
                    stock_delay_seconds: parseInt(e.target.value) || 0,
                  })
                }
                className="config-input"
              />
            ) : (
              <span className="config-value">{config.stock_delay_seconds} sec</span>
            )}
          </div>

          <div className="config-row">
            <label className="config-label">
              <span className="label-with-tooltip">
                Max Expirations:
                <span className="tooltip-icon" title="Number of nearest option expiration dates to fetch per stock. E.g., if set to 8, the scraper will fetch the 8 nearest expiration dates (typically covering 8 weeks for weekly options, or 8 months for monthly options). Most trading activity occurs in near-term options.">
                  ⓘ
                </span>
              </span>
              <span className="hint">Nearest expiration dates (1-100)</span>
            </label>
            {isEditing ? (
              <input
                type="number"
                min="1"
                max="100"
                value={config.max_expirations}
                onChange={(e) =>
                  setConfig({
                    ...config,
                    max_expirations: parseInt(e.target.value) || 1,
                  })
                }
                className="config-input"
              />
            ) : (
              <span className="config-value">{config.max_expirations} dates</span>
            )}
          </div>

          <div className="button-group">
            {isEditing ? (
              <>
                <button onClick={handleSave} className="button button-primary" disabled={saving}>
                  {saving ? 'Saving...' : 'Save Settings'}
                </button>
                <button onClick={handleCancel} className="button button-secondary" disabled={saving}>
                  Cancel
                </button>
              </>
            ) : (
              <button onClick={() => setIsEditing(true)} className="button button-primary">
                Edit Settings
              </button>
            )}
          </div>
        </div>

        {/* Rate Limit Calculation */}
        {rateCalc && (
          <div className="config-section">
            <h3>Expected API Usage</h3>
            
            <div className="rate-summary">
              <div className="rate-metric">
                <span className="metric-label">Watchlist Size:</span>
                <span className="metric-value">{rateCalc.watchlist_size} stocks</span>
              </div>
              <div className="rate-metric">
                <span className="metric-label">Requests per Stock:</span>
                <span className="metric-value">{rateCalc.requests_per_stock}</span>
              </div>
              <div className="rate-metric">
                <span className="metric-label">Cycle Duration:</span>
                <span className="metric-value">{rateCalc.cycle_duration_minutes.toFixed(1)} min</span>
              </div>
            </div>

            <div className="rate-limits">
              <div className={`rate-limit-row ${getRateLimitClass(rateCalc.within_minute_limit)}`}>
                <span className="rate-icon">{getRateLimitStatus(rateCalc.within_minute_limit)}</span>
                <span className="rate-label">Per Minute:</span>
                <span className="rate-value">
                  {rateCalc.requests_per_minute.toFixed(1)} / 60
                </span>
              </div>
              
              <div className={`rate-limit-row ${getRateLimitClass(rateCalc.within_hour_limit)}`}>
                <span className="rate-icon">{getRateLimitStatus(rateCalc.within_hour_limit)}</span>
                <span className="rate-label">Per Hour:</span>
                <span className="rate-value">
                  {rateCalc.requests_per_hour.toFixed(0)} / 360
                </span>
              </div>
              
              <div className={`rate-limit-row ${getRateLimitClass(rateCalc.within_day_limit)}`}>
                <span className="rate-icon">{getRateLimitStatus(rateCalc.within_day_limit)}</span>
                <span className="rate-label">Per Day:</span>
                <span className="rate-value">
                  {rateCalc.requests_per_day} / 8,000
                </span>
              </div>
            </div>

            {rateCalc.warnings.length > 0 && (
              <div className="warnings-section">
                <h4>⚠ Warnings</h4>
                <ul className="warning-list">
                  {rateCalc.warnings.map((warning, idx) => (
                    <li key={idx}>{warning}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}

        {/* Market Hours (Read-Only) */}
        <div className="config-section">
          <h3>Market Hours</h3>
          <div className="config-row">
            <span className="config-label">Trading Hours:</span>
            <span className="config-value">
              {config.market_hours_start} - {config.market_hours_end}
            </span>
          </div>
          <div className="config-row">
            <span className="config-label">Timezone:</span>
            <span className="config-value">{config.timezone}</span>
          </div>
          {config.next_run && (
            <div className="config-row">
              <span className="config-label">Next Run:</span>
              <span className="config-value">
                {new Date(config.next_run).toLocaleString()}
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Info Modal */}
      {showInfoModal && (
        <div className="modal-overlay" onClick={() => setShowInfoModal(false)}>
          <div className="modal-content large" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Yahoo Finance Rate Limits Guide</h2>
              <button onClick={() => setShowInfoModal(false)} className="modal-close">
                ×
              </button>
            </div>
            <div className="modal-body">
              <div className="info-section">
                <h3>Rate Limits</h3>
                <ul>
                  <li><strong>60 requests per minute</strong></li>
                  <li><strong>360 requests per hour</strong></li>
                  <li><strong>8,000 requests per day</strong></li>
                </ul>
              </div>

              <div className="info-section">
                <h3>How Settings Affect Requests</h3>
                
                <h4>Polling Interval</h4>
                <p>
                  How often the scraper runs. Lower values = more frequent updates but more requests.
                  <strong> Recommended: 120 minutes (2 hours)</strong> for 30-50 stocks.
                </p>

                <h4>Stock Delay</h4>
                <p>
                  Seconds to wait between scraping each stock. Higher values spread requests over time,
                  preventing burst requests that trigger rate limits.
                  <strong> Recommended: 10 seconds</strong> (allows ~6 stocks/minute).
                </p>

                <h4>Max Expirations</h4>
                <p>
                  Number of option expiration dates to fetch per stock. Each expiration = 1 API call.
                  Most trading happens in near-term options (0-90 days).
                  <strong> Recommended: 8 expirations</strong> (balances coverage vs requests).
                </p>
              </div>

              <div className="info-section">
                <h3>Request Calculation</h3>
                <p>Per stock: <code>2 + max_expirations</code> requests</p>
                <ul>
                  <li>1 request for current price</li>
                  <li>1 request for expiration dates list</li>
                  <li>N requests for option chains (N = max_expirations)</li>
                </ul>
                
                <p><strong>Example with current settings:</strong></p>
                <p>
                  {rateCalc && (
                    <>
                      {rateCalc.watchlist_size} stocks × {rateCalc.requests_per_stock} requests = {rateCalc.requests_per_cycle} per cycle
                      <br />
                      {rateCalc.cycles_per_day} cycles/day = {rateCalc.requests_per_day} requests/day
                    </>
                  )}
                </p>
              </div>

              <div className="info-section">
                <h3>Recommended Configurations</h3>
                <table className="config-table">
                  <thead>
                    <tr>
                      <th>Stocks</th>
                      <th>Interval</th>
                      <th>Delay</th>
                      <th>Expirations</th>
                      <th>Daily Requests</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td>10</td>
                      <td>30 min</td>
                      <td>5 sec</td>
                      <td>8</td>
                      <td>~4,800</td>
                    </tr>
                    <tr>
                      <td>30</td>
                      <td>60 min</td>
                      <td>10 sec</td>
                      <td>8</td>
                      <td>~7,200</td>
                    </tr>
                    <tr className="highlighted">
                      <td>50</td>
                      <td>120 min</td>
                      <td>10 sec</td>
                      <td>8</td>
                      <td>~6,000</td>
                    </tr>
                    <tr>
                      <td>80</td>
                      <td>180 min</td>
                      <td>10 sec</td>
                      <td>8</td>
                      <td>~6,400</td>
                    </tr>
                  </tbody>
                </table>
              </div>

              <div className="info-section warning-box">
                <h3>⚠ If You Get Rate Limited</h3>
                <ol>
                  <li><strong>Pause the scheduler immediately</strong></li>
                  <li>Wait 24-48 hours for IP ban to clear</li>
                  <li>Reduce watchlist size or increase polling interval</li>
                  <li>Ensure settings show green checkmarks before resuming</li>
                </ol>
              </div>

              <div className="info-section">
                <h3>Tips</h3>
                <ul>
                  <li>Start with conservative settings and increase gradually</li>
                  <li>Monitor warnings after each change</li>
                  <li>Higher intervals (2-4 hours) are safer for large watchlists</li>
                  <li>Near-term options (8 expirations) cover 90% of trading activity</li>
                  <li>Use stock delay to stay under 60 requests/minute limit</li>
                </ul>
              </div>
            </div>
            <div className="modal-footer">
              <button onClick={() => setShowInfoModal(false)} className="button button-primary">
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
