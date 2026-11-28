# Multi-Store Retail Operations Platform

A comprehensive retail operations management system built with FastAPI (Python) backend and React frontend, featuring transaction log ingestion, price list management, reconciliation, dashboard analytics, price change workflows, AI invoice processing, and a Hub simulator.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                      React Frontend (Port 3000)                 │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│  │Dashboard │ │Reconcil. │ │ Pricing  │ │   AI     │  ...      │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘           │
└────────────────────────────┬────────────────────────────────────┘
                             │ REST API /api/*
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                     FastAPI Backend (Port 8000)                 │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│  │Connectors│ │Dashboard │ │Reconcil. │ │ Pricing  │           │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘           │
│  ┌──────────┐ ┌──────────────────┐                              │
│  │    AI    │ │  Hub Simulator   │                              │
│  └──────────┘ └──────────────────┘                              │
│                             │                                   │
│                        SQLite DB                                │
└─────────────────────────────────────────────────────────────────┘
```

## Features

### 1. Transaction Log Ingestion (Connectors)
- **XML v2 Format**: Legacy transaction log format with header, lines, tenders, tax, discounts
- **JSON v3 Format**: Modern format with metadata, extended line items, tender details
- **Price List Import**: CSV/XML price list files with validation

### 2. Price List Management
- Current price list viewing with filtering
- Price change requests with approval workflow
- Export price lists to standard formats
- ACK/REJ file handling for hub communication

### 3. Reconciliation
- **Shift Summaries**: Cash/non-cash totals per shift per store/device
- **EOD Summaries**: End-of-day aggregation across all shifts
- **Daily Reconciliation**: Complete daily view with variance detection
- **Cash Variance Report**: Cross-store comparison with variance percentages
- **Discrepancy Detection**: Automated flagging of variances exceeding thresholds

### 4. Dashboard Analytics
- **KPIs**: Total sales, transactions, average value, tax, gross margin
- **Sales Trends**: Daily/weekly/monthly with moving averages
- **Top Items**: Best-selling by quantity/revenue with department breakdown
- **Store Comparison**: Multi-store performance metrics
- **Department Performance**: Sales, margins, transaction counts per department
- **Hourly Heatmap**: Transaction volume and value by hour/day
- **Tender Mix**: Payment method distribution (cash, card, mobile, voucher)

### 5. Price Change Workflows
- Create price changes with effective dates
- Multi-level approval (store → area → regional)
- Export approved changes for distribution
- Process inbound price change files from hub
- Send acknowledgements/rejections back to hub

### 6. AI Invoice Processing
- Mock OCR extraction from invoices (PDF, XML, images)
- Supplier, line items, totals, tax extraction with confidence scores
- Purchase Order matching
- Goods receipt creation from matched invoices
- Inbox batch processing

### 7. Hub Simulator
- Background worker polling inbox/outbox directories
- Store submission simulation (tlogs, price changes, goods receipts)
- Price list distribution to stores
- Inbox/outbox file management
- Configuration management
- Real-time activity monitoring

## Tech Stack

### Backend
- **FastAPI** - Modern async Python web framework
- **SQLite** - Embedded database with exact decimal money handling (stored as TEXT)
- **Uvicorn** - ASGI server with hot reload
- **Pydantic** - Data validation and serialization

### Frontend
- **React 18** - Component-based UI
- **React Router** - Client-side routing
- **Recharts** - Data visualizations
- **Axios** - HTTP client
- **react-icons** - Icon library (Feather icons)

### Data Formats
- **XML v2** - Transaction logs (legacy)
- **JSON v3** - Transaction logs (modern)
- **CSV** - Price lists

## Database Schema

14 tables with composite primary keys for multi-store device support:

| Table | Purpose |
|-------|---------|
| stores | Store master data |
| devices | POS devices (composite PK: store_id, id) |
| departments | Product departments |
| items | Product catalog |
| item_variants | Size/color variants |
| staff | Employee records |
| business_accounts | B2B customer accounts |
| transactions | Sales transactions |
| transaction_lines | Line items per transaction |
| transaction_tenders | Payment tenders per transaction |
| transaction_taxes | Tax breakdown per transaction |
| transaction_discounts | Discounts per transaction |
| price_list | Current prices (composite PK: store_id, item_code, variant_code, effective_date) |
| price_changes | Price change requests with approval workflow |

## Getting Started

### Prerequisites
- Python 3.10+
- Node.js 18+
- npm 9+

### Installation

```bash
# Backend
cd backend
pip install -r requirements.txt

# Frontend
cd frontend
npm install
```

### Generate Mock Data

```bash
cd backend
python ../generate_mock_data.py
```

This creates:
- 28 transaction log files (XML v2 + JSON v3) in `outbox/`
- Price list files in `outbox/`
- ACK/REJ files in `outbox/`
- Price change files in `inbox/`

### Run Services

```bash
# Terminal 1: Backend
cd backend
PYTHONPATH=/c/claudepro python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2: Frontend
cd frontend
npm start
```

### Access Points
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs (Swagger UI)
- **Health Check**: http://localhost:8000/health

## API Endpoints

### Connectors
- `POST /api/connectors/import/tlog-xml` - Import XML v2 transaction log
- `POST /api/connectors/import/tlog-json` - Import JSON v3 transaction log
- `POST /api/connectors/import/price-list` - Import price list
- `GET /api/connectors/imports` - List import history

### Dashboard
- `GET /api/dashboard/kpis` - Key performance indicators
- `GET /api/dashboard/sales-trend` - Sales trend data
- `GET /api/dashboard/top-items` - Top selling items
- `GET /api/dashboard/store-comparison` - Multi-store comparison
- `GET /api/dashboard/department-performance` - Department metrics
- `GET /api/dashboard/hourly-heatmap` - Hourly activity heatmap
- `GET /api/dashboard/tender-mix` - Payment method distribution

### Reconciliation
- `GET /api/reconciliation/shift-summaries` - Shift summaries
- `GET /api/reconciliation/eod-summaries` - End-of-day summaries
- `GET /api/reconciliation/daily-reconciliation/{store_id}/{date}` - Daily reconciliation
- `GET /api/reconciliation/cash-variance-report` - Cash variance report
- `GET /api/reconciliation/discrepancies` - Flagged discrepancies

### Pricing
- `GET /api/pricing/price-list` - Current price list
- `POST /api/pricing/price-changes` - Create price change
- `GET /api/pricing/price-changes` - List price changes
- `POST /api/pricing/price-changes/{id}/approve` - Approve price change
- `POST /api/pricing/price-changes/{id}/reject` - Reject price change
- `POST /api/pricing/export-price-list` - Export price list
- `POST /api/pricing/process-inbox-price-changes` - Process inbound price changes
- `POST /api/pricing/send-ack/{id}` - Send ACK/REJ

### AI Invoice Processing
- `POST /api/ai/process-invoice` - Process single invoice
- `POST /api/ai/process-inbox-invoices` - Batch process inbox
- `POST /api/ai/match-invoice-to-po` - Match invoice to PO
- `GET /api/ai/invoice-status/{id}` - Get processing status
- `GET /api/ai/extracted-data/{id}` - Get extracted data
- `POST /api/ai/create-goods-receipt` - Create goods receipt

### Hub Simulator
- `GET /api/hub/status` - Worker status
- `POST /api/hub/start` - Start worker
- `POST /api/hub/stop` - Stop worker
- `POST /api/hub/cycle` - Run single cycle
- `GET /api/hub/inbox-files` - List inbox files
- `GET /api/hub/outbox-files` - List outbox files
- `GET /api/hub/outbox-file/{filename}` - Get outbox file content
- `POST /api/hub/simulate-store-submission` - Simulate store submission
- `GET /api/hub/overview` - Hub overview stats
- `POST /api/hub/process-inbox` - Process inbox
- `POST /api/hub/process-store-outbox` - Process store outbox
- `GET /api/hub/config` - Get configuration
- `PUT /api/hub/config` - Update configuration

## Data Flow

```
Store POS → Transaction Logs (XML v2 / JSON v3)
                ↓
         Outbox Directory
                ↓
    Hub Simulator (Background Worker)
                ↓
         Connector Import
                ↓
         SQLite Database
                ↓
    Dashboard / Reconciliation / Pricing APIs
                ↓
         React Frontend
```

## Price Change Flow

```
Price Change Request → Store Manager Approval
                          ↓
                   Area Manager Approval
                          ↓
                 Regional Manager Approval
                          ↓
                   Export to Hub Outbox
                          ↓
              Store Pickup & Acknowledge
```

## Money Handling

All monetary values stored as **TEXT** in SQLite to preserve exact decimal precision (no floating-point errors). Application layer uses Python `Decimal` for all calculations.

## Development Notes

### Adding New Transaction Format
1. Add new endpoint in `connectors/router.py`
2. Create parser for the format
3. Map to database schema (transactions, lines, tenders, taxes, discounts)

### Extending Dashboard
1. Add new endpoint in `dashboard/router.py`
2. Create chart component in frontend
3. Add route/page in `App.js` and sidebar

### Mock Data Generation
Run `generate_mock_data.py` to create realistic test data:
- 2 stores, 3 departments, 18 items, 5 staff, 6 devices
- 28 transaction log files across 14 days
- Complete price lists and price change files

## Project Structure

```
claudepro/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI app entry point
│   │   ├── connectors/             # Transaction log import
│   │   ├── dashboard/              # Analytics & KPIs
│   │   ├── reconciliation/         # Cash reconciliation
│   │   ├── pricing/                # Price management
│   │   ├── ai/                     # Invoice processing
│   │   └── hub_simulator/          # Hub communication
│   ├── database/
│   │   ├── schema.sql              # PostgreSQL schema reference
│   │   └── db.py                   # SQLite init & connection
│   └── requirements.txt
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── components/             # Shared UI components
│   │   ├── pages/                  # Page components
│   │   ├── api/                    # API client
│   │   ├── App.js                  # Routing
│   │   └── index.js                # Entry point
│   └── package.json
├── generate_mock_data.py           # Test data generator
└── README.md
```

## License

Take-home assignment project for retail operations platform.