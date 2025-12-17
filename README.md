# Options Premium Analyzer

Web application for analyzing stock options premium pricing with historical data visualization and intra-day data collection from Yahoo Finance.

## Overview

Options Premium Analyzer helps options traders validate if their target premium prices are realistic by analyzing historical options data. The system automatically polls Yahoo Finance at configurable intervals (default: every 5 minutes during market hours) to collect options contract data with current stock prices, storing time-series data for comprehensive analysis.

### Key Features

- **Query Historical Premium Data**: Search by ticker, strike price, and contract duration to see historical min/max/avg premiums
- **Interactive 3D Visualizations**: Explore premium patterns across strike prices, durations, and time with Plotly.js charts
- **Automated Intra-Day Polling**: Configurable data collection (1-60 minute intervals) during market hours with stock price capture
- **Watchlist Management**: Customize which stocks to monitor (54 stocks pre-configured)
- **Flexible Scheduler**: Configure polling frequency, market hours, timezone, pause/resume controls

## Quick Start

**Full documentation**: See [quickstart.md](./specs/001-options-premium-analyzer/quickstart.md) for detailed setup instructions.

### Prerequisites

- Docker 20.10+ and Docker Compose 2.0+
- OR: Python 3.11+, Node.js 18+, PostgreSQL 15+ with TimescaleDB

### Installation (Docker)

```bash
# Clone repository
git clone https://github.com/your-org/premium-meter.git
cd premium-meter
git checkout 001-options-premium-analyzer

# Configure environment
cp .env.example .env
# Edit .env with your settings (database password, secret key, etc.)

# Start services
docker-compose up -d

# Initialize database
docker-compose exec backend alembic upgrade head

# Verify installation
curl http://localhost:8000/health
```

### Usage

- **Frontend**: Open http://localhost:3000 in your browser
- **API Documentation**: http://localhost:8000/docs (OpenAPI/Swagger UI)
- **Admin Panel**: Configure scraper schedule, manage watchlist

## Architecture

- **Backend**: FastAPI (Python 3.11+) with async API endpoints
- **Frontend**: React + TypeScript with Plotly.js for 3D charts
- **Database**: PostgreSQL 15+ with TimescaleDB extension for time-series optimization
- **Scraper**: yfinance library for Yahoo Finance data, APScheduler for interval-based polling
- **Deployment**: Docker Compose (development), HTTPS/SSL (production)

## Project Structure

```
premium-meter/
├── backend/
│   ├── src/
│   │   ├── api/           # FastAPI endpoints
│   │   ├── models/        # SQLAlchemy models, Pydantic schemas
│   │   ├── services/      # Business logic (scraper, scheduler, Greeks calculator)
│   │   ├── database/      # Database connection, migrations
│   │   └── config.py      # Environment configuration
│   ├── tests/            # pytest tests
│   └── requirements.txt  # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── components/    # React components (QueryForm, ChartViewer, etc.)
│   │   ├── pages/         # Home, Admin pages
│   │   ├── services/      # API client
│   │   └── types/         # TypeScript type definitions
│   ├── tests/            # Jest + React Testing Library tests
│   └── package.json      # Node.js dependencies
├── specs/                # Feature specification and design documents
├── docker-compose.yml    # Service orchestration
└── .env.example          # Environment variable template
```

## Development

```bash
# Install backend dependencies
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Install frontend dependencies
cd frontend
npm install

# Run database migrations
cd backend
alembic upgrade head

# Start backend (development mode with auto-reload)
uvicorn src.api.main:app --reload

# Start frontend (separate terminal)
cd frontend
npm run dev
```

## Testing

```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
npm test

# Coverage reports
pytest --cov=src --cov-report=html  # Backend
npm run test:coverage                # Frontend
```

## Configuration

### Scraper Schedule

Default: Poll every 5 minutes during market hours (9:30 AM - 4:00 PM ET)

Configure via Admin UI or environment variables:
- `POLLING_INTERVAL_MINUTES`: 1-60 minutes (default: 5)
- `MARKET_HOURS_START`: HH:MM:SS format (default: 09:30:00)
- `MARKET_HOURS_END`: HH:MM:SS format (default: 16:00:00)
- `DEFAULT_TIMEZONE`: pytz timezone (default: America/New_York)

### Initial Watchlist

54 pre-configured stocks (AAPL, META, NVDA, TSLA, etc.). Customize via Admin UI after installation.

## License

MIT License - see LICENSE file for details

## Contributing

See CONTRIBUTING.md for development guidelines

## Support

- **Documentation**: [specs/001-options-premium-analyzer/](./specs/001-options-premium-analyzer/)
- **Issues**: GitHub Issues
- **Discussions**: GitHub Discussions
