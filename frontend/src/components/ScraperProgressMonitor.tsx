import React, { useEffect, useState } from 'react';
import apiClient from '../services/api';
import type { ScraperProgress } from '../types/api';
import './ScraperProgressMonitor.css';

export const ScraperProgressMonitor: React.FC = () => {
  const [progress, setProgress] = useState<ScraperProgress | null>(null);

  useEffect(() => {
    const loadProgress = async () => {
      try {
        const data = await apiClient.getScraperProgress();
        setProgress(data);
      } catch (err) {
        console.error('Failed to load scraper progress:', err);
      }
    };

    // Load immediately
    loadProgress();

    // Poll every 2 seconds when scraper is running
    const interval = setInterval(loadProgress, 2000);

    return () => clearInterval(interval);
  }, []);

  if (!progress || !progress.is_running) {
    return null;
  }

  const progressPercent = progress.total_stocks > 0 
    ? Math.round((progress.completed_stocks / progress.total_stocks) * 100) 
    : 0;

  return (
    <div className="scraper-progress-monitor">
      <h3>🔄 Scraper Running</h3>
      
      <div className="progress-bar-container">
        <div className="progress-bar" style={{ width: `${progressPercent}%` }}>
          <span className="progress-text">{progressPercent}%</span>
        </div>
      </div>

      <div className="progress-stats">
        <span className="stat">
          <strong>Progress:</strong> {progress.completed_stocks} / {progress.total_stocks} stocks
        </span>
        {progress.current_stock && (
          <span className="stat current-stock">
            <strong>Currently scraping:</strong> {progress.current_stock}
            {progress.current_source && (
              <span className="source-badge"> via {progress.current_source}</span>
            )}
          </span>
        )}
      </div>

      {progress.start_time && (
        <div className="progress-time">
          <span>Started: {new Date(progress.start_time).toLocaleTimeString('en-GB', {
            timeZone: 'Europe/Brussels',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            hour12: false
          })}</span>
          {progress.estimated_completion && (
            <span>ETA: {new Date(progress.estimated_completion).toLocaleTimeString('en-GB', {
              timeZone: 'Europe/Brussels',
              hour: '2-digit',
              minute: '2-digit',
              second: '2-digit',
              hour12: false
            })}</span>
          )}
        </div>
      )}

      <div className="stock-lists">
        {progress.completed_stock_list.length > 0 && (
          <div className="stock-list completed">
            <h4>✓ Completed ({progress.completed_stock_list.length})</h4>
            <div className="stock-tags">
              {progress.completed_stock_list.map(ticker => (
                <span key={ticker} className="stock-tag success">{ticker}</span>
              ))}
            </div>
          </div>
        )}

        {progress.pending_stocks.length > 0 && (
          <div className="stock-list pending">
            <h4>⏳ Pending ({progress.pending_stocks.length})</h4>
            <div className="stock-tags">
              {progress.pending_stocks.slice(0, 10).map(ticker => (
                <span key={ticker} className="stock-tag pending">{ticker}</span>
              ))}
              {progress.pending_stocks.length > 10 && (
                <span className="stock-tag more">+{progress.pending_stocks.length - 10} more</span>
              )}
            </div>
          </div>
        )}

        {progress.failed_stocks.length > 0 && (
          <div className="stock-list failed">
            <h4>✗ Failed ({progress.failed_stocks.length})</h4>
            <div className="stock-tags">
              {progress.failed_stocks.map(ticker => (
                <span key={ticker} className="stock-tag error">{ticker}</span>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
