import React, { useState, useEffect } from 'react';
import Plot from 'react-plotly.js';
import apiClient from '../services/api';
import './PremiumSurface3D.css';

interface PremiumSurface3DProps {
  ticker: string;
  optionType: string;
  initialDuration: number;
  lookbackDays?: number;
  toleranceDays?: number;
  queryStrikePrices?: number[];  // Strike prices from the premium query results
}

const PremiumSurface3D: React.FC<PremiumSurface3DProps> = ({
  ticker,
  optionType,
  initialDuration,
  lookbackDays = 30,
  toleranceDays = 3,
  queryStrikePrices,
}) => {
  const [durationDays, setDurationDays] = useState(initialDuration);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showRelative, setShowRelative] = useState(false); // Toggle for relative vs absolute
  const [currentStockPrice, setCurrentStockPrice] = useState<number | null>(null);
  const [xAxisRange, setXAxisRange] = useState<[number, number] | null>(null);
  const [yAxisRange, setYAxisRange] = useState<[number, number] | null>(null);
  const [zAxisRange, setZAxisRange] = useState<[number, number] | null>(null);
  const [surfaceData, setSurfaceData] = useState<{
    strike_prices: number[];
    stock_prices: number[];
    premium_grid: (number | null)[][];
    data_point_counts: number[][];
    total_points: number;
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

  const fetchSurfaceData = async (duration: number) => {
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

      setSurfaceData({
        strike_prices: data.strike_prices,
        stock_prices: data.stock_prices,
        premium_grid: data.premium_grid,
        data_point_counts: data.data_point_counts,
        total_points: data.total_points,
      });

      // Filter surface data to match query strike prices if provided
      let filteredStrikePrices = data.strike_prices;
      let filteredPremiumGrid = data.premium_grid;
      let filteredDataPointCounts = data.data_point_counts;

      if (queryStrikePrices && queryStrikePrices.length > 0) {
        // Find indices of strikes that match the query
        const strikeIndices: number[] = [];
        filteredStrikePrices = [];

        queryStrikePrices.forEach(queryStrike => {
          const idx = data.strike_prices.findIndex(sp => Math.abs(sp - queryStrike) < 0.01);
          if (idx !== -1) {
            strikeIndices.push(idx);
            filteredStrikePrices.push(data.strike_prices[idx]);
          }
        });

        // Filter the grid columns to only include matching strikes
        filteredPremiumGrid = data.premium_grid.map(row =>
          strikeIndices.map(idx => row[idx])
        );
        filteredDataPointCounts = data.data_point_counts.map(row =>
          strikeIndices.map(idx => row[idx])
        );

        setSurfaceData({
          strike_prices: filteredStrikePrices,
          stock_prices: data.stock_prices,
          premium_grid: filteredPremiumGrid,
          data_point_counts: filteredDataPointCounts,
          total_points: data.total_points,
        });
      }

      // Calculate default axis ranges if current stock price is available
      const stockPrice = currentStockPrice || await fetchCurrentStockPrice();
      if (stockPrice && data.strike_prices.length > 0 && data.stock_prices.length > 0) {
        // Y-axis: current stock price ±5%, but expand to database range if it's wider
        const defaultYMin = stockPrice * 0.95;
        const defaultYMax = stockPrice * 1.05;
        const dbYMin = Math.min(...data.stock_prices);
        const dbYMax = Math.max(...data.stock_prices);

        // Use whichever range is wider to avoid compressing data into a narrow band
        const yMin = Math.min(defaultYMin, dbYMin);
        const yMax = Math.max(defaultYMax, dbYMax);
        setYAxisRange([yMin, yMax]);

        // X-axis: use strike prices from the query results if available, otherwise use surface data range
        if (queryStrikePrices && queryStrikePrices.length > 0) {
          const xMin = Math.min(...queryStrikePrices);
          const xMax = Math.max(...queryStrikePrices);
          setXAxisRange([xMin, xMax]);
        } else {
          const xMin = Math.min(...data.strike_prices);
          const xMax = Math.max(...data.strike_prices);
          setXAxisRange([xMin, xMax]);
        }
      }
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to load surface data';
      setError(errorMsg);
      console.error('Surface plot error:', err);
    } finally {
      setLoading(false);
    }
  };

  // Load initial data
  useEffect(() => {
    fetchCurrentStockPrice().then(() => {
      fetchSurfaceData(durationDays);
    });
  }, []);

  // Reset z-axis range when switching between absolute/relative mode
  useEffect(() => {
    if (surfaceData) {
      // Recalculate display values and reset z-axis
      setZAxisRange(null);  // Will be recalculated in render
    }
  }, [showRelative]);

  const handleDurationChange = (newDuration: number) => {
    setDurationDays(newDuration);
    fetchSurfaceData(newDuration);
  };

  if (loading && !surfaceData) {
    return (
      <div className="surface-3d-container">
        <div className="surface-3d-loading">
          <div className="spinner"></div>
          <p>Loading 3D surface data...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="surface-3d-container">
        <div className="surface-3d-error">
          <p>Error loading 3D surface: {error}</p>
        </div>
      </div>
    );
  }

  if (!surfaceData || surfaceData.strike_prices.length === 0) {
    return (
      <div className="surface-3d-container">
        <div className="surface-3d-error">
          <p>No data available for the selected parameters.</p>
        </div>
      </div>
    );
  }

  // Calculate statistics
  const allPremiums = surfaceData.premium_grid
    .flat()
    .filter((p): p is number => p !== null);

  const stats = {
    minPremium: Math.min(...allPremiums),
    maxPremium: Math.max(...allPremiums),
    avgPremium: allPremiums.reduce((a, b) => a + b, 0) / allPremiums.length,
    dataPoints: surfaceData.total_points,
    gridCells: surfaceData.strike_prices.length * surfaceData.stock_prices.length,
    filledCells: allPremiums.length,
  };

  // Calculate display values (absolute or relative)
  const displayGrid = showRelative
    ? surfaceData.premium_grid.map((row) =>
      row.map((premium, xIdx) => {
        if (premium === null) return null;
        const strike = surfaceData.strike_prices[xIdx];
        return (premium / strike) * 100; // Percentage of strike price
      })
    )
    : surfaceData.premium_grid;

  // Calculate stats for display values
  const allDisplayValues = displayGrid
    .flat()
    .filter((p): p is number => p !== null);

  const displayStats = {
    min: Math.min(...allDisplayValues),
    max: Math.max(...allDisplayValues),
    avg: allDisplayValues.reduce((a, b) => a + b, 0) / allDisplayValues.length,
  };

  // Initialize z-axis range if not set
  if (zAxisRange === null && allDisplayValues.length > 0) {
    setZAxisRange([displayStats.min, displayStats.max]);
  }

  // Calculate visible data range based on current axis settings for dynamic color coding
  const getVisibleDataStats = () => {
    if (!xAxisRange || !yAxisRange || !zAxisRange) {
      return { min: displayStats.min, max: displayStats.max };
    }

    const visibleValues: number[] = [];
    displayGrid.forEach((row, yIdx) => {
      const stockPrice = surfaceData.stock_prices[yIdx];
      // Check if this stock price is within y-axis range
      if (stockPrice >= yAxisRange[0] && stockPrice <= yAxisRange[1]) {
        row.forEach((value, xIdx) => {
          const strikePrice = surfaceData.strike_prices[xIdx];
          // Check if this strike price is within x-axis range and value is within z-axis range
          if (value !== null &&
            strikePrice >= xAxisRange[0] && strikePrice <= xAxisRange[1] &&
            value >= zAxisRange[0] && value <= zAxisRange[1]) {
            visibleValues.push(value);
          }
        });
      }
    });

    if (visibleValues.length === 0) {
      return { min: displayStats.min, max: displayStats.max };
    }

    return {
      min: Math.min(...visibleValues),
      max: Math.max(...visibleValues),
    };
  };

  const visibleStats = getVisibleDataStats();

  // Create color array based on premium values for dynamic color coding
  // Use visible data range for color normalization
  const surfaceColors = displayGrid.map((row) => {
    return row.map(value => {
      if (value === null) return null;
      // Normalize value to 0-1 range using VISIBLE data range for dynamic color coding
      const normalizedValue = (value - visibleStats.min) / (visibleStats.max - visibleStats.min);
      return normalizedValue;
    });
  });

  return (
    <div className="surface-3d-container">
      <div className="surface-3d-header">
        <h3>
          3D Premium Surface
        </h3>
        <div className="surface-3d-info">
          <span className="ticker-badge">{ticker}</span>
          <span>{optionType.toUpperCase()}</span>
        </div>
      </div>

      <div className="surface-3d-controls">
        <div className="control-group toggle-group">
          <label className="toggle-label">
            <input
              type="checkbox"
              checked={showRelative}
              onChange={(e) => setShowRelative(e.target.checked)}
              className="toggle-checkbox"
            />
            <span className="toggle-text">
              {showRelative ? '📊 Relative Premium (% of Strike)' : '💵 Absolute Premium ($)'}
            </span>
          </label>
        </div>

        <div className="control-group">
          <label htmlFor="duration-slider">
            <strong>Duration (Days to Expiration):</strong> {durationDays} days
            {loading && <span className="loading-indicator"> ⟳ Loading...</span>}
          </label>
          <div className="slider-container">
            <input
              id="duration-slider"
              type="range"
              min="1"
              max="180"
              value={durationDays}
              onChange={(e) => handleDurationChange(parseInt(e.target.value))}
              disabled={loading}
              className="duration-slider"
            />
            <div className="slider-labels">
              <span>1 day</span>
              <span>30 days</span>
              <span>90 days</span>
              <span>180 days</span>
            </div>
          </div>
        </div>

        <div className="quick-durations">
          <span>Quick select:</span>
          {[7, 14, 30, 60, 90].map((days) => (
            <button
              key={days}
              onClick={() => handleDurationChange(days)}
              disabled={loading}
              className={durationDays === days ? 'active' : ''}
            >
              {days}d
            </button>
          ))}
        </div>

        {/* Axis Range Controls */}
        {xAxisRange && yAxisRange && (
          <div className="axis-controls">
            <div className="control-group">
              <label htmlFor="x-axis-min-slider">
                <strong>Strike Price Range (X-axis):</strong> ${xAxisRange[0].toFixed(2)} - ${xAxisRange[1].toFixed(2)}
              </label>
              <div className="axis-slider-container">
                <div className="axis-slider-row">
                  <span className="slider-label-small">Min:</span>
                  <input
                    id="x-axis-min-slider"
                    type="range"
                    min={surfaceData ? Math.min(...surfaceData.strike_prices) : 0}
                    max={surfaceData ? Math.max(...surfaceData.strike_prices) : 1000}
                    step="0.5"
                    value={xAxisRange[0]}
                    onChange={(e) => {
                      const newMin = parseFloat(e.target.value);
                      if (newMin < xAxisRange[1]) {
                        setXAxisRange([newMin, xAxisRange[1]]);
                      }
                    }}
                    className="axis-slider"
                  />
                  <span className="slider-value">${xAxisRange[0].toFixed(2)}</span>
                </div>
                <div className="axis-slider-row">
                  <span className="slider-label-small">Max:</span>
                  <input
                    id="x-axis-max-slider"
                    type="range"
                    min={surfaceData ? Math.min(...surfaceData.strike_prices) : 0}
                    max={surfaceData ? Math.max(...surfaceData.strike_prices) : 1000}
                    step="0.5"
                    value={xAxisRange[1]}
                    onChange={(e) => {
                      const newMax = parseFloat(e.target.value);
                      if (newMax > xAxisRange[0]) {
                        setXAxisRange([xAxisRange[0], newMax]);
                      }
                    }}
                    className="axis-slider"
                  />
                  <span className="slider-value">${xAxisRange[1].toFixed(2)}</span>
                </div>
              </div>
            </div>

            <div className="control-group">
              <label htmlFor="y-axis-min-slider">
                <strong>Stock Price Range (Y-axis):</strong> ${yAxisRange[0].toFixed(2)} - ${yAxisRange[1].toFixed(2)}
                {currentStockPrice && (
                  <span className="current-price-indicator"> (Current: ${currentStockPrice.toFixed(2)})</span>
                )}
              </label>
              <div className="axis-slider-container">
                <div className="axis-slider-row">
                  <span className="slider-label-small">Min:</span>
                  <input
                    id="y-axis-min-slider"
                    type="range"
                    min={surfaceData ? Math.min(...surfaceData.stock_prices) : 0}
                    max={surfaceData ? Math.max(...surfaceData.stock_prices) : 1000}
                    step="0.5"
                    value={yAxisRange[0]}
                    onChange={(e) => {
                      const newMin = parseFloat(e.target.value);
                      if (newMin < yAxisRange[1]) {
                        setYAxisRange([newMin, yAxisRange[1]]);
                      }
                    }}
                    className="axis-slider"
                  />
                  <span className="slider-value">${yAxisRange[0].toFixed(2)}</span>
                </div>
                <div className="axis-slider-row">
                  <span className="slider-label-small">Max:</span>
                  <input
                    id="y-axis-max-slider"
                    type="range"
                    min={surfaceData ? Math.min(...surfaceData.stock_prices) : 0}
                    max={surfaceData ? Math.max(...surfaceData.stock_prices) : 1000}
                    step="0.5"
                    value={yAxisRange[1]}
                    onChange={(e) => {
                      const newMax = parseFloat(e.target.value);
                      if (newMax > yAxisRange[0]) {
                        setYAxisRange([yAxisRange[0], newMax]);
                      }
                    }}
                    className="axis-slider"
                  />
                  <span className="slider-value">${yAxisRange[1].toFixed(2)}</span>
                </div>
              </div>
            </div>

            {zAxisRange && (
              <div className="control-group">
                <label htmlFor="z-axis-min-slider">
                  <strong>{showRelative ? 'Premium % Range (Z-axis):' : 'Premium Range (Z-axis):'}</strong>{' '}
                  {showRelative
                    ? `${zAxisRange[0].toFixed(2)}% - ${zAxisRange[1].toFixed(2)}%`
                    : `$${zAxisRange[0].toFixed(2)} - $${zAxisRange[1].toFixed(2)}`
                  }
                </label>
                <div className="axis-slider-container">
                  <div className="axis-slider-row">
                    <span className="slider-label-small">Min:</span>
                    <input
                      id="z-axis-min-slider"
                      type="range"
                      min={displayStats.min}
                      max={displayStats.max}
                      step={showRelative ? 0.01 : 0.1}
                      value={zAxisRange[0]}
                      onChange={(e) => {
                        const newMin = parseFloat(e.target.value);
                        if (newMin < zAxisRange[1]) {
                          setZAxisRange([newMin, zAxisRange[1]]);
                        }
                      }}
                      className="axis-slider"
                    />
                    <span className="slider-value">
                      {showRelative ? `${zAxisRange[0].toFixed(2)}%` : `$${zAxisRange[0].toFixed(2)}`}
                    </span>
                  </div>
                  <div className="axis-slider-row">
                    <span className="slider-label-small">Max:</span>
                    <input
                      id="z-axis-max-slider"
                      type="range"
                      min={displayStats.min}
                      max={displayStats.max}
                      step={showRelative ? 0.01 : 0.1}
                      value={zAxisRange[1]}
                      onChange={(e) => {
                        const newMax = parseFloat(e.target.value);
                        if (newMax > zAxisRange[0]) {
                          setZAxisRange([zAxisRange[0], newMax]);
                        }
                      }}
                      className="axis-slider"
                    />
                    <span className="slider-value">
                      {showRelative ? `${zAxisRange[1].toFixed(2)}%` : `$${zAxisRange[1].toFixed(2)}`}
                    </span>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      <div className="surface-3d-stats">
        <div className="stat-item">
          <span className="stat-label">Data Points:</span>
          <span className="stat-value">{stats.dataPoints}</span>
        </div>
        <div className="stat-item">
          <span className="stat-label">Grid Coverage:</span>
          <span className="stat-value">
            {stats.filledCells}/{stats.gridCells} cells ({((stats.filledCells / stats.gridCells) * 100).toFixed(1)}%)
          </span>
        </div>
        <div className="stat-item">
          <span className="stat-label">{showRelative ? 'Premium % Range:' : 'Premium Range:'}</span>
          <span className="stat-value primary">
            {showRelative
              ? `${displayStats.min.toFixed(2)}% - ${displayStats.max.toFixed(2)}%`
              : `$${displayStats.min.toFixed(2)} - $${displayStats.max.toFixed(2)}`
            }
          </span>
        </div>
        <div className="stat-item">
          <span className="stat-label">{showRelative ? 'Avg Premium %:' : 'Avg Premium:'}</span>
          <span className="stat-value primary">
            {showRelative
              ? `${displayStats.avg.toFixed(2)}%`
              : `$${displayStats.avg.toFixed(2)}`
            }
          </span>
        </div>
      </div>

      <div className="surface-3d-plot">
        <Plot
          key={`${xAxisRange?.[0]}-${xAxisRange?.[1]}-${yAxisRange?.[0]}-${yAxisRange?.[1]}-${zAxisRange?.[0]}-${zAxisRange?.[1]}-${showRelative}`}
          data={[
            {
              type: 'surface',
              x: surfaceData.strike_prices,
              y: surfaceData.stock_prices,
              z: displayGrid,
              surfacecolor: surfaceColors,
              colorscale: [
                [0, '#1e3a8a'],      // Deep blue (low)
                [0.25, '#3b82f6'],   // Blue
                [0.5, '#fbbf24'],    // Yellow (mid)
                [0.75, '#f97316'],   // Orange
                [1, '#dc2626']       // Red (high)
              ],
              colorbar: {
                title: showRelative ? 'Premium (%)' : 'Premium ($)',
                thickness: 20,
                len: 0.7,
                ticktext: showRelative
                  ? [
                    `${visibleStats.min.toFixed(2)}%`,
                    `${((visibleStats.min + visibleStats.max) / 2).toFixed(2)}%`,
                    `${visibleStats.max.toFixed(2)}%`
                  ]
                  : [
                    `$${visibleStats.min.toFixed(2)}`,
                    `$${((visibleStats.min + visibleStats.max) / 2).toFixed(2)}`,
                    `$${visibleStats.max.toFixed(2)}`
                  ],
                tickvals: [0, 0.5, 1],
              },
              contours: {
                z: {
                  show: true,
                  usecolormap: true,
                  highlightcolor: '#fff',
                  project: { z: true },
                },
              },
              hovertemplate: showRelative
                ? '<b>Strike:</b> $%{x:.2f}<br>' +
                '<b>Stock Price:</b> $%{y:.2f}<br>' +
                '<b>Premium:</b> %{z:.2f}%<br>' +
                '<extra></extra>'
                : '<b>Strike:</b> $%{x:.2f}<br>' +
                '<b>Stock Price:</b> $%{y:.2f}<br>' +
                '<b>Premium:</b> $%{z:.2f}<br>' +
                '<extra></extra>',
            },
          ]}
          layout={{
            title: `Premium Surface - ${durationDays} Days to Expiration (${showRelative ? 'Relative %' : 'Absolute $'})`,
            scene: {
              xaxis: {
                title: 'Strike Price ($)',
                range: xAxisRange ? [xAxisRange[0], xAxisRange[1]] : undefined,
                autorange: xAxisRange ? false : true,
                autorangeoptions: {
                  clipmin: xAxisRange ? xAxisRange[0] : undefined,
                  clipmax: xAxisRange ? xAxisRange[1] : undefined,
                },
              },
              yaxis: {
                title: 'Stock Price ($)',
                range: yAxisRange ? [yAxisRange[0], yAxisRange[1]] : undefined,
                autorange: yAxisRange ? false : true,
                autorangeoptions: {
                  clipmin: yAxisRange ? yAxisRange[0] : undefined,
                  clipmax: yAxisRange ? yAxisRange[1] : undefined,
                },
              },
              zaxis: {
                title: showRelative ? 'Premium (% of Strike)' : 'Premium ($)',
                range: zAxisRange ? [zAxisRange[0], zAxisRange[1]] : undefined,
                autorange: zAxisRange ? false : true,
              },
              camera: {
                eye: { x: -1.5, y: -1.5, z: 1.3 },
              },
              aspectmode: 'auto',  // Allow axes to scale independently
            },
            autosize: true,
            height: 700,
            margin: { t: 50, r: 0, b: 0, l: 0 },
          }}
          config={{
            displayModeBar: true,
            displaylogo: false,
            responsive: true,
            modeBarButtonsToAdd: [
              {
                name: 'Reset axes',
                icon: {
                  width: 500,
                  height: 600,
                  path: 'M255.545 8c-66.269.119-126.438 26.233-170.86 68.685L48.971 40.971C33.851 25.851 8 36.559 8 57.941V192c0 13.255 10.745 24 24 24h134.059c21.382 0 32.09-25.851 16.971-40.971l-41.75-41.75c30.864-28.899 70.801-44.907 113.23-45.273 92.398-.798 170.283 73.977 169.484 169.442C423.236 348.009 349.816 424 256 424c-41.127 0-79.997-14.678-110.63-41.556-4.743-4.161-11.906-3.908-16.368.553L89.34 422.659c-4.872 4.872-4.631 12.815.482 17.433C133.798 479.813 192.074 504 256 504c136.966 0 247.999-111.033 248-247.998C504.001 119.193 392.354 7.755 255.545 8z',
                },
                click: function (gd: any) {
                  // Reset to default ranges
                  if (surfaceData && currentStockPrice) {
                    const yMin = currentStockPrice * 0.95;
                    const yMax = currentStockPrice * 1.05;

                    // Use query strike prices if available, otherwise surface data
                    let xMin, xMax;
                    if (queryStrikePrices && queryStrikePrices.length > 0) {
                      xMin = Math.min(...queryStrikePrices);
                      xMax = Math.max(...queryStrikePrices);
                    } else {
                      xMin = Math.min(...surfaceData.strike_prices);
                      xMax = Math.max(...surfaceData.strike_prices);
                    }

                    setXAxisRange([xMin, xMax]);
                    setYAxisRange([yMin, yMax]);
                    setZAxisRange([displayStats.min, displayStats.max]);

                    const update = {
                      'scene.xaxis.range': [xMin, xMax],
                      'scene.yaxis.range': [yMin, yMax],
                      'scene.zaxis.range': [displayStats.min, displayStats.max],
                    };
                    // @ts-ignore - Plotly.relayout exists
                    window.Plotly?.relayout(gd, update);
                  }
                },
              },
            ],
            modeBarButtonsToRemove: ['toImage'],
          }}
          style={{ width: '100%', height: '700px' }}
        />
      </div>

      <div className="surface-3d-interpretation">
        <h4>📊 How to Read This 3D Surface:</h4>
        <ul>
          <li>
            <strong>X-axis (Strike Price):</strong> Different strike prices for the option.
            Default range shows all available strike prices from your data.
          </li>
          <li>
            <strong>Y-axis (Stock Price):</strong> The underlying stock price at collection time.
            Default range is current stock price ±5%.
          </li>
          <li>
            <strong>Z-axis (Premium):</strong> The option premium height - either absolute dollar value or relative percentage of strike price
          </li>
          <li>
            <strong>Axis Range Sliders:</strong> Adjust the X-axis (strike price) and Y-axis (stock price) ranges
            to zoom into specific regions of interest. Use the sliders to set min/max values for each axis.
          </li>
          <li>
            <strong>View Mode Toggle:</strong> Switch between absolute premiums ($) and relative premiums (% of strike price)
            to compare options across different strike levels
          </li>
          <li>
            <strong>Color gradient:</strong> Blue (low premiums) → Yellow (medium) → Red (high premiums).
            Colors dynamically adjust based on the visible data range when you change axis sliders.
          </li>
          <li>
            <strong>Contour lines:</strong> Show equal-premium levels projected on the floor
          </li>
          <li>
            <strong>Interactive controls:</strong>
            <ul>
              <li><strong>Rotate:</strong> Click and drag to view from different angles</li>
              <li><strong>Zoom:</strong> Scroll wheel to zoom in/out on specific regions</li>
              <li><strong>Pan:</strong> Hold Shift + drag to pan the view</li>
              <li><strong>Box select:</strong> Drag to select and zoom into a specific area</li>
              <li><strong>Reset:</strong> Use the "Reset axes" button in the toolbar to restore default ranges</li>
            </ul>
          </li>
        </ul>
        <p className="interpretation-insight">
          <strong>💡 Insight:</strong> The surface shape reveals how option premiums respond to both
          strike price selection and stock price movements. Steeper slopes indicate higher sensitivity
          to price changes. Red peaks show expensive premiums, blue valleys show cheaper options.
          Toggle between absolute and relative views to understand premium costs in different contexts.
          Use the axis sliders to focus on specific strike/stock price ranges of interest!
        </p>
      </div>
    </div>
  );
};

export default PremiumSurface3D;
