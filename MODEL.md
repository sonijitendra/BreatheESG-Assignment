# Data Model — Breathe ESG Emissions Ingestion Platform

## Design Philosophy

This data model is built around one core principle: **source data is sacred**.

In ESG reporting, auditors need to trace every emission number back to the original document. If a utility bill says 14,320 kWh, that number must be preserved exactly as received — even after we normalize it, convert units, apply emission factors, and calculate tonnes of CO₂e.

This leads to a **two-layer architecture**:

1. **Raw Layer** — Immutable records exactly as received from the source system. Original field names, original units, original values. Never modified after ingestion.
2. **Normalized Layer** — Derived emission records with standardized units (tCO₂e), scope classification, and calculated values. These are what analysts review and approve. Each one links back to its raw source.

### Why Two Layers?

**Alternative considered:** Single table with both raw and normalized fields.

**Why rejected:** A single table conflates two concerns. When an emission factor is updated, you'd need to re-calculate in place, destroying the previous value. With two layers, you can re-run normalization against the same immutable raw data. Auditors can always compare the raw input to the normalized output. And the raw layer serves as an immutable audit trail of what was actually received.

**Alternative considered:** Event sourcing (append-only log of all changes).

**Why rejected:** Event sourcing is architecturally elegant but operationally complex for a 4-day prototype. The two-layer model gives us the key benefit (immutable source data) without the complexity (event replay, projections, eventual consistency). In production, you'd consider event sourcing for the review workflow specifically.

---

## Entity Relationship Overview

```
Tenant
  │
  ├── DataSource (configured source for this tenant)
  │     │
  │     └── IngestionJob (one file upload / import event)
  │           │
  │           └── RawRecord (immutable source record, 1 per row in source file)
  │                 │
  │                 └── EmissionRecord (normalized, calculated emission)
  │                       │
  │                       └── ReviewAction (audit trail of review decisions)
  │
  ├── EmissionFactor (tenant-specific overrides, or system defaults)
  │
  └── AuditLog (system-wide append-only log)
```

---

## Table Definitions

### 1. `core_tenant`

**Purpose:** Represents a client organization. All data is scoped to a tenant. This is the root of multi-tenancy isolation.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | UUID | PK | Unique tenant identifier |
| `name` | VARCHAR(255) | NOT NULL, UNIQUE | Organization name |
| `slug` | VARCHAR(100) | NOT NULL, UNIQUE | URL-safe identifier |
| `is_active` | BOOLEAN | DEFAULT TRUE | Soft-delete / deactivation |
| `created_at` | TIMESTAMPTZ | NOT NULL, auto | When tenant was created |
| `updated_at` | TIMESTAMPTZ | NOT NULL, auto | Last modification |

**Indexes:**
- `UNIQUE(slug)` — for URL routing and API filtering

**Why UUID for PK?** Sequential integers leak information (tenant count, creation order). UUIDs prevent enumeration attacks and are better for distributed systems. For a prototype this doesn't matter much, but it's the right default for multi-tenant SaaS.

**Why `slug`?** API URLs like `/api/v1/tenants/acme-corp/` are more readable than UUID-based URLs for debugging and support.

**Future scalability:** Row-level security (RLS) in PostgreSQL could enforce tenant isolation at the database level, eliminating the risk of application-layer bugs leaking data across tenants.

---

### 2. `ingestion_datasource`

**Purpose:** Represents a configured data source for a tenant. A tenant might have multiple SAP systems, multiple utility accounts, or multiple travel platforms. Each gets its own DataSource entry.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | UUID | PK | Unique identifier |
| `tenant_id` | UUID | FK → core_tenant, NOT NULL | Owning tenant |
| `name` | VARCHAR(255) | NOT NULL | Human-readable name (e.g., "SAP Munich Plant") |
| `source_type` | VARCHAR(20) | NOT NULL, CHECK IN ('sap', 'utility', 'travel') | Category of source |
| `description` | TEXT | NULLABLE | Notes about this source |
| `configuration` | JSONB | DEFAULT '{}' | Source-specific config (e.g., expected columns, unit mappings) |
| `is_active` | BOOLEAN | DEFAULT TRUE | Whether this source is active |
| `created_at` | TIMESTAMPTZ | NOT NULL, auto | |
| `updated_at` | TIMESTAMPTZ | NOT NULL, auto | |

**Indexes:**
- `(tenant_id, source_type)` — common filter pattern: "show me all SAP sources for this tenant"
- `(tenant_id, is_active)` — active sources for a tenant

**Why `source_type` as a constrained VARCHAR instead of an integer enum?** Readability. When you query the database directly, `source_type = 'sap'` is instantly readable. Integer enums require a lookup. For three values, the storage difference is negligible.

**Why `configuration` as JSONB?** Each source type has different configuration needs. SAP might need a plant code mapping. Utility might need a grid region. Travel might need default cabin class. JSONB lets us store this without a separate config table per source type, while still being queryable in PostgreSQL.

**Future scalability:** When adding new source types (e.g., fleet telematics, manual spreadsheet entry), you add a new `source_type` value and a new parser — no schema changes needed.

---

### 3. `ingestion_ingestionjob`

**Purpose:** Represents a single upload/import event. One CSV file upload = one IngestionJob. This provides batch-level tracking: how many records were in the file, how many succeeded, how many failed, who uploaded it, when.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | UUID | PK | Unique identifier |
| `tenant_id` | UUID | FK → core_tenant, NOT NULL | Owning tenant |
| `data_source_id` | UUID | FK → ingestion_datasource, NOT NULL | Which source this came from |
| `file_name` | VARCHAR(500) | NOT NULL | Original uploaded filename |
| `file_hash` | VARCHAR(64) | NULLABLE | SHA-256 hash of uploaded file (duplicate detection) |
| `status` | VARCHAR(20) | NOT NULL, DEFAULT 'processing' | processing, completed, completed_with_errors, failed |
| `total_rows` | INTEGER | DEFAULT 0 | Total rows in the source file |
| `successful_rows` | INTEGER | DEFAULT 0 | Rows that parsed and normalized successfully |
| `failed_rows` | INTEGER | DEFAULT 0 | Rows that failed validation |
| `error_summary` | JSONB | DEFAULT '[]' | List of errors encountered during processing |
| `uploaded_by` | VARCHAR(255) | NOT NULL | User who initiated the upload |
| `started_at` | TIMESTAMPTZ | NOT NULL, auto | When processing began |
| `completed_at` | TIMESTAMPTZ | NULLABLE | When processing finished |
| `created_at` | TIMESTAMPTZ | NOT NULL, auto | |

**Indexes:**
- `(tenant_id, status)` — "show me all failed jobs for this tenant"
- `(tenant_id, data_source_id, created_at DESC)` — latest jobs per source
- `(file_hash)` — duplicate file detection

**Why `file_hash`?** Prevents accidental double-uploads. If someone uploads the same CSV twice, we can warn them. SHA-256 is fast and collision-resistant.

**Why `error_summary` as JSONB?** Errors are heterogeneous (missing field on row 5, invalid date on row 12, unknown unit on row 23). A structured JSON array is more flexible than a TEXT blob and can be rendered as a list in the UI.

**Why separate `total_rows`, `successful_rows`, `failed_rows`?** These are the first thing an analyst checks after upload. "Did everything come through?" Having them as top-level fields avoids counting queries against RawRecord every time the job detail is viewed.

---

### 4. `ingestion_rawrecord`

**Purpose:** Stores exactly one row from the source file, exactly as received. This is the immutable source-of-truth layer. The `raw_data` field contains the original values with original field names and units. This record is never modified after creation.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | UUID | PK | Unique identifier |
| `tenant_id` | UUID | FK → core_tenant, NOT NULL | Owning tenant (denormalized for query performance) |
| `ingestion_job_id` | UUID | FK → ingestion_ingestionjob, NOT NULL | Which upload batch |
| `source_row_number` | INTEGER | NOT NULL | Row number in original file (for error reporting) |
| `raw_data` | JSONB | NOT NULL | Complete original row as key-value pairs |
| `is_valid` | BOOLEAN | NOT NULL, DEFAULT TRUE | Whether validation passed |
| `validation_errors` | JSONB | DEFAULT '[]' | List of validation issues found |
| `created_at` | TIMESTAMPTZ | NOT NULL, auto | |

**Indexes:**
- `(ingestion_job_id, source_row_number)` — lookup by position in original file
- `(tenant_id, is_valid)` — find invalid records for a tenant
- GIN index on `raw_data` — allows querying into the JSON structure

**Why `raw_data` as JSONB instead of typed columns?**

This is a critical design decision. The three source types have completely different schemas:
- SAP: EBELN, MATNR, WERKS, MENGE, MEINS, LIFNR, BEDAT, NETPR, WAERS...
- Utility: account_number, meter_number, billing_start, billing_end, usage_kwh, demand_kw...
- Travel: employee_id, trip_id, expense_type, origin, destination, amount, currency...

**Alternatives considered:**
1. **Separate tables per source type** (RawSapRecord, RawUtilityRecord, RawTravelRecord): More type-safe, but triplicates the schema. Querying across sources requires UNION ALL. Adding a new source type requires a migration.
2. **Single table with all possible columns** (wide table): Most columns would be NULL for any given source type. Schema changes needed for every new field.
3. **JSONB** (chosen): Flexible, queryable in PostgreSQL, and accurately reflects the reality that source schemas vary and evolve. The normalization layer extracts typed values.

**Why is `tenant_id` denormalized here?** It could be derived via `ingestion_job.data_source.tenant_id`. But that's a 3-join path. Since every query filters by tenant (for isolation), having it directly on the record avoids expensive joins on what will be the largest table.

**Future scalability:** Partitioning by `tenant_id` would be the first optimization when data volume grows. PostgreSQL native partitioning supports this with minimal application changes.

---

### 5. `emissions_emissionfactor`

**Purpose:** Lookup table for emission conversion factors. Maps an activity (burning diesel, consuming grid electricity, flying short-haul economy) to a CO₂e emission factor. Sourced primarily from DEFRA/DESNZ (UK Government) and EPA (US).

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | UUID | PK | Unique identifier |
| `tenant_id` | UUID | FK → core_tenant, NULLABLE | NULL = system default; set = tenant override |
| `category` | VARCHAR(50) | NOT NULL | e.g., 'fuel', 'electricity', 'travel_flight', 'travel_rail', 'travel_car' |
| `subcategory` | VARCHAR(100) | NOT NULL | e.g., 'diesel', 'petrol', 'grid_average', 'short_haul_economy' |
| `scope` | SMALLINT | NOT NULL, CHECK IN (1, 2, 3) | GHG Protocol scope |
| `unit_numerator` | VARCHAR(20) | NOT NULL | e.g., 'kgCO2e' — the emission unit |
| `unit_denominator` | VARCHAR(20) | NOT NULL | e.g., 'litre', 'kWh', 'passenger-km' — per unit of activity |
| `factor_value` | DECIMAL(12,6) | NOT NULL | The conversion factor |
| `source_reference` | VARCHAR(255) | NOT NULL | e.g., 'DEFRA 2024 - Fuels, Liquid fuels, Diesel (average biofuel blend)' |
| `valid_from` | DATE | NOT NULL | Start of validity period |
| `valid_to` | DATE | NULLABLE | End of validity (NULL = currently valid) |
| `region` | VARCHAR(100) | NULLABLE | Geographic applicability (e.g., 'UK', 'US-WECC', 'Global') |
| `created_at` | TIMESTAMPTZ | NOT NULL, auto | |

**Indexes:**
- `(category, subcategory, scope, valid_from)` — primary lookup path
- `(tenant_id, category)` — tenant-specific overrides

**Why `tenant_id` is nullable?** System-wide default factors (from DEFRA/EPA) have `tenant_id = NULL`. A specific tenant can override a factor if they have a supplier-specific emission factor or a different regional grid factor. The lookup logic is: try tenant-specific first, fall back to system default.

**Why `valid_from`/`valid_to` instead of a `year` field?** Emission factors can change mid-year (though usually annually). Date ranges are more precise and support retroactive corrections.

**Why `unit_numerator` and `unit_denominator` instead of just `unit`?** Emission factors are ratios. "2.68 kgCO₂e per litre of diesel" has both a numerator (kgCO₂e) and a denominator (litre). Storing both enables the normalization service to validate unit compatibility: if the raw data is in gallons but the factor expects litres, we know a unit conversion is needed.

**Design note on scope classification:**
- **Scope 1:** Direct emissions from owned/controlled sources. SAP fuel data → Scope 1.
- **Scope 2:** Indirect emissions from purchased electricity/energy. Utility data → Scope 2.
- **Scope 3 (Category 6):** Business travel. Travel data → Scope 3.

The scope is stored on the emission factor rather than inferred from source type, because some edge cases cross boundaries (e.g., electricity for company-owned EV charging could be Scope 2 but relates to fleet data).

---

### 6. `emissions_emissionrecord`

**Purpose:** The core normalized emission record. One RawRecord produces one EmissionRecord (or zero, if the raw record is invalid). Contains standardized units, scope classification, calculated emissions in tCO₂e, and the review workflow status.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | UUID | PK | Unique identifier |
| `tenant_id` | UUID | FK → core_tenant, NOT NULL | Owning tenant |
| `raw_record_id` | UUID | FK → ingestion_rawrecord, NOT NULL, UNIQUE | Source raw record (1:1) |
| `data_source_id` | UUID | FK → ingestion_datasource, NOT NULL | Which source (denormalized) |
| `scope` | SMALLINT | NOT NULL, CHECK IN (1, 2, 3) | GHG Protocol scope |
| `category` | VARCHAR(100) | NOT NULL | Activity category (e.g., 'stationary_combustion', 'purchased_electricity', 'business_travel_flight') |
| `description` | VARCHAR(500) | NULLABLE | Human-readable description of the activity |
| `activity_date` | DATE | NOT NULL | When the activity occurred (normalized from source date) |
| `reporting_period_start` | DATE | NULLABLE | Start of the reporting period (for utility billing periods) |
| `reporting_period_end` | DATE | NULLABLE | End of the reporting period |
| `quantity_value` | DECIMAL(14,4) | NOT NULL | Normalized activity quantity |
| `quantity_unit` | VARCHAR(30) | NOT NULL | Unit of activity (e.g., 'litre', 'kWh', 'passenger-km') |
| `original_quantity_value` | DECIMAL(14,4) | NULLABLE | Original value before unit conversion |
| `original_quantity_unit` | VARCHAR(30) | NULLABLE | Original unit from source |
| `emission_factor_id` | UUID | FK → emissions_emissionfactor, NULLABLE | Which factor was applied |
| `emission_factor_value` | DECIMAL(12,6) | NULLABLE | Snapshot of the factor value at calculation time |
| `co2e_kg` | DECIMAL(14,4) | NULLABLE | Calculated emissions in kgCO₂e |
| `co2e_tonnes` | DECIMAL(14,6) | NULLABLE | Calculated emissions in tCO₂e (co2e_kg / 1000) |
| `status` | VARCHAR(20) | NOT NULL, DEFAULT 'pending' | Workflow status: pending, flagged, reviewed, approved, locked |
| `flags` | JSONB | DEFAULT '[]' | Automated quality flags (e.g., 'high_value', 'missing_data', 'unit_mismatch') |
| `analyst_notes` | TEXT | NULLABLE | Free-text notes from the reviewing analyst |
| `reviewed_by` | VARCHAR(255) | NULLABLE | Who reviewed this record |
| `reviewed_at` | TIMESTAMPTZ | NULLABLE | When it was reviewed |
| `approved_by` | VARCHAR(255) | NULLABLE | Who approved this record |
| `approved_at` | TIMESTAMPTZ | NULLABLE | When it was approved |
| `locked_at` | TIMESTAMPTZ | NULLABLE | When it was locked for audit |
| `created_at` | TIMESTAMPTZ | NOT NULL, auto | |
| `updated_at` | TIMESTAMPTZ | NOT NULL, auto | |

**Indexes:**
- `(tenant_id, scope, status)` — the primary dashboard query: "how many Scope 1 records are pending for this tenant?"
- `(tenant_id, status, activity_date)` — records by status and date range
- `(tenant_id, data_source_id, activity_date)` — records by source and date
- `(raw_record_id)` UNIQUE — enforces 1:1 with raw record
- `(status)` — filter by workflow status across tenants (admin view)

**Why 1:1 with RawRecord (not 1:many)?**

**Alternative considered:** One raw record producing multiple emission records (e.g., splitting a utility bill across months).

**Why rejected for the prototype:** 1:1 is simpler to reason about, simpler to audit ("this emission came from this source row"), and covers the common case. The uncommon case (apportioning a billing period across months) is handled by using the midpoint date or the billing period fields, not by splitting records.

**Why snapshot `emission_factor_value`?** Emission factors change yearly. If we only stored a FK to the factor table, re-querying would give the current factor, not the one used at calculation time. The snapshot preserves auditability: "this record was calculated using factor 2.68 kgCO₂e/litre, which was the DEFRA 2024 diesel factor."

**Why both `original_quantity_*` and `quantity_*`?** Auditability. If the source said "500 gallons" and we converted to "1,892.7 litres", both values are preserved. An auditor can verify the conversion.

**Why `co2e_kg` AND `co2e_tonnes`?** Redundant, but intentional. Analysts think in tonnes for reporting, but kg is the natural calculation unit (most emission factors are in kgCO₂e). Storing both avoids repeated division in queries and aggregations.

**Why `flags` as JSONB?** A record can have multiple flags simultaneously (e.g., both "high_value" AND "estimated_read"). An array of flag objects is more flexible than boolean columns like `is_high_value`, `is_estimated`, etc., because new flag types can be added without migrations.

**Why denormalize `data_source_id`?** It's derivable from `raw_record.ingestion_job.data_source_id`. But "show me all emissions from SAP sources" is a common query. Denormalizing avoids two joins.

**Status lifecycle:**
```
PENDING ──── analyst reviews ────→ REVIEWED
   │                                    │
   └─ system flags ─→ FLAGGED          │
                         │              ▼
                         └──→ REVIEWED → APPROVED → LOCKED
                                  │
                                  └──→ REJECTED → PENDING
```

**Future scalability:**
- Add `reporting_year` and `reporting_quarter` as computed fields for faster aggregation
- Partition by `tenant_id` or `activity_date` for large datasets
- Add `calculation_methodology` field for market-based vs location-based Scope 2

---

### 7. `emissions_reviewaction`

**Purpose:** Append-only log of every review workflow action taken on an emission record. This is the detailed audit trail for the review process. While the EmissionRecord stores the current status, this table stores the complete history.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | UUID | PK | Unique identifier |
| `tenant_id` | UUID | FK → core_tenant, NOT NULL | Owning tenant |
| `emission_record_id` | UUID | FK → emissions_emissionrecord, NOT NULL | Which record was acted on |
| `action` | VARCHAR(20) | NOT NULL | 'review', 'approve', 'reject', 'flag', 'lock', 'edit' |
| `from_status` | VARCHAR(20) | NOT NULL | Status before this action |
| `to_status` | VARCHAR(20) | NOT NULL | Status after this action |
| `performed_by` | VARCHAR(255) | NOT NULL | User who performed the action |
| `reason` | TEXT | NULLABLE | Why this action was taken (required for reject) |
| `changes` | JSONB | DEFAULT '{}' | If action='edit', what fields were changed (before/after) |
| `created_at` | TIMESTAMPTZ | NOT NULL, auto | When this action occurred |

**Indexes:**
- `(emission_record_id, created_at)` — history for a specific record, in order
- `(tenant_id, action, created_at DESC)` — "show me all approvals for this tenant this month"
- `(performed_by, created_at DESC)` — "show me all actions by this analyst"

**Why separate from AuditLog?** The AuditLog (below) captures ALL system mutations (model saves, deletes, API calls). ReviewAction is specifically the review workflow — it's a domain concept, not a technical one. Analysts and managers will query ReviewActions ("who approved what?"). Only system admins would query the AuditLog.

**Why `from_status` and `to_status`?** Explicit state transitions are clearer than just logging the action. If someone reviews an already-reviewed record, the `from_status` tells you it was a re-review.

**Why `changes` as JSONB?** If an analyst edits a normalized value (e.g., corrects a quantity), we store `{"quantity_value": {"before": 500.0, "after": 450.0}, "reason": "Source file had typo, verified with client"}`. This gives auditors a complete change history.

---

### 8. `core_auditlog`

**Purpose:** System-wide, append-only audit log for ALL data mutations. This captures everything: record creation, updates, deletions, API calls, login events. This is the technical audit trail (complementing the domain-specific ReviewAction).

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | BIGINT | PK, AUTO | Sequential ID (for ordering) |
| `tenant_id` | UUID | NULLABLE | NULL for system-level events |
| `entity_type` | VARCHAR(100) | NOT NULL | Model name (e.g., 'EmissionRecord', 'IngestionJob') |
| `entity_id` | VARCHAR(255) | NOT NULL | PK of the affected record |
| `action` | VARCHAR(20) | NOT NULL | 'create', 'update', 'delete' |
| `changes` | JSONB | DEFAULT '{}' | Field-level changes (before/after) |
| `performed_by` | VARCHAR(255) | NOT NULL | User or system process |
| `ip_address` | VARCHAR(45) | NULLABLE | Client IP address |
| `user_agent` | VARCHAR(500) | NULLABLE | Client user agent |
| `created_at` | TIMESTAMPTZ | NOT NULL, auto | |

**Indexes:**
- `(entity_type, entity_id)` — "show me all changes to this specific record"
- `(tenant_id, created_at DESC)` — recent activity for a tenant
- `(performed_by, created_at DESC)` — activity by user

**Why BIGINT auto-increment PK instead of UUID?** The audit log needs guaranteed ordering. UUIDs don't guarantee sort order. BIGINT auto-increment ensures `id` order = chronological order, which simplifies pagination and "show me changes since X" queries.

**Why a separate audit log instead of using Django signals + the ReviewAction table?** ReviewAction is domain-specific (review workflow only). The AuditLog captures everything: ingestion job status changes, data source configuration changes, emission factor updates. These non-review events are important for security auditing ("who changed the emission factors?") but don't belong in the review workflow table.

**Future scalability:**
- Archive old audit logs to cold storage (S3/GCS) after a retention period
- Partition by `created_at` (monthly) for large volumes
- Add full-text search index on `changes` for searching audit history

---

## Normalization Pipeline Data Flow

```
SAP CSV Row:
  MATNR=DIESEL-001, WERKS=1000, MENGE=500, MEINS=L, BEDAT=15.03.2024
    ↓
RawRecord.raw_data = {"MATNR": "DIESEL-001", "WERKS": "1000", "MENGE": "500", "MEINS": "L", "BEDAT": "15.03.2024"}
    ↓
Normalization Service:
  - Parse date: 15.03.2024 → 2024-03-15
  - Identify fuel type: DIESEL-001 → diesel
  - Classify scope: fuel combustion → Scope 1
  - Quantity: 500 L (no conversion needed, factor expects litres)
  - Look up emission factor: DEFRA 2024 Diesel = 2.70 kgCO₂e/litre
  - Calculate: 500 × 2.70 = 1,350 kgCO₂e = 1.350 tCO₂e
    ↓
EmissionRecord:
  scope=1, category='stationary_combustion', activity_date=2024-03-15
  quantity_value=500.0000, quantity_unit='litre'
  emission_factor_value=2.700000, co2e_kg=1350.0000, co2e_tonnes=1.350000
  status='pending'
```

---

## Multi-Tenancy Strategy

**Approach:** Shared database, shared schema, tenant_id column on every table.

**Alternatives considered:**
1. **Separate databases per tenant:** Maximum isolation but operationally complex (migrations, backups, connection pooling per tenant).
2. **Separate schemas per tenant:** Good isolation, supported by PostgreSQL, but complicates Django ORM and migrations.
3. **Shared schema with `tenant_id`** (chosen): Simplest to implement. Tenant isolation enforced at the application layer (middleware + queryset filtering).

**Why chosen:** For a prototype with a single demo tenant, shared schema is correct. The `tenant_id` column on every table demonstrates that multi-tenancy was considered from the start. In production, you'd add PostgreSQL Row-Level Security (RLS) as a defense-in-depth measure.

**Implementation:**
- Django middleware extracts tenant from request (header or URL)
- Custom manager/queryset automatically filters by tenant
- Serializers validate that referenced objects belong to the same tenant
- All API endpoints are tenant-scoped

---

## Indexing Strategy

Indexes are chosen based on expected query patterns:

| Query Pattern | Table | Index |
|--------------|-------|-------|
| "All emissions for tenant X with status Y" | EmissionRecord | `(tenant_id, status)` |
| "Dashboard: emissions by scope for tenant X" | EmissionRecord | `(tenant_id, scope, status)` |
| "All raw records from upload job Y" | RawRecord | `(ingestion_job_id)` |
| "Audit history for record Z" | ReviewAction | `(emission_record_id, created_at)` |
| "Recent activity by analyst A" | ReviewAction | `(performed_by, created_at DESC)` |
| "Duplicate file detection" | IngestionJob | `(file_hash)` |
| "Latest jobs for source S" | IngestionJob | `(tenant_id, data_source_id, created_at DESC)` |

**Not indexed (intentionally):**
- `EmissionRecord.description` — free text, would need full-text search index. Not justified until data volume warrants it.
- `RawRecord.raw_data` deep paths — GIN index on the JSONB column covers basic lookups. Path-specific indexes are premature.

---

## Data Integrity Constraints

1. **Foreign keys** enforce referential integrity (no orphaned records)
2. **CHECK constraints** on `scope` (1, 2, 3) and `status` (valid values only)
3. **UNIQUE on `raw_record_id`** in EmissionRecord enforces 1:1 relationship
4. **NOT NULL** on all critical fields (no emission record without a quantity or scope)
5. **TIMESTAMPTZ** (not TIMESTAMP) for all datetime fields — timezone-aware storage prevents ambiguity
6. **DECIMAL** (not FLOAT) for financial and emission values — no floating-point precision errors

---

## Schema Migration Strategy

Django's migration framework handles schema evolution. Key considerations:

1. **Initial migration** creates all tables with proper constraints and indexes
2. **Seed migration** loads default emission factors (DEFRA 2024 values)
3. **Forward-only** — no squashed migrations in a prototype. Each migration is reviewable.
4. All migrations are committed to version control and applied automatically on deployment.
