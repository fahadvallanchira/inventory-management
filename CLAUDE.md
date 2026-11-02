# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Factory Inventory Management System Demo with GitHub integration - Full-stack application with Vue 3 frontend, Python FastAPI backend, and in-memory mock data (no database).

> ⚠️ **This repository and any fork you create are PUBLIC.** Do not commit credentials, internal hostnames, or private registry URLs. `client/.npmrc` pins the public npm registry and `client/package-lock.json` is gitignored to prevent locally-configured registries from leaking into commits — leave both in place.

## Critical Tool Usage Rules

### Subagents
Use the Task tool with these specialized subagents for appropriate tasks:

- **vue-expert**: Use for Vue 3 frontend features, UI components, styling, and client-side functionality
  - Examples: Creating components, fixing reactivity issues, performance optimization, complex state management
  - **MANDATORY RULE: ANY time you need to create or significantly modify a .vue file, you MUST delegate to vue-expert**
- **code-reviewer**: Use after writing significant code to review quality and best practices
- **Explore**: Use for understanding codebase structure, searching for patterns, or answering questions about how components work
- **general-purpose**: Use for complex multi-step tasks or when other agents don't fit

### Skills
- **backend-api-test** skill: Use when writing or modifying tests in `tests/backend` directory with pytest and FastAPI TestClient

### MCP Tools
- **ALWAYS use GitHub MCP tools** (`mcp__github__*`) for ALL GitHub operations
  - Exception: Local branches only - use `git checkout -b` instead of `mcp__github__create_branch`
- **ALWAYS use Playwright MCP tools** (`mcp__playwright__*`) for browser testing
  - Test against: `http://localhost:3000` (frontend), `http://localhost:8001` (API)

## Stack
- **Frontend**: Vue 3 + Composition API + Vite (port 3000)
- **Backend**: Python FastAPI (port 8001)
- **Data**: JSON files in `server/data/` loaded via `server/mock_data.py`

## Commands

```bash
# Both servers (logs in /tmp/inventory-*.log); stop with ./scripts/stop.sh
./scripts/start.sh

# Backend
cd server
uv run python main.py

# Frontend
cd client
npm install && npm run dev
npm run build

# Backend tests - tests/ has no uv project of its own, so --project is required
cd tests
uv run --project ../server pytest
uv run --project ../server pytest backend/test_inventory.py
uv run --project ../server pytest backend/test_inventory.py::TestInventoryEndpoints::test_get_all_inventory
```

There is no linter, type checker, or frontend test suite configured.

## Key Patterns

**Filter System**: 4 filters (Time Period, Warehouse, Category, Order Status), sent as query params by endpoints that support them (see API Endpoints)
**Shared Filter State**: `useFilters` holds module-level refs, so selections persist across views. `FilterBar` writes them; views read them and refetch
**Data Flow**: Vue filters → `client/src/api.js` → FastAPI → In-memory filtering → Pydantic validation → Computed properties
**Reactivity**: Raw data in refs (`allOrders`, `inventoryItems`), derived data in computed properties
**Period Values**: `month` accepts a month (`2025-01`) or a quarter (`Q1-2025`). Quarters come from `QUARTER_MAP` in `server/main.py`, which only covers 2025; unknown quarters return unfiltered data
**i18n**: User-facing strings go through `useI18n` with keys in both `client/src/locales/en.js` and `ja.js`

## API Endpoints
- `GET /api/inventory` - Filters: warehouse, category
- `GET /api/orders` - Filters: warehouse, category, status, month
- `GET /api/inventory/{id}`, `/api/orders/{id}` - Single item, 404 if missing
- `GET /api/dashboard/summary` - All filters
- `GET /api/demand`, `/api/backlog` - No filters
- `GET /api/spending/*` - Summary, monthly, categories, transactions
- `GET /api/reports/quarterly`, `/api/reports/monthly-trends` - Called directly with axios from `Reports.vue`, not through `api.js`

## Known Gaps
- `api.js` calls `/api/tasks` and `/api/purchase-orders`, but `server/main.py` has no such routes, so those calls fail
- `Backlog.vue` exists but has no route in `client/src/main.js`
- `api.js` and `Reports.vue` hardcode `http://localhost:8001`; there is no Vite proxy

## Common Issues
1. Use unique keys in v-for (not `index`) - use `sku`, `month`, etc.
2. Validate dates before `.getMonth()` calls
3. Update Pydantic models when changing JSON data structure
4. Inventory filters don't support month (no time dimension)
5. Revenue goals: $800K/month single, $9.6M YTD all months

## File Locations
- Views: `client/src/views/*.vue`
- API Client: `client/src/api.js`
- Backend: `server/main.py`, `server/mock_data.py`
- Data: `server/data/*.json`
- Styles: `client/src/App.vue`
- Area-specific guidance: `client/CLAUDE.md`, `server/CLAUDE.md`

## Design System
- Colors: Slate/gray (#0f172a, #64748b, #e2e8f0)
- Status: green/blue/yellow/red
- Charts: Custom SVG, CSS Grid for layouts
- No emojis in UI
