import React, { useState, useEffect } from 'react';
import Plot from 'react-plotly.js';
import apiClient from '../services/api';
import './PremiumScatter3D.css';

interface PremiumScatter3DProps {
  ticker: string;
  optionType: string;
  initialDuration: number;
  lookbackDays?: number;
  toleranceDays?: number;
  queryStrikePrices?: number[];
  queryStockPrice?: number;
  queryStockPriceRange?: number;
}

const PremiumScatter3D: React.FC<PremiumScatter3DProps> = ({
  ticker,
  optionType,
  initialDuration,
  lookbackDays = 30,
  toleranceDays = 3,
  queryStrikePrices,
  queryStockPrice,
  queryStockPriceRange,
}) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [durationDays, setDurationDays] = useState(initialDuration);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showRelative, setShowRelative] = useState(true);
  const [currentStockPrice, setCurrentStockPrice] = useState<number | null>(null);
  const [scatterData, setScatterData] = useState<{
    strike_prices: number[];
    stock_prices: number[];
    premiums: number[];
    data_point_counts: number[];
  } | null>(null);

  const fetchCurrentStockPrice = async () => {
    try {
      const data = await apiClient.getStockPrice(ticker);
      if (data.latest_price !== null) {
        setCurrentStockPrice(data.latest_price);
        return data.latest_price;
      }
    } catch (err) {
      console.error('Failed to fetch current stock price:', err);
    }
    return null;
  };

  const fetchScatterData = async (duration: number) => {
    setLoading(true);
    setError(null);

    try {
      const data = await apiClient.queryPremiumSurface({
        ticker,
        option_type: optionType,
        duration_days: duration,
        duration_tolerance_days: toleranceDays,
        lookback_days: lookbackDays,
      });

      // Convert grid data to scatter points
      const strikePoints: number[] = [];
      const stockPoints: number[] = [];
      const premiumPoints: number[] = [];
      const countPoints: number[] = [];

      data.stock_prices.forEach((stockPrice, i) => {
        data.strike_prices.forEach((strikePrice, j) => {
          const premium = data.premium_grid[i][j];
          const count = data.data_point_counts[i][j];
          
          if (premium !== null) {
            // Filter by query strike prices if provided
            if (!queryStrikePrices || queryStrikePrices.length === 0 || 
                queryStrikePrices.some(qsp => Math.abs(qsp - strikePrice) < 0.01)) {
              strikePoints.push(strikePrice);
              stockPoints.push(stockPrice);
              premiumPoints.push(premium);
              countPoints.push(count);
            }
          }
        });
      });

      setScatterData({
        strike_prices: strikePoints,
        stock_prices: stockPoints,
        premiums: premiumPoints,
        data_point_counts: countPoints,
      });

      if (!currentStockPrice) {
        await fetchCurrentStockPrice();
      }
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('Failed to fetch premium scatter data');
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCurrentStockPrice();
  }, [ticker]);

  useEffect(() => {
    if (durationDays) {
      fetchScatterData(durationDays);
    }
  }, [durationDays, ticker, optionType, lookbackDays, toleranceDays]);

  const handleDurationChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = parseInt(e.target.value);
    if (!isNaN(value) && value > 0) {
      setDurationDays(value);
    }
  };

  if (loading && !scatterData) {
    return (
      <div className="scatter-3d-container">
        <div className="scatter-loading">
          <div className="spinner"></div>
          <p>Loading 3D scatter plot...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="scatter-3d-container">
        <div className="scatter-error">
          <p>Error: {error}</p>
        </div>
      </div>
    );
  }

  if (!scatterData || scatterData.premiums.length === 0) {
    return (
      <div className="scatter-3d-container">
        <div className="scatter-empty">
          <p>No data available for scatter plot</p>
        </div>
      </div>
    );
  }

  // Calculate display values (relative or absolute)
  const displayPremiums = showRelative
    ? scatterData.premiums.map((premium, i) => (premium / scatterData.strike_prices[i]) * 100)
    : scatterData.premiums;

  const stats = {
    min: Math.min(...displayPremiums),
    max: Math.max(...displayPremiums),
    avg: displayPremiums.reduce((a, b) => a + b, 0) / displayPremiums.length,
  };

  // Calculate axis ranges based on data and query parameters
  const getAxisRanges = () => {
    const stockPrice = queryStockPrice || currentStockPrice;
    
    if (!stockPrice) {
      // Fallback to data bounds
      return {
        xRange: [Math.min(...scatterData.strike_prices), Math.max(...scatterData.strike_prices)],
        yRange: [Math.min(...scatterData.stock_prices), Math.max(...scatterData.stock_prices)],
        zRange: [stats.min, stats.max],
      };
    }

    // Y-axis range: use query values if provided, otherwise default to ±5%
    const rangePercent = queryStockPriceRange || 5;
    const rangeMultiplier = rangePercent / 100;

    const baseYMin = stockPrice * (1 - rangeMultiplier);
    const baseYMax = stockPrice * (1 + rangeMultiplier);

    // Find actual min/max stock prices that have data
    const uniqueStockPrices = Array.from(new Set(scatterData.stock_prices)).sort((a, b) => a - b);
    const stockPricesWithData = uniqueStockPrices.filter(sp => 
      scatterData.stock_prices.includes(sp)
    );

    let yMin, yMax;
    if (stockPricesWithData.length > 0) {
      yMin = Math.min(...stockPricesWithData);
      yMax = Math.max(...stockPricesWithData);
    } else {
      yMin = baseYMin;
      yMax = baseYMax;
    }

    // X-axis range (Strike Price): Based on option type and stock price
    let defaultXMin, defaultXMax;
    if (optionType.toLowerCase() === 'call') {
      defaultXMin = stockPrice * 0.99;
      defaultXMax = stockPrice * 1.10;
    } else {
      // PUT
      defaultXMin = stockPrice * 0.90;
      defaultXMax = stockPrice * 1.01;
    }

    const dbXMin = Math.min(...scatterData.strike_prices);
    const dbXMax = Math.max(...scatterData.strike_prices);

    const xMin = Math.max(defaultXMin, dbXMin);
    const xMax = Math.min(defaultXMax, dbXMax);

    // Z-axis range: Filter values within visible x and y ranges
    const visiblePremiums = displayPremiums.filter((_, i) => {
      const strikePrice = scatterData.strike_prices[i];
      const stockPriceVal = scatterData.stock_prices[i];
      return strikePrice >= xMin && strikePrice <= xMax &&
             stockPriceVal >= yMin && stockPriceVal <= yMax;
    });

    let zMin, zMax;
    if (visiblePremiums.length > 0) {
      zMin = Math.min(...visiblePremiums);
      zMax = Math.max(...visiblePremiums);
    } else {
      zMin = stats.min;
      zMax = stats.max;
    }

    return { xRange: [xMin, xMax], yRange: [yMin, yMax], zRange: [zMin, zMax] };
  };

  const axisRanges = getAxisRanges();

  return (
    <div className="scatter-3d-container">
      <div className="scatter-3d-header">
        <h3>3D Premium Scatter Plot</h3>
        <div className="scatter-3d-meta">
          <span><strong>Ticker:</strong> {ticker}</span>
          <span><strong>Type:</strong> {optionType.toUpperCase()}</span>
          <span><strong>Duration:</strong> {durationDays} days</span>
          <span><strong>Points:</strong> {scatterData.premiums.length}</span>
        </div>
      </div>

      <div className="scatter-3d-controls">
        <div className="control-group toggle-group">
          <label className="toggle-label">
            <input
              type="checkbox"
              className="toggle-checkbox"
              checked={showRelative}
              onChange={(e) => setShowRelative(e.target.checked)}
            />
            <span className="toggle-text">
              {showRelative ? '� Relative Premium (% of Strike)' : '💵 Absolute Premium ($)'}
            </span>
          </label>
        </div>

        <div className="control-group">
          <label htmlFor="duration-slider">
            <strong>Duration (Days to Expiration):</strong> {durationDays} days
            {loading && <span className="loading-indicator"> ⟳ Loading...</span>}
          </label>
          <input
            id="duration-slider"
            type="range"
            min="1"
            max="90"
            value={durationDays}
            onChange={handleDurationChange}
            className="duration-slider"
          />
          <div className="duration-marks">
            <span>1d</span>
            <span>30d</span>
            <span>60d</span>
            <span>90d</span>
          </div>
        </div>
      </div>

      <div className="scatter-3d-stats">
        <div className="stat-item">
          <span className="stat-label">Data Points:</span>
          <span className="stat-value">{scatterData.premiums.length}</span>
        </div>
        <div className="stat-item">
          <span className="stat-label">{showRelative ? 'Premium % Range:' : 'Premium Range:'}</span>
          <span className="stat-value primary">
            {showRelative
              ? `${stats.min.toFixed(2)}% - ${stats.max.toFixed(2)}%`
              : `$${stats.min.toFixed(2)} - $${stats.max.toFixed(2)}`
            }
          </span>
        </div>
        <div className="stat-item">
          <span className="stat-label">{showRelative ? 'Avg Premium %:' : 'Avg Premium:'}</span>
          <span className="stat-value primary">
            {showRelative
              ? `${stats.avg.toFixed(2)}%`
              : `$${stats.avg.toFixed(2)}`
            }
          </span>
        </div>
      </div>

      <div className="scatter-plot-wrapper">
        <Plot
          data={[
            {
              type: 'scatter3d',
              mode: 'markers',
              x: scatterData.strike_prices,
              y: scatterData.stock_prices,
              z: displayPremiums,
              marker: {
                size: 4,
                color: displayPremiums,
                cauto: false,
                cmin: axisRanges.zRange[0],
                cmax: axisRanges.zRange[1],
                colorscale: [
                  [0, '#1e3a8a'],      // Deep blue (low)
                  [0.25, '#3b82f6'],   // Blue
                  [0.5, '#fbbf24'],    // Yellow (mid)
                  [0.75, '#f97316'],   // Orange
                  [1, '#dc2626']       // Red (high)
                ],
                showscale: true,
                colorbar: {
                  title: showRelative ? 'Premium (%)' : 'Premium ($)',
                  thickness: 20,
                  len: 0.7,
                  tickvals: [0, 1 / 6, 2 / 6, 3 / 6, 4 / 6, 5 / 6, 1].map(v =>
                    axisRanges.zRange[0] + v * (axisRanges.zRange[1] - axisRanges.zRange[0])
                  ),
                  ticktext: [0, 1 / 6, 2 / 6, 3 / 6, 4 / 6, 5 / 6, 1].map(v => {
                    const val = axisRanges.zRange[0] + v * (axisRanges.zRange[1] - axisRanges.zRange[0]);
                    return showRelative ? `${val.toFixed(2)}%` : `$${val.toFixed(2)}`;
                  }),
                },
                line: {
                  color: 'rgba(50, 50, 50, 0.3)',
                  width: 0.5,
                },
              },
              text: scatterData.data_point_counts.map((count, i) => 
                `Strike: $${scatterData.strike_prices[i].toFixed(2)}<br>` +
                `Stock: $${scatterData.stock_prices[i].toFixed(2)}<br>` +
                `Premium: ${showRelative 
                  ? `${displayPremiums[i].toFixed(2)}%` 
                  : `$${displayPremiums[i].toFixed(2)}`}<br>` +
                `Data Points: ${count}`
              ),
              hovertemplate: '%{text}<extra></extra>',
            },
          ]}
          layout={{
            scene: {
              xaxis: {
                title: 'Strike Price ($)',
                gridcolor: '#e5e7eb',
                showgrid: true,
                range: axisRanges.xRange,
              },
              yaxis: {
                title: 'Stock Price ($)',
                gridcolor: '#e5e7eb',
                showgrid: true,
                range: axisRanges.yRange,
              },
              zaxis: {
                title: showRelative ? 'Premium (% of Strike)' : 'Premium ($)',
                gridcolor: '#e5e7eb',
                showgrid: true,
                range: axisRanges.zRange,
              },
              camera: {
                eye: { x: -1.5, y: -1.5, z: 1.3 },
              },
              aspectmode: 'auto',
            },
            autosize: true,
            height: 900,
            margin: { t: 50, r: 0, b: 0, l: 0 },
          }}
          config={{
            displayModeBar: true,
            displaylogo: false,
            responsive: true,
            modeBarButtonsToRemove: ['toImage'],
          }}
          style={{ width: '100%', height: '900px' }}
        />
      </div>

      <div className={`expandable-section ${isExpanded ? 'expanded' : ''}`}>
        <div className="expandable-header" onClick={() => setIsExpanded(!isExpanded)}>
          <h4>📊 How to Read This 3D Scatter Plot</h4>
          <span className="toggle-icon">▼</span>
        </div>
        <div className="expandable-content">
          <ul>
            <li>
              <strong>X-axis (Strike Price):</strong> Different strike prices for the option.
              Each dot represents a specific strike price from the historical data.
            </li>
            <li>
              <strong>Y-axis (Stock Price):</strong> The underlying stock price at collection time.
              Shows the various stock price levels when the premium data was collected.
            </li>
            <li>
              <strong>Z-axis (Premium):</strong> The option premium value - either absolute dollar value 
              or relative percentage of strike price.
            </li>
            <li>
              <strong>Dot Color:</strong> Color indicates premium value intensity using the Viridis colorscale.
              Darker colors indicate lower premiums, brighter colors indicate higher premiums.
            </li>
            <li>
              <strong>Hover Info:</strong> Hover over any dot to see exact strike price, stock price, 
              premium value, and number of data points averaged for that position.
            </li>
            <li>
              <strong>Interactive Controls:</strong> Click and drag to rotate, scroll to zoom, 
              and use the toolbar to reset view or take screenshots.
            </li>
            <li>
              <strong>Relative vs Absolute:</strong> Toggle between percentage (relative to strike) 
              and dollar amounts to see different perspectives of premium behavior.
            </li>
          </ul>
        </div>
      </div>
    </div>
  );
};

export default PremiumScatter3D;
