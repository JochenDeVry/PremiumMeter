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
  const [optionType, setOptionType] = useState<OptionType>(OptionType.PUT);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const [isSearching, setIsSearching] = useState<boolean>(false);  // Track if user is actively searching
  const [strikeMode, setStrikeMode] = useState<StrikeMode>(StrikeMode.NEAREST);
  const [strikePrice, setStrikePrice] = useState<string>('270');
  const [strikeRangePercent, setStrikeRangePercent] = useState<string>('5');
  const [nearestCountAbove, setNearestCountAbove] = useState<string>('5');
  const [nearestCountBelow, setNearestCountBelow] = useState<string>('5');
  const [durationDays, setDurationDays] = useState<string>('7');
  const [durationToleranceDays, setDurationToleranceDays] = useState<string>('0');
  const [lookbackDays, setLookbackDays] = useState<string>('');  // Empty string means entire database
  const [showAdvancedSettings, setShowAdvancedSettings] = useState<boolean>(false);

  // Load stocks on component mount
  useEffect(() => {
    const loadStocks = async () => {
      try {
        const stockList = await apiClient.listAllStocks();
        setStocks(stockList);
        setFilteredStocks(stockList);
        
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

  const handleStockSelect = (selectedTicker: string) => {
    setTicker(selectedTicker);
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
      <div className="form-section">
        <h3>Stock & Option Type</h3>
        
        <div className="form-group">
          <label htmlFor="ticker">Ticker Symbol</label>
          <div className="stock-search-container" ref={dropdownRef}>
            <input
              type="text"
              id="ticker"
              value={isSearching ? searchTerm : ticker}
              onChange={handleSearchChange}
              onFocus={handleInputFocus}
              placeholder="Search stocks..."
              required
              disabled={loading}
              autoComplete="off"
              className="stock-search-input"
            />
            <span className="dropdown-arrow">▼</span>
            {showDropdown && filteredStocks.length > 0 && (
              <div className="stock-dropdown">
                {filteredStocks.slice(0, 10).map((stock) => (
                  <div
                    key={stock.ticker}
                    className="stock-dropdown-item"
                    onClick={() => handleStockSelect(stock.ticker)}
                  >
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
          <small className="form-help">Selected: {ticker}</small>
        </div>

        <div className="form-group">
          <label htmlFor="optionType">Option Type</label>
          <div className="select-wrapper">
            <select
              id="optionType"
              value={optionType}
              onChange={(e) => setOptionType(e.target.value as OptionType)}
              disabled={loading}
              className="styled-select"
            >
              <option value={OptionType.CALL}>Call</option>
              <option value={OptionType.PUT}>Put</option>
            </select>
            <span className="dropdown-arrow">▼</span>
          </div>
        </div>
      </div>

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
                max="10"
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
                max="10"
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
          <label htmlFor="durationDays">Expiration (days)</label>
          <input
            type="number"
            id="durationDays"
            value={durationDays}
            onChange={(e) => setDurationDays(e.target.value)}
            min="1"
            required
            disabled={loading}
          />
          <small className="form-help">Days to expiration (e.g., 30 for ~1 month)</small>
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

      <button type="submit" className="submit-button" disabled={loading}>
        {loading ? 'Querying...' : 'Query Premium Data'}
      </button>
    </form>
  );
};

export default QueryForm;
