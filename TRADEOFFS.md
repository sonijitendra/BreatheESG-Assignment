# Architectural Tradeoffs — Breathe ESG Prototype

As a Staff Software Engineer and Principal Data Architect, I believe the quality of a system is defined not just by what you build, but by what you **intentionally choose not to build**.

To maximize velocity and focus 100% on the core competencies evaluated in this assignment (data model quality, source realism, normalization logic, and verification workflows), several features were deliberately omitted. Each omission is detailed below with its rationale, business impact, and production implementation blueprint.

---

## 1. Authentication and Role-Based Authorization (RBAC)

### What Was Omitted
We have omitted user accounts, sessions, passwords, JWT authentication, and group-based permission rules. A hardcoded analyst user (`system_analyst`) is assumed for all record transitions.

### Rationale
Implementing robust auth (e.g., Django-allauth, custom JWT, or Auth0 integrations) is a well-understood commodity problem. In a 4-day hiring prototype, spending 2 days building secure password resets, token refreshing, and decorator checks adds zero value to evaluating **ESG data normalization, multi-tenant isolation, and auditability**.

### Business Impact
- **Security:** The prototype is entirely insecure and should only be run in isolated local environments or private VPCs.
- **Audit Defensibility:** An auditor cannot *prove* that `system_analyst` was actually the human operating the console without correlating IP addresses and external network logs.

### Production Blueprint
1. Integrate **Auth0** or **Okta** via standard OpenID Connect (OIDC) protocols.
2. Store users as custom profile objects in Django.
3. Map groups to three standard ESG roles:
   - `ESG Analyst`: Can ingest data, edit draft quantity values, and apply the `review` action.
   - `ESG Reviewer / Manager`: Can apply the `approve` or `reject` actions.
   - `Financial Auditor`: Read-only access to emission ledgers, audit logs, and calculation factors.
4. Implement decorator checks (e.g., DRF's `PermissionClasses`) to block analysts from approving their own records.

---

## 2. Asynchronous Ingestion Processing (Celery & Redis)

### What Was Omitted
All file uploads, parsing, row validations, and conversions are processed **synchronously** within the lifecycle of the single HTTP POST request.

### Rationale
For the provided sample files (<100 rows), synchronous processing completes in <200ms. Introducing **Celery, Redis/RabbitMQ, and background worker threads** introduces local development friction, complex deployment configurations, and heavy resource overhead on free hosting plans (like Render). 

### Business Impact
- **Scale:** If an enterprise client uploads a SAP procurement ledger containing 500,000 purchase lines, the synchronous HTTP thread will time out (e.g., Gunicorn's 30-second boundary), leaving the database in an inconsistent state.
- **UX:** The UI spinner blocks the analyst from doing other work while a large file is processing.

### Production Blueprint
1. Implement a **Celery + Redis** task worker pool.
2. Change the `upload` endpoint to immediately return an `IngestionJob` in status `processing` with a HTTP 202 Accepted.
3. Delegate the parser and normalization pipeline to an asynchronous Celery task:
   ```python
   @shared_task(bind=True)
   def run_ingestion_pipeline(self, job_id):
       # background parsing and normalization...
   ```
4. Configure the frontend to poll the job status or connect via **WebSockets (Django Channels)** to receive real-time row progress updates.

---

## 3. Market-Based Scope 2 Accounting Method

### What Was Omitted
The prototype implements only the **Location-based** calculation method for Scope 2 electricity emissions, using average regional grid factors.

### Rationale
The GHG Protocol Scope 2 Guidance requires dual reporting: Location-based and Market-based. Market-based calculations require tracking contractual instruments (e.g., Renewable Energy Certificates (RECs), Power Purchase Agreements (PPAs), and specific utility supplier tariffs). This would require a separate contracts sub-ledger, supplier allocation models, and a much more complex factor matching matrix. Location-based calculations are sufficient to demonstrate the engineering pipeline's capability.

### Business Impact
- **Compliance:** Multi-national clients reporting under GHG Protocol will fail full compliance audits without dual-reporting.
- **Abatement:** Clients who purchase green tariffs will see zero carbon reduction on their dashboard because location-based accounting reflects only physical grid averages.

### Production Blueprint
1. Extend `EmissionRecord` to store both `co2e_tonnes_location` and `co2e_tonnes_market`.
2. Add a `ContractualInstrument` model to track purchased RECs and PPAs, including dates, locations, and certificate IDs.
3. Update `normalization.py` to match the facility against active contracts. If an active REC covers the electricity consumed, apply a `0.000000 kgCO2e/kWh` factor. If not covered, fall back to the supplier-specific tariff factor, and finally to the grid average.

---

## 4. Automated & Dynamic Emission Factor Feeds

### What Was Omitted
Emission factors are seeded once via a static Django management command and stored in PostgreSQL. There is no automated synchronization with API databases or bulk historical re-calculation engine.

### Rationale
Seeding the database with official 2024 DEFRA and EPA factors is the most defensible way to ensure mathematical accuracy in a prototype without adding fragile network dependecies on external APIs.

### Business Impact
- **Maintenance:** Sustainability managers must manually add next year's factors or run SQL seed scripts annually.
- **Historical Drift:** If an emission factor is updated retroactively (e.g., EPA refines grid estimates), existing locked records will not reflect the correction unless manually recalculating.

### Production Blueprint
1. Integrate with the **Climatiq API** or standard ESG factor endpoints to pull annual DEFRA, EPA, and IEA datasets automatically.
2. Build an asynchronous **historical recalculation workflow** that queries all `pending` or `flagged` records within the factor's validity dates, updates their emission numbers, and appends a `re-calculated` tag to the `ReviewAction` log.

---

## 5. Automated PDF Utility Invoice OCR & Parsing

### What Was Omitted
Facility managers must upload structured CSV exports from utility portals. There is no native ability to scan PDF invoices.

### Rationale
Utility bill parsing is a highly specialized NLP/Vision task. Building a reliable PDF OCR extractor requires training machine learning models or integrating expensive enterprise document services (such as AWS Textract or Google Document AI), which is far beyond the scope of a core architecture assignment.

### Business Impact
- **Friction:** Facilities teams must manually compile spreadsheets or download portal exports, slowing down monthly reporting cycles.

### Production Blueprint
1. Create a PDF ingestion pipeline that stores uploaded documents in an S3 Bucket.
2. Trigger an asynchronous task that passes the PDF to **Google Document AI (Utility Parser schema)**.
3. Parse the extracted JSON output (start date, end date, usage, meter, cost) into our standardized `parser_utility` dictionary format, and continue through the existing `normalization.py` workflow.
