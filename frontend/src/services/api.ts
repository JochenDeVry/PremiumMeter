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
  SchedulerConfig,
  SchedulerConfigRequest,
  StockListResponse,
  StockDetailsResponse,
  ErrorResponse,
  SuccessResponse,
  HealthResponse,
} from '../types/api';

// ============================================================================
// API Client Configuration
// ============================================================================

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

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
      '/query/premium',
      request
    );
    return response.data;
  }

  async getChartData(request: ChartDataRequest): Promise<ChartDataResponse> {
    const response = await this.client.post<ChartDataResponse>(
      '/query/chart-data',
      request
    );
    return response.data;
  }

  // ==========================================================================
  // Watchlist Endpoints
  // ==========================================================================

  async getWatchlist(): Promise<WatchlistResponse> {
    const response = await this.client.get<WatchlistResponse>('/watchlist');
    return response.data;
  }

  async addStockToWatchlist(request: AddStockRequest): Promise<SuccessResponse> {
    const response = await this.client.post<SuccessResponse>(
      '/watchlist/add',
      request
    );
    return response.data;
  }

  async removeStockFromWatchlist(request: RemoveStockRequest): Promise<SuccessResponse> {
    const response = await this.client.delete<SuccessResponse>('/watchlist/remove', {
      data: request,
    });
    return response.data;
  }

  // ==========================================================================
  // Scheduler Endpoints
  // ==========================================================================

  async getSchedulerConfig(): Promise<SchedulerConfig> {
    const response = await this.client.get<SchedulerConfig>('/scheduler/config');
    return response.data;
  }

  async updateSchedulerConfig(
    request: SchedulerConfigRequest
  ): Promise<SchedulerConfig> {
    const response = await this.client.put<SchedulerConfig>(
      '/scheduler/config',
      request
    );
    return response.data;
  }

  async pauseScheduler(): Promise<SuccessResponse> {
    const response = await this.client.post<SuccessResponse>('/scheduler/pause');
    return response.data;
  }

  async resumeScheduler(): Promise<SuccessResponse> {
    const response = await this.client.post<SuccessResponse>('/scheduler/resume');
    return response.data;
  }

  // ==========================================================================
  // Stock Endpoints
  // ==========================================================================

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
