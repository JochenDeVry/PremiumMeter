import React, { useEffect, useState } from 'react';
import apiClient from '../services/api';
import type { ScraperRun, StockScrapeLog } from '../types/api';
import './ScraperRunHistory.css';

export const ScraperRunHistory: React.FC = () => {
  const [runs, setRuns] = useState<ScraperRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedRuns, setExpandedRuns] = useState<Set<number>>(new Set());

  useEffect(() => {
    loadRunHistory();
  }, []);

  const loadRunHistory = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiClient.getRunHistory(20);
      setRuns(data.runs);
    } catch (err) {
      console.error('Failed to load run history:', err);
      setError('Failed to load scraper history');
    } finally {
      setLoading(false);
    }
  };

  const toggleExpanded = (runId: number) => {
    const newExpanded = new Set(expandedRuns);
    if (newExpanded.has(runId)) {
      newExpanded.delete(runId);
    } else {
      newExpanded.add(runId);
    }
    setExpandedRuns(newExpanded);
  };

  const formatDuration = (startTime: string, endTime?: string) => {
    if (!endTime) return 'Running...';
    const start = new Date(startTime);
    const end = new Date(endTime);
    const durationMs = end.getTime() - start.getTime();
    const minutes = Math.floor(durationMs / 60000);
    const seconds = Math.floor((durationMs % 60000) / 1000);
    return `${minutes}m ${seconds}s`;
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed': return '✓';
      case 'running': return '⏳';
      case 'failed': return '✗';
      default: return '?';
    }
  };

  const getStatusClass = (status: string) => {
    switch (status) {
      case 'completed': return 'status-completed';
      case 'running': return 'status-running';
      case 'failed': return 'status-failed';
      default: return '';
    }
  };

  if (loading) {
    return (
      <div className="run-history-loading">
        <div className="spinner"></div>
        <p>Loading scraper history...</p>
      </div>
    );
  }

  if (error) {
    return <div className="run-history-error">{error}</div>;
  }

  if (runs.length === 0) {
    return (
      <div className="run-history-empty">
        <p>No scraper runs yet. Start the scheduler to see history.</p>
      </div>
    );
  }

  return (
    <div className="scraper-run-history">
      <h2>Scraper Run History</h2>
      <button onClick={loadRunHistory} className="button refresh-button">
        🔄 Refresh
      </button>

      <div className="runs-list">
        {runs.map((run) => {
          const isExpanded = expandedRuns.has(run.id);
          const successLogs = run.stock_logs.filter(log => log.status === 'success');
          const failedLogs = run.stock_logs.filter(log => log.status === 'failed');

          return (
            <div key={run.id} className={`run-card ${getStatusClass(run.status)}`}>
              <div className="run-header" onClick={() => toggleExpanded(run.id)}>
                <div className="run-header-main">
                  <span className="run-status-icon">{getStatusIcon(run.status)}</span>
                  <div className="run-info">
                    <div className="run-time">
                      {new Date(run.start_time).toLocaleString()}
                    </div>
                    <div className="run-stats">
                      <span className="stat-success">{run.successful_stocks} succeeded</span>
                      {run.failed_stocks > 0 && (
                        <span className="stat-failed">{run.failed_stocks} failed</span>
                      )}
                      <span className="stat-duration">{formatDuration(run.start_time, run.end_time)}</span>
                      <span className="stat-contracts">{run.total_contracts} contracts</span>
                    </div>
                  </div>
                </div>
                <button className="expand-button">
                  {isExpanded ? '▼' : '▶'}
                </button>
              </div>

              {isExpanded && (
                <div className="run-details">
                  {successLogs.length > 0 && (
                    <div className="stock-logs-section">
                      <h4>✓ Successful ({successLogs.length})</h4>
                      <div className="stock-logs">
                        {successLogs.map((log, idx) => (
                          <div key={idx} className="stock-log success">
                            <span className="log-ticker">{log.ticker}</span>
                            {log.source_used && (
                              <span className="log-source">via {log.source_used}</span>
                            )}
                            {log.contracts_scraped !== undefined && (
                              <span className="log-contracts">{log.contracts_scraped} contracts</span>
                            )}
                            <span className="log-time">
                              {new Date(log.timestamp).toLocaleTimeString()}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {failedLogs.length > 0 && (
                    <div className="stock-logs-section">
                      <h4>✗ Failed ({failedLogs.length})</h4>
                      <div className="stock-logs">
                        {failedLogs.map((log, idx) => (
                          <div key={idx} className="stock-log failed">
                            <span className="log-ticker">{log.ticker}</span>
                            <span className="log-time">
                              {new Date(log.timestamp).toLocaleTimeString()}
                            </span>
                            {log.error_message && (
                              <div className="log-error">{log.error_message}</div>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
