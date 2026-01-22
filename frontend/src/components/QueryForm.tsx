import React, { useState, useEffect, useRef } from 'react';
import { OptionType, StrikeMode, PremiumQueryRequest } from '../types/api';
import apiClient from '../services/api';

interface QueryFormProps {
  onSubmit: (request: PremiumQueryRequest) => void;
  loading?: boolean;
}

interface Stock {
  ticker: string;
  company_name: string;
}

const QueryForm: React.FC<QueryFormProps> = ({ onSubmit, loading = false }) => {
  const [stocks, setStocks] = useState<Stock[]>([]);
  const [filteredStocks, setFilteredStocks] = useState<Stock[]>([]);
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [showDropdown, setShowDropdown] = useState<boolean>(false);
  const [ticker, setTicker] = useState<string>('AAPL');
  const [selectedStock, setSelectedStock] = useState<Stock | null>(null);
  const [optionType, setOptionType] = useState<OptionType>(OptionType.PUT);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);
  const [isSearching, setIsSearching] = useState<boolean>(false);  // Track if user is actively searching
  const [strikeMode, setStrikeMode] = useState<StrikeMode>(StrikeMode.NEAREST);
  const [strikePrice, setStrikePrice] = useState<string>('270');
  const [strikeRangePercent, setStrikeRangePercent] = useState<string>('5');
  const [nearestCountAbove, setNearestCountAbove] = useState<string>('20');
  const [nearestCountBelow, setNearestCountBelow] = useState<string>('20');
  const [expirationDate, setExpirationDate] = useState<string>('');
  const [durationDays, setDurationDays] = useState<string>('7');
  const [durationToleranceDays, setDurationToleranceDays] = useState<string>('0');
  const [lookbackDays, setLookbackDays] = useState<string>('');  // Empty string means entire database
  const [stockPriceRangePercent, setStockPriceRangePercent] = useState<string>('5');
  const [currentStockPrice, setCurrentStockPrice] = useState<number | null>(null);
  const [showAdvancedSettings, setShowAdvancedSettings] = useState<boolean>(false);

  // Get next N Fridays from today
  const getUpcomingFridays = (count: number = 20): Array<{ date: string; label: string; days: number }> => {
    const fridays: Array<{ date: string; label: string; days: number }> = [];
    const today = new Date();
    today.setHours(0, 0, 0, 0);

    // Find next Friday
    let current = new Date(today);
    const dayOfWeek = current.getDay();
    const daysUntilFriday = (5 - dayOfWeek + 7) % 7 || 7; // If today is Friday, get next Friday
    current.setDate(current.getDate() + daysUntilFriday);

    // Generate next N Fridays
    for (let i = 0; i < count; i++) {
      const dateString = current.toISOString().split('T')[0];
      const diffTime = current.getTime() - today.getTime();
      const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

      const label = current.toLocaleDateString('en-US', {
        weekday: 'short',
        month: 'short',
        day: 'numeric',
        year: 'numeric'
      });

      fridays.push({
        date: dateString,
        label: `${label} (${diffDays} days until expiry)`,
        days: diffDays
      });

      // Move to next Friday
      current.setDate(current.getDate() + 7);
    }

    return fridays;
  };

  const [upcomingFridays] = useState(getUpcomingFridays());

  // Initialize with next Friday
  useEffect(() => {
    if (upcomingFridays.length > 0) {
      setExpirationDate(upcomingFridays[0].date);
      setDurationDays(upcomingFridays[0].days.toString());
    }
  }, []);

  // Update duration when date changes
  const handleDateChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const dateString = e.target.value;
    const selectedFriday = upcomingFridays.find(f => f.date === dateString);

    if (selectedFriday) {
      setExpirationDate(dateString);
      setDurationDays(selectedFriday.days.toString());
    }
  };

  // Load stocks on component mount
  useEffect(() => {
    const loadStocks = async () => {
      try {
        const stockList = await apiClient.listAllStocks();
        setStocks(stockList);
        setFilteredStocks(stockList);

        // Set initial selected stock (AAPL)
        const initialStock = stockList.find(s => s.ticker === 'AAPL');
        if (initialStock) {
          setSelectedStock(initialStock);
        }

        // Fetch initial strike price for default ticker (AAPL)
        fetchStockPrice('AAPL');
      } catch (error) {
        console.error('Failed to load stocks:', error);
      }
    };
    loadStocks();
  }, []);

  // Filter stocks based on search term
  useEffect(() => {
    if (searchTerm.trim() === '') {
      setFilteredStocks(stocks);
    } else {
      const term = searchTerm.toLowerCase();
      const filtered = stocks.filter(
        stock =>
          stock.ticker.toLowerCase().includes(term) ||
          stock.company_name.toLowerCase().includes(term)
      );
      setFilteredStocks(filtered);
    }
  }, [searchTerm, stocks]);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setShowDropdown(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  // Automatically focus the search input when search mode is activated
  useEffect(() => {
    if (isSearching && searchInputRef.current) {
      searchInputRef.current.focus();
    }
  }, [isSearching]);

  const handleStockSelect = (selectedTicker: string) => {
    const stock = stocks.find(s => s.ticker === selectedTicker);
    setTicker(selectedTicker);
    setSelectedStock(stock || null);
    setSearchTerm(selectedTicker);
    setShowDropdown(false);
    setIsSearching(false);  // Done searching

    // Fetch and set the current stock price as strike price
    fetchStockPrice(selectedTicker);
  };

  const fetchStockPrice = async (ticker: string) => {
    try {
      const priceInfo = await apiClient.getStockPrice(ticker);
      if (priceInfo.latest_price !== null) {
        setStrikePrice(priceInfo.latest_price.toFixed(2));
        setCurrentStockPrice(priceInfo.latest_price);
      }
    } catch (error) {
      console.error('Failed to fetch stock price:', error);
      // Silently fail - user can manually set strike price
    }
  };

  const handleInputFocus = () => {
    // Clear search term and start searching mode
    setSearchTerm('');
    setIsSearching(true);
    setShowDropdown(true);
  };

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setSearchTerm(value);
    setIsSearching(true);
    // Only update ticker when user types, keep it in sync
    if (value.trim() !== '') {
      setTicker(value.toUpperCase());
    }
    setShowDropdown(true);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    const request: PremiumQueryRequest = {
      ticker: ticker.toUpperCase(),
      option_type: optionType,
      strike_mode: strikeMode,
      strike_price: parseFloat(strikePrice),
      duration_days: parseInt(durationDays),
      duration_tolerance_days: parseInt(durationToleranceDays),
      // If lookbackDays is empty, use a very large number to query entire database
      lookback_days: lookbackDays.trim() === '' ? 3650 : parseInt(lookbackDays),
      // Stock price matching
      current_stock_price: currentStockPrice || undefined,
      stock_price_range_percent: parseFloat(stockPriceRangePercent),
    };

    // Add mode-specific parameters
    if (strikeMode === StrikeMode.PERCENTAGE_RANGE) {
      request.strike_range_percent = parseFloat(strikeRangePercent);
    } else if (strikeMode === StrikeMode.NEAREST) {
      request.nearest_count_above = parseInt(nearestCountAbove);
      request.nearest_count_below = parseInt(nearestCountBelow);
    }

    onSubmit(request);
  };

  return (
    <form onSubmit={handleSubmit} className="query-form">
      <div className="query-cards-container">
        {/* LEFT CARD: Stock & Option Type + Stock Price Matching */}
        <div className="query-settings-card">
            <div className="form-section">
              <h3>Stock & Option Type</h3>

              <div className="form-group">
                <label htmlFor="ticker">Ticker Symbol</label>
                <div className="stock-search-container" ref={dropdownRef}>
                  {!isSearching && selectedStock ? (
                    <div
                      className="stock-display-selected"
                      onClick={handleInputFocus}
                    >
                      <img
                        src={`/logos/${selectedStock.ticker.toUpperCase()}.png`}
                        alt=""
                        className="stock-logo-mini"
                        onError={(e) => (e.currentTarget.style.display = 'none')}
                      />
                      <span className="stock-ticker">{selectedStock.ticker}</span>
                      <span className="stock-name">{selectedStock.company_name}</span>
                      <span className="dropdown-arrow">▼</span>
                    </div>
                  ) : (
                    <>
                      <input
                        type="text"
                        id="ticker"
                        ref={searchInputRef}
                        autoFocus
                        value={searchTerm}
                        onChange={handleSearchChange}
                        onFocus={handleInputFocus}
                        placeholder="Search stocks..."
                        required
                        disabled={loading}
                        autoComplete="off"
                        className="stock-search-input"
                      />
                      <span className="dropdown-arrow">▼</span>
                    </>
                  )}
                  {showDropdown && filteredStocks.length > 0 && (
                    <div className="stock-dropdown">
                      {filteredStocks.slice(0, 10).map((stock) => (
                        <div
                          key={stock.ticker}
                          className="stock-dropdown-item"
                          onClick={() => handleStockSelect(stock.ticker)}
                        >
                          <img
                            src={`/logos/${stock.ticker.toUpperCase()}.png`}
                            alt=""
                            className="stock-logo-mini"
                            onError={(e) => (e.currentTarget.style.display = 'none')}
                          />
                          <span className="stock-ticker">{stock.ticker}</span>
                          <span className="stock-name">{stock.company_name}</span>
                        </div>
                      ))}
                      {filteredStocks.length > 10 && (
                        <div className="stock-dropdown-item disabled">
                          <span className="stock-name">+ {filteredStocks.length - 10} more...</span>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>

              <div className="form-group">
                <label>Option Type</label>
                <div className="option-type-radios">
                  <label className="radio-option">
                    <input
                      type="radio"
                      name="optionType"
                      value={OptionType.CALL}
                      checked={optionType === OptionType.CALL}
                      onChange={() => setOptionType(OptionType.CALL)}
                      disabled={loading}
                    />
                    <span>Call</span>
                  </label>
                  <label className="radio-option">
                    <input
                      type="radio"
                      name="optionType"
                      value={OptionType.PUT}
                      checked={optionType === OptionType.PUT}
                      onChange={() => setOptionType(OptionType.PUT)}
                      disabled={loading}
                    />
                    <span>Put</span>
                  </label>
                </div>
              </div>
            </div>

            <div className="form-section">
              <h3>Stock Price Matching</h3>

              <div className="form-group">
                <label>Current Stock Price ($)</label>
                <div className="current-price-display">
                  {currentStockPrice !== null ? (
                    <span>${currentStockPrice.toFixed(2)}</span>
                  ) : (
                    <span className="price-loading">Fetching price...</span>
                  )}
                </div>
              </div>

              <div className="form-group">
                <label htmlFor="stockPriceRangePercent">Stock Price Range (%)</label>
                <input
                  type="number"
                  id="stockPriceRangePercent"
                  value={stockPriceRangePercent}
                  onChange={(e) => setStockPriceRangePercent(e.target.value)}
                  step="0.1"
                  min="0"
                  max="100"
                  required
                  disabled={loading}
                />
                <small className="form-help">
                  Only use data from when stock was ±{stockPriceRangePercent}% of ${currentStockPrice?.toFixed(2) || '...'}
                  {currentStockPrice && (
                    <>: ${(currentStockPrice * (1 - parseFloat(stockPriceRangePercent) / 100)).toFixed(2)} - ${(currentStockPrice * (1 + parseFloat(stockPriceRangePercent) / 100)).toFixed(2)}</>
                  )}
                </small>
              </div>
            </div>
          </div>

        {/* RIGHT CARD: Strike Price Matching + Expiration & Time Window */}
        <div className="query-settings-card">
          <div className="form-section">
              <h3>Strike Price Matching</h3>

              <div className="form-group">
                <label htmlFor="strikeMode">Strike Mode</label>
                <div className="select-wrapper">
                  <select
                    id="strikeMode"
                    value={strikeMode}
                    onChange={(e) => setStrikeMode(e.target.value as StrikeMode)}
                    disabled={loading}
                    className="styled-select"
                  >
                    <option value={StrikeMode.EXACT}>Exact Strike</option>
                    <option value={StrikeMode.PERCENTAGE_RANGE}>Percentage Range</option>
                    <option value={StrikeMode.NEAREST}>Nearest Strikes</option>
                  </select>
                  <span className="dropdown-arrow">▼</span>
                </div>
              </div>

              <div className="form-group">
                <label htmlFor="strikePrice">Strike Price ($)</label>
                <input
                  type="number"
                  id="strikePrice"
                  value={strikePrice}
                  onChange={(e) => setStrikePrice(e.target.value)}
                  step="0.01"
                  min="0"
                  required
                  disabled={loading}
                />
                <small className="form-help">
                  {strikeMode === StrikeMode.EXACT && 'Exact target strike price'}
                  {strikeMode === StrikeMode.PERCENTAGE_RANGE && 'Center price for range calculation'}
                  {strikeMode === StrikeMode.NEAREST && 'Reference price (usually current stock price)'}
                </small>
              </div>

              {strikeMode === StrikeMode.PERCENTAGE_RANGE && (
                <div className="form-group">
                  <label htmlFor="strikeRangePercent">Range (%)</label>
                  <input
                    type="number"
                    id="strikeRangePercent"
                    value={strikeRangePercent}
                    onChange={(e) => setStrikeRangePercent(e.target.value)}
                    step="0.1"
                    min="0"
                    max="100"
                    required
                    disabled={loading}
                  />
                  <small className="form-help">
                    ±{strikeRangePercent}% around ${strikePrice} = ${(parseFloat(strikePrice) * (1 - parseFloat(strikeRangePercent) / 100)).toFixed(2)} - ${(parseFloat(strikePrice) * (1 + parseFloat(strikeRangePercent) / 100)).toFixed(2)}
                  </small>
                </div>
              )}

              {strikeMode === StrikeMode.NEAREST && (
                <>
                  <div className="form-group">
                    <label htmlFor="nearestCountAbove">Strikes Above</label>
                    <input
                      type="number"
                      id="nearestCountAbove"
                      value={nearestCountAbove}
                      onChange={(e) => setNearestCountAbove(e.target.value)}
                      min="0"
                      max="50"
                      required
                      disabled={loading}
                    />
                  </div>

                  <div className="form-group">
                    <label htmlFor="nearestCountBelow">Strikes Below</label>
                    <input
                      type="number"
                      id="nearestCountBelow"
                      value={nearestCountBelow}
                      onChange={(e) => setNearestCountBelow(e.target.value)}
                      min="0"
                      max="50"
                      required
                      disabled={loading}
                    />
                  </div>
                </>
              )}
            </div>

            <div className="form-section">
              <h3>Expiration & Time Window</h3>

              <div className="form-group">
                <label htmlFor="expirationDate">Expiration Date</label>
                <div className="select-wrapper">
                  <select
                    id="expirationDate"
                    value={expirationDate}
                    onChange={handleDateChange}
                    required
                    disabled={loading}
                    className="styled-select"
                  >
                    {upcomingFridays.map((friday) => (
                      <option key={friday.date} value={friday.date}>
                        {friday.label}
                      </option>
                    ))}
                  </select>
                  <span className="dropdown-arrow">▼</span>
                </div>
              </div>

              {/* Advanced Settings Section */}
              <div className="advanced-settings-section">
                <button
                  type="button"
                  className="advanced-settings-toggle"
                  onClick={() => setShowAdvancedSettings(!showAdvancedSettings)}
                >
                  {showAdvancedSettings ? '▼' : '▶'} Advanced Settings
                </button>

                {showAdvancedSettings && (
                  <div className="advanced-settings-content">
                    <div className="form-group">
                      <label htmlFor="durationToleranceDays">Duration Tolerance (days)</label>
                      <input
                        type="number"
                        id="durationToleranceDays"
                        value={durationToleranceDays}
                        onChange={(e) => setDurationToleranceDays(e.target.value)}
                        min="0"
                        required
                        disabled={loading}
                      />
                      <small className="form-help">
                        Match durations within ±{durationToleranceDays} days ({parseInt(durationDays) - parseInt(durationToleranceDays)}-{parseInt(durationDays) + parseInt(durationToleranceDays)} days)
                      </small>
                    </div>

                    <div className="form-group">
                      <label htmlFor="lookbackDays">Lookback Period (days)</label>
                      <input
                        type="text"
                        id="lookbackDays"
                        value={lookbackDays}
                        onChange={(e) => setLookbackDays(e.target.value)}
                        placeholder="Leave empty for entire database"
                        disabled={loading}
                      />
                      <small className="form-help">How far back in history to search (empty = all data)</small>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>

      <button type="submit" className="submit-button" disabled={loading}>
        {loading ? 'Querying...' : 'Query Premium Data'}
      </button>
    </form >
  );
};

export default QueryForm;
