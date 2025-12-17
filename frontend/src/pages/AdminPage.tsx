import React, { useEffect, useState } from 'react';
import apiClient, { APIError } from '../services/api';
import type { SchedulerConfig, WatchlistResponse } from '../types/api';

const AdminPage: React.FC = () => {
  const [schedulerConfig, setSchedulerConfig] = useState<SchedulerConfig | null>(null);
  const [watchlist, setWatchlist] = useState<WatchlistResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);

      // Load scheduler config and watchlist in parallel
      const [configData, watchlistData] = await Promise.all([
        apiClient.getSchedulerConfig(),
        apiClient.getWatchlist(),
      ]);

      setSchedulerConfig(configData);
      setWatchlist(watchlistData);
    } catch (err) {
      if (err instanceof APIError) {
        setError(err.message);
      } else {
        setError('Failed to load admin data');
      }
      console.error('Admin data load error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handlePauseScheduler = async () => {
    try {
      await apiClient.pauseScheduler();
      await loadData(); // Reload to get updated status
    } catch (err) {
      if (err instanceof APIError) {
        setError(err.message);
      } else {
        setError('Failed to pause scheduler');
      }
    }
  };

  const handleResumeScheduler = async () => {
    try {
      await apiClient.resumeScheduler();
      await loadData(); // Reload to get updated status
    } catch (err) {
      if (err instanceof APIError) {
        setError(err.message);
      } else {
        setError('Failed to resume scheduler');
      }
    }
  };

  if (loading) {
    return (
      <div className="container">
        <h1>Admin Panel</h1>
        <p>Loading...</p>
      </div>
    );
  }

  return (
    <div className="container">
      <h1>Admin Panel</h1>

      {error && (
        <div className="error-banner">
          <strong>Error:</strong> {error}
          <button onClick={() => setError(null)} className="close-button">×</button>
        </div>
      )}

      <section className="section">
        <h2>Scheduler Configuration</h2>
        {schedulerConfig ? (
          <div className="config-panel">
            <div className="config-row">
              <span className="config-label">Status:</span>
              <span className={`status-badge ${schedulerConfig.status}`}>
                {schedulerConfig.status.toUpperCase()}
              </span>
            </div>
            <div className="config-row">
              <span className="config-label">Polling Interval:</span>
              <span>{schedulerConfig.polling_interval_minutes} minutes</span>
            </div>
            <div className="config-row">
              <span className="config-label">Market Hours:</span>
              <span>
                {schedulerConfig.market_hours_start} - {schedulerConfig.market_hours_end}
              </span>
            </div>
            <div className="config-row">
              <span className="config-label">Timezone:</span>
              <span>{schedulerConfig.timezone}</span>
            </div>
            <div className="config-row">
              <span className="config-label">Exclude Weekends:</span>
              <span>{schedulerConfig.exclude_weekends ? 'Yes' : 'No'}</span>
            </div>
            <div className="config-row">
              <span className="config-label">Exclude Holidays:</span>
              <span>{schedulerConfig.exclude_holidays ? 'Yes' : 'No'}</span>
            </div>
            {schedulerConfig.next_run && (
              <div className="config-row">
                <span className="config-label">Next Run:</span>
                <span>{new Date(schedulerConfig.next_run).toLocaleString()}</span>
              </div>
            )}
            {schedulerConfig.last_run && (
              <div className="config-row">
                <span className="config-label">Last Run:</span>
                <span>{new Date(schedulerConfig.last_run).toLocaleString()}</span>
              </div>
            )}

            <div className="button-group">
              {schedulerConfig.status === 'active' ? (
                <button onClick={handlePauseScheduler} className="button button-warning">
                  Pause Scheduler
                </button>
              ) : (
                <button onClick={handleResumeScheduler} className="button button-success">
                  Resume Scheduler
                </button>
              )}
              <button onClick={loadData} className="button button-secondary">
                Refresh
              </button>
            </div>
          </div>
        ) : (
          <p>Scheduler configuration not available</p>
        )}
      </section>

      <section className="section">
        <h2>Watchlist Overview</h2>
        {watchlist ? (
          <div>
            <p>
              <strong>Total Stocks:</strong> {watchlist.total_count}
            </p>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Ticker</th>
                  <th>Company</th>
                  <th>Status</th>
                  <th>Data Points</th>
                  <th>Last Scraped</th>
                </tr>
              </thead>
              <tbody>
                {watchlist.watchlist.slice(0, 10).map((stock) => (
                  <tr key={stock.stock_id}>
                    <td><strong>{stock.ticker}</strong></td>
                    <td>{stock.company_name}</td>
                    <td>
                      <span className={`status-badge ${stock.status}`}>
                        {stock.status}
                      </span>
                    </td>
                    <td>{stock.data_points_count.toLocaleString()}</td>
                    <td>
                      {stock.last_scraped
                        ? new Date(stock.last_scraped).toLocaleString()
                        : 'Never'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {watchlist.total_count > 10 && (
              <p className="note">
                Showing first 10 of {watchlist.total_count} stocks
              </p>
            )}
          </div>
        ) : (
          <p>Watchlist data not available</p>
        )}
      </section>

      <section className="section">
        <h2>System Information</h2>
        <p>
          <strong>API Base URL:</strong>{' '}
          {import.meta.env.VITE_API_URL || 'http://localhost:8000'}
        </p>
        <p>
          <strong>Version:</strong> 1.0.0
        </p>
      </section>
    </div>
  );
};

export default AdminPage;
