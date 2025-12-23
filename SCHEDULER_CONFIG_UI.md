# Scheduler Configuration UI Implementation

## Overview
Comprehensive editable scheduler configuration UI with real-time rate limit calculations and warnings.

## Changes Implemented

### Backend Changes

#### 1. Database Model (`backend/src/models/scraper_schedule.py`)
Added new columns to `ScraperSchedule` table:
- `stock_delay_seconds` (INTEGER, default: 10) - Delay between scraping stocks
- `max_expirations` (INTEGER, default: 8) - Maximum option expirations per stock

#### 2. Database Migration (`backend/migrations/add_rate_limit_settings.sql`)
SQL migration script to add new columns:
```sql
ALTER TABLE scraper_schedule 
ADD COLUMN IF NOT EXISTS stock_delay_seconds INTEGER NOT NULL DEFAULT 10,
ADD COLUMN IF NOT EXISTS max_expirations INTEGER NOT NULL DEFAULT 8;
```

**TO RUN MIGRATION:**
```bash
cd backend
psql -U premiummeter -d premiummeter -f migrations/add_rate_limit_settings.sql
```

#### 3. Schemas (`backend/src/models/schemas.py`)
- Added fields to `SchedulerConfig`: `stock_delay_seconds`, `max_expirations`
- Added fields to `SchedulerConfigRequest`: `stock_delay_seconds` (0-300), `max_expirations` (1-100)
- **New Schema:** `RateLimitCalculation` - Complete rate limit calculation response with:
  - Watchlist size and requests per stock
  - Requests per cycle/minute/hour/day
  - Boolean flags for limit compliance
  - Warning messages and recommendations

#### 4. Scheduler Endpoint (`backend/src/api/endpoints/scheduler.py`)
**Updated endpoints:**
- `GET /api/scheduler/config` - Now returns `stock_delay_seconds` and `max_expirations`
- `PUT /api/scheduler/config` - Accepts and updates new fields, applies to scheduler service

**New endpoint:**
- `GET /api/scheduler/rate-calculation` - Returns `RateLimitCalculation`:
  ```json
  {
    "watchlist_size": 54,
    "requests_per_stock": 10,
    "requests_per_cycle": 540,
    "cycle_duration_minutes": 9.0,
    "requests_per_minute": 60.0,
    "cycles_per_hour": 0.5,
    "requests_per_hour": 270,
    "cycles_per_day": 12,
    "requests_per_day": 6480,
    "within_minute_limit": true,
    "within_hour_limit": true,
    "within_day_limit": true,
    "warnings": []
  }
  ```

#### 5. Scraper Service (`backend/src/services/scraper.py`)
**Now reads settings from database instead of hardcoded:**
- `stock_delay_seconds` - Loaded from ScraperSchedule config
- `max_expirations` - Loaded from ScraperSchedule config, applied as `expirations[:max_exp]`

**Impact:**
- Settings can be changed without code deployment
- Admin can tune rate limiting dynamically

#### 6. Scheduler Validation (`backend/src/services/scheduler.py`)
- Extended `polling_interval_minutes` validation: 1-1440 minutes (was 1-60)
- Allows intervals up to 24 hours for very conservative setups

---

### Frontend Changes

#### 1. TypeScript Types (`frontend/src/types/api.ts`)
**Updated:**
- `SchedulerConfig` - Added `stock_delay_seconds`, `max_expirations`
- `SchedulerConfigRequest` - Added optional `stock_delay_seconds`, `max_expirations`

**New:**
- `RateLimitCalculation` interface - Matches backend schema

#### 2. API Client (`frontend/src/services/api.ts`)
**New method:**
- `getRateLimitCalculation()` - Fetches rate calculation from `/api/scheduler/rate-calculation`

#### 3. New Component: SchedulerConfigPanel (`frontend/src/components/SchedulerConfigPanel.tsx`)
Comprehensive scheduler configuration UI with:

**Features:**
- **Editable Settings:**
  - Polling Interval (1-1440 minutes)
  - Stock Delay (0-300 seconds)
  - Max Expirations (1-100 dates)
  
- **Real-Time Rate Calculations:**
  - Watchlist size, requests per stock
  - Cycle duration in minutes
  - Requests per minute/hour/day
  - Visual indicators (✓ green, ⚠ yellow)
  
- **Warning System:**
  - Automatically displays warnings when limits exceeded
  - Shows recommendations (reduce watchlist, increase interval)
  
- **Info Modal:**
  - Comprehensive rate limit documentation
  - How each setting affects requests
  - Request calculation formulas
  - Recommended configurations table
  - Troubleshooting guide
  
- **Status Controls:**
  - Start/Pause scheduler buttons
  - Visual status badge
  
- **Read-Only Info:**
  - Market hours
  - Timezone
  - Next run time

**UI States:**
- View mode (default) - Settings displayed as text
- Edit mode - Settings shown as inputs with validation
- Saving state - Disabled buttons during save
- Error state - Red error banner if save fails

#### 4. Styling (`frontend/src/components/SchedulerConfigPanel.css`)
Complete styling for:
- Panel layout with sections
- Editable inputs with focus states
- Rate limit indicators (green/yellow)
- Warning banners
- Large info modal with scrolling
- Configuration tables
- Responsive grid layouts

#### 5. Admin Page Integration (`frontend/src/pages/AdminPage.tsx`)
**Updated:**
- Imports `SchedulerConfigPanel` component
- Replaces old read-only scheduler section
- Passes handlers for pause/resume
- Handles config updates via callback

**Before:**
```tsx
<section className="section">
  <h2>Scheduler Configuration</h2>
  {/* Read-only config display */}
</section>
```

**After:**
```tsx
<section className="section">
  <SchedulerConfigPanel
    initialConfig={schedulerConfig}
    onConfigUpdated={(config) => setSchedulerConfig(config)}
    onPause={handlePauseScheduler}
    onResume={handleResumeScheduler}
  />
</section>
```

---

## Usage Instructions

### 1. Run Database Migration
```bash
cd C:\PremiumMeter\PremiumMeter\backend
psql -U premiummeter -d premiummeter -f migrations/add_rate_limit_settings.sql
```

Verify migration:
```sql
SELECT column_name, data_type, column_default 
FROM information_schema.columns 
WHERE table_name = 'scraper_schedule' 
  AND column_name IN ('stock_delay_seconds', 'max_expirations');
```

### 2. Restart Backend
```bash
cd C:\PremiumMeter\PremiumMeter\backend
python -m src.api.main
```

### 3. Verify Backend
Test rate calculation endpoint:
```bash
curl http://localhost:8000/api/scheduler/rate-calculation
```

### 4. Frontend Should Auto-Update
If frontend running, it will hot-reload. Otherwise:
```bash
cd C:\PremiumMeter\PremiumMeter\frontend
npm run serve
```

### 5. Access Admin Page
Navigate to: `http://localhost:5173/admin`

---

## Admin Page Workflow

### Viewing Current Configuration
1. Go to Admin page
2. Scheduler Configuration panel shows:
   - Current status (Active/Paused)
   - All settings (polling interval, delays, expirations)
   - Expected API usage with color-coded indicators
   - Warnings if limits will be exceeded

### Editing Settings
1. Click "Edit Settings" button
2. Modify values using input fields:
   - Polling Interval: 1-1440 minutes
   - Stock Delay: 0-300 seconds
   - Max Expirations: 1-100 dates
3. Rate calculations update automatically as you type
4. Warnings appear if values exceed limits
5. Click "Save Settings" to apply
6. Click "Cancel" to discard changes

### Understanding Rate Limits
1. Click "ℹ Info" button
2. Modal opens with comprehensive documentation:
   - Rate limit explanation (60/min, 360/hour, 8000/day)
   - How each setting affects requests
   - Request calculation formula
   - Recommended configurations table
   - Troubleshooting guide
3. Click "Close" or overlay to dismiss

### Starting/Stopping Scheduler
- **When Paused:** Green "Start Scheduler" button
- **When Active:** Yellow "Pause Scheduler" button
- Status badge updates immediately
- Next run time displayed when active

---

## Rate Calculation Logic

### Formula
```
requests_per_stock = 2 + max_expirations
  (1 price + 1 expirations list + N option chains)

requests_per_cycle = watchlist_size × requests_per_stock

cycle_duration_minutes = (watchlist_size × stock_delay_seconds) / 60

requests_per_minute = requests_per_cycle / cycle_duration_minutes

cycles_per_hour = 60 / polling_interval_minutes

requests_per_hour = requests_per_cycle × cycles_per_hour

cycles_per_day = (24 × 60) / polling_interval_minutes

requests_per_day = requests_per_cycle × cycles_per_day
```

### Example Calculation
With current defaults (54 stocks, 120min interval, 10sec delay, 8 expirations):
```
requests_per_stock = 2 + 8 = 10
requests_per_cycle = 54 × 10 = 540
cycle_duration = (54 × 10) / 60 = 9 minutes
requests_per_minute = 540 / 9 = 60
cycles_per_hour = 60 / 120 = 0.5
requests_per_hour = 540 × 0.5 = 270
cycles_per_day = 1440 / 120 = 12
requests_per_day = 540 × 12 = 6,480

Results:
✓ 60/min (at limit, spread over 9 minutes)
✓ 270/hour (under 360 limit)
✓ 6,480/day (under 8,000 limit)
```

---

## Validation Rules

### Polling Interval
- **Min:** 1 minute
- **Max:** 1440 minutes (24 hours)
- **Recommended:** 120 minutes (2 hours) for 30-50 stocks

### Stock Delay
- **Min:** 0 seconds (not recommended)
- **Max:** 300 seconds (5 minutes)
- **Recommended:** 10 seconds (allows ~6 stocks/minute)

### Max Expirations
- **Min:** 1 expiration
- **Max:** 100 expirations
- **Recommended:** 8 expirations (covers 0-90 days, most trading activity)

---

## Warning Thresholds

### Yellow Warnings
- Requests per minute > 60
- Requests per hour > 360
- Requests per day > 8,000

### Recommendations Provided
- **If exceeding day limit:** "Reduce watchlist to X stocks or increase interval"
- **If exceeding hour limit:** "Increase interval to X+ minutes or reduce watchlist"
- **If exceeding minute limit:** "Increase stock delay or reduce scrape frequency"

---

## Testing

### Test Rate Calculation API
```bash
curl http://localhost:8000/api/scheduler/rate-calculation | jq
```

### Test Config Update
```bash
curl -X PUT http://localhost:8000/api/scheduler/config \
  -H "Content-Type: application/json" \
  -d '{
    "polling_interval_minutes": 120,
    "stock_delay_seconds": 10,
    "max_expirations": 8
  }'
```

### Verify Scraper Uses Settings
1. Check logs after scheduler runs
2. Look for: "Scraped N contracts for TICKER (M API calls)"
3. Verify M matches expected (2 + max_expirations)

---

## Troubleshooting

### "Settings not saving"
- Check browser console for errors
- Verify backend is running: `curl http://localhost:8000/health`
- Check backend logs for validation errors

### "Rate calculations show 0"
- Ensure watchlist has stocks: `curl http://localhost:8000/api/watchlist`
- Verify rate-calculation endpoint works: `curl http://localhost:8000/api/scheduler/rate-calculation`

### "Still hitting rate limits"
1. Pause scheduler immediately
2. Wait 24-48 hours for IP ban to clear
3. Reduce watchlist size or increase intervals
4. Verify green checkmarks before resuming

### "Scraper not using new settings"
- Settings apply on next scheduler cycle
- Restart backend to force reload: `python -m src.api.main`
- Check ScraperSchedule table has updated values:
  ```sql
  SELECT stock_delay_seconds, max_expirations FROM scraper_schedule;
  ```

---

## Files Modified

### Backend
- `backend/src/models/scraper_schedule.py` - Added columns
- `backend/src/models/schemas.py` - Added/updated schemas
- `backend/src/api/endpoints/scheduler.py` - Added rate-calculation endpoint
- `backend/src/services/scraper.py` - Read settings from DB
- `backend/src/services/scheduler.py` - Extended validation range
- `backend/migrations/add_rate_limit_settings.sql` - **NEW** Migration script

### Frontend
- `frontend/src/types/api.ts` - Added interfaces
- `frontend/src/services/api.ts` - Added getRateLimitCalculation()
- `frontend/src/components/SchedulerConfigPanel.tsx` - **NEW** Component
- `frontend/src/components/SchedulerConfigPanel.css` - **NEW** Styles
- `frontend/src/pages/AdminPage.tsx` - Integrated new component

---

## Summary

✅ **Database:** New columns for rate limit settings
✅ **Backend:** API endpoint for rate calculations
✅ **Frontend:** Editable configuration UI with real-time feedback
✅ **Documentation:** Comprehensive info modal with guidelines
✅ **Validation:** Input validation and warning system
✅ **Flexibility:** All settings now configurable without code changes

The scheduler is now fully configurable from the Admin UI with real-time rate limit calculations and warnings!
