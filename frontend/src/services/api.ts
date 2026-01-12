// API client for Options Premium Analyzer
import axios, { AxiosInstance, AxiosError } from 'axios';
import type {
  PremiumQueryRequest,
  PremiumQueryResponse,
  ChartDataRequest,
  ChartDataResponse,
  WatchlistResponse,
  AddStockRequest,
  RemoveStockRequest,
  UpdateStockStatusRequest,
  BulkStockActionRequest,
  SchedulerConfig,
  SchedulerConfigRequest,
  RateLimitCalculation,
  ScraperProgress,
  ScraperRunHistoryResponse,
  StockListResponse,
  StockDetailsResponse,
  ErrorResponse,
  SuccessResponse,
  HealthResponse,
} from '../types/api';

// ============================================================================
// API Client Configuration
// ============================================================================

// Dynamically determine API URL based on current hostname
// This allows the app to work in both development (localhost) and production (NAS) without rebuilding
const getApiBaseUrl = (): string => {
  // If VITE_API_URL is set, use it (for explicit overrides)
  if (import.meta.env.VITE_API_URL) {
    return import.meta.env.VITE_API_URL;
  }
  
  // Otherwise, derive from current location
  const protocol = window.location.protocol;
  const hostname = window.location.hostname;
  const port = window.location.port;
  
  // If on localhost with a specific port, backend is likely on port 8000
  if (hostname === 'localhost' || hostname === '127.0.0.1') {
    return `${protocol}//${hostname}:8000`;
  }
  
  // For production/NAS deployment, assume backend is on same host with /api prefix
  // or use the same port as frontend if port is specified
  if (port && port !== '80' && port !== '443') {
    // If frontend is on a custom port, try backend on 8000
    return `${protocol}//${hostname}:8000`;
  }
  
  // Default: same origin (for reverse proxy setups)
  return `${protocol}//${hostname}${port ? ':' + port : ''}`;
};

const API_BASE_URL = getApiBaseUrl();

class APIClient {
  private client: AxiosInstance;

  constructor(baseURL: string = API_BASE_URL) {
    this.client = axios.create({
      baseURL,
      timeout: 30000, // 30 second timeout
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Add response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError<ErrorResponse>) => {
        if (error.response) {
          // Server responded with error status
          const errorData = error.response.data;
          throw new APIError(
            errorData.message || 'An error occurred',
            error.response.status,
            errorData.error,
            errorData.details,
            errorData.suggestion
          );
        } else if (error.request) {
          // Request made but no response received
          throw new APIError('No response from server', 0, 'network_error');
        } else {
          // Error in request setup
          throw new APIError(error.message, 0, 'request_error');
        }
      }
    );
  }

  // ==========================================================================
  // Health Check
  // ==========================================================================

  async health(): Promise<HealthResponse> {
    const response = await this.client.get<HealthResponse>('/health');
    return response.data;
  }

  // ==========================================================================
  // Query Endpoints
  // ==========================================================================

  async queryPremium(request: PremiumQueryRequest): Promise<PremiumQueryResponse> {
    const response = await this.client.post<PremiumQueryResponse>(
      '/api/query/premium',
      request
    );
    return response.data;
  }

  async queryPremiumDistribution(request: {
    ticker: string;
    option_type: string;
    strike_price: number;
    duration_days: number;
    duration_tolerance_days?: number;
    lookback_days?: number;
  }): Promise<{
    ticker: string;
    option_type: string;
    strike_price: number;
    duration_days: number;
    premiums: number[];
    data_points: number;
    collection_period: { start: string; end: string };
  }> {
    const response = await this.client.post(
      '/api/query/premium-distribution',
      request
    );
    return response.data;
  }

  async queryPremiumBoxPlot(request: {
    ticker: string;
    option_type: string;
    strike_price: number;
    duration_days: number;
    duration_tolerance_days?: number;
    lookback_days?: number;
  }): Promise<{
    ticker: string;
    option_type: string;
    strike_price: number;
    duration_days: number;
    data_points: Array<{
      stock_price: number;
      premium: number;
      timestamp: string;
    }>;
    total_points: number;
    stock_price_range: {
      min: number;
      max: number;
      mean: number;
    };
    collection_period: { start: string; end: string };
  }> {
    const response = await this.client.post(
      '/api/query/premium-boxplot',
      request
    );
    return response.data;
  }

  async queryPremiumSurface(request: {
    ticker: string;
    option_type: string;
    duration_days: number;
    duration_tolerance_days?: number;
    lookback_days?: number;
  }): Promise<{
    ticker: string;
    option_type: string;
    duration_days: number;
    strike_prices: number[];
    stock_prices: number[];
    premium_grid: (number | null)[][];
    data_point_counts: number[][];
    total_points: number;
    collection_period: { start: string; end: string };
  }> {
    const response = await this.client.post(
      '/api/query/premium-surface',
      request
    );
    return response.data;
  }

  async getChartData(request: ChartDataRequest): Promise<ChartDataResponse> {
    const response = await this.client.post<ChartDataResponse>(
      '/api/query/chart-data',
      request
    );
    return response.data;
  }

  // ==========================================================================
  // Watchlist Endpoints
  // ==========================================================================

  async getWatchlist(): Promise<WatchlistResponse> {
    const response = await this.client.get<WatchlistResponse>('/api/watchlist');
    return response.data;
  }

  async addStockToWatchlist(request: AddStockRequest): Promise<SuccessResponse> {
    const response = await this.client.post<SuccessResponse>(
      '/api/watchlist/add',
      request
    );
    return response.data;
  }

  async removeStockFromWatchlist(request: RemoveStockRequest): Promise<SuccessResponse> {
    const response = await this.client.delete<SuccessResponse>('/api/watchlist/remove', {
      data: request,
    });
    return response.data;
  }

  async updateStockStatus(request: UpdateStockStatusRequest): Promise<SuccessResponse> {
    const response = await this.client.post<SuccessResponse>(
      '/api/watchlist/update-status',
      request
    );
    return response.data;
  }

  async bulkStockAction(request: BulkStockActionRequest): Promise<SuccessResponse> {
    const response = await this.client.post<SuccessResponse>(
      '/api/watchlist/bulk-action',
      request
    );
    return response.data;
  }

  // ==========================================================================
  // Scheduler Endpoints
  // ==========================================================================

  async getSchedulerConfig(): Promise<SchedulerConfig> {
    const response = await this.client.get<SchedulerConfig>('/api/scheduler/config');
    return response.data;
  }

  async updateSchedulerConfig(
    request: SchedulerConfigRequest
  ): Promise<SchedulerConfig> {
    const response = await this.client.put<SchedulerConfig>(
      '/api/scheduler/config',
      request
    );
    return response.data;
  }

  async pauseScheduler(): Promise<SuccessResponse> {
    const response = await this.client.post<SuccessResponse>('/api/scheduler/pause');
    return response.data;
  }

  async resumeScheduler(startNow: boolean = false): Promise<SuccessResponse> {
    const response = await this.client.post<SuccessResponse>('/api/scheduler/resume', null, {
      params: { start_now: startNow }
    });
    return response.data;
  }

  async getRateLimitCalculation(
    polling_interval_minutes?: number,
    stock_delay_seconds?: number,
    max_expirations?: number
  ): Promise<RateLimitCalculation> {
    const params: any = {};
    if (polling_interval_minutes !== undefined) params.polling_interval_minutes = polling_interval_minutes;
    if (stock_delay_seconds !== undefined) params.stock_delay_seconds = stock_delay_seconds;
    if (max_expirations !== undefined) params.max_expirations = max_expirations;
    
    const response = await this.client.get<RateLimitCalculation>('/api/scheduler/rate-calculation', { params });
    return response.data;
  }

  async getScraperProgress(): Promise<ScraperProgress> {
    const response = await this.client.get<ScraperProgress>('/api/scheduler/progress');
    return response.data;
  }

  async getRunHistory(limit: number = 20): Promise<ScraperRunHistoryResponse> {
    const response = await this.client.get<ScraperRunHistoryResponse>('/api/scheduler/run-history', {
      params: { limit }
    });
    return response.data;
  }

  // ==========================================================================
  // Stock Endpoints
  // ==========================================================================

  async listAllStocks(): Promise<Array<{ticker: string, company_name: string}>> {
    const response = await this.client.get<Array<{ticker: string, company_name: string}>>('/api/stocks');
    return response.data;
  }

  async getStockPrice(ticker: string): Promise<{
    ticker: string;
    company_name: string;
    latest_price: number | null;
    price_timestamp: string | null;
  }> {
    const response = await this.client.get(`/api/stocks/${ticker}/price`);
    return response.data;
  }

  async getUSStocks(): Promise<{stocks: Array<{ticker: string, company_name: string}>, total_count: number}> {
    const response = await this.client.get<{stocks: Array<{ticker: string, company_name: string}>, total_count: number}>('/api/us-stocks');
    return response.data;
  }

  async listStocks(
    status?: string,
    limit: number = 100,
    offset: number = 0
  ): Promise<StockListResponse> {
    const response = await this.client.get<StockListResponse>('/stocks', {
      params: { status, limit, offset },
    });
    return response.data;
  }

  async getStockDetails(ticker: string): Promise<StockDetailsResponse> {
    const response = await this.client.get<StockDetailsResponse>(`/stocks/${ticker}`);
    return response.data;
  }

  async getIntradayPrices(ticker: string): Promise<{
    ticker: string;
    company_name: string;
    data_points: Array<{
      timestamp: string;
      price: number;
      volume?: number;
    }>;
    source: string;
    date: string;
  }> {
    const response = await this.client.get(`/api/intraday/${ticker}`);
    return response.data;
  }
}

// ============================================================================
// Custom Error Class
// ============================================================================

export class APIError extends Error {
  constructor(
    message: string,
    public statusCode: number,
    public errorCode?: string,
    public details?: Record<string, unknown>,
    public suggestion?: string
  ) {
    super(message);
    this.name = 'APIError';
  }

  toString(): string {
    let str = `${this.name}: ${this.message}`;
    if (this.statusCode) str += ` (HTTP ${this.statusCode})`;
    if (this.errorCode) str += ` [${this.errorCode}]`;
    if (this.suggestion) str += `\nSuggestion: ${this.suggestion}`;
    return str;
  }
}

// ============================================================================
// Export Singleton Instance
// ============================================================================

const apiClient = new APIClient();
export default apiClient;
