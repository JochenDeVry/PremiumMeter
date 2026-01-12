// TypeScript type definitions generated from OpenAPI schema
// contracts/openapi.yaml

// ============================================================================
// Enums
// ============================================================================

export enum OptionType {
  CALL = 'call',
  PUT = 'put',
}

export enum StrikeMode {
  EXACT = 'exact',
  PERCENTAGE_RANGE = 'percentage_range',
  NEAREST = 'nearest',
}

export enum ChartType {
  SURFACE_3D = 'surface_3d',
  TIME_SERIES_2D = 'time_series_2d',
  HEATMAP = 'heatmap',
}

export enum MonitoringStatus {
  ACTIVE = 'active',
  PAUSED = 'paused',
}

export enum SchedulerStatus {
  IDLE = 'idle',
  RUNNING = 'running',
  PAUSED = 'paused',
  ERROR = 'error',
}

export enum StockStatus {
  ACTIVE = 'active',
  DELISTED = 'delisted',
  INACTIVE = 'inactive',
}

// ============================================================================
// Query Types
// ============================================================================

export interface PremiumQueryRequest {
  ticker: string;
  option_type: OptionType;
  strike_mode: StrikeMode;
  strike_price: number;
  strike_range_percent?: number;
  nearest_count_above?: number;
  nearest_count_below?: number;
  duration_days: number;
  duration_tolerance_days?: number;
  lookback_days?: number;
}

export interface GreeksAverage {
  delta?: number;
  gamma?: number;
  theta?: number;
  vega?: number;
}

export interface PremiumResult {
  strike_price: number;
  duration_days: number;
  data_points: number;
  min_premium: number;
  max_premium: number;
  avg_premium: number;
  latest_premium?: number;
  greeks_avg?: GreeksAverage;
}

export interface PremiumQueryResponse {
  ticker: string;
  option_type: OptionType;
  query_timestamp: string;
  current_stock_price?: number;
  results: PremiumResult[];
}

// ============================================================================
// Chart Types
// ============================================================================

export interface ChartDataRequest {
  ticker: string;
  option_type: OptionType;
  chart_type: ChartType;
  strike_prices?: number[];
  duration_days?: number[];
  lookback_days?: number;
}

export interface CollectionPeriod {
  start: string;
  end: string;
}

export interface ChartDataResponse {
  ticker: string;
  option_type: OptionType;
  chart_type: ChartType;
  strike_prices: number[];
  durations_days: number[];
  premium_grid: number[][];
  collection_period: CollectionPeriod;
}

// ============================================================================
// Watchlist Types
// ============================================================================

export interface WatchlistStock {
  stock_id: number;
  ticker: string;
  company_name: string;
  status: MonitoringStatus;
  added_at: string;
  last_scraped?: string;
  data_points_count: number;
}

export interface WatchlistResponse {
  watchlist: WatchlistStock[];
  total_count: number;
}

export interface AddStockRequest {
  ticker: string;
  company_name?: string;
}

export interface RemoveStockRequest {
  ticker: string;
}

export interface UpdateStockStatusRequest {
  ticker: string;
  status: string;
}

export interface BulkStockActionRequest {
  tickers: string[];
  action: 'activate' | 'deactivate' | 'remove';
}

export interface ScraperProgress {
  is_running: boolean;
  total_stocks: number;
  completed_stocks: number;
  current_stock?: string;
  current_source?: string;
  pending_stocks: string[];
  completed_stock_list: string[];
  failed_stocks: string[];
  start_time?: string;
  estimated_completion?: string;
}

export interface StockScrapeLog {
  ticker: string;
  status: 'success' | 'failed';
  source_used?: string;
  contracts_scraped?: number;
  timestamp: string;
  error_message?: string;
}

export interface ScraperRun {
  id: number;
  start_time: string;
  end_time?: string;
  status: 'running' | 'completed' | 'failed';
  total_stocks: number;
  successful_stocks: number;
  failed_stocks: number;
  total_contracts: number;
  stock_logs: StockScrapeLog[];
}

export interface ScraperRunHistoryResponse {
  runs: ScraperRun[];
  total_count: number;
}

// ============================================================================
// Scheduler Types
// ============================================================================

export interface SchedulerConfig {
  polling_interval_minutes: number;
  market_hours_start: string;
  market_hours_end: string;
  timezone: string;
  exclude_weekends: boolean;
  exclude_holidays: boolean;
  status: SchedulerStatus;
  next_run?: string;
  last_run?: string;
  stock_delay_seconds: number;
  max_expirations: number;
}

export interface SchedulerConfigRequest {
  polling_interval_minutes?: number;
  market_hours_start?: string;
  market_hours_end?: string;
  timezone?: string;
  exclude_weekends?: boolean;
  exclude_holidays?: boolean;
  stock_delay_seconds?: number;
  max_expirations?: number;
}

export interface RateLimitCalculation {
  watchlist_size: number;
  requests_per_stock: number;
  requests_per_cycle: number;
  cycle_duration_minutes: number;
  requests_per_minute: number;
  cycles_per_hour: number;
  requests_per_hour: number;
  cycles_per_day: number;
  requests_per_day: number;
  within_minute_limit: boolean;
  within_hour_limit: boolean;
  within_day_limit: boolean;
  warnings: string[];
  actual_queries_today: number;
  last_reset_time: string | null;
}

// ============================================================================
// Stock Types
// ============================================================================

export interface StockListItem {
  stock_id: number;
  ticker: string;
  company_name: string;
  status: StockStatus;
  in_watchlist: boolean;
  data_points_count: number;
}

export interface StockListResponse {
  stocks: StockListItem[];
  total_count: number;
  limit: number;
  offset: number;
}

export interface StockDetailsResponse {
  stock_id: number;
  ticker: string;
  company_name: string;
  current_price?: number;
  status: StockStatus;
  in_watchlist: boolean;
  data_points_count: number;
  earliest_data?: string;
  latest_data?: string;
}

// ============================================================================
// Common Response Types
// ============================================================================

export interface ErrorResponse {
  error: string;
  message: string;
  details?: Record<string, unknown>;
  suggestion?: string;
}

export interface SuccessResponse {
  success: boolean;
  message: string;
}

export interface HealthResponse {
  status: string;
  service: string;
  version: string;
}
