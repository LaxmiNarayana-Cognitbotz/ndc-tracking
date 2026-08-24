# NDC/GCC Workflow Tracking Backend

A FastAPI-based backend for tracking, parsing, and reporting Employee No-Due-Clearance (NDC) and GCC workflow processes. The system automates the ingestion of weekly workflow reports from Excel (supporting `.xlsb` and `.xlsx`), normalizes status codes across 13 distinct approval stages, tracks processing bottlenecks, calculates turnaround times (TAT), and generates comprehensive multi-sheet MIS Excel reports.

---

## Key Features

1. **Excel Parsing & Normalization**:
   - Supports ingestion of binary Excel sheets (`.xlsb`) and standard spreadsheet formats (`.xlsx`).
   - Cleans Excel-serial dates and maps custom stage status combinations to standardized states (`PENDING`, `IN_PROGRESS`, `CLEARED`, `NOT_APPLICABLE`).
   - Automatically handles record updates via upserts keyed on `person_number`.

2. **Unified REST Response Architecture**:
   - Standardized envelope wrapper (`status`, `message`, `data`, `meta`).
   - Unified error handling that hides internal server tracebacks.
   - **`camelCase` Key Serialization**: All JSON payload keys are automatically serialized to camelCase for smooth frontend integration.

3. **Complex Filter Queries**:
   - Offers 20+ query parameters to filter workflow records (by stage, department, location, date ranges, and computed pending day limits).

4. **Workflow Analytics Engine**:
   - Calculates Turnaround Times (TAT) across completed clearing cycles.
   - Tracks pending bottlenecks by stage and individual approver.
   - Summarizes clearance rates across different business divisions and plots monthly trends.

5. **MIS Excel Exporter**:
   - Generates formatted, multi-sheet Excel reports including raw records, TAT analytics, bottlenecks, department clearances, and trends.

---

## Tech Stack
* **Python 3.12+**
* **FastAPI**
* **SQLAlchemy 2.0 (Async)**
* **PostgreSQL**
* **openpyxl & pyxlsb** (for Excel spreadsheet processing)
* **python-jose** (JWT Security)

---

## Quick Start Guide

### 1. Configure Environment Variables
Copy and fill out the `.env` file at the root of the project:
```ini
DB_USER=your_db_username
DB_PASSWORD=your_db_password
DB_HOST=your_db_host
DB_PORT=5432
DB_NAME=your_db_name
SSL_MODE=require  # Optional: For cloud databases like Aiven

JWT_SECRET=your_jwt_secret_key
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=480
UPLOAD_DIR=uploads
```

### 2. Install Dependencies
Install dependencies using `uv` or `pip`:
```bash
uv sync
```

### 3. Initialize or Synchronize the Database Schema
The database uses Alembic to strictly synchronize the SQL tables with your Python models. To initialize the database or apply new model changes, run:
```bash
uv run .\scripts\sync_db.py
```

### 4. Run the Server
Launch the FastAPI application:
```bash
uv run .\main.py
```
The server will start at `http://localhost:8010`. You can access the interactive API docs at `http://localhost:8010/docs`.

### 5. Manual SharePoint Sync (Optional)
If you need to instantly bypass the background polling and manually download/ingest the latest Excel workflow reports from SharePoint, run:
```bash
uv run .\scripts\manual_sync.py
```

---

## API Documentation

For detailed information about endpoint inputs, response fields, success/error envelopes, and request samples, please refer to:
* **[API Documentation Guide (docs/api_documentation.md)](docs/api_documentation.md)**
