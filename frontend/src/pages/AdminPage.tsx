import React, { useEffect, useState } from 'react';
import apiClient, { APIError } from '../services/api';
import type { SchedulerConfig, WatchlistResponse } from '../types/api';
import { SchedulerConfigPanel } from '../components/SchedulerConfigPanel';
import { ScraperRunHistory } from '../components/ScraperRunHistory';

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
  const [selectedStocks, setSelectedStocks] = useState<Set<number>>(new Set());
  const [bulkAction, setBulkAction] = useState<string>('');
  const [selectAll, setSelectAll] = useState(false);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [minDataPoints, setMinDataPoints] = useState<string>('');
  const [maxDataPoints, setMaxDataPoints] = useState<string>('');
  const [showFilters, setShowFilters] = useState(false);

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

  const handleResumeScheduler = async (startNow: boolean = false) => {
    try {
      await apiClient.resumeScheduler(startNow);
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

  const handleActivateStock = async (ticker: string) => {
    const scrollPosition = window.scrollY;
    setOperationInProgress(true);
    try {
      await apiClient.updateStockStatus({ ticker, status: 'active' });
      await loadData();
      requestAnimationFrame(() => {
        window.scrollTo(0, scrollPosition);
      });
    } catch (err) {
      if (err instanceof APIError) {
        setError(err.message);
      } else {
        setError('Failed to activate stock');
      }
    } finally {
      setOperationInProgress(false);
    }
  };

  const handleDeactivateStock = async (ticker: string) => {
    const scrollPosition = window.scrollY;
    setOperationInProgress(true);
    try {
      await apiClient.updateStockStatus({ ticker, status: 'inactive' });
      await loadData();
      requestAnimationFrame(() => {
        window.scrollTo(0, scrollPosition);
      });
    } catch (err) {
      if (err instanceof APIError) {
        setError(err.message);
      } else {
        setError('Failed to deactivate stock');
      }
    } finally {
      setOperationInProgress(false);
    }
  };

  const handleToggleStock = (stockId: number) => {
    setSelectedStocks(prev => {
      const newSet = new Set(prev);
      if (newSet.has(stockId)) {
        newSet.delete(stockId);
      } else {
        newSet.add(stockId);
      }
      return newSet;
    });
  };

  const handleToggleAllVisible = (displayedStocks: any[]) => {
    if (selectAll) {
      setSelectedStocks(new Set());
      setSelectAll(false);
    } else {
      setSelectedStocks(new Set(displayedStocks.map(s => s.stock_id)));
      setSelectAll(true);
    }
  };

  const handleBulkAction = async () => {
    if (selectedStocks.size === 0) {
      setError('Please select at least one stock');
      return;
    }

    if (!bulkAction) {
      setError('Please select an action');
      return;
    }

    if (bulkAction === 'remove') {
      if (!confirm(`Are you sure you want to remove ${selectedStocks.size} stock(s) from the watchlist? This will delete all historical data for these stocks.`)) {
        return;
      }
    }

    const scrollPosition = window.scrollY;
    setOperationInProgress(true);
    try {
      const tickers = watchlist?.watchlist
        .filter(s => selectedStocks.has(s.stock_id))
        .map(s => s.ticker) || [];

      await apiClient.bulkStockAction({
        tickers,
        action: bulkAction as 'activate' | 'deactivate' | 'remove'
      });

      setSelectedStocks(new Set());
      setSelectAll(false);
      setBulkAction('');
      await loadData();
      requestAnimationFrame(() => {
        window.scrollTo(0, scrollPosition);
      });
    } catch (err) {
      if (err instanceof APIError) {
        setError(err.message);
      } else {
        setError('Failed to perform bulk action');
      }
    } finally {
      setOperationInProgress(false);
    }
  };

  if (loading) {
    return (
      <div className="container">
        <h1>Admin Panel</h1>
        <div className="loading-container">
          <div className="spinner"></div>
          <p>Loading admin data...</p>
        </div>
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

      {/* Scraper Run History */}
      <ScraperRunHistory />

      {/* Watchlist Overview */}
      <div className="watchlist-overview-card">
        <h2>Watchlist Overview</h2>
        {watchlist ? (
          <div>
            <div className="watchlist-controls">
              <div className="filter-info">
                {(searchTerm || statusFilter !== 'all' || minDataPoints || maxDataPoints) && (
                  <span className="active-filters-badge">
                    Filters active
                  </span>
                )}
              </div>
              <div className="bulk-actions">
                <select 
                  value={bulkAction} 
                  onChange={(e) => setBulkAction(e.target.value)}
                  className="bulk-action-select"
                  disabled={selectedStocks.size === 0 || operationInProgress}
                >
                  <option value="">Bulk Actions ({selectedStocks.size} selected)</option>
                  <option value="activate">Activate Selected</option>
                  <option value="deactivate">Deactivate Selected</option>
                  <option value="remove">Remove Selected</option>
                </select>
                <button
                  onClick={handleBulkAction}
                  className="button button-secondary button-sm"
                  disabled={!bulkAction || selectedStocks.size === 0 || operationInProgress}
                >
                  Apply
                </button>
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
                  <th style={{width: '50px'}}>
                    <input
                      type="checkbox"
                      checked={selectAll}
                      onChange={() => {
                        const filteredStocks = watchlist.watchlist.filter(stock => {
                          const searchLower = searchTerm.toLowerCase();
                          const matchesSearch = !searchTerm || 
                            stock.ticker.toLowerCase().includes(searchLower) ||
                            stock.company_name.toLowerCase().includes(searchLower);
                          const matchesStatus = statusFilter === 'all' || stock.status === statusFilter;
                          const minDP = minDataPoints ? parseInt(minDataPoints) : null;
                          const maxDP = maxDataPoints ? parseInt(maxDataPoints) : null;
                          const matchesDataPoints = 
                            (!minDP || stock.data_points_count >= minDP) &&
                            (!maxDP || stock.data_points_count <= maxDP);
                          return matchesSearch && matchesStatus && matchesDataPoints;
                        });
                        const startIndex = (currentPage - 1) * itemsPerPage;
                        const endIndex = startIndex + itemsPerPage;
                        const displayedStocks = filteredStocks.slice(startIndex, endIndex);
                        handleToggleAllVisible(displayedStocks);
                      }}
                    />
                  </th>
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
                <tr className="filter-row">
                  <th>
                    <button 
                      onClick={() => setShowFilters(!showFilters)}
                      className="filter-toggle"
                      title="Toggle filters"
                    >
                      {showFilters ? '▼' : '▶'}
                    </button>
                  </th>
                  <th>
                    {showFilters && (
                      <input
                        type="text"
                        placeholder="Filter ticker..."
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                        className="column-filter"
                      />
                    )}
                  </th>
                  <th>
                    {showFilters && (
                      <input
                        type="text"
                        placeholder="Filter company..."
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                        className="column-filter"
                      />
                    )}
                  </th>
                  <th>
                    {showFilters && (
                      <select
                        value={statusFilter}
                        onChange={(e) => setStatusFilter(e.target.value)}
                        className="column-filter"
                      >
                        <option value="all">All</option>
                        <option value="active">Active</option>
                        <option value="paused">Inactive</option>
                      </select>
                    )}
                  </th>
                  <th>
                    {showFilters && (
                      <div style={{display: 'flex', gap: '2px', flexDirection: 'column'}}>
                        <input
                          type="number"
                          placeholder="Min"
                          value={minDataPoints}
                          onChange={(e) => setMinDataPoints(e.target.value)}
                          className="column-filter column-filter-small"
                        />
                        <input
                          type="number"
                          placeholder="Max"
                          value={maxDataPoints}
                          onChange={(e) => setMaxDataPoints(e.target.value)}
                          className="column-filter column-filter-small"
                        />
                      </div>
                    )}
                  </th>
                  <th></th>
                  <th>
                    {showFilters && (
                      <button
                        onClick={() => {
                          setSearchTerm('');
                          setStatusFilter('all');
                          setMinDataPoints('');
                          setMaxDataPoints('');
                        }}
                        className="button button-secondary button-sm"
                        style={{fontSize: '0.75rem', padding: '0.2rem 0.4rem'}}
                      >
                        Clear
                      </button>
                    )}
                  </th>
                </tr>
              </thead>
              <tbody>
                {(() => {
                  // Filter by all criteria
                  let filteredStocks = watchlist.watchlist.filter(stock => {
                    // Search term filter (ticker or company name)
                    const searchLower = searchTerm.toLowerCase();
                    const matchesSearch = !searchTerm || 
                      stock.ticker.toLowerCase().includes(searchLower) ||
                      stock.company_name.toLowerCase().includes(searchLower);
                    
                    // Status filter
                    const matchesStatus = statusFilter === 'all' || stock.status === statusFilter;
                    
                    // Data points filter
                    const minDP = minDataPoints ? parseInt(minDataPoints) : null;
                    const maxDP = maxDataPoints ? parseInt(maxDataPoints) : null;
                    const matchesDataPoints = 
                      (!minDP || stock.data_points_count >= minDP) &&
                      (!maxDP || stock.data_points_count <= maxDP);
                    
                    return matchesSearch && matchesStatus && matchesDataPoints;
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
                      <td>
                        <input
                          type="checkbox"
                          checked={selectedStocks.has(stock.stock_id)}
                          onChange={() => handleToggleStock(stock.stock_id)}
                        />
                      </td>
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
                        <div style={{display: 'flex', gap: '5px', flexWrap: 'wrap'}}>
                          <button
                            onClick={() => handleActivateStock(stock.ticker)}
                            className="button button-success button-sm"
                            disabled={operationInProgress || stock.status === 'active'}
                            title="Activate stock"
                          >
                            Activate
                          </button>
                          <button
                            onClick={() => handleDeactivateStock(stock.ticker)}
                            className="button button-warning button-sm"
                            disabled={operationInProgress || stock.status !== 'active'}
                            title="Deactivate stock"
                          >
                            Deactivate
                          </button>
                          <button
                            onClick={() => handleRemoveStock(stock.ticker)}
                            className="button button-danger button-sm"
                            disabled={operationInProgress}
                            title="Remove from watchlist"
                          >
                            Remove
                          </button>
                        </div>
                      </td>
                    </tr>
                  ));
                })()}
              </tbody>
            </table>
            {(() => {
              const filteredCount = watchlist.watchlist.filter(stock => {
                const searchLower = searchTerm.toLowerCase();
                const matchesSearch = !searchTerm || 
                  stock.ticker.toLowerCase().includes(searchLower) ||
                  stock.company_name.toLowerCase().includes(searchLower);
                const matchesStatus = statusFilter === 'all' || stock.status === statusFilter;
                const minDP = minDataPoints ? parseInt(minDataPoints) : null;
                const maxDP = maxDataPoints ? parseInt(maxDataPoints) : null;
                const matchesDataPoints = 
                  (!minDP || stock.data_points_count >= minDP) &&
                  (!maxDP || stock.data_points_count <= maxDP);
                return matchesSearch && matchesStatus && matchesDataPoints;
              }).length;

              const hasActiveFilters = searchTerm || statusFilter !== 'all' || minDataPoints || maxDataPoints;

              return (
                <>
                  {hasActiveFilters && (
                    <p className="search-results-info">
                      Found {filteredCount} stock{filteredCount !== 1 ? 's' : ''} matching filters
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
      </div>

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
                <div className="loading-container">
                  <div className="spinner"></div>
                  <p>Loading available stocks...</p>
                  <p className="info-text">This may take up to 15 seconds</p>
                </div>
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
