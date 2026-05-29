# Breathe ESG — Production-Quality Emissions Ingestion Platform

Welcome! This repository contains a production-quality, highly defensible ESG carbon accounting prototype built for the Breathe ESG hiring assignment. 

The primary goal of this application is not to maximize feature bloat, but to demonstrate **rigorous data modeling, realistic source handling, complete transparency, and auditability**.

---

## 🌟 Key Architecture & Core Capabilities

- **Two-Layer Ledger Design:** Separates the *immutable raw intake layer* (JSONB raw payloads stored exactly as received) from the *mutable analytical layer* (normalized records containing scope classification, unit standardizations, and snapshot calculation histories).
- **Realistic Source Handling:** Standardizes and sanitizes real-world raw CSV exports:
  - **SAP Fuel Procurement:** Maps German headers (e.g. `Materialnummer`), resolves technical names (e.g. `WERKS`), filters deleted/reversed records (`LOEKZ`/`STBLG`), and handles European decimal formats.
  - **Utility Electricity Bills:** Normalizes billing cycles across arbitrary monthly ranges using period midpoints, flags estimated reads, and logs gaps/overlaps.
  - **Corporate Travel Analytics:** Standardizes flight logs, automatically computes great-circle flight distances using the **Haversine formula** with a **8% routing efficiency uplift**, and falls back to spend-based estimation rules (EEIO) for hotels and ground transport when mileage is missing.
- **Workflow State Machine:** Enforces a rigid analyst state progression (Pending → Flagged → Reviewed → Approved → Locked) where every state change generates an analyst-facing `ReviewAction` and an immutable, append-only IT `AuditLog` mapping physical IP addresses and user agents.
- **Sustainability Dashboard:** Aggregates real-time tCO₂e profiles by scope, source type, and verification status using interactive charts.

---

## 📂 Project Repository Structure

```
BreatheESG/
│
├── MODEL.md             # 35% of grade - Complete data model and database schema document
├── DECISIONS.md         # 25% of grade - Comprehensive justification of all architectural decisions
├── SOURCES.md           # 20% of grade - In-depth research on SAP, Utility, and Travel data shapes
├── TRADEOFFS.md         # 10% of grade - Honest architectural boundaries and future roadmap
│
├── backend/             # Django + Django REST Framework Backend
│   ├── breathe_esg/     # Django settings, WSGI, root URL routing (multi-tenant enabled)
│   ├── core/            # Tenant multi-tenancy & immutable system AuditLog
│   ├── ingestion/       # CSV Flat-file parsers (SAP, Utility, Travel) and file intake layer
│   ├── emissions/       # Normalization engines, carbon calculator, and review workflow
│   ├── Procfile         # Web process entry point for Render/Heroku
│   ├── build.sh         # Render build script compiling database migrations and seeded factors
│   ├── render.yaml      # Infrastructure-as-code Render configuration
│   └── requirements.txt # Python package dependencies
│
├── frontend/            # Vite + React + TypeScript + Material UI Frontend
│   ├── src/
│   │   ├── api/         # Axios API Client matching tenant URL paths
│   │   ├── components/  # Sidebar Layout, ScopeChip, StatusChip, EmptyState
│   │   ├── theme/       # Sustainability green palette MUI design system
│   │   ├── types/       # Strictly checked TypeScript interfaces
│   │   ├── pages/       # Dashboard, CSV Upload, Ledger Records, Record Detail, Audit Trail
│   │   ├── App.tsx      # Routing and root theme wrappers
│   │   └── main.tsx     # Main entry point
│   ├── package.json     # Node scripts and dependencies
│   └── vercel.json      # Vercel proxy configuration routing API queries to Render
│
└── sample_data/         # Dirty real-world spreadsheets to test normalizations
    ├── sap_procurement.csv
    ├── utility_electricity.csv
    └── travel_expenses.csv
```

---

## 🛠️ Local Development & Setup

### Prerequisites
- Python 3.10+
- Node.js 18+

---

### 1. Django Backend Setup

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Create and activate a Python virtual environment:
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Create database schema migrations:
   ```bash
   python manage.py makemigrations core ingestion emissions
   ```
5. Apply migrations:
   ```bash
   python manage.py migrate
   ```
6. Seed standard 2024 DEFRA/EPA factors and the `acme-corp` demo tenant:
   ```bash
   python manage.py seed_data
   ```
7. Start the local development server:
   ```bash
   python manage.py runserver 8000
   ```
   The API will be live at `http://localhost:8000/`.

---

### 2. React Frontend Setup

1. Navigate to the frontend directory:
   ```bash
   cd ../frontend
   ```
2. Install base packages:
   ```bash
   npm install
   ```
3. Start the Vite React development server:
   ```bash
   npm run dev
   ```
   The web portal will be live at `http://localhost:5173/`. Open it in your browser.

---

## 🔒 Environment Variables Checklist

### Backend `.env` (optional, defaults provided):
```ini
DEBUG=True
SECRET_KEY=dev-fallback-secret-key-change-in-production
ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=postgresql://user:pass@localhost:5432/dbname  # Fallback to local SQLite if empty
```

### Frontend `.env` (optional, defaults provided):
```ini
VITE_API_URL=http://localhost:8000
```
