-- Add rate limiting configuration fields to scraper_schedule table
-- Migration: add_rate_limit_settings
-- Date: 2025-12-22

ALTER TABLE scraper_schedule 
ADD COLUMN IF NOT EXISTS stock_delay_seconds INTEGER NOT NULL DEFAULT 10,
ADD COLUMN IF NOT EXISTS max_expirations INTEGER NOT NULL DEFAULT 8;

COMMENT ON COLUMN scraper_schedule.stock_delay_seconds IS 'Delay between scraping stocks (seconds) - helps avoid rate limiting';
COMMENT ON COLUMN scraper_schedule.max_expirations IS 'Maximum number of option expirations to fetch per stock (nearest dates)';

-- Update existing row with default values if they don't exist
UPDATE scraper_schedule 
SET stock_delay_seconds = 10, max_expirations = 8
WHERE stock_delay_seconds IS NULL OR max_expirations IS NULL;
