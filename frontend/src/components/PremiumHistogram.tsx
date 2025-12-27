import React from 'react';
import Plot from 'react-plotly.js';
import './PremiumHistogram.css';

interface PremiumHistogramProps {
  premiums: number[];
  ticker: string;
  optionType: string;
  strikePrice: number;
  durationDays: number;
  dataPoints: number;
}

const PremiumHistogram: React.FC<PremiumHistogramProps> = ({
  premiums,
  ticker,
  optionType,
  strikePrice,
  durationDays,
  dataPoints,
}) => {
  if (!premiums || premiums.length === 0) {
    return (
      <div className="histogram-container">
        <div className="no-data">
          <p>No premium data available for histogram.</p>
        </div>
      </div>
    );
  }

  // Calculate statistics
  const minPremium = Math.min(...premiums);
  const maxPremium = Math.max(...premiums);
  const avgPremium = premiums.reduce((sum, p) => sum + p, 0) / premiums.length;

  // Determine optimal number of bins (Sturges' formula)
  const numBins = Math.ceil(Math.log2(premiums.length) + 1);

  return (
    <div className="histogram-container">
      <div className="histogram-header">
        <h3>Premium Distribution</h3>
        <div className="histogram-meta">
          <span><strong>Ticker:</strong> {ticker}</span>
          <span><strong>Type:</strong> {optionType.toUpperCase()}</span>
          <span><strong>Strike:</strong> ${strikePrice.toFixed(2)}</span>
          <span><strong>Duration:</strong> {durationDays} days</span>
          <span><strong>Data Points:</strong> {dataPoints}</span>
        </div>
      </div>

      <div className="histogram-stats">
        <div className="stat-item">
          <span className="stat-label">Min:</span>
          <span className="stat-value">${minPremium.toFixed(2)}</span>
        </div>
        <div className="stat-item">
          <span className="stat-label">Avg:</span>
          <span className="stat-value highlight-primary">${avgPremium.toFixed(2)}</span>
        </div>
        <div className="stat-item">
          <span className="stat-label">Max:</span>
          <span className="stat-value">${maxPremium.toFixed(2)}</span>
        </div>
      </div>

      <Plot
        data={[
          {
            x: premiums,
            type: 'histogram',
            nbinsx: numBins,
            marker: {
              color: optionType === 'call' ? 'rgba(76, 175, 80, 0.7)' : 'rgba(244, 67, 54, 0.7)',
              line: {
                color: optionType === 'call' ? 'rgba(76, 175, 80, 1)' : 'rgba(244, 67, 54, 1)',
                width: 1,
              },
            },
            name: 'Frequency',
            hovertemplate: 
              '<b>Premium Range:</b> $%{x}<br>' +
              '<b>Frequency:</b> %{y}<br>' +
              '<extra></extra>',
          },
        ]}
        layout={{
          title: {
            text: `Premium Frequency Distribution`,
            font: { size: 16 },
          },
          xaxis: {
            title: 'Premium ($)',
            gridcolor: '#e0e0e0',
          },
          yaxis: {
            title: 'Number of Data Points',
            gridcolor: '#e0e0e0',
          },
          plot_bgcolor: '#fafafa',
          paper_bgcolor: 'white',
          margin: { l: 60, r: 40, t: 60, b: 60 },
          hovermode: 'closest',
          bargap: 0.05,
        }}
        config={{
          displayModeBar: true,
          displaylogo: false,
          modeBarButtonsToRemove: ['pan2d', 'lasso2d', 'select2d'],
          responsive: true,
        }}
        style={{ width: '100%', height: '450px' }}
      />

      <div className="histogram-interpretation">
        <p className="help-text">
          <strong>Interpretation:</strong> This histogram shows how frequently different premium values occur.
          Higher bars indicate premium levels that appear more often in the historical data, suggesting
          higher probability of those premium levels occurring.
        </p>
      </div>
    </div>
  );
};

export default PremiumHistogram;
