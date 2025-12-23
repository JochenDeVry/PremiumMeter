import React, { useEffect, useState } from 'react';
import apiClient, { APIError } from '../services/api';
import type { SchedulerConfig, WatchlistResponse } from '../types/api';
import { SchedulerConfigPanel } from '../components/SchedulerConfigPanel';

type SortColumn = 'ticker' | 'company_name' | 'status' | 'data_points_count' | 'last_scraped';
type SortDirection = 'asc' | 'desc';

const AdminPage: React.FC = () => {
  const [schedulerConfig, setSchedulerConfig] = useState<SchedulerConfig | null>(null);
  const [watchlist, setWatchlist] = useState<WatchlistResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage, setItemsPerPage] = useState(10);
  const [searchTerm, setSearchTerm] = useState('');
  const [sortColumn, setSortColumn] = useState<SortColumn>('ticker');
  const [sortDirection, setSortDirection] = useState<SortDirection>('asc');
  const [showAddModal, setShowAddModal] = useState(false);
  const [availableStocks, setAvailableStocks] = useState<Array<{ticker: string, company_name: string}>>([]);
  const [loadingStocks, setLoadingStocks] = useState(false);
  const [addSearchTerm, setAddSearchTerm] = useState('');
  const [selectedTicker, setSelectedTicker] = useState('');
  const [operationInProgress, setOperationInProgress] = useState(false);

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

  const handleSort = (column: SortColumn) => {
    if (sortColumn === column) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortColumn(column);
      setSortDirection('asc');
    }
    setCurrentPage(1);
  };

  const handleOpenAddModal = async () => {
    setShowAddModal(true);
    if (availableStocks.length === 0) {
      setLoadingStocks(true);
      try {
        const data = await apiClient.getUSStocks();
        setAvailableStocks(data.stocks);
      } catch (err) {
        console.error('Failed to load US stocks:', err);
        setError('Failed to load available stocks');
      } finally {
        setLoadingStocks(false);
      }
    }
  };

  const handleAddStock = async () => {
    if (!selectedTicker) return;
    
    // Find the company name for the selected ticker
    const selectedStock = availableStocks.find(s => s.ticker === selectedTicker);
    
    setOperationInProgress(true);
    try {
      await apiClient.addStockToWatchlist({ 
        ticker: selectedTicker,
        company_name: selectedStock?.company_name
      });
      await loadData();
      setShowAddModal(false);
      setSelectedTicker('');
      setAddSearchTerm('');
    } catch (err) {
      if (err instanceof APIError) {
        setError(err.message);
      } else {
        setError('Failed to add stock to watchlist');
      }
    } finally {
      setOperationInProgress(false);
    }
  };

  const handleRemoveStock = async (ticker: string) => {
    if (!confirm(`Are you sure you want to remove ${ticker} from the watchlist? This will delete all historical data for this stock.`)) {
      return;
    }
    
    setOperationInProgress(true);
    try {
      await apiClient.removeStockFromWatchlist({ ticker });
      await loadData();
    } catch (err) {
      if (err instanceof APIError) {
        setError(err.message);
      } else {
        setError('Failed to remove stock from watchlist');
      }
    } finally {
      setOperationInProgress(false);
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
        {schedulerConfig ? (
          <SchedulerConfigPanel
            initialConfig={schedulerConfig}
            onConfigUpdated={(config) => setSchedulerConfig(config)}
            onPause={handlePauseScheduler}
            onResume={handleResumeScheduler}
          />
        ) : (
          <div>
            <h2>Scheduler Configuration</h2>
            <p>Loading scheduler configuration...</p>
          </div>
        )}
      </section>

      <section className="section">
        <h2>Watchlist Overview</h2>
        {watchlist ? (
          <div>
            <div className="watchlist-controls">
              <div className="search-bar">
                <input
                  type="text"
                  placeholder="Search by ticker or company name..."
                  value={searchTerm}
                  onChange={(e) => {
                    setSearchTerm(e.target.value);
                    setCurrentPage(1);
                  }}
                  className="search-input"
                />
              </div>
              <button 
                onClick={handleOpenAddModal}
                className="button button-primary"
                disabled={operationInProgress}
              >
                + Add Stock
              </button>
              <div className="pagination-controls">
                <label>
                  Items per page:
                  <select 
                    value={itemsPerPage} 
                    onChange={(e) => {
                      setItemsPerPage(Number(e.target.value));
                      setCurrentPage(1);
                    }}
                    className="items-per-page-select"
                  >
                    <option value={10}>10</option>
                    <option value={20}>20</option>
                    <option value={50}>50</option>
                    <option value={watchlist.total_count}>All</option>
                  </select>
                </label>
              </div>
            </div>
            <table className="data-table">
              <thead>
                <tr>
                  <th className="sortable" onClick={() => handleSort('ticker')}>
                    Ticker {sortColumn === 'ticker' && (sortDirection === 'asc' ? '▲' : '▼')}
                  </th>
                  <th className="sortable" onClick={() => handleSort('company_name')}>
                    Company {sortColumn === 'company_name' && (sortDirection === 'asc' ? '▲' : '▼')}
                  </th>
                  <th className="sortable" onClick={() => handleSort('status')}>
                    Status {sortColumn === 'status' && (sortDirection === 'asc' ? '▲' : '▼')}
                  </th>
                  <th className="sortable" onClick={() => handleSort('data_points_count')}>
                    Data Points {sortColumn === 'data_points_count' && (sortDirection === 'asc' ? '▲' : '▼')}
                  </th>
                  <th className="sortable" onClick={() => handleSort('last_scraped')}>
                    Last Scraped {sortColumn === 'last_scraped' && (sortDirection === 'asc' ? '▲' : '▼')}
                  </th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {(() => {
                  // Filter by search term
                  let filteredStocks = watchlist.watchlist.filter(stock => {
                    const searchLower = searchTerm.toLowerCase();
                    return stock.ticker.toLowerCase().includes(searchLower) ||
                           stock.company_name.toLowerCase().includes(searchLower);
                  });

                  // Sort the filtered results
                  filteredStocks.sort((a, b) => {
                    let aValue: any = a[sortColumn];
                    let bValue: any = b[sortColumn];

                    // Handle null values for last_scraped
                    if (sortColumn === 'last_scraped') {
                      aValue = aValue ? new Date(aValue).getTime() : 0;
                      bValue = bValue ? new Date(bValue).getTime() : 0;
                    }

                    // Handle string comparisons
                    if (typeof aValue === 'string' && typeof bValue === 'string') {
                      aValue = aValue.toLowerCase();
                      bValue = bValue.toLowerCase();
                    }

                    if (aValue < bValue) return sortDirection === 'asc' ? -1 : 1;
                    if (aValue > bValue) return sortDirection === 'asc' ? 1 : -1;
                    return 0;
                  });

                  // Paginate
                  const startIndex = (currentPage - 1) * itemsPerPage;
                  const endIndex = startIndex + itemsPerPage;
                  const displayedStocks = filteredStocks.slice(startIndex, endIndex);
                  
                  return displayedStocks.map((stock) => (
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
                      <td>
                        <button
                          onClick={() => handleRemoveStock(stock.ticker)}
                          className="button button-danger button-sm"
                          disabled={operationInProgress}
                          title="Remove from watchlist"
                        >
                          Remove
                        </button>
                      </td>
                    </tr>
                  ));
                })()}
              </tbody>
            </table>
            {(() => {
              const filteredCount = watchlist.watchlist.filter(stock => {
                const searchLower = searchTerm.toLowerCase();
                return stock.ticker.toLowerCase().includes(searchLower) ||
                       stock.company_name.toLowerCase().includes(searchLower);
              }).length;

              return (
                <>
                  {searchTerm && (
                    <p className="search-results-info">
                      Found {filteredCount} stock{filteredCount !== 1 ? 's' : ''} matching "{searchTerm}"
                    </p>
                  )}
                  {itemsPerPage < filteredCount && (
                    <div className="pagination">
                      <button
                        onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                        disabled={currentPage === 1}
                        className="pagination-button"
                      >
                        Previous
                      </button>
                      <span className="pagination-info">
                        Page {currentPage} of {Math.ceil(filteredCount / itemsPerPage)}
                        {' '}
                        (Showing {((currentPage - 1) * itemsPerPage) + 1}-{Math.min(currentPage * itemsPerPage, filteredCount)} of {filteredCount})
                      </span>
                      <button
                        onClick={() => setCurrentPage(p => Math.min(Math.ceil(filteredCount / itemsPerPage), p + 1))}
                        disabled={currentPage >= Math.ceil(filteredCount / itemsPerPage)}
                        className="pagination-button"
                      >
                        Next
                      </button>
                    </div>
                  )}
                </>
              );
            })()}
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

      {/* Add Stock Modal */}
      {showAddModal && (
        <div className="modal-overlay" onClick={() => setShowAddModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Add Stock to Watchlist</h2>
              <button className="close-button" onClick={() => setShowAddModal(false)}>×</button>
            </div>
            <div className="modal-body">
              {loadingStocks ? (
                <p>Loading available stocks...</p>
              ) : (
                <>
                  <div className="form-group">
                    <label>Search for a stock:</label>
                    <input
                      type="text"
                      placeholder="Type ticker or company name..."
                      value={addSearchTerm}
                      onChange={(e) => setAddSearchTerm(e.target.value)}
                      className="search-input"
                      autoFocus
                    />
                  </div>
                  <div className="stock-list">
                    {(() => {
                      const filteredStocks = availableStocks.filter(stock => {
                        const searchLower = addSearchTerm.toLowerCase();
                        return stock.ticker.toLowerCase().includes(searchLower) ||
                               stock.company_name.toLowerCase().includes(searchLower);
                      });
                      
                      return (
                        <>
                          {filteredStocks.length > 100 && (
                            <div className="stock-list-info">
                              Showing {filteredStocks.length} stocks. Type to filter results.
                            </div>
                          )}
                          {filteredStocks.map(stock => (
                            <div
                              key={stock.ticker}
                              className={`stock-item ${selectedTicker === stock.ticker ? 'selected' : ''}`}
                              onClick={() => setSelectedTicker(stock.ticker)}
                            >
                              <strong>{stock.ticker}</strong> - {stock.company_name}
                            </div>
                          ))}
                        </>
                      );
                    })()}
                  </div>
                </>
              )}
            </div>
            <div className="modal-footer">
              <button
                onClick={() => setShowAddModal(false)}
                className="button button-secondary"
              >
                Cancel
              </button>
              <button
                onClick={handleAddStock}
                className="button button-primary"
                disabled={!selectedTicker || operationInProgress}
              >
                {operationInProgress ? 'Adding...' : 'Add to Watchlist'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AdminPage;
