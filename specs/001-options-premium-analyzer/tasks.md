# Tasks: Options Premium Analyzer

**Input**: Design documents from `/specs/001-options-premium-analyzer/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/openapi.yaml, quickstart.md

**Tests**: Tests will be implemented during `/speckit.implement` phase per SpecKit methodology.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `- [ ] [TaskID] [P?] [Story?] Description with file path`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4, US5)
- Include exact file paths in descriptions

## Path Conventions

Based on plan.md Project Structure:
- **Backend**: `backend/src/`, `backend/tests/`
- **Frontend**: `frontend/src/`, `frontend/tests/`
- **Database**: `backend/src/database/migrations/`
- **Deployment**: Repository root (`docker-compose.yml`, `.env.example`)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [ ] T001 Create backend directory structure per plan.md (api/, models/, services/, database/, config.py)
- [ ] T002 Create frontend directory structure per plan.md (components/, pages/, services/, types/)
- [ ] T003 [P] Initialize Python backend with FastAPI, SQLAlchemy, Pydantic, yfinance, APScheduler dependencies in backend/requirements.txt
- [ ] T004 [P] Initialize React frontend with TypeScript, Plotly.js, axios, react-router dependencies in frontend/package.json
- [ ] T005 [P] Create Docker Compose configuration in docker-compose.yml (PostgreSQL with TimescaleDB, backend, frontend services)
- [ ] T006 [P] Create environment variables template in .env.example per quickstart.md (database URL, API host, scraper schedule defaults)
- [ ] T007 [P] Setup pytest configuration in backend/tests/conftest.py
- [ ] T008 [P] Setup Jest configuration in frontend/tests/jest.config.js
- [ ] T009 Create README.md with project overview and link to quickstart.md

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T010 Setup PostgreSQL + TimescaleDB connection in backend/src/database/connection.py
- [ ] T011 Setup Alembic migrations framework in backend/src/database/migrations/
- [ ] T012 [P] Create SQLAlchemy base models configuration in backend/src/models/__init__.py
- [ ] T013 [P] Create Pydantic base schemas configuration in backend/src/models/schemas.py
- [ ] T014 [P] Setup FastAPI application initialization in backend/src/api/main.py with CORS, error handling, logging
- [ ] T015 [P] Create configuration management in backend/src/config.py (environment variables, database URLs, scraper settings)
- [ ] T016 Create Migration 001: Core tables schema (Stock, HistoricalPremiumRecord, Watchlist, ScraperSchedule) per data-model.md in backend/src/database/migrations/versions/001_core_schema.py
- [ ] T017 Create Migration 002: TimescaleDB hypertable setup for HistoricalPremiumRecord partitioned by collection_timestamp in backend/src/database/migrations/versions/002_timescaledb_hypertable.py
- [ ] T018 Create Migration 003: Seed 54-stock watchlist per spec.md table in backend/src/database/migrations/versions/003_seed_watchlist.py
- [ ] T019 Create Migration 004: Continuous aggregates for daily premium summaries per data-model.md in backend/src/database/migrations/versions/004_continuous_aggregates.py
- [ ] T020 Create Migration 005: Phase 2 User and Role entities (not activated for MVP) in backend/src/database/migrations/versions/005_phase2_user_role.py
- [ ] T021 [P] Setup API routing structure in backend/src/api/dependencies.py (database session dependency injection)
- [ ] T022 [P] Setup React Router in frontend/src/App.tsx with routes for Home and Admin pages
- [ ] T023 [P] Create TypeScript type definitions from OpenAPI schemas in frontend/src/types/models.ts
- [ ] T024 [P] Create backend API client service in frontend/src/services/api.ts with axios configuration

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 4 - Automated Real-Time Data Collection (Priority: P1) 🎯 MVP Foundation

**Goal**: Build the historical database by automatically scraping Yahoo Finance daily for options contract data

**Independent Test**: Initialize system with test watchlist, wait for scraper cycle, verify database contains HistoricalPremiumRecord rows with all attributes populated

### Implementation for User Story 4

- [ ] T025 [P] [US4] Create Stock model in backend/src/models/domain.py with attributes per data-model.md (ticker, company_name, current_price, status, date_added)
- [ ] T026 [P] [US4] Create HistoricalPremiumRecord model in backend/src/models/domain.py with TimescaleDB hypertable attributes per data-model.md (stock_id, option_type, strike_price, premium, stock_price_at_collection, expiration_date, collection_timestamp, Greeks, volume, open_interest, contract_status)
- [ ] T027 [P] [US4] Create Watchlist model in backend/src/models/domain.py (stock_id, monitoring_status, date_added, date_removed)
- [ ] T028 [P] [US4] Create ScraperSchedule model in backend/src/models/domain.py (polling_interval_minutes, market_hours_start, market_hours_end, timezone, enabled, excluded_days, last_run, next_run, status)
- [ ] T029 [US4] Implement Black-Scholes Greeks calculator in backend/src/services/greeks.py using scipy.stats per research.md (inputs: stock_price, strike, time_to_expiry, risk_free_rate, implied_volatility)
- [ ] T030 [US4] Implement Yahoo Finance scraper service in backend/src/services/scraper.py using yfinance per research.md (fetch options chains, extract all strikes, capture current stock price, map to HistoricalPremiumRecord with stock_price_at_collection, call greeks.py for missing Greeks)
- [ ] T031 [US4] Implement scraper error handling and retry logic in backend/src/services/scraper.py (log failures, mark stocks as failed, continue with remaining stocks per FR-014)
- [ ] T032 [US4] Implement APScheduler integration in backend/src/services/scheduler.py per research.md (IntervalTrigger with polling_interval_minutes from database, market hours window checking, pytz timezone support, job persistence, pause/resume capabilities)
- [ ] T033 [US4] Create expired contract marking job in backend/src/services/scraper.py (scheduled task to update contract_status='expired' for contracts past expiration_date)
- [ ] T034 [US4] Initialize scheduler on backend startup in backend/src/api/main.py (load ScraperSchedule configuration from database, register scraper job with APScheduler)
- [ ] T034.5 [US4] Add concurrency protection to scraper in backend/src/services/scheduler.py (set APScheduler max_instances=1 to prevent concurrent executions, or implement application-level mutex lock)
- [ ] T035 [US4] Add scraper execution logging in backend/src/services/scraper.py (log start/end times, success/failure counts, stock-level errors per SC-008, contracts-per-stock metric for SC-007 validation)

**Checkpoint**: At this point, scraper should poll on configured interval during market hours, populate HistoricalPremiumRecord table with 54 stocks' options data including current stock prices

---

## Phase 4: User Story 1 - Query Historical Premium Data (Priority: P1) 🎯 MVP Core

**Goal**: Enable users to query historical premium statistics by ticker, strike price, and duration to validate target premiums

**Independent Test**: Select META, enter strike $635, select 2-week duration, select Put, verify historical min/max/avg premiums are displayed

### Implementation for User Story 1

- [ ] T036 [P] [US1] Create PremiumQueryRequest Pydantic schema in backend/src/models/schemas.py per contracts/openapi.yaml (ticker, option_type, strike_mode, strike_price, duration_days, lookback_days, strike_range_percent, nearest_count_above, nearest_count_below)
- [ ] T037 [P] [US1] Create PremiumQueryResponse Pydantic schema in backend/src/models/schemas.py per contracts/openapi.yaml (ticker, option_type, results array with strike_price, min/max/avg premium, Greeks averages, data_points count)
- [ ] T038 [US1] Implement query service in backend/src/services/query_service.py with exact strike matching logic (SQLAlchemy query: WHERE strike_price = target)
- [ ] T039 [US1] Implement percentage range strike matching in backend/src/services/query_service.py (WHERE strike_price BETWEEN target*(1-pct) AND target*(1+pct))
- [ ] T040 [US1] Implement nearest strikes matching in backend/src/services/query_service.py (subquery UNION approach: N strikes above + N strikes below per data-model.md query patterns)
- [ ] T041 [US1] Implement duration matching in backend/src/services/query_service.py (WHERE (expiration_date - collection_timestamp) matches target duration_days)
- [ ] T042 [US1] Implement premium aggregation in backend/src/services/query_service.py (GROUP BY strike_price, calculate MIN/MAX/AVG premium, AVG Greeks)
- [ ] T043 [US1] Create POST /api/query/premium endpoint in backend/src/api/endpoints/query.py per contracts/openapi.yaml (validate request schema, call query_service, return response schema)
- [ ] T044 [US1] Add input validation and error handling in backend/src/api/endpoints/query.py (validate ticker exists, strike_price positive, handle no data found with 404 per FR-009)
- [ ] T045 [US1] Implement QueryForm React component in frontend/src/components/QueryForm.tsx (ticker dropdown, option type radio, strike price input with three matching modes, duration input, submit button)
- [ ] T046 [US1] Implement premium results display component in frontend/src/components/PremiumResults.tsx (table showing strikes, min/max/avg premiums, Greeks, data points count)
- [ ] T047 [US1] Create Home page in frontend/src/pages/Home.tsx integrating QueryForm and PremiumResults components
- [ ] T048 [US1] Add API integration in frontend/src/components/QueryForm.tsx calling POST /api/query/premium via api.ts service

**Checkpoint**: At this point, User Story 1 should be fully functional - users can query and view historical premium statistics

---

## Phase 5: User Story 2 - Visualize Premium Trends with Interactive Charts (Priority: P2)

**Goal**: Provide 3D and 2D interactive visualizations of premium data across strike prices, durations, and time

**Independent Test**: Query any stock, switch between 3D surface plot (strike × duration × premium), 2D time-series (date × premium), and heatmap views, verify charts render within 2 seconds and support rotation/hover interactions

### Implementation for User Story 2

- [ ] T049 [P] [US2] Create ChartDataRequest Pydantic schema in backend/src/models/schemas.py per contracts/openapi.yaml (ticker, option_type, strike_range, duration_range, lookback_days)
- [ ] T050 [P] [US2] Create ChartDataResponse Pydantic schema in backend/src/models/schemas.py per contracts/openapi.yaml (strike_prices array, durations_days array, premium_grid 2D array, timestamps array)
- [ ] T051 [US2] Implement chart data query service in backend/src/services/query_service.py (fetch premium data across strike/duration ranges, format as grid for Plotly.js)
- [ ] T052 [US2] Create POST /api/query/chart-data endpoint in backend/src/api/endpoints/query.py per contracts/openapi.yaml (validate request, call query service, return grid data)
- [ ] T053 [US2] Implement 3D surface chart component in frontend/src/components/ChartViewer.tsx using react-plotly.js per research.md (strike price X-axis, duration Y-axis, premium Z-axis, rotation controls)
- [ ] T054 [US2] Implement 2D time-series chart component in frontend/src/components/ChartViewer.tsx (date X-axis, premium Y-axis, line plot for selected strike/duration)
- [ ] T055 [US2] Implement heatmap chart component in frontend/src/components/ChartViewer.tsx (strike × duration grid with premium color intensity)
- [ ] T056 [US2] Add chart type selector in frontend/src/components/ChartViewer.tsx (radio buttons: 3D Surface, 2D Time-Series, Heatmap)
- [ ] T057 [US2] Add hover tooltips in frontend/src/components/ChartViewer.tsx showing exact premium, date, strike, duration per FR-013
- [ ] T058 [US2] Integrate ChartViewer into Home page in frontend/src/pages/Home.tsx (display below query results, populate from same query data)
- [ ] T059 [US2] Add chart performance optimization in frontend/src/components/ChartViewer.tsx (debouncing, data point limiting to meet SC-005 <2s rendering)

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently - query + visualize premium data

---

## Phase 6: User Story 3 - Manage Stock Watchlist for Data Collection (Priority: P3)

**Goal**: Allow administrators to add/remove stocks from monitored watchlist to customize data collection

**Independent Test**: Add AAPL to watchlist via admin UI, verify next scraper cycle collects AAPL data; remove TSLA, verify scraper stops collecting new TSLA data while retaining historical records

### Implementation for User Story 3

- [ ] T060 [P] [US3] Create WatchlistResponse Pydantic schema in backend/src/models/schemas.py per contracts/openapi.yaml (stocks array with ticker, company_name, monitoring_status, date_added)
- [ ] T061 [P] [US3] Create WatchlistAddRequest Pydantic schema in backend/src/models/schemas.py (ticker, validate with yfinance per FR-011)
- [ ] T062 [US3] Implement watchlist service in backend/src/services/watchlist_service.py (add stock with yfinance validation, remove stock with soft delete, get active watchlist)
- [ ] T063 [US3] Create GET /api/watchlist endpoint in backend/src/api/endpoints/watchlist.py per contracts/openapi.yaml (return active stocks in watchlist)
- [ ] T064 [US3] Create POST /api/watchlist endpoint in backend/src/api/endpoints/watchlist.py (validate ticker via yfinance, add to watchlist, return updated list)
- [ ] T065 [US3] Create DELETE /api/watchlist/{ticker} endpoint in backend/src/api/endpoints/watchlist.py (soft delete: set date_removed, update monitoring_status='inactive', keep historical data per FR-012)
- [ ] T066 [US3] Add invalid ticker validation in backend/src/api/endpoints/watchlist.py (return 400 error for non-existent tickers per acceptance scenario 4)
- [ ] T067 [US3] Implement WatchlistManager React component in frontend/src/components/WatchlistManager.tsx (display active stocks table, add ticker input form, remove button per stock)
- [ ] T068 [US3] Create Admin page in frontend/src/pages/Admin.tsx with WatchlistManager component
- [ ] T069 [US3] Add API integration in frontend/src/components/WatchlistManager.tsx (GET watchlist on load, POST to add, DELETE to remove via api.ts)
- [ ] T070 [US3] Update scraper service in backend/src/services/scraper.py to read active watchlist from database (filter by monitoring_status='active')

**Checkpoint**: At this point, User Stories 1, 2, AND 3 should all work independently - query, visualize, manage watchlist

---

## Phase 7: User Story 5 - Configure Scraper Schedule (Priority: P2)

**Goal**: Provide admin interface to configure scraper schedule with timezone awareness, pause/resume, and day exclusions

**Independent Test**: Configure scrape time to 5:00 PM ET via admin UI, pause scraper, verify no scrapes occur, resume scraper, exclude weekends, verify scraper skips Saturday/Sunday

### Implementation for User Story 5

- [ ] T071 [P] [US5] Create SchedulerConfigResponse Pydantic schema in backend/src/models/schemas.py per contracts/openapi.yaml (polling_interval_minutes, market_hours_start, market_hours_end, timezone, enabled, excluded_days, last_run, next_run, status)
- [ ] T072 [P] [US5] Create SchedulerConfigUpdateRequest Pydantic schema in backend/src/models/schemas.py (polling_interval_minutes, market_hours_start, market_hours_end, timezone, excluded_days array)
- [ ] T073 [US5] Implement scheduler configuration service in backend/src/services/scheduler.py (get config from ScraperSchedule table, update polling_interval_minutes/market_hours/timezone, reschedule APScheduler IntervalTrigger without restart per FR-020, validate interval 1-60 minutes, validate market hours start < end)
- [ ] T074 [US5] Create GET /api/scheduler/config endpoint in backend/src/api/endpoints/scheduler.py per contracts/openapi.yaml (return current schedule configuration)
- [ ] T075 [US5] Create PUT /api/scheduler/config endpoint in backend/src/api/endpoints/scheduler.py (validate timezone with pytz, validate polling_interval 1-60 minutes, validate market_hours_start < market_hours_end, update schedule, reschedule APScheduler IntervalTrigger)
- [ ] T076 [US5] Create POST /api/scheduler/pause endpoint in backend/src/api/endpoints/scheduler.py (set enabled=false, pause APScheduler job per FR-017)
- [ ] T077 [US5] Create POST /api/scheduler/resume endpoint in backend/src/api/endpoints/scheduler.py (set enabled=true, resume APScheduler job)
- [ ] T078 [US5] Add timezone validation in backend/src/api/endpoints/scheduler.py (validate against pytz.all_timezones, return 400 for invalid timezones)
- [ ] T079 [US5] Add market hours and excluded days checking in backend/src/services/scheduler.py polling job (before execution: verify current time within market_hours_start to market_hours_end, skip if current date in excluded_days per FR-018, skip if outside market hours per FR-019)
- [ ] T080 [US5] Implement SchedulerConfig React component in frontend/src/components/SchedulerConfig.tsx (polling interval slider 1-60 minutes, market hours start/end time pickers, timezone selector, excluded days checkboxes, pause/resume buttons, last run / next run display, polling frequency impact estimate)
- [ ] T081 [US5] Integrate SchedulerConfig into Admin page in frontend/src/pages/Admin.tsx (below WatchlistManager)
- [ ] T082 [US5] Add API integration in frontend/src/components/SchedulerConfig.tsx (GET config on load, PUT to update, POST to pause/resume via api.ts)
- [ ] T083 [US5] Add market hours and DST handling validation in backend/src/services/scheduler.py (verify polling only occurs within market_hours_start to market_hours_end window per FR-019, verify pytz automatically adjusts for DST transitions per acceptance scenario 1)

**Checkpoint**: At this point, all P1 and P2 user stories should be complete and independently functional

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T084 [P] Add HTTPS deployment configuration in docker-compose.yml and nginx configuration per quickstart.md (SSL certificate paths, reverse proxy, static file serving)
- [ ] T085 [P] Add input validation and SQL injection prevention across all API endpoints per FR-023 (Pydantic validation, SQLAlchemy parameterized queries)
- [ ] T086 [P] Add XSS prevention in API responses per FR-023 (sanitize error messages, validate JSON responses)
- [ ] T087 [P] Create health check endpoint GET /api/health in backend/src/api/main.py (check database connection, return status per quickstart.md monitoring)
- [ ] T088 [P] Create stock information endpoint GET /api/stocks in backend/src/api/endpoints/stocks.py per contracts/openapi.yaml (return all stocks with current prices)
- [ ] T089 [P] Create single stock endpoint GET /api/stocks/{ticker} in backend/src/api/endpoints/stocks.py (return stock details including options count)
- [ ] T090 [P] Add comprehensive error logging in backend/src/services/scraper.py (log all scraping errors with stock ticker, timestamp, error message per SC-008)
- [ ] T091 [P] Add performance monitoring for query service in backend/src/services/query_service.py (log query execution times to verify SC-001 <3s target)
- [ ] T092 [P] Add performance monitoring for chart rendering in frontend/src/components/ChartViewer.tsx (log render times to verify SC-005 <2s target)
- [ ] T093 [P] Optimize database queries in backend/src/services/query_service.py (verify indexes used, add EXPLAIN ANALYZE logging for slow queries)
- [ ] T094 [P] Add database compression policy configuration per data-model.md (compress HistoricalPremiumRecord data older than 90 days)
- [ ] T095 [P] Create system documentation in docs/ directory (architecture overview, API usage examples, deployment guide references to quickstart.md)
- [ ] T096 [P] Add frontend loading states in all components (spinners during API calls, disabled buttons during submission)
- [ ] T097 [P] Add frontend error handling in all components (display user-friendly error messages from API, toast notifications)
- [ ] T098 [P] Verify quickstart.md accuracy by following Docker Compose quick start steps (validate all commands work, environment variables match code)
- [ ] T099 Create production deployment checklist (HTTPS certificate setup, environment variable security, database backup configuration)
- [ ] T100 Run end-to-end validation across all user stories (verify independent functionality, test story integration points, validate success criteria SC-001 through SC-008)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Story 4 (Phase 3, P1)**: Depends on Foundational - MUST complete first to build historical database
- **User Story 1 (Phase 4, P1)**: Depends on Foundational + User Story 4 (needs historical data to query)
- **User Story 2 (Phase 5, P2)**: Depends on Foundational + User Story 4 (needs historical data to visualize)
- **User Story 3 (Phase 6, P3)**: Depends on Foundational + User Story 4 (modifies scraper data sources)
- **User Story 5 (Phase 7, P2)**: Depends on Foundational + User Story 4 (configures existing scraper)
- **Polish (Phase 8)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 4 (P1) - Automated Scraping**: Foundation for all other stories - MUST complete first to build historical database
- **User Story 1 (P1) - Query Premium**: Depends on US4 (needs historical data) - Core MVP value
- **User Story 2 (P2) - Visualize Charts**: Depends on US4 (needs historical data) - Enhances US1, can be implemented in parallel with US1
- **User Story 3 (P3) - Manage Watchlist**: Depends on US4 (modifies scraper input) - Admin feature, can be implemented in parallel with US1/US2
- **User Story 5 (P2) - Configure Scheduler**: Depends on US4 (configures scraper) - Admin feature, can be implemented in parallel with US1/US2/US3

### Within Each User Story

- **User Story 4**: Models → Greeks calculator → Scraper service → Scheduler integration → Startup initialization
- **User Story 1**: Schemas → Query service (exact → range → nearest) → API endpoint → Frontend form → Frontend results
- **User Story 2**: Schemas → Chart data service → API endpoint → Chart components (3D → 2D → Heatmap) → Integration
- **User Story 3**: Schemas → Watchlist service → API endpoints (GET/POST/DELETE) → Frontend manager → Scraper integration
- **User Story 5**: Schemas → Scheduler service → API endpoints (GET/PUT/Pause/Resume) → Frontend config → DST validation

### Parallel Opportunities

**Within Setup (Phase 1)**:
- T003 (Backend init), T004 (Frontend init), T005 (Docker), T006 (.env), T007 (pytest), T008 (Jest) can all run in parallel

**Within Foundational (Phase 2)**:
- T012 (SQLAlchemy), T013 (Pydantic), T014 (FastAPI), T015 (Config) can run in parallel
- T021 (API routing), T022 (React Router), T023 (TypeScript types), T024 (API client) can run in parallel after migrations complete

**Within User Story 4**:
- T025, T026, T027, T028 (all models) can run in parallel
- T035 (logging) can run in parallel with other tasks (different files)

**Within User Story 1**:
- T036, T037 (schemas) can run in parallel
- T045 (QueryForm), T046 (PremiumResults) can run in parallel (different components)

**Within User Story 2**:
- T049, T050 (schemas) can run in parallel
- T053, T054, T055 (chart components) can run in parallel (different chart types)

**Within User Story 3**:
- T060, T061 (schemas) can run in parallel
- T063, T064, T065, T066 (API endpoints) can run in parallel after service complete

**Within User Story 5**:
- T071, T072 (schemas) can run in parallel
- T074, T075, T076, T077, T078 (API endpoints) can run in parallel after service complete

**Within Polish (Phase 8)**:
- Most tasks marked [P] can run in parallel (T084-T097) as they touch different files

**Across User Stories (after US4 complete)**:
- User Story 1 (Phase 4) and User Story 2 (Phase 5) can run in parallel with different developers
- User Story 3 (Phase 6) and User Story 5 (Phase 7) can run in parallel with different developers
- All P2/P3 stories can run in parallel if team capacity allows (US2, US3, US5 are independent)

---

## Parallel Example: User Story 4 (Scraper Foundation)

```bash
# Launch all model creation tasks together:
Task T025: "Create Stock model in backend/src/models/domain.py"
Task T026: "Create HistoricalPremiumRecord model in backend/src/models/domain.py"
Task T027: "Create Watchlist model in backend/src/models/domain.py"
Task T028: "Create ScraperSchedule model in backend/src/models/domain.py"

# After models complete, launch service implementation:
Task T029: "Implement Black-Scholes Greeks calculator in backend/src/services/greeks.py"
Task T030: "Implement Yahoo Finance scraper in backend/src/services/scraper.py"
```

---

## Parallel Example: User Story 1 (Query Premium)

```bash
# Launch schema creation tasks together:
Task T036: "Create PremiumQueryRequest schema in backend/src/models/schemas.py"
Task T037: "Create PremiumQueryResponse schema in backend/src/models/schemas.py"

# Launch frontend component tasks together:
Task T045: "Implement QueryForm component in frontend/src/components/QueryForm.tsx"
Task T046: "Implement PremiumResults component in frontend/src/components/PremiumResults.tsx"
```

---

## Implementation Strategy

### MVP First (User Story 4 + User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 4 (Automated Scraping) - **Wait 24-48 hours for data collection**
4. Complete Phase 4: User Story 1 (Query Premium)
5. **STOP and VALIDATE**: Test US1 independently (query META $635 2-week puts, verify historical data returned)
6. Deploy/demo if ready

**Rationale**: US4 builds the historical database, US1 delivers core user value (premium validation). This is minimum viable product.

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 4 → **Wait for data collection** → Validate scraper working
3. Add User Story 1 → Test independently → **Deploy/Demo MVP!** (Can validate premiums)
4. Add User Story 2 → Test independently → Deploy/Demo (Adds visualization)
5. Add User Story 5 → Test independently → Deploy/Demo (Adds scheduler control)
6. Add User Story 3 → Test independently → Deploy/Demo (Adds watchlist customization)
7. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. **Week 1-2**: Team completes Setup + Foundational together
2. **Week 3**: All developers work on User Story 4 together (scraper is complex, foundational)
3. **Week 4**: Wait for historical data to accumulate (24-48 hours minimum)
4. **Week 5+**: Once US4 complete and data exists:
   - Developer A: User Story 1 (Query Premium - P1)
   - Developer B: User Story 2 (Visualize Charts - P2)
   - Developer C: User Story 5 (Configure Scheduler - P2)
   - Developer D: User Story 3 (Manage Watchlist - P3)
5. Stories complete and integrate independently
6. **Final Week**: Team completes Polish phase together

**Critical Path**: Setup → Foundational → US4 (scraper) → Data Collection Wait → US1 (query) → MVP Complete

---

## Notes

- **[P] tasks**: Different files, no dependencies, can execute in parallel
- **[Story] label**: Maps task to specific user story (US1, US2, US3, US4, US5) for traceability
- **Test strategy**: Tests will be implemented during `/speckit.implement` per SpecKit methodology (not included in task breakdown)
- **User Story 4 is blocking**: All other stories depend on historical data from scraper - complete US4 first and allow 24-48 hours for data accumulation before implementing query features
- **Each user story is independently testable**: Can validate US1 without US2/US3/US5, can validate US2 without US3/US5, etc.
- **Success criteria validation**: 
  - SC-001 (<3s query): Validate in T091 (performance monitoring)
  - SC-003 (95% scrape success): Validate in T090 (error logging)
  - SC-004 (30 days data): Validate after 30 days of US4 operation
  - SC-005 (<2s charts): Validate in T092 (chart performance monitoring)
  - SC-007 (≥100 contracts/stock): Validate in T090 (scraper logging)
  - SC-008 (error logging): Validate in T090 (comprehensive logging)
- **Phase 2 preparation**: Migration 005 creates User/Role entities but they are not activated in MVP (single-user application per spec clarification 6)
- **Security baseline**: FR-022 (HTTPS) addressed in T084, FR-023 (input validation/SQL injection/XSS) addressed in T085-T086
- **Commit strategy**: Commit after each task or logical group of parallel tasks
- **Stop at checkpoints**: Validate each user story independently before proceeding to next priority
- **Avoid**: Vague tasks, same file conflicts, cross-story dependencies that break independence
