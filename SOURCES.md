# Upstream Data Sources Research & Realism — Breathe ESG

In ESG reporting, data does not arrive in neat, pre-sanitized API packages. It comes from heterogeneous legacy enterprise systems, disorganized utility portals, and complex corporate travel portals.

This document records the extensive industry research conducted to design a highly realistic, defensive ingestion platform for Breathe ESG.

---

## 1. SAP Fuel & Procurement Ingestion (Scope 1 & 2)

### Real-World Production Context
Typical enterprise clients do not integrate their production SAP ERP with an ESG platform on day one. Instead, an administrative business user runs a standard purchasing transaction code (such as **ME2M** for purchase orders by material, **MB51** for material documents, or **SE16/SE16N** for direct table views like `EKPO`) and exports the resulting ALV Grid list to an Excel spreadsheet, saving it as a CSV.

### Technical Field Registry
A realistic SAP export contains raw technical field names representing the underlying database tables (`EKKO` header and `EKPO` item):
- **EBELN** (Einkaufsbeleg) → Purchasing Document (PO) Number
- **MATNR** (Materialnummer) → Opaque Material Code (e.g. `000000000000450012`)
- **TXZ01** (Kurztext) → Short Description Text
- **WERKS** (Werk) → Plant / Facility Code
- **MENGE** (Bestellmenge) → Order Quantity
- **MEINS** (Mengeneinheit) → Order Unit of Measure
- **NETWR** (Nettowert) → Net Purchase Value
- **WAERS** (Währung) → Currency Key
- **NAME1** (Name 1) → Vendor Name
- **MATKL** (Warengruppe) → Material Group
- **BEDAT** (Bestelldatum) → Purchasing Document Date
- **BUKRS** (Buchungskreis) → Company Code
- **LOEKZ** (Löschkennzeichen) → Deletion Indicator (e.g., 'L')
- **STBLG** (Stornobeleg) → Reversal Document Number (indicates a cancelled entry)

### Data Quality Anomaly Rationale
Our seeded SAP sample data (`sample_data/sap_procurement.csv`) contains:
1. **German configurations:** Headers like `Materialnummer` and `Mengeneinheit` are mixed with English headers. This happens because SAP ALV exports generate column labels based on the user's active logon language.
2. **Reversals and deletions:** Includes records with `LOEKZ = 'L'` and records with an active `STBLG` reversal document. These represent cancelled purchases and must be filtered to prevent emission inflation.
3. **Opaque plant codes:** Codes like `WERKS = 'US01'` and `WERKS = 'UK02'` which are meaningless without a plant master data mapping table.
4. **Unit inconsistencies:** Fuel ordered in gallons (`GAL`) and kilograms (`KG`) alongside standard litres (`L`).

### What Breaks in Production
- **Custom material codes:** If the client changes their internal SAP material taxonomy, our keyword search (looking for `"diesel"`, `"petrol"`) will default to diesel, potentially misclassifying natural gas.
- **European decimal notations:** German systems represent decimals with commas (e.g., `1.500,50` instead of `1500.50`). Our parser includes a robust sanitizer for these formats.

---

## 2. Utility Electricity Billing Ingestion (Scope 2)

### Real-World Production Context
Facilities teams download billing data from utility portals (such as PG&E, National Grid, or ConEd) in flat CSV structures, or manually transcribe paper PDF bills into a master Excel file.

### Technical Field Registry
Unlike SAP, utility CSV portal exports do not use SAP codes. They use diverse column headers:
- **Account Number** (Acct No., Account #) → Corporate billing reference
- **Meter Number** (Meter ID, Meter No.) → Specific physical hardware meter
- **Billing Period Start & End** (From/To) → Calendar ranges of active consumption
- **Usage kWh** (Consumption, Total kWh) → Physical active energy consumed
- **Demand kW** (Peak Demand) → Maximum rate of energy draw (affects cost calculations)
- **Total Cost** (Amount Due, Bill Amount) → Total invoice cost
- **Read Type** (Meter Read Type) → Indicates whether the bill is based on an `Actual` physical reading or an `Estimated` algorithm.

### Data Quality Anomaly Rationale
Our seeded Utility sample data (`sample_data/utility_electricity.csv`) contains:
1. **Estimated reads:** Utility companies frequently estimate usage during bad weather or labor shortages, resolving discrepancies months later. Our system flags `read_type = 'estimated'` because estimates have a high error rate (up to 30%).
2. **Non-calendar billing periods:** Invoices start on arbitrary days (e.g. November 14 to December 15). To align these with calendar months, our platform calculates the midpoint of the billing range.
3. **Negative credits/adjustments:** Represents manual refunds or solar net-metering.
4. **Gaps in periods:** Visualized when a month of billing is missing (e.g. billing leaps from January directly to March), triggering audit flags.

### What Breaks in Production
- **Multi-meter premises:** When a single facility has 20 meters, simple imports result in overlapping billing dates. We resolve this in the schema by indexing on `(account_number, meter_number, billing_period)`.
- **MWh reporting:** Heavy industrial users receive invoices in Megawatt-hours (`MWh`). If imported directly as kWh, it creates a 1000x under-reporting error. Our normalization service checks and converts MWh to kWh.

---

## 3. Corporate Business Travel Ingestion (Scope 3)

### Real-World Production Context
Business travel is tracked in Travel Management Companies (TMCs) like SAP Concur or Navan. Expense managers export monthly travel spreadsheets containing ledger lines of airline bookings, hotel stays, and ground transit claims.

### Technical Field Registry
A representative corporate travel CSV contains:
- **Employee ID / Name** → Links travel to specific headcount
- **Department / Cost Center** → Standard accounting hierarchy for Scope 3 allocation
- **Expense Date** → Date of travel or purchase
- **Expense Type** (Category) → Airfare, Lodging, Taxi, Car Rental, Rail
- **Vendor Name** → Airline name, hotel chain, rideshare app
- **Origin / Destination** → Airport IATA codes (e.g., `LHR`, `JFK`)
- **Cabin Class** → Economy, Premium, Business, First (affects DEFRA flight multipliers)
- **Distance** → Flight or driving distance in miles or km (frequently blank for flights)
- **Amount & Currency** → Spend values (used for spend-based fallbacks)

### Data Quality Anomaly Rationale
Our seeded Travel sample data (`sample_data/travel_expenses.csv`) contains:
1. **Missing flight distances:** Flight booking lines with blank distances but active origin and destination airport codes (`JFK` to `LHR`). The platform calculates the great circle distance using the **Haversine formula** and appends the standard **8% routing uplift**.
2. **Missing cabin classes:** Defaulting to economy as a conservative baseline and flagging the record.
3. **Spend-based fallbacks:** Rental cars and hotel bills with spend data but zero distance or room-night data. The normalization service implements economic-input-output (EEIO) style calculations (e.g., estimating 1 hotel room night per $150 spend).

### What Breaks in Production
- **Airport codes missing in coordinates DB:** If a client flies to a regional airport not in our database, distance calculation falls back to default mileage. In production, this coordinates database should link to an official worldwide IATA dataset.
- **Multi-leg flight bookings:** Flights that stop (e.g., LHR -> DXB -> SIN) appearing as a single origin-destination record, creating a major under-calculation of takeoff emissions.
- **Flight radiative forcing:** The controversial DEFRA multiplier for high-altitude non-CO2 heat effects (radiative forcing). Our factors include radiative forcing multipliers to ensure maximum defensibility.
