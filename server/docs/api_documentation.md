# NDC Tracking System - API & System Architecture Documentation

This document provides a highly detailed, in-depth reference for the NDC Tracking System backend architecture, database schemas, API routes, service layer workflows, background scheduler loops, and CLI administration utilities.

---

## 1. System Architecture & Core Design

The NDC Tracking System is a FastAPI-based backend application designed to automate, track, and manage employee exit clearances (No Demand Certificate - NDC) and Full & Final (F&F) settlements. 

### Technology Stack
* **Web Framework**: FastAPI (Asynchronous Python ASGI framework)
* **ASGI Server**: Uvicorn
* **Database ORM**: SQLAlchemy 2.0 (with `asyncpg` driver for asynchronous PostgreSQL connectivity)
* **Dependency Manager**: `uv`
* **Integrations**: Microsoft Graph API (via MSAL and httpx) for SharePoint document synchronization

### Project Directory Layout
```text
server/
├── app/
│   ├── auth/              # JWT Authentication handlers and dependency providers
│   ├── dto/               # Data Transfer Objects / Pydantic schemas (common, email, RM configs)
│   ├── models/            # SQLAlchemy database models (NdcRecord, NdcApproval, etc.)
│   ├── routers/           # FastAPI APIRouters (Common, Email, F&F, RM Configuration)
│   ├── services/          # Business logic services (Excel parser, Email, SharePoint, Sync)
│   └── utils/             # Utilities (Response helpers, cron daemon, manual job CLI wrapper)
├── config/                # Configuration and database engine initialization
├── scripts/               # Utility scripts (Alembic DB Sync, Manual SharePoint Sync)
├── docs/                  # API and System Architecture Documentation
├── main.py                # Application entrypoint & background lifecycle tasks
└── .env                   # Configuration environment variables
```

---

## 2. API Response Wrapper Architecture

To ensure a predictable API contract, all standard JSON responses are wrapped in a unified response envelope via the custom `UnifiedJSONResponse` class.

### 2.1 Success Response Envelope
For singular object returns or action confirmations:
* **Status Code**: `200 OK`
* **JSON Structure**:
```json
{
  "status": true,
  "data": {
    /* Application-specific payload */
  },
  "message": "Optional message details or null"
}
```

### 2.2 List & Pagination Success Envelope
When list operations are requested, the response data contains a JSON array accompanied by pagination metrics in a `meta` block:
* **Status Code**: `200 OK`
* **JSON Structure**:
```json
{
  "status": true,
  "data": [
    {
      "id": "1",
      "person_number": "10045"
    }
  ],
  "message": null,
  "meta": {
    "total": 120,      // Total records matching filter
    "page": 1,         // Current page number
    "page_size": 10,   // Number of records per page
    "pages": 12        // Total pages available
  }
}
```

### 2.3 Error Response Envelope
If an exception or validation check fails, the API returns semantic HTTP codes (e.g., `400`, `401`, `403`, `422`, `500`) and a standardized error structure:
* **JSON Structure**:
```json
{
  "status": false,
  "data": null,
  "message": "Error description message details"
}
```

### 2.4 Form Validation Error Envelope (HTTP 422)
If a client request fails Pydantic schema validation, the fields are normalized in `snake_case` and returned under `data.errors`:
```json
{
  "status": false,
  "data": {
    "errors": [
      {
        "field": "person_number",
        "message": "field required"
      }
    ]
  },
  "message": "Validation failed"
}
```

---

## 3. Database Schema Specifications

The database layer consists of 5 core PostgreSQL tables modeled via SQLAlchemy Declarative Base.

### 3.1 `NdcRecord` (Table: `ndc_records`)
Stores the master employee exit details.
* `id` (Integer, Primary Key, Autoincrement)
* `person_number` (String(50), Unique, Indexed) - Employee ID.
* `employee_name` (String(255)) - Employee's full name.
* `department` (String(255), Nullable) - Assigned business department.
* `department_reporting_name` (String(255), Nullable) - Reporting division name.
* `ndc_assigned_date` (Date, Nullable) - Date when NDC clearance was assigned.
* `resignation_date` (Date, Nullable) - Date resignation was submitted.
* `last_working_date` (Date, Nullable) - Employee's last day.
* `ndc_initiated_date` (Date, Nullable) - Date the clearance process started.
* `ndc_completed_date` (Date, Nullable) - Date all stages were completed.
* `created_by` (String(100), default `'system'`) - User who created the record.
* `ndc_stage` (String(100), Nullable) - e.g., `"Recovery Pending"`, `"GCC Pending"`, `"NDC Completed"`.
* `is_fnf_completed` (Boolean, default `False`) - True when F&F processing is finished.
* `is_fnf_closed` (Boolean, default `False`) - True when F&F record is closed.
* `is_fnf_revision` (Boolean, default `False`) - True if F&F requires corrections.
* `fnf_completed_date` (Date, Nullable) - Timestamp of F&F completion.
* `fnf_document_count` (Integer, default `0`) - Number of F&F documents in SharePoint.
* `gcc_initiate_date` (Date, Nullable) - Date GCC HR approval stage was initialized.
* **Stage Completion Dates (Date, Nullable)**:
  * `rm_approval_date`, `it_approval_date`, `abex_approval_date`, `telecom_approval_date`, `store_approval_date`, `safety_approval_date`, `administration_approval_date`, `security_approval_date`, `hr_approval_date`, `gcc_hr_approval_date`, `final_abex_approval_date`, `business_specific_approval_date`, `legatrix_approval_date`

### 3.2 `NdcApproval` (Table: `ndc_approvals`)
Tracks approvals needed for a specific record across clearance departments.
* `id` (Integer, Primary Key, Autoincrement)
* `ndc_record_id` (Integer, Foreign Key to `ndc_records.id`, On Delete Cascade)
* `stage_name` (String(100), Indexed) - e.g., `"RM"`, `"IT"`, `"Telecom"`, `"Security"`, `"HR"`, `"GCC HR"`.
* `status` (String(50)) - Status values: `PENDING`, `IN_PROGRESS`, `COMPLETED`, `NOT_APPLICABLE`.
* `approver_name` (String(255), Nullable) - Name of the individual approver.
* `stage_started_at` (DateTime, Nullable) - Timestamp when stage was opened.
* `stage_completed_at` (DateTime, Nullable) - Timestamp when stage was completed.

### 3.3 `EmailRecipient` (Table: `email_recipients`)
Maps departments to their configured email addresses for automated reminders.
* `id` (Integer, Primary Key, Autoincrement)
* `name` (String(255)) - Recipient's name.
* `email` (String(255), Unique, Indexed) - Target email address.
* `department` (String(100)) - Target department key (e.g., `"hr"`, `"it"`, `"security"`).
* `role` (String(100), Nullable) - Role title.

### 3.4 `RmEmailConfiguration` (Table: `rm_email_configurations`)
Configures Reporting Managers and their specific notification email addresses.
* `id` (Integer, Primary Key, Autoincrement)
* `rm_name` (String(255), Indexed) - Manager's name.
* `email` (String(255)) - Manager's email address.

### 3.5 `UploadBatch` (Table: `upload_batches`)
Tracks Excel ingestion operations.
* `id` (Integer, Primary Key, Autoincrement)
* `filename` (String(255)) - Ingested file name.
* `processed_at` (DateTime) - Timestamp of upload.
* `status` (String(50)) - Ingestion status (`COMPLETED`, `FAILED`).
* `records_count` (Integer) - Count of records parsed.

---

## 4. API Endpoints Reference

### 4.1 Exit Clearance & Settlement Operations (`/api/v1`)
Handles NDC record queries and updating F&F statuses.

#### `GET /api/v1/ndc-records`
* **Description**: Returns all NDC records with unified approval stages.
* **Query Parameters**:
  * `start_date` (optional, Date, e.g. `2026-07-01`) - Filters records last working date starting from this date.
  * `end_date` (optional, Date, e.g. `2026-07-31`) - Filters records last working date up to this date.
* **Success Response (200 OK)**:
```json
{
  "status": true,
  "data": [
    {
      "id": "1",
      "person_number": "1004523",
      "employee_name": "John Doe",
      "department": "IT Operations",
      "ndc_stage": "Recovery Pending",
      "resignation_date": "2026-06-10",
      "last_working_date": "2026-07-15",
      "ndc_initiated_date": "2026-06-11",
      "ndc_completed_date": "",
      "fnf_status": "",
      "fnf_document": "",
      "is_fnf_completed": false,
      "is_fnf_closed": false,
      "is_fnf_revision": false,
      "fnf_document_count": 0,
      "rm_approval_status": "Completed",
      "rm_approver": "Jane Manager",
      "rm_approval_date": "2026-06-15",
      "it_approval_status": "Pending",
      "it_approver": "",
      "it_approval_date": ""
      /* ... rest of the 13 approval stages */
    }
  ],
  "message": null
}
```

#### `GET /api/v1/fnf-records`
* **Description**: Returns F&F records (fetches all NDC records using same compiler).
* **Success Response (200 OK)**: JSON List of `CommonNDCRecord` objects.

#### `GET /api/v1/analytics-records`
* **Description**: Returns analytics-specific NDC compiled view.
* **Success Response (200 OK)**: JSON List of `CommonNDCRecord` objects.

#### `PUT /api/v1/ndc-records/{record_id}`
* **Description**: Updates the F&F status of a record.
* **Request Body**: `FnfUpdateRequest`
```json
{
  "is_fnf_completed": true,
  "is_fnf_closed": false,
  "is_fnf_revision": false,
  "fnf_document_count": 2
}
```
* **Success Response (200 OK)**:
```json
{
  "status": true,
  "data": {
    "status": "ok",
    "id": 123
  },
  "message": null
}
```
* **Error Response (404 Not Found)**:
```json
{
  "status": false,
  "data": null,
  "message": "Record not found"
}
```
* **Side Effects**: If `is_fnf_completed` or `is_fnf_closed` is set to `True`, auto-fills blank approval dates (`stage_completed_at` / department columns) with today's date.

---

### 4.2 Email Notification Management (`/api/v1`)
Manages recipient configuration and manual triggers for email notifications.

#### `GET /api/v1/email-recipients`
* **Description**: Retrieves all configured department email addresses.
* **Success Response (200 OK)**:
```json
{
  "status": true,
  "data": [
    {
      "id": "1",
      "name": "HR Operations",
      "email": "hr-ops@company.com",
      "department": "hr",
      "role": "Admin"
    }
  ],
  "message": null
}
```

#### `POST /api/v1/email-recipients`
* **Description**: Adds a new department email recipient.
* **Request Body**: `EmailRecipientSchema`
* **Success Response (200 OK)**:
```json
{
  "status": true,
  "data": {
    "status": "success"
  },
  "message": null
}
```
* **Error Response (409 Conflict)**:
```json
{
  "status": false,
  "data": null,
  "message": "A recipient with this email already exists."
}
```

#### `PUT /api/v1/email-recipients/{id}`
* **Description**: Updates an existing email recipient.
* **Path Parameters**:
  * `id` (Integer) - Database recipient ID.
* **Request Body**: `EmailRecipientSchema`
* **Success Response (200 OK)**:
```json
{
  "status": true,
  "data": {
    "status": "success"
  },
  "message": null
}
```
* **Error Response (409 Conflict)**: Returned if the modified email matches another existing recipient.

#### `DELETE /api/v1/email-recipients/{id}`
* **Description**: Deletes a department email configuration by ID.
* **Success Response (200 OK)**:
```json
{
  "status": true,
  "data": {
    "status": "success"
  },
  "message": null
}
```
* **Error Response (404 Not Found)**: Returned if recipient is not found.

#### `POST /api/v1/send-delayed-reminder`
* **Description**: Compiles delayed/overdue cases (top 10 for NDC delayed cases, or all records for F&F open/revision required cases) and sends a reminder summary email to the custom recipient email address.
* **Request Body**: `DelayedReminderRequest`
```json
{
  "email": "admin@company.com",
  "type": "fnf_open"
}
```
* **Success Response (200 OK)**:
```json
{
  "status": true,
  "data": {
    "status": "success",
    "message": "Reminder email sent to admin@company.com with 56 records.",
    "records_sent": 56
  },
  "message": null
}
```

#### `POST /api/v1/send-fnf-email`
* **Description**: Dispatches F&F settlement documents for an employee.
* **Request Body**: `FnfEmailRequest`
```json
{
  "record_id": 142,
  "email": "employee@personal.com"
}
```
* **Success Response (200 OK)**:
```json
{
  "status": true,
  "data": {
    "status": "success",
    "message": "F&F email sent successfully with attachments."
  },
  "message": null
}
```
* **Service Logic**: Connects to SharePoint, searches for the employee's folder, downloads documents, groups them inside an in-memory ZIP if there are multiple documents, and emails them to the target address. Falls back to local uploads if SharePoint cannot be reached or contains no documents.

---

### 4.3 Settlement Documents (SharePoint) (`/api/ff`)
Integrates directly with SharePoint to pull and stream active exit documents.

#### `GET /api/ff/download/{person_number}`
* **Description**: Downloads files from the SharePoint directory matching the employee's `person_number`.
* **Path Parameters**:
  * `person_number` (String, e.g., `1004523`)
* **Response**: 
  * If a single file exists: Streams the file with matching Content-Type.
  * If multiple files exist: Dynamically creates and streams a ZIP file.
  * If no file exists: `404 Not Found` JSON error block.

---

### 4.4 Reporting Manager Email Configurations (`/api/v1`)
Configures manager email mappings to support automated email routing.

#### `GET /api/v1/rm-email-configuration`
* **Description**: Fetches paginated RM email mappings.
* **Query Parameters**:
  * `page` (Integer, default `1`)
  * `limit` (Integer, default `10`)
  * `search` (String, default `""` - Filters by manager name)
* **Success Response (200 OK)**:
```json
{
  "status": true,
  "data": {
    "total": 45,
    "page": 1,
    "limit": 10,
    "data": [
      {
        "id": 12,
        "rm_name": "Happy Singh",
        "email": "happy.singh@company.com"
      }
    ]
  },
  "message": null
}
```

#### `POST /api/v1/rm-email-configuration`
* **Description**: Creates a new Reporting Manager email mapping.
* **Request Body**: `RmEmailCreate`
```json
{
  "rm_name": "Jane Manager",
  "email": "jane.manager@company.com"
}
```
* **Success Response (200 OK)**:
```json
{
  "status": true,
  "data": {
    "success": true,
    "message": "RM added successfully"
  },
  "message": null
}
```

#### `PUT /api/v1/rm-email-configuration/{id}`
* **Description**: Updates an existing manager config.
* **Request Body**: `RmEmailUpdate`
* **Success Response (200 OK)**:
```json
{
  "status": true,
  "data": {
    "success": true,
    "message": "RM updated successfully"
  },
  "message": null
}
```

#### `DELETE /api/v1/rm-email-configuration/{id}`
* **Description**: Deletes a manager config mapping.
* **Success Response (200 OK)**:
```json
{
  "status": true,
  "data": {
    "success": true,
    "message": "Record deleted successfully"
  },
  "message": null
}
```

#### `POST /api/v1/rm-email-configuration/import`
* **Description**: Bulk imports manager configs from an uploaded Excel file.
* **Form Data**: `file: UploadFile` (Excel Spreadsheet)
* **Success Response (200 OK)**:
```json
{
  "status": true,
  "data": {
    "success": true,
    "records_inserted": 24,
    "errors": []
  },
  "message": null
}
```

#### `GET /api/v1/rm-email-configuration/sample`
* **Description**: Downloads a blank sample Excel file matching the format required for bulk imports.
* **Response**: `StreamingResponse` (Excel file attachment: `sample_rm_email_configuration.xlsx`).

---

## 5. Backend Service Layer Workflows

The application isolates database queries, file systems, and external Graph APIs in dedicated service classes:

### 5.1 `common_service`
* **`fetch_common_records`**: Pulls `NdcRecord` rows, merges them with `NdcApproval` rows, checks local `uploads/` directory for any offline F&F documents, and constructs `CommonNDCRecord` objects.
* **`update_fnf_status`**: Handles transactions to update F&F database fields.
* **`_propagate_department_dates`**: Automatically fills blank department completion dates when F&F status changes to completed/closed.

### 5.2 `email_service`
* **`send_delayed_reminder`**: Asynchronously generates HTML with top 10 delayed cases and sends the email via SMTP.
* **`send_fnf_email_service`**: Queries SharePoint for F&F documents (using `SharePointService`), packages multiple documents inside a ZIP in-memory using `zipfile` and `io.BytesIO`, constructs MIMEMultipart emails, and dispatches them.
* **`run_10am_job`**: Daily consolidation notifier. Iterates over pending clearances, matches manager names to the `RmEmailConfiguration` table, groups notifications, identifies manager email conflicts, redirects conflicts to HR, and emails each department their pending list in batches to prevent SMTP throttling.
* **`run_tomorrow_alert_job`**: Queries records whose last working date is tomorrow and sends high-priority alerts to IT and Security.

### 5.3 `sharepoint_service`
Uses MSAL credentials to authenticate with Azure AD and perform Microsoft Graph operations:
* **`get_site_id`**: Resolves site URL to Microsoft Graph Site ID.
* **`get_drive_details`**: Translates `SHAREPOINT_TARGET_FOLDER` to the corresponding Drive ID (matching `Shared Documents` URL path to `Documents` API key).
* **`get_person_folder_files`**: Lists files inside the subfolder matching the employee's `person_number`.
* **`download_employee_documents`**: Retrieves target files from SharePoint, downloading and streaming single files directly or compressing multiple files into an in-memory ZIP.

### 5.4 `sharepoint_sync_service`
* **`sync_sharepoint_folders_to_db`**: Scans the SharePoint site, parses folder names to extract `person_number` values, and updates database records with the count of files stored under each employee folder.

### 5.5 `excel_parser`
* **`parse_and_save_excel`**: Extracts employee data, manager names, resignation details, and department assignment dates from raw Oracle Web Reports (MHTML/XLS formats), inserting new records or updating existing ones.

---

## 6. Background Loops & Task Scheduling

The application starts several concurrent background loops during the FastAPI startup lifecycle (`lifespan` in `server/main.py`):

1. **SharePoint Document Sync Loop (`sharepoint_sync_loop`)**: Runs periodically (polls configuration times, e.g. `10:10`, `13:10`, `16:10`, `19:10`) to update document counts on records.
2. **F&F Completed Ingestion Sync (`fnf_completed_sync_loop`)**: Periodically updates document statuses in the DB.
3. **Email Automation Loop (`email_automation_loop` in `server/app/utils/scheduler.py`)**: Checks current local time continuously. Triggers both `run_10am_job()` (consolidated notifications) and `run_tomorrow_alert_job()` (IT/Security tomorrow warnings) automatically at **10:00 AM** daily.

### Manual CLI Utilities (`server/scripts/` & `server/app/utils/`)
The application includes standalone scripts to allow the operations team to bypass background schedules and execute critical actions manually:

**1. SharePoint Data Ingestion**
Instantly downloads and ingests the latest Excel reports from SharePoint without waiting for the background polling loop:
```bash
uv run .\scripts\manual_sync.py
```

**2. Database Synchronization**
Evaluates SQLAlchemy models and strictly synchronizes the PostgreSQL schema via Alembic migrations:
```bash
uv run .\scripts\sync_db.py
```

**3. Email Automations**
Run email batches manually:
```bash
# Execute both consolidated and next-day alert jobs
uv run python -m app.utils.run_email_jobs --job both

# Execute only the daily 10:00 AM consolidated batch
uv run python -m app.utils.run_email_jobs --job 10am

# Execute only the tomorrow alerts for IT & Security
uv run python -m app.utils.run_email_jobs --job tomorrow
```

---

## 7. How to Run Locally

### Prerequisites
* Python 3.10+
* `uv` installed (`pip install uv`)

### Configuration (`server/.env`)
Copy environment keys and update database & SharePoint settings:
```ini
DB_USER=avnadmin
DB_PASSWORD=your_password
DB_HOST=your_host
DB_PORT=your_port
DB_NAME=defaultdb

SHAREPOINT_TENANT_ID=your_tenant_id
SHAREPOINT_SITE_URL=https://yourcompany.sharepoint.com/sites/your_site
SHAREPOINT_CLIENT_ID=your_client_id
SHAREPOINT_CLIENT_SECRET=your_client_secret
SHAREPOINT_TARGET_FOLDER=/sites/your_site/Shared Documents/your_folder
```

### Installation & Run
1. Navigate to the server folder:
   ```bash
   cd server
   ```
2. Install dependencies:
   ```bash
   uv sync
   ```
3. Start the FastAPI server:
   ```bash
   uv run main.py
   ```
The Swagger UI documentation is available at `http://localhost:8010/docs`.
