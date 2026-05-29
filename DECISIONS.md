# Design Decisions

Every non-obvious choice made during the design and implementation of this system, documented with the ambiguity that prompted it, the alternatives considered, and the reasoning behind what was chosen.

---

## Architecture Decisions

### 1. Monolith vs Microservices

**Ambiguity:** The assignment describes a multi-source ingestion platform with separate parsers, a normalization pipeline, a review workflow, and a dashboard. This could be decomposed into independent services.

**What we chose:** Django monolith with an internal services layer.

**Why:**
- This is a 4-day prototype. Microservices introduce deployment complexity (Docker Compose at minimum, Kubernetes at worst), inter-service communication (HTTP/gRPC), distributed tracing, and independent deployment pipelines — all of which consume time without adding business value at this scale.
- A well-structured monolith IS the correct architecture for a small team and bounded scope. Basecamp, Shopify, and GitHub all started as monoliths. The architecture should match the team size and operational maturity.
- The services layer inside the monolith gives us the same logical separation. `IngestionService`, `NormalizationService`, and `ReviewService` are importable Python classes with clear interfaces. If we needed to extract one to a microservice later, the refactor would be straightforward because the boundaries already exist.

**Alternatives rejected:**
- **Microservices (separate ingestion, normalization, review services):** Adds Docker, message queues, service discovery, API gateway, circuit breakers. Zero benefit for a prototype with one developer and demo-sized data. Would spend 2 of 4 days on infrastructure.
- **Serverless (Lambda/Cloud Functions):** Cold start latency, 15-minute execution limits, complex local development story. Doesn't match Django's ORM-centric data access patterns.

**Questions for the PM:**
- What's the expected team size at launch? If it's >5 engineers, microservice boundaries should be planned earlier.

---

### 2. Services Layer vs Fat Models vs Fat Views

**Ambiguity:** Django has no prescribed pattern for where business logic lives. The community is split between "fat models," "fat views," and dedicated service layers.

**What we chose:** Thin views + thin models + a services layer (`services/` directory with `IngestionService`, `NormalizationService`, etc.).

**Why:**
- **Fat views** couple HTTP request/response handling to domain logic. You can't reuse the normalization logic in a management command or a Celery task without importing the view.
- **Fat models** couple ORM persistence to business rules. When the normalization logic needs to call an external API for emission factors, or when the review workflow needs to send a notification, embedding that in the model creates circular dependencies and untestable code.
- **Services** are plain Python classes that accept data, apply business rules, and return results. They're independently testable (mock the ORM, test the logic), independently replaceable (swap the normalization algorithm without touching models or views), and reusable across entry points (API views, management commands, Celery tasks).

**Alternatives rejected:**
- **Fat models (Django tradition):** Works for simple CRUD. Breaks down when business logic spans multiple models (e.g., normalization touches RawRecord, EmissionFactor, and EmissionRecord). Model methods that call other models create implicit coupling.
- **Fat views (quick-and-dirty):** The most common anti-pattern. Makes testing require HTTP mocking. Business logic is scattered across view functions with no clear boundaries. Fine for a TODO app, unacceptable for an ESG platform.
- **Django's `Manager` pattern:** Good for query-related logic, but normalization isn't a query — it's a transformation pipeline. Managers are the wrong abstraction for this.

---

### 3. Synchronous vs Asynchronous Ingestion

**Ambiguity:** CSV file processing could block the HTTP request for seconds (or minutes for large files). Should we process inline or offload to a background worker?

**What we chose:** Synchronous processing in the request/response cycle.

**Why:**
- The prototype handles demo-sized files (tens to hundreds of rows). Processing completes in under a second.
- Celery would be the correct choice for production, but it requires a message broker (Redis or RabbitMQ), a separate worker process, result backend configuration, and retry/failure handling. That's 1-2 days of infrastructure work.
- The architecture is designed so that `IngestionService.process_file()` is a self-contained method. Moving it to a Celery task is a one-line change: `@shared_task` decorator and calling `.delay()` instead of direct invocation.

**Alternatives rejected:**
- **Celery + Redis:** Correct for production. Adds `redis-server`, `celery worker`, `celery beat` processes. Three additional services to configure and monitor. For a prototype, this is over-engineering.
- **Django Channels (WebSocket for progress):** Even more infrastructure. The upload API would return a job ID, and the client would subscribe to a WebSocket for progress. Architecturally sound but 3x the implementation effort.
- **Thread pool:** Simpler than Celery but loses reliability (no retry, no persistence, worker death loses the job). Worst of both worlds.

**Known limitation:** Synchronous processing will time out for files with >10K rows. This is documented and understood.

**Questions for the PM:**
- What's the expected file size per upload? Hundreds of rows is fine synchronously. Millions requires Celery.

---

### 4. Repository Pattern — Why NOT Used

**Ambiguity:** Many enterprise architectures use a Repository pattern to abstract database access. Should we add a repository layer between services and the ORM?

**What we chose:** Services use Django ORM directly. No repository abstraction.

**Why:**
- Django's ORM already IS a repository. `EmissionRecord.objects.filter(tenant_id=x, scope=1)` is a clean, well-documented query interface. Wrapping it in `EmissionRepository.find_by_tenant_and_scope(x, 1)` adds a layer of indirection with zero benefit.
- We are not building for database portability. We chose PostgreSQL deliberately (for JSONB, GIN indexes, and row-level security). The repository pattern's primary benefit — swapping database backends — is not a requirement.
- The services layer already handles business logic separation. Adding repositories would create a `view → service → repository → ORM` call chain where `service → ORM` is sufficient.

**When a repository WOULD be appropriate:**
- If we needed to support multiple data stores (e.g., PostgreSQL for transactional data + Elasticsearch for search + Redis for caching), a repository could provide a unified interface.
- If the query logic became complex enough to warrant reuse across services, a query object pattern (lighter than a full repository) would be sufficient.

---

## Data Model Decisions

### 5. Two-Layer Model (Raw + Normalized)

**Ambiguity:** Should we store source data and calculated emissions in the same table, or separate them?

**What we chose:** Two layers — `RawRecord` (immutable source data) and `EmissionRecord` (normalized, calculated emissions). See [MODEL.md](MODEL.md) for full schema.

**Why:**
- **Auditability:** ESG auditors need to trace every emission number back to the original document. "This 1.35 tCO₂e came from 500 litres of diesel, which was row 7 in the SAP export uploaded on March 15th." Two layers make this trace explicit.
- **Re-processability:** When DEFRA publishes 2025 emission factors, we can re-run normalization against the same immutable raw data. A single table would require in-place updates, destroying the previous calculation.
- **Schema heterogeneity:** SAP, utility, and travel data have completely different schemas. The raw layer uses JSONB to accommodate this. The normalized layer has a consistent schema.

**Alternatives rejected:**
- **Single table with both raw and normalized fields:** Conflates two concerns. Update semantics become ambiguous (is this an "update" to the raw data or a "re-normalization"?). Column count explodes when adding new source types.
- **Event sourcing:** Architecturally elegant, but adds complexity (event store, projections, eventual consistency) that isn't justified for a prototype. The two-layer model gives us the key benefit (immutable source data) without the operational complexity (event replay, read model rebuilds).

---

### 6. JSONB for `raw_data` vs Typed Columns

**Ambiguity:** The `RawRecord` table stores source data. Should each field be a typed column, or should we use a single JSONB column?

**What we chose:** Single JSONB column (`raw_data`).

**Why:**
The three source types have completely different schemas:
- **SAP:** EBELN, MATNR, WERKS, MENGE, MEINS, LIFNR, BEDAT, NETPR, WAERS
- **Utility:** account_number, meter_number, billing_start, billing_end, usage_kwh, demand_kw
- **Travel:** employee_id, trip_id, expense_type, origin, destination, amount, currency

**Alternatives rejected:**
1. **Separate tables per source type** (RawSapRecord, RawUtilityRecord, RawTravelRecord): More type-safe, but triplicates the schema. Cross-source queries require `UNION ALL`. Adding a new source type requires a migration and a new model. Doesn't scale to 10+ source types.
2. **Single wide table with all possible columns:** Most columns would be NULL for any given source type. The table would have 40+ columns with maybe 12 populated per row. Schema changes needed for every new field from any source.
3. **EAV (Entity-Attribute-Value):** Extremely flexible but terrible for query performance and readability. Every "row" of source data becomes N rows in EAV. Aggregation queries become impossible without pivoting.

**Why JSONB specifically (not JSON):**
- JSONB is binary-formatted and supports GIN indexes for efficient querying
- JSONB supports containment operators (`@>`) and path queries (`->`, `->>`)
- JSON is stored as text and must be re-parsed on every access

---

### 7. UUID Primary Keys vs Integer Primary Keys

**Ambiguity:** PostgreSQL supports both auto-incrementing integers and UUIDs as primary keys.

**What we chose:** UUID (v4) for all models except `AuditLog`.

**Why:**
- **Security:** Sequential integers leak information. An attacker can enumerate resources (`/api/records/1`, `/api/records/2`, …). UUIDs are opaque and unguessable.
- **Multi-tenancy:** In a shared-schema multi-tenant system, integer sequences are shared. Tenant A sees record IDs 1, 3, 7 (gaps imply other tenants exist). UUIDs prevent this inference.
- **Distributed systems:** If we ever need to generate IDs client-side, in Celery workers, or in multiple application instances, UUIDs don't require coordination.

**Exception — AuditLog uses BigAutoField:**
- The audit log needs guaranteed chronological ordering. UUIDs (v4) are random and don't sort temporally.
- `id` order = insertion order = chronological order. This simplifies "show me the last 100 mutations" queries.
- BigAutoField supports 9.2 × 10¹⁸ records, which is sufficient for any practical audit log.

---

### 8. Denormalized `tenant_id` on RawRecord and EmissionRecord

**Ambiguity:** `tenant_id` is derivable from the foreign key chain (e.g., `EmissionRecord → RawRecord → IngestionJob → DataSource → Tenant`). Should we duplicate it?

**What we chose:** Store `tenant_id` directly on both `RawRecord` and `EmissionRecord`.

**Why:**
- Every query in a multi-tenant system filters by tenant. This is the WHERE clause on literally every API call.
- Without denormalization, the query "get all Scope 1 emissions for Tenant X" requires: `EmissionRecord → RawRecord → IngestionJob → DataSource` — three JOINs just to filter by tenant.
- With denormalization: `WHERE tenant_id = X AND scope = 1`. One table, one index scan.
- The `(tenant_id, scope, status)` composite index on `EmissionRecord` becomes the primary dashboard index. Without `tenant_id` on the table, this index is impossible.

**Tradeoff:** Denormalization creates a consistency risk — the `tenant_id` on `EmissionRecord` could theoretically disagree with the `tenant_id` on the related `IngestionJob`. We mitigate this in the service layer (always set `tenant_id` from the parent job) and could add a database trigger or CHECK constraint in production.

---

### 9. Emission Factor Snapshot on EmissionRecord

**Ambiguity:** When calculating emissions, we reference an `EmissionFactor` record. Should we store just the FK, or also snapshot the factor value?

**What we chose:** Store both `emission_factor_id` (FK) and `emission_factor_value` (snapshot of the decimal value at calculation time).

**Why:**
- Emission factors change annually. DEFRA publishes new factors every June. EPA updates eGRID factors periodically.
- If we only stored the FK, re-querying `EmissionRecord.emission_factor.factor_value` would give the current factor, not the one that was used to calculate this record.
- Example: Record calculated in March 2024 using DEFRA 2024 diesel factor (2.70 kgCO₂e/L). In July 2024, DEFRA 2025 factor is loaded (2.68 kgCO₂e/L). Without the snapshot, the record now appears to use 2.68, which is wrong.
- The snapshot makes the emission record self-contained and auditable without joining to the factor table.

**Questions for the PM:**
- When emission factors are updated, should we offer a "re-calculate with new factors" workflow? Our two-layer model supports this, but the workflow isn't built.

---

### 10. Storing Both `co2e_kg` AND `co2e_tonnes`

**Ambiguity:** These are redundant (`co2e_tonnes = co2e_kg / 1000`). Is storing both justified?

**What we chose:** Store both.

**Why:**
- Emission factors are published in kgCO₂e. The natural calculation is `quantity × factor = kgCO₂e`. Storing this avoids rounding issues from converting and back-converting.
- ESG reports use tCO₂e (tonnes). Dashboard aggregations sum `co2e_tonnes` directly without dividing every row.
- The storage cost is negligible (8 bytes per row for one extra DECIMAL column). The query simplification is meaningful — aggregation queries are the most common read pattern.
- Without `co2e_tonnes`, every dashboard query needs: `SUM(co2e_kg) / 1000 AS co2e_tonnes`. With it: `SUM(co2e_tonnes)`. Minor, but it eliminates a class of bugs where someone forgets the division.

---

## Source Handling Decisions

### 11. SAP: CSV Flat File (ALV Export) Over Other Integration Methods

**Ambiguity:** SAP has many data extraction mechanisms. Which one do we design for?

**What we chose:** CSV flat file simulating an ALV (ABAP List Viewer) export from transaction ME2M or MB51.

**Why this is the most realistic format:**
- In practice, a sustainability consultant asks the client's SAP admin: "I need all fuel purchases for 2024." The admin runs ME2M (Purchase Orders by Material), applies filters, clicks the ALV export button, exports to Excel, saves as CSV, and emails it.
- This is not a technical integration — it's a human workflow. The CSV is the artifact of that workflow.

**Alternatives rejected:**
- **IDoc (Intermediate Document):** SAP's B2B EDI format. Designed for automated system-to-system integration (e.g., purchase orders between SAP instances). No one uses IDocs for ad-hoc data handover to a sustainability platform. Requires SAP middleware configuration.
- **OData/API (SAP Gateway):** Requires S/4HANA or SAP Gateway configuration. Many clients are still on ECC 6.0 (pre-S/4HANA). Even S/4HANA clients rarely expose procurement APIs externally without significant IT involvement.
- **BAPI (Business Application Programming Interface):** Requires RFC connection, SAP .NET Connector or PyRFC, and VPN access to the client's SAP system. This is a deep technical integration, not a prototype data source.
- **SE16N (table browser):** Direct table export. Produces raw data but requires knowledge of SAP table names (EKKO, EKPO, MSEG). More realistic than IDoc but less common than ALV export — most business users don't know table names.

---

### 12. SAP: Handling German Column Headers

**Ambiguity:** SAP export language depends on the user's logon language. The same system can produce headers in English ("Material", "Quantity") or German ("Materialnummer", "Menge").

**What we chose:** Parser maps both German and English column names to canonical internal names.

**Why:**
- SAP was built in Germany. Many SAP installations, especially in manufacturing, still use German-language logon.
- The same export from the same system will have different headers depending on who exported it. The Munich admin exports in German; the London admin exports in English.
- A header mapping dictionary (`{"Materialnummer": "material_number", "MATNR": "material_number", "Material": "material_number"}`) handles this with minimal code.

**Limitation:** We handle German and English. French, Spanish, Portuguese, and other SAP languages are not mapped. This would need to be extended for a global deployment.

---

### 13. SAP: Identifying Fuel Type from Material Data

**Ambiguity:** SAP material numbers (MATNR) are opaque codes (e.g., "000000000000045678"). How do we know "45678" is diesel?

**What we chose:** Multi-signal approach using material group (MATKL) + description keyword matching.

**Why:**
- **Material number (MATNR)** is unique per client. "45678" means diesel at one company and lubricating oil at another. Useless without the client's MARA master data.
- **Material group (MATKL)** is more standardized. Groups like "FUEL", "DIESEL", "PETROL" are common. But naming varies by client.
- **Short text (TXZ01/MAKTX)** is human-readable but inconsistent. "Diesel EN590", "Gasöl", "AGO (Automotive Gas Oil)" all mean diesel.
- We combine: if MATKL contains "DIESEL" or "FUEL", and the description contains keywords like "diesel", "gasoil", "AGO", classify as diesel.

**Limitation:** This heuristic fails for clients who use numeric material groups or cryptic descriptions. In production, we'd need a client-specific mapping table configured during onboarding.

**Questions for the PM:**
- Should the onboarding workflow include a "map your material groups to fuel types" step?

---

### 14. Utility: Portal CSV Export Over Other Formats

**Ambiguity:** Utility billing data can come from many sources: portal downloads, PDF bills, Green Button XML, direct API integrations, or EPA ENERGY STAR Portfolio Manager.

**What we chose:** CSV simulating a utility portal export.

**Why:**
- Most facilities teams download a CSV from their utility provider's online portal. This is the universal lowest-common-denominator format.
- Some facilities teams maintain their own Excel spreadsheet, manually entering values from PDF bills. This produces the same CSV-like format.

**Alternatives rejected:**
- **PDF bills:** Require OCR/document AI (AWS Textract, Google Document AI). Significant ML investment. Out of scope for a prototype. See TRADEOFFS.md.
- **Green Button XML:** An industry standard (NAESB ESPI), but adoption is inconsistent. Mostly US residential utilities. Most commercial/industrial accounts don't support it.
- **Utility APIs:** Every utility has a different API (or none). There's no universal standard. Integration requires per-utility development.
- **EPA ENERGY STAR Portfolio Manager:** Good standardized format, but adds a third-party dependency. Not all clients use ENERGY STAR.

---

### 15. Utility: Billing Period Handling

**Ambiguity:** Utility billing periods don't align with calendar months. A bill might cover November 14 to December 15. How do we assign this to a reporting period?

**What we chose:** Store both start and end dates. Use the midpoint date as `activity_date`. Don't prorate across calendar months.

**Why:**
- Real utility billing periods are ~30 days but start on random dates. Trying to split a Nov 14 – Dec 15 bill into "November" and "December" portions requires assumptions about daily usage patterns.
- The midpoint approach assigns the entire bill to a single date, which is simple and auditable.
- For annual reporting (the most common ESG use case), the billing period alignment doesn't matter — 12 bills cover 12 months regardless of exact dates.

**Limitation:** Monthly reporting will show uneven values because billing periods don't align with month boundaries. This is a known limitation documented in the system.

**Future enhancement:** Prorate by day count. A Nov 14 – Dec 15 bill (32 days) would allocate 17/32 to November and 15/32 to December. This requires the `reporting_period_start` and `reporting_period_end` fields we've already included in the schema.

---

### 16. Utility: Location-Based Scope 2 Only

**Ambiguity:** GHG Protocol requires both location-based and market-based Scope 2 reporting. Which do we implement?

**What we chose:** Location-based only.

**Why:**
- Location-based uses grid-average emission factors (e.g., eGRID subregion averages in the US). It's the simpler, more universal method — every electricity consumer can use it.
- Market-based requires tracking contractual instruments: Renewable Energy Certificates (RECs), Power Purchase Agreements (PPAs), supplier-specific emission factors, and residual mix factors. This is a significant domain feature with its own data model.
- For a prototype, one method demonstrates the full calculation pipeline. The second method is the same pipeline with different factors.

**Questions for the PM:**
- Do clients need both methods from day one? Market-based Scope 2 is 1-2 days of additional work and significantly impacts the emission factor model.

---

### 17. Travel: Concur-Style CSV Export

**Ambiguity:** Corporate travel data can come from travel management companies (TMCs), expense platforms (Concur, Navan), corporate credit card feeds, or manual entry.

**What we chose:** CSV simulating a Concur expense report export.

**Why:**
- SAP Concur holds ~50%+ market share in enterprise expense management. It's the most likely source for corporate travel data.
- Concur's export format, while customizable, has a relatively standard set of fields: employee, date, expense type, amount, vendor, origin/destination for flights.
- The format is representative enough that a Navan, Egencia, or BCD Travel export would be structurally similar.

**Limitation:** Real Concur instances have highly customized fields (cost centers, project codes, approval hierarchies). Our parser handles a "standard" export, not every possible Concur configuration.

---

### 18. Travel: Flight Distance Calculation

**Ambiguity:** Travel expense exports typically include origin and destination airport codes but NOT distance. How do we calculate the distance needed for distance-based emission factors?

**What we chose:** Haversine formula (great-circle distance) + 8% uplift factor for routing inefficiency.

**Why:**
- The Haversine formula calculates the shortest distance between two points on a sphere. It's mathematically exact for the idealized case.
- Real flights don't follow great-circle routes — they detour around restricted airspace, follow jet streams, and use standard airways. DEFRA and the GHG Protocol recommend an 8% uplift to account for this.
- This is the industry-standard approach. DEFRA's methodology guidance explicitly references great-circle distance with uplift.

**Limitation:** The Haversine formula requires a lookup table of airport code → latitude/longitude. We include a static table of major airports. Missing airport codes will fall back to spend-based calculation.

---

### 19. Travel: Hotel Emissions as Spend-Based

**Ambiguity:** Hotel stays generate emissions, but expense reports rarely include the data needed for an activity-based calculation (e.g., room-nights, hotel energy intensity, country-specific grid factors).

**What we chose:** Spend-based calculation using EEIO (Environmentally Extended Input-Output) factors.

**Why:**
- Expense reports contain the hotel amount. That's it. No room-night count, no hotel star rating, no country-specific data.
- EEIO factors convert spend (e.g., $200 on "accommodation") to estimated kgCO₂e. They're the least accurate method but always applicable.
- DEFRA publishes hotel factors by country per room-night, but room-night data isn't available in typical expense exports.

**Limitation:** Spend-based hotel emissions can vary by 50%+ from actual emissions depending on hotel energy efficiency and local grid carbon intensity. This is a known limitation of the method, not of our implementation.

---

## Workflow Decisions

### 20. Review Status as String Enum vs Integer

**Ambiguity:** The review workflow has 5-6 states. Should these be stored as integers or strings?

**What we chose:** String enum (VARCHAR with CHECK constraint): `'pending'`, `'flagged'`, `'reviewed'`, `'approved'`, `'locked'`.

**Why:**
- When querying the database directly (which every developer and data analyst does), `WHERE status = 'pending'` is instantly readable. `WHERE status = 2` requires consulting documentation or a lookup table.
- For 5-6 values, the storage difference is negligible (~10 bytes vs ~2 bytes per row). On a table with millions of rows, this adds ~8MB. Not worth optimizing.
- Django's `TextChoices` provides the same validation guarantees as `IntegerChoices` but with readable database values.

---

### 21. Separate ReviewAction Table vs Audit Log Only

**Ambiguity:** Review actions (approve, reject, flag) could be logged in the system-wide AuditLog. Do we need a separate table?

**What we chose:** Separate `ReviewAction` table for domain workflow events, plus `AuditLog` for system-level mutations.

**Why:**
- **Different audiences:** Analysts and managers query ReviewActions — "Who approved this record? When? What was the reason for rejection?" System admins query AuditLog — "Who changed the emission factors? When was this data source configuration modified?"
- **Different schemas:** ReviewAction has `from_status`, `to_status`, `reason` (domain-specific fields). AuditLog has `entity_type`, `entity_id`, `ip_address` (generic mutation tracking).
- **Different retention:** ReviewActions are regulatory records (auditors need them for years). AuditLog entries for routine model saves could be archived after 90 days.

---

### 22. No Authentication in Prototype

**Ambiguity:** Should the prototype include user authentication and authorization?

**What we chose:** No authentication. A hardcoded analyst user identifier is used for all actions.

**Why:**
- The assignment is a 4-day prototype. Auth adds 2-3 days of work: JWT or session-based authentication, user registration, login/logout, password reset, role-based permissions, record-level access control.
- None of this demonstrates the core competency being evaluated: data model design, source parsing, normalization pipeline, and review workflow.
- A hardcoded user identifier still enables the review workflow to record "who" performed an action, preserving the audit trail structure.

**What production auth would look like:**
- Django REST Framework + `djangorestframework-simplejwt` for token-based auth
- Django-allauth or Auth0 for identity provider integration
- Role-based access: `analyst` (view, review), `reviewer` (approve), `admin` (configure, manage users)
- Tenant-scoped permissions: users belong to a tenant, can only access that tenant's data

---

## Open Questions for the PM

These are questions we'd ask before starting production development. The prototype makes reasonable assumptions for each, documented above, but production decisions should be confirmed.

1. **Data volume per client.** Hundreds vs millions of records per month affects whether synchronous ingestion is viable and whether we need Celery, table partitioning, and query optimization.

2. **Emission factor overrides.** Do clients need to override system-default emission factors (e.g., they have a supplier-specific fuel blend factor), or are DEFRA/EPA defaults sufficient? Our model supports tenant-specific overrides, but the UI/workflow for managing them isn't built.

3. **Workflow linearity.** Is the analyst workflow always linear (`pending → reviewed → approved → locked`), or can records skip steps? Can an admin directly lock a record? Can a rejected record be re-submitted?

4. **Concurrent review.** How many analysts review data concurrently? If two analysts review the same record simultaneously, do we need record-level locking (pessimistic or optimistic) to prevent conflicts?

5. **Tenant count and isolation.** What's the expected tenant count? Dozens → shared schema is fine. Thousands → we'd need schema-per-tenant or database-per-tenant for isolation and performance. Our `tenant_id` column approach works up to hundreds of tenants.

6. **Re-normalization workflow.** When emission factors are updated (annually), should we offer a "re-calculate historical records with new factors" workflow? Our two-layer model enables this — raw data is immutable, and normalized records can be regenerated. But the workflow (confirm, preview changes, apply, notify) isn't built.

7. **Scope 2 methodology.** Location-based vs market-based — do clients need both methods? Both are required by GHG Protocol for comprehensive reporting. Market-based requires significant additional data modeling (RECs, PPAs, contractual instruments). This is a product decision, not a technical one.

8. **Data correction workflow.** When a client discovers an error in source data (e.g., wrong quantity in the SAP export), what's the process? Re-upload the entire file? Edit individual records? Our model supports both, but the UI and validation for corrections aren't built.
