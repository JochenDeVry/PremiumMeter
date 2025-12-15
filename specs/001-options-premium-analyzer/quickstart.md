# Quickstart Guide: Options Premium Analyzer

**Feature**: 001-options-premium-analyzer | **Last Updated**: 2025-12-15

## Overview

Options Premium Analyzer is a web application that helps options traders validate if their target premium prices are realistic by analyzing historical options data from Yahoo Finance. Query historical premium statistics, visualize trends with interactive 3D charts, and manage automated data collection.

**Key Features**:
- Query historical premium data by ticker, strike, and duration
- 3D interactive visualizations (Plotly.js)
- Automated daily scraping from Yahoo Finance
- Configurable scraper schedule with timezone support
- Admin watchlist management (54 stocks pre-configured)

## Prerequisites

- **Docker** 20.10+ and **Docker Compose** 2.0+ (recommended)
- OR **Python** 3.11+, **Node.js** 18+, **PostgreSQL** 15+ with TimescaleDB extension
- **Git** for cloning the repository
- **SSL Certificate** for HTTPS deployment (Let's Encrypt recommended)

## Quick Start (Docker Compose)

### 1. Clone Repository

```bash
git clone https://github.com/your-org/premium-meter.git
cd premium-meter
git checkout 001-options-premium-analyzer
```

### 2. Environment Configuration

Create `.env` file from template:

```bash
cp .env.example .env
```

Edit `.env` with your settings:

```bash
# Database
POSTGRES_USER=premiummeter
POSTGRES_PASSWORD=your_secure_password_here
POSTGRES_DB=premiummeter
POSTGRES_HOST=db
POSTGRES_PORT=5432

# Backend
API_HOST=0.0.0.0
API_PORT=8000
SECRET_KEY=your_secret_key_here_min_32_chars
ALLOWED_ORIGINS=https://premiummeter.com,http://localhost:3000

# Scraper
DEFAULT_SCRAPE_TIME=17:00:00
DEFAULT_TIMEZONE=America/New_York
RISK_FREE_RATE=0.045  # 4.5% for Black-Scholes Greeks calculation

# Frontend
REACT_APP_API_URL=https://premiummeter.com/api

# SSL (for production)
SSL_CERT_PATH=/etc/letsencrypt/live/premiummeter.com/fullchain.pem
SSL_KEY_PATH=/etc/letsencrypt/live/premiummeter.com/privkey.pem
```

### 3. Start Services

```bash
docker-compose up -d
```

This starts:
- **PostgreSQL** with TimescaleDB extension (port 5432)
- **Backend API** (FastAPI on port 8000)
- **Frontend** (React served by Nginx on port 443/80)

### 4. Initialize Database

Run migrations to create tables and seed initial 54-stock watchlist:

```bash
docker-compose exec backend alembic upgrade head
```

### 5. Verify Installation

Check service health:

```bash
# Backend API health
curl http://localhost:8000/health

# Database connection
docker-compose exec backend python -c "from src.database.connection import get_db; next(get_db())"

# Check watchlist seeded
docker-compose exec db psql -U premiummeter -d premiummeter -c "SELECT COUNT(*) FROM watchlist;"
# Should return: 54
```

### 6. Access Application

Open browser to:
- **Production**: https://premiummeter.com
- **Development**: http://localhost:3000

**MVP Note**: No login required (single-user mode). All features accessible immediately.

### 7. Trigger First Scrape (Optional)

Wait for scheduled scrape (default: 5:00 PM ET daily), or trigger manually:

```bash
docker-compose exec backend python -m src.services.scraper --run-now
```

Check scraper logs:

```bash
docker-compose logs -f backend | grep scraper
```

---

## Manual Installation (Without Docker)

### Backend Setup

#### 1. Install PostgreSQL + TimescaleDB

**Ubuntu/Debian**:
```bash
# Add TimescaleDB repo
sudo sh -c "echo 'deb https://packagecloud.io/timescale/timescaledb/ubuntu/ $(lsb_release -c -s) main' > /etc/apt/sources.list.d/timescaledb.list"
wget --quiet -O - https://packagecloud.io/timescale/timescaledb/gpgkey | sudo apt-key add -

# Install
sudo apt update
sudo apt install postgresql-15 postgresql-15-timescaledb

# Enable TimescaleDB
sudo timescaledb-tune --quiet --yes
sudo systemctl restart postgresql
```

**macOS**:
```bash
brew install postgresql@15 timescaledb
timescaledb-tune --quiet --yes
brew services start postgresql@15
```

#### 2. Create Database

```bash
sudo -u postgres psql -c "CREATE DATABASE premiummeter;"
sudo -u postgres psql -c "CREATE USER premiummeter WITH PASSWORD 'your_password';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE premiummeter TO premiummeter;"
sudo -u postgres psql -d premiummeter -c "CREATE EXTENSION IF NOT EXISTS timescaledb;"
```

#### 3. Install Python Dependencies

```bash
cd backend
python3.11 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
```

#### 4. Configure Environment

Create `backend/.env`:

```bash
DATABASE_URL=postgresql://premiummeter:your_password@localhost:5432/premiummeter
SECRET_KEY=your_secret_key_here_min_32_chars
ALLOWED_ORIGINS=http://localhost:3000
DEFAULT_SCRAPE_TIME=17:00:00
DEFAULT_TIMEZONE=America/New_York
RISK_FREE_RATE=0.045
```

#### 5. Run Migrations

```bash
cd backend
source venv/bin/activate
alembic upgrade head
```

#### 6. Start Backend Server

```bash
# Development
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

# Production
gunicorn src.api.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### Frontend Setup

#### 1. Install Node Dependencies

```bash
cd frontend
npm install
```

#### 2. Configure Environment

Create `frontend/.env`:

```bash
REACT_APP_API_URL=http://localhost:8000/api
```

#### 3. Start Development Server

```bash
npm start
# Opens http://localhost:3000
```

#### 4. Build for Production

```bash
npm run build
# Output in frontend/build/

# Serve with Nginx
sudo cp -r build/* /var/www/premium-meter/
```

---

## Usage Examples

### Query Historical Premium Data

**Via Web UI**:
1. Navigate to Home page
2. Select stock: **META**
3. Option type: **Put**
4. Strike price: **635.00**
5. Strike mode: **Exact**
6. Duration: **14 days**
7. Click **Query**

**Via API (curl)**:

```bash
curl -X POST http://localhost:8000/api/query/premium \
  -H "Content-Type: application/json" \
  -d '{
    "ticker": "META",
    "option_type": "put",
    "strike_mode": "exact",
    "strike_price": 635.00,
    "duration_days": 14,
    "lookback_days": 90
  }'
```

**Response**:
```json
{
  "ticker": "META",
  "option_type": "put",
  "query_timestamp": "2025-12-15T18:30:00Z",
  "results": [
    {
      "strike_price": 635.00,
      "duration_days": 14,
      "data_points": 45,
      "min_premium": 8.50,
      "max_premium": 12.75,
      "avg_premium": 10.20,
      "latest_premium": 11.00,
      "greeks_avg": {
        "delta": -0.35,
        "gamma": 0.008,
        "theta": -0.15,
        "vega": 0.22
      }
    }
  ]
}
```

### Visualize Premium Trends (3D Chart)

**Via Web UI**:
1. After querying data, switch to **3D Visualization** tab
2. Rotate chart with mouse drag
3. Zoom with scroll wheel
4. Hover over surface for exact values

**Via API**:

```bash
curl -X POST http://localhost:8000/api/query/chart-data \
  -H "Content-Type: application/json" \
  -d '{
    "ticker": "TSLA",
    "option_type": "call",
    "chart_type": "surface_3d",
    "strike_min": 850,
    "strike_max": 950,
    "duration_min_days": 7,
    "duration_max_days": 30,
    "lookback_days": 90
  }'
```

### Manage Watchlist

**Add Stock**:

```bash
curl -X POST http://localhost:8000/api/watchlist \
  -H "Content-Type: application/json" \
  -d '{"ticker": "AAPL"}'
```

**Remove Stock**:

```bash
curl -X DELETE http://localhost:8000/api/watchlist/TSLA
```

**View Watchlist**:

```bash
curl http://localhost:8000/api/watchlist
```

### Configure Scraper Schedule

**Get Current Config**:

```bash
curl http://localhost:8000/api/scheduler/config
```

**Update Scrape Time**:

```bash
curl -X PUT http://localhost:8000/api/scheduler/config \
  -H "Content-Type: application/json" \
  -d '{
    "scrape_time": "16:30:00",
    "timezone": "America/New_York",
    "excluded_days": ["saturday", "sunday", "2025-12-25"]
  }'
```

**Pause Scraper**:

```bash
curl -X POST http://localhost:8000/api/scheduler/pause
```

**Resume Scraper**:

```bash
curl -X POST http://localhost:8000/api/scheduler/resume
```

---

## Production Deployment

### HTTPS Setup with Let's Encrypt

#### 1. Install Certbot

```bash
sudo apt install certbot python3-certbot-nginx
```

#### 2. Obtain SSL Certificate

```bash
sudo certbot --nginx -d premiummeter.com -d www.premiummeter.com
```

#### 3. Configure Nginx

Edit `/etc/nginx/sites-available/premium-meter`:

```nginx
server {
    listen 443 ssl http2;
    server_name premiummeter.com;
    
    ssl_certificate /etc/letsencrypt/live/premiummeter.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/premiummeter.com/privkey.pem;
    
    # Frontend static files
    location / {
        root /var/www/premium-meter;
        try_files $uri /index.html;
    }
    
    # Backend API proxy
    location /api/ {
        proxy_pass http://localhost:8000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name premiummeter.com www.premiummeter.com;
    return 301 https://$server_name$request_uri;
}
```

#### 4. Enable Site

```bash
sudo ln -s /etc/nginx/sites-available/premium-meter /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

#### 5. Auto-Renewal

Certbot sets up auto-renewal cron job automatically. Verify:

```bash
sudo certbot renew --dry-run
```

### Systemd Services (Background Processes)

#### Backend API Service

Create `/etc/systemd/system/premium-meter-api.service`:

```ini
[Unit]
Description=Premium Meter FastAPI Backend
After=network.target postgresql.service

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=/var/www/premium-meter/backend
Environment="PATH=/var/www/premium-meter/backend/venv/bin"
EnvironmentFile=/var/www/premium-meter/backend/.env
ExecStart=/var/www/premium-meter/backend/venv/bin/gunicorn src.api.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl enable premium-meter-api
sudo systemctl start premium-meter-api
sudo systemctl status premium-meter-api
```

---

## Monitoring & Maintenance

### Health Checks

**Backend API**:
```bash
curl http://localhost:8000/health
# Expected: {"status": "healthy", "database": "connected", "scraper": "idle"}
```

**Database**:
```bash
docker-compose exec db psql -U premiummeter -d premiummeter -c "SELECT version();"
```

**Scraper Status**:
```bash
curl http://localhost:8000/api/scheduler/config | jq '.status'
# Expected: "idle" (between scrapes) or "running" (during scrape)
```

### Log Locations

**Docker**:
```bash
# Backend logs
docker-compose logs -f backend

# Database logs
docker-compose logs -f db

# Nginx logs
docker-compose logs -f nginx
```

**Manual Installation**:
```bash
# Backend logs (if using systemd)
journalctl -u premium-meter-api -f

# Nginx access logs
tail -f /var/log/nginx/access.log

# PostgreSQL logs
tail -f /var/log/postgresql/postgresql-15-main.log
```

### Database Maintenance

**Vacuum & Analyze** (weekly recommended):
```bash
docker-compose exec db psql -U premiummeter -d premiummeter -c "VACUUM ANALYZE;"
```

**Check TimescaleDB Compression** (monthly):
```bash
docker-compose exec db psql -U premiummeter -d premiummeter -c "SELECT * FROM timescaledb_information.compression_settings;"
```

**Backup Database**:
```bash
# Full dump
docker-compose exec db pg_dump -U premiummeter premiummeter > backup_$(date +%Y%m%d).sql

# Restore
docker-compose exec -T db psql -U premiummeter -d premiummeter < backup_20251215.sql
```

---

## Troubleshooting

### Scraper Not Running

**Check scheduler status**:
```bash
curl http://localhost:8000/api/scheduler/config
```

If `enabled: false`, resume:
```bash
curl -X POST http://localhost:8000/api/scheduler/resume
```

**Check logs for errors**:
```bash
docker-compose logs backend | grep -i "scraper\|error"
```

**Common issues**:
- **Yahoo Finance rate limiting**: Scraper implements exponential backoff; wait and retry
- **Invalid ticker in watchlist**: Remove invalid tickers via API or database
- **Timezone misconfiguration**: Verify timezone name in scheduler config

### No Historical Data for Query

**Possible causes**:
1. **Scraper hasn't run yet**: Trigger manual scrape or wait for scheduled time
2. **Stock not in watchlist**: Add to watchlist via API
3. **Lookback period too short**: Increase `lookback_days` in query
4. **Strike price never existed**: Use `percentage_range` or `nearest` strike mode

**Verify data exists**:
```bash
docker-compose exec db psql -U premiummeter -d premiummeter -c "SELECT COUNT(*) FROM historical_premium_records WHERE stock_id = (SELECT id FROM stock WHERE ticker='META');"
```

### Chart Not Rendering

**Check browser console** for JavaScript errors.

**Common fixes**:
- Clear browser cache (Plotly.js may be cached incorrectly)
- Verify API response contains `premium_grid` data
- Check network tab for CORS errors (verify `ALLOWED_ORIGINS` in backend .env)

### Database Connection Errors

**Check PostgreSQL running**:
```bash
docker-compose ps db
# OR
sudo systemctl status postgresql
```

**Test connection**:
```bash
docker-compose exec backend python -c "from src.database.connection import engine; print(engine.connect())"
```

**Verify credentials** in `.env` match PostgreSQL user/password.

---

## Performance Tuning

### Database Indexing

Most critical indexes created automatically via migrations. Verify:

```bash
docker-compose exec db psql -U premiummeter -d premiummeter -c "\di"
```

Expected indexes:
- `idx_stock_status`
- `idx_hpr_stock_id`
- `idx_hpr_query_pattern` (composite: stock_id, option_type, strike_price, expiration_date)
- `idx_watchlist_status`

### Query Optimization

For slow queries (>3s), use continuous aggregate view instead of raw table:

```sql
-- Use pre-computed daily summary
SELECT * FROM daily_premium_summary
WHERE stock_id = (SELECT id FROM stock WHERE ticker = 'META')
  AND day >= NOW() - INTERVAL '90 days';
```

### Frontend Caching

Enable service worker for offline support and asset caching (future enhancement).

---

## Next Steps

### Phase 2: Multi-User Authentication

When ready to add user authentication:

1. Run migration to create `users` and `role` tables
2. Uncomment authentication middleware in `src/api/dependencies.py`
3. Update frontend to check `user.role` for conditional rendering
4. Add login page routing

See `data-model.md` Phase 2 section for schema details.

### Data Backfilling

To import historical data before first scrape:

```bash
docker-compose exec backend python -m src.services.scraper --backfill --days=30
```

This scrapes last 30 days of data for all watchlist stocks (may take hours depending on stock count).

### Additional Features

- **Export to CSV**: Add endpoint to export query results
- **Email alerts**: Notify when premium crosses thresholds
- **Mobile app**: React Native wrapper for mobile access
- **Advanced analytics**: Implied volatility surface modeling

---

## Support & Resources

- **API Documentation**: https://premiummeter.com/api/docs (Swagger UI auto-generated)
- **OpenAPI Spec**: See `specs/001-options-premium-analyzer/contracts/openapi.yaml`
- **Data Model**: See `specs/001-options-premium-analyzer/data-model.md`
- **Research Decisions**: See `specs/001-options-premium-analyzer/research.md`

**Getting Help**:
- File issues on GitHub: https://github.com/your-org/premium-meter/issues
- Check logs first (see Monitoring section above)
- Include error messages and relevant config when reporting bugs
