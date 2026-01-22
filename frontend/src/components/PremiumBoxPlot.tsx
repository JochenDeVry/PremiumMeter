import React, { useMemo } from 'react';
import Plot from 'react-plotly.js';
import './PremiumBoxPlot.css';

interface DataPoint {
  stock_price: number;
  premium: number;
  timestamp: string;
}

interface PremiumBoxPlotProps {
  ticker: string;
  optionType: string;
  strikePrice: number;
  durationDays: number;
  currentStockPrice?: number;
  dataPoints: DataPoint[];
  stockPriceRange: {
    min: number;
    max: number;
    mean: number;
  };
}

const PremiumBoxPlot: React.FC<PremiumBoxPlotProps> = ({
  ticker,
  optionType,
  strikePrice,
  durationDays,
  currentStockPrice,
  dataPoints,
  stockPriceRange,
}) => {
  const [isExpanded, setIsExpanded] = React.useState(false);
  // Group data into stock price bins
  const binData = useMemo(() => {
    if (dataPoints.length === 0) return [];

    // Determine number of bins (use Sturges' formula, similar to histogram)
    const numBins = Math.max(5, Math.min(10, Math.ceil(Math.log2(dataPoints.length) + 1)));

    // Calculate bin width
    const range = stockPriceRange.max - stockPriceRange.min;
    const binWidth = range / numBins;

    // Create bins
    const bins: { [key: string]: number[] } = {};
    const binRanges: { min: number; max: number; label: string }[] = [];

    for (let i = 0; i < numBins; i++) {
      const binMin = stockPriceRange.min + i * binWidth;
      const binMax = binMin + binWidth;
      const binLabel = `$${binMin.toFixed(2)}-$${binMax.toFixed(2)}`;

      bins[binLabel] = [];
      binRanges.push({ min: binMin, max: binMax, label: binLabel });
    }

    // Assign data points to bins
    dataPoints.forEach(point => {
      for (const binRange of binRanges) {
        if (point.stock_price >= binRange.min && point.stock_price <= binRange.max) {
          bins[binRange.label].push(point.premium);
          break;
        }
      }
    });

    // Create box plot data
    return binRanges.map(binRange => ({
      label: binRange.label,
      premiums: bins[binRange.label],
      count: bins[binRange.label].length,
    }));
  }, [dataPoints, stockPriceRange]);

  // Calculate overall statistics
  const stats = useMemo(() => {
    if (dataPoints.length === 0) return null;

    const premiums = dataPoints.map(d => d.premium);
    const stockPrices = dataPoints.map(d => d.stock_price);

    return {
      totalPoints: dataPoints.length,
      premiumMin: Math.min(...premiums),
      premiumMax: Math.max(...premiums),
      premiumMean: premiums.reduce((a, b) => a + b, 0) / premiums.length,
      stockPriceMin: Math.min(...stockPrices),
      stockPriceMax: Math.max(...stockPrices),
    };
  }, [dataPoints]);

  if (!stats || dataPoints.length === 0) {
    return (
      <div className="box-plot-container">
        <div className="box-plot-error">
          No data available for the selected parameters.
        </div>
      </div>
    );
  }

  return (
    <div className="box-plot-container">
      <div className="box-plot-header">
        <div className="box-plot-title-row">
          <h3>Premium vs Stock Price Box Plot</h3>
          <div className="strike-price-badge">
            <span className="price-label">Strike Price</span>
            <span className="price-value">${strikePrice.toFixed(2)}</span>
          </div>
        </div>
        <div className="box-plot-meta">
          <span><strong>Ticker:</strong> {ticker}</span>
          <span><strong>Type:</strong> {optionType.toUpperCase()}</span>
          <span><strong>Duration:</strong> {durationDays} days</span>
        </div>
      </div>

      <div className="box-plot-stats">
        <div className="stat-item">
          <span className="stat-label">Data Points:</span>
          <span className="stat-value">{stats.totalPoints}</span>
        </div>
        <div className="stat-item">
          <span className="stat-label">Stock Price Range:</span>
          <span className="stat-value">
            ${stats.stockPriceMin.toFixed(2)} - ${stats.stockPriceMax.toFixed(2)}
          </span>
        </div>
        <div className="stat-item">
          <span className="stat-label">Premium Range:</span>
          <span className="stat-value primary">
            ${stats.premiumMin.toFixed(2)} - ${stats.premiumMax.toFixed(2)}
          </span>
        </div>
        <div className="stat-item">
          <span className="stat-label">Avg Premium:</span>
          <span className="stat-value primary">
            ${stats.premiumMean.toFixed(2)}
          </span>
        </div>
      </div>

      <div className="box-plot-chart">
        <Plot
          data={[
            {
              type: 'box',
              x: binData.flatMap(bin => Array(bin.premiums.length).fill(bin.label)),
              y: binData.flatMap(bin => bin.premiums),
              name: 'Premium',
              boxmean: 'sd',
              marker: {
                color: optionType.toLowerCase() === 'call' ? '#22c55e' : '#ef4444',
              },
              line: {
                color: optionType.toLowerCase() === 'call' ? '#16a34a' : '#dc2626',
              },
            },
          ]}
          layout={{
            title: 'Premium Distribution Across Stock Price Ranges',
            xaxis: {
              title: 'Stock Price Range',
              tickangle: -45,
            },
            yaxis: {
              title: 'Premium ($)',
            },
            showlegend: false,
            hovermode: 'closest',
            height: 500,
            margin: { t: 50, r: 30, b: 100, l: 60 },
          }}
          config={{
            displayModeBar: true,
            displaylogo: false,
            responsive: true,
          }}
          style={{ width: '100%' }}
        />
      </div>

      <div className={`expandable-section ${isExpanded ? 'expanded' : ''}`}>
        <div className="expandable-header" onClick={() => setIsExpanded(!isExpanded)}>
          <h4>📊 How to Read This Plot</h4>
          <span className="toggle-icon">▼</span>
        </div>
        <div className="expandable-content">
          <ul>
            <li><strong>Each box</strong> represents premiums within a stock price range</li>
            <li><strong>Box boundaries</strong> show the 25th and 75th percentiles (middle 50% of data)</li>
            <li><strong>Line inside box</strong> is the median premium</li>
            <li><strong>Diamond marker</strong> shows the mean (average) premium</li>
            <li><strong>Whiskers</strong> extend to show the data range (excluding outliers)</li>
            <li><strong>Outlier points</strong> appear as individual dots beyond the whiskers</li>
          </ul>
          <p className="interpretation-insight">
            <strong>💡 Insight:</strong> This shows how option premiums vary with the underlying stock price.
            Higher stock prices typically lead to different premium ranges for the same strike.
          </p>
        </div>
      </div>
    </div>
  );
};

export default PremiumBoxPlot;
