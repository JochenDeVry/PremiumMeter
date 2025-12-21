import React, { useState } from 'react';
import QueryForm from '../components/QueryForm';
import PremiumResults from '../components/PremiumResults';
import apiClient from '../services/api';
import { PremiumQueryRequest, PremiumQueryResponse } from '../types/api';

const HomePage: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [response, setResponse] = useState<PremiumQueryResponse | null>(null);

  const handleQuery = async (request: PremiumQueryRequest) => {
    setLoading(true);
    setError(null);
    setResponse(null);

    try {
      const result = await apiClient.queryPremium(request);
      setResponse(result);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('An unexpected error occurred');
      }
      console.error('Query error:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container">
      <h1>Options Premium Analyzer</h1>
      
      <section className="section">
        <h2>Query Historical Premium Data</h2>
        <p>
          Search historical options premium data with flexible strike price matching
          (exact, percentage range, or nearest strikes) and duration filtering.
        </p>
      </section>

      <div className="query-section">
        <div className="query-form-wrapper">
          <QueryForm onSubmit={handleQuery} loading={loading} />
        </div>

        <div className="query-results-wrapper">
          <PremiumResults response={response} loading={loading} error={error} />
        </div>
      </div>
    </div>
  );
};

export default HomePage;
