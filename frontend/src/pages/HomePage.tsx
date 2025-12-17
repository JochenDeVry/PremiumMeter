import React from 'react';
import { Link } from 'react-router-dom';

const HomePage: React.FC = () => {
  return (
    <div className="container">
      <h1>Options Premium Analyzer</h1>
      
      <section className="section">
        <h2>Welcome</h2>
        <p>
          Query historical options premium data with advanced strike price matching
          and powerful 3D visualizations.
        </p>
      </section>

      <section className="section">
        <h2>Features</h2>
        <ul>
          <li>Query historical premium data with flexible strike matching (exact, range, nearest)</li>
          <li>3D surface plots and 2D time-series visualizations</li>
          <li>Manage stock watchlist with automated data collection</li>
          <li>Configure scraping schedule with market hours and timezone support</li>
        </ul>
      </section>

      <section className="section">
        <h2>Quick Links</h2>
        <div className="links">
          <Link to="/query" className="button">Query Premium Data</Link>
          <Link to="/visualize" className="button">Visualizations</Link>
          <Link to="/watchlist" className="button">Manage Watchlist</Link>
          <Link to="/admin" className="button">Admin Panel</Link>
        </div>
      </section>

      <section className="section">
        <h2>System Status</h2>
        <p>
          <strong>Polling Interval:</strong> 5 minutes (during market hours)<br />
          <strong>Market Hours:</strong> 9:30 AM - 4:00 PM ET<br />
          <strong>Stocks Monitored:</strong> 54 in watchlist
        </p>
      </section>
    </div>
  );
};

export default HomePage;
