import React, { useState, useEffect } from 'react';
import type { SchedulerConfig, SchedulerConfigRequest, RateLimitCalculation } from '../types/api';
import { SchedulerStatus } from '../types/api';
import apiClient from '../services/api';
import { ScraperProgressMonitor } from './ScraperProgressMonitor';
import './SchedulerConfigPanel.css';

interface Props {
  initialConfig: SchedulerConfig;
  onConfigUpdated: (config: SchedulerConfig) => void;
  onPause: () => Promise<void>;
  onResume: (startNow?: boolean) => Promise<void>;
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
  const [startNow, setStartNow] = useState(false);
  const [showBrusselsTime, setShowBrusselsTime] = useState(true);

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

  const convertTimeToTimezone = (time: string, fromTz: string, toTz: string) => {
    // Create a date in the source timezone
    const today = new Date().toISOString().split('T')[0];
    const dateString = `${today}T${time}`;
    
    // Parse in source timezone
    const sourceDate = new Date(dateString + 'Z'); // Treat as UTC first
    
    // Convert New York time to Brussels
    // NY is typically UTC-5 (EST) or UTC-4 (EDT)
    // Brussels is UTC+1 (CET) or UTC+2 (CEST)
    // Difference is typically 6 hours (Brussels ahead)
    const [hours, minutes, seconds] = time.split(':').map(Number);
    const brusselsHours = (hours + 6) % 24; // Simple conversion, add 6 hours
    
    return `${brusselsHours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds?.toString().padStart(2, '0') || '00'}`;
  };

  const displayMarketHours = () => {
    if (showBrusselsTime) {
      const startBrussels = convertTimeToTimezone(config.market_hours_start, 'America/New_York', 'Europe/Brussels');
      const endBrussels = convertTimeToTimezone(config.market_hours_end, 'America/New_York', 'Europe/Brussels');
      return { start: startBrussels, end: endBrussels, tz: 'Europe/Brussels (CET/CEST)' };
    }
    return { start: config.market_hours_start, end: config.market_hours_end, tz: config.timezone };
  };

  const marketHours = displayMarketHours();

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

      {/* Scraper Progress Monitor */}
      <ScraperProgressMonitor />

      <div className="config-sections config-grid">
        {/* Top Left: Status Section */}
        <div className="config-section status-section">
          <h3>Status</h3>
          <div className="config-row">
            <span className="config-label">Current Status:</span>
            <span className={`status-badge ${config.status}`}>
              {config.status.toUpperCase()}
            </span>
          </div>
          {config.next_run && (
            <div className="config-row">
              <span className="config-label">Next Scheduled Run:</span>
              <span className="config-value next-run-highlight">
                {new Date(config.next_run).toLocaleString('en-GB', {
                  timeZone: 'Europe/Brussels',
                  year: 'numeric',
                  month: '2-digit',
                  day: '2-digit',
                  hour: '2-digit',
                  minute: '2-digit',
                  second: '2-digit',
                  hour12: false
                })}
              </span>
            </div>
          )}
          {config.status === 'active' && !config.next_run && (
            <div className="config-row">
              <span className="config-label status-info">
                Scheduler is active and waiting to determine next run time
              </span>
            </div>
          )}
          <div className="button-group">
            {config.status === SchedulerStatus.PAUSED ? (
              <>
                <div className="start-controls">
                  <button 
                    onClick={() => onResume(startNow)} 
                    className="button button-success"
                  >
                    Start Scheduler
                  </button>
                  <label className="checkbox-label">
                    <input
                      type="checkbox"
                      checked={startNow}
                      onChange={(e) => setStartNow(e.target.checked)}
                    />
                    Start now
                  </label>
                </div>
              </>
            ) : (
              <button 
                onClick={onPause} 
                className="button button-warning"
                disabled={config.status === SchedulerStatus.RUNNING}
              >
                Pause Scheduler
              </button>
            )}
          </div>
        </div>

        {/* Top Right: Market Hours (Read-Only) */}
        <div className="config-section market-hours-section">
          <div className="section-header-with-toggle">
            <h3>Market Hours</h3>
            <button 
              onClick={() => setShowBrusselsTime(!showBrusselsTime)}
              className="button button-small timezone-toggle"
              title="Switch timezone view"
            >
              🔄 {showBrusselsTime ? '🇧🇪 Brussels' : '🇺🇸 New York'}
            </button>
          </div>
          <div className="config-row">
            <span className="config-label">Trading Hours:</span>
            <span className="config-value">
              {marketHours.start} - {marketHours.end}
            </span>
          </div>
          <div className="config-row">
            <span className="config-label">Timezone:</span>
            <span className="config-value">{marketHours.tz}</span>
          </div>
          <div className="config-row info-text">
            <span className="config-note">
              ⓘ Market hours are set to US stock market trading hours. 
              Times shown are approximate and may vary during daylight saving transitions.
            </span>
          </div>
        </div>

        {/* Bottom Left: Scraper Settings */}
        <div className="config-section scraper-settings-section">
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

        {/* Bottom Right: Rate Limit Calculation */}
        {rateCalc && (
          <div className="config-section api-usage-section">
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

        {/* Market Hours section removed - now at top right */}
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
