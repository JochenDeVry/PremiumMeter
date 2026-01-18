import React, { useState } from 'react';
import QueryForm from '../components/QueryForm';
import PremiumResults from '../components/PremiumResults';
import apiClient from '../services/api';
import { PremiumQueryRequest, PremiumQueryResponse } from '../types/api';

const HomePage: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [response, setResponse] = useState<PremiumQueryResponse | null>(null);
  const [lastRequest, setLastRequest] = useState<PremiumQueryRequest | null>(null);

  const handleQuery = async (request: PremiumQueryRequest) => {
    setLoading(true);
    setError(null);
    setResponse(null);
    setLastRequest(request);

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
      <h1>Query Settings</h1>
      <div className="query-section-fullwidth">
        <div className="query-form-wrapper-fullwidth">
          <QueryForm onSubmit={handleQuery} loading={loading} />
        </div>
        <h1>Premium Data</h1>
        <div className="query-results-wrapper-fullwidth">
          <PremiumResults
            response={response}
            loading={loading}
            error={error}
            queryRequest={lastRequest}
          />
        </div>
      </div>
    </div>
  );
};

export default HomePage;
