# Data generator development plan — EBOS use cases

This plan covers **implementing all new data required by the EBOS use cases** ([docs/EBOS_USE_CASES.md](EBOS_USE_CASES.md)), **augmenting the existing `healthcare_data_generator`** where possible and adding separate generators only where the domain is orthogonal.

**Local/remote workflow**: For a high-level description of data generation and medallion (local vs Databricks, DuckDB/local dbt), see [data/README.md](../data/README.md).

---

## 1. Current state

### 1.1 Existing generators

| Asset                          | Location                           | Output                                                                                                                                                                |
| ------------------------------ | ---------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Healthcare data generator**  | `data/healthcare_data_generator/`  | `healthcare_pharmacies`, `healthcare_hospitals`, `healthcare_products`, `healthcare_orders`, `healthcare_inventory`, `healthcare_supply_chain_events` → Unity Catalog |
| **Healthcare medallion**       | `data/healthcare_data_medallion/`  | dbt bronze → silver → gold on the above                                                                                                                               |
| **Prescription PDF generator** | `data/prescription_pdf_generator/` | Synthetic prescription PDFs + JSON labels (files); no UC tables                                                                                                       |

### 1.2 Existing schema (relevant for extension)

- **products**: `product_id`, `name`, `generic_name`, `category`, `manufacturer`, `supplier` (string), `pbs_code`, `atc_code`, `unit_price`, `wholesale_price`, `retail_price`, `is_prescription`, `is_controlled_substance`, `requires_cold_chain`, `storage_type`, `expiry_months`, `batch_size`, `minimum_order_quantity`, `lead_time_days`, `active_ingredient`, `dosage_form`, `pack_size`, `created_date`, `last_updated`.
  **Missing for use cases**: `therapeutic_category`, `brand`, `generic_equivalent_id`, `pack_size_variants`, `margin_percentage`; and a proper **supplier_id** (supplier is currently a free-text field).
- **inventory**: keyed by `pharmacy_id`, `product_id`; has `batch_number`, `expiry_date`, `current_stock`, `reorder_level`, etc. No **warehouse_id** (only pharmacy_id).
- **orders**: `order_id`, `customer_id` (pharmacy_id or hospital_id), `product_id`, `order_date`, quantity, amounts, status, etc.
- **supply_chain_events**: `order_id`, `event_type`, `event_timestamp`, `location`, etc. Can be used for **order_status_events**-style tracking if we expose or derive it.

### 1.3 New data required by use case (from EBOS_USE_CASES.md)

| Use case                       | New tables / extensions                                                                                                                                                          | Source (extend vs new)                                                |
| ------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------- |
| **1. Recommendation Engine**   | `substitution_events`, `product_interactions`, `inventory_availability`; **products** +therapeutic_category, brand, generic_equivalent_id, pack_size_variants, margin_percentage | Extend healthcare generator                                           |
| **2. Inventory Optimisation**  | `expiry_batches`, `writeoff_events`, `purchase_orders`, `supplier_performance`                                                                                                   | Extend healthcare generator                                           |
| **3. Customer Service Agents** | `customer_service_cases`, `case_messages`, `knowledge_documents`, `order_status_events`                                                                                          | **New** generator (links to orders/customers)                         |
| **4. Document Intelligence**   | Synthetic invoice/PO/delivery-note PDFs; `bronze_documents` metadata; ground truth for NER                                                                                       | **New** generator (reuse prescription PDF patterns)                   |
| **5. Insights & Analytics**    | `warehouse_costs`, `competitor_products`, `competitor_price_history`; `store_sales`, `store_attributes`, `promotions`                                                            | Part extend (warehouse_costs), part new (competitor, store/franchise) |

Several of the above need **suppliers** and **warehouses** as first-class entities (supplier_id, warehouse_id) so we can join inventory, POs, and availability consistently.

---

## 2. Cross-cutting: suppliers and warehouses

- **Suppliers**: Today `products.supplier` is a string. Use cases 1 (inventory_availability), 2 (purchase_orders, supplier_performance), and 4 (silver_suppliers for matching) need **supplier_id**.
  **Decision**: Add a **suppliers** table (`supplier_id`, `name`, `region`, etc.) and **products.supplier_id** (FK), and keep or derive `supplier` name for backward compatibility in silver.
- **Warehouses**: Inventory and several new tables use **warehouse_id**. Options: (a) Add a **warehouses** table (e.g. distribution centres); (b) Treat **pharmacy_id** as warehouse_id for “pharmacy as stock location”.
  **Decision**: Add a small **warehouses** table (e.g. 20–50 rows) and **inventory_availability / expiry_batches / writeoff_events** keyed by `warehouse_id`. Optionally link warehouses to regions; inventory can stay at pharmacy level for existing use cases and we add warehouse-level views or a separate **inventory_by_warehouse**-style table if needed. Simpler alternative for Phase 1: **reuse pharmacy_id as warehouse_id** (one warehouse per pharmacy) and add a `warehouses` view/table that is 1:1 with pharmacies, so no schema change to existing inventory.

**Recommended for Phase 1**: Add **suppliers** table + **products.supplier_id**. For warehouse_id, use **pharmacy_id as warehouse_id** (pharmacy = stock-holding location) and add an optional **warehouses** table that is initially a copy of pharmacies with a `warehouse_id` alias, so all new tables can use `warehouse_id` and we can later swap to real DCs if needed.

---

## 3. Phased implementation plan

### Phase 0: Foundation (suppliers + product enhancements)

**Goal**: One-off schema and generator changes so all later phases can depend on them.

1. **Suppliers table**
   - Add `generate_suppliers(n)` → `supplier_id`, `name`, `region`, `lead_time_days` (default), etc.
   - In **products**, add `supplier_id` (FK to suppliers); backfill from existing `supplier` string (e.g. derive or sample supplier_id from name) or generate supplier_id when generating products.
2. **Product columns for Recommendation Engine**
   - Add to product generation: `therapeutic_category`, `brand`, `generic_equivalent_id`, `pack_size_variants`, `margin_percentage`.
3. **Warehouse_id convention**
   - Add a small **warehouses** table (e.g. `warehouse_id`, `name`, `region`) and optionally treat it as a subset of pharmacies or a separate dimension. For minimal change, **inventory_availability** and **expiry_batches** can use `pharmacy_id` as `warehouse_id` and we document that “warehouse = pharmacy” for now.

**Deliverables**: `healthcare_suppliers` table; products extended and writing to UC; medallion sources + silver/products updated; optional `healthcare_warehouses` or doc that warehouse_id = pharmacy_id.

**Medallion**: New bronze/silver for `healthcare_suppliers`; silver_products extended with new columns and supplier_id.

---

### Phase 1: Recommendation Engine data

**Goal**: All raw data needed for reco (interactions, substitutions, product attributes, availability).

1. **product_interactions**
   - `interaction_id`, `customer_id`, `product_id`, `action_type` (viewed, searched, added, purchased), `timestamp`, `session_id`.
   - Derive “purchased” from orders; generate viewed/searched/added synthetically with plausible distribution (e.g. many views, fewer purchases).
2. **substitution_events**
   - `substitution_id`, `order_id`, `requested_product_id`, `substituted_product_id`, `reason`, `customer_accepted`, `margin_delta`, `timestamp`.
   - Link to existing orders; generate substitutions for a subset of orders (e.g. out-of-stock or therapeutic substitution).
3. **inventory_availability**
   - `product_id`, `warehouse_id`, `quantity_available`, `lead_time_days`, `supplier_id`, `snapshot_date`.
   - Can be derived from existing inventory + products (using pharmacy_id as warehouse_id and products.supplier_id) plus a snapshot date; or generated as a dedicated table.

**Deliverables**: New generator methods (e.g. in `healthcare_data_generator.py` or a dedicated `generate_recommendation_data.py` that uses the main generator and adds these tables); write to UC as `healthcare_product_interactions`, `healthcare_substitution_events`, `healthcare_inventory_availability`. Medallion: bronze/silver (and gold as in EBOS) for these.

---

### Phase 2: Inventory Optimisation data

**Goal**: Expiry, write-offs, POs, supplier performance.

1. **expiry_batches**
   - `batch_id`, `product_id`, `warehouse_id`, `expiry_date`, `quantity`, `cost_basis`.
   - Can be derived from inventory (batch_number, expiry_date, quantity, cost) and warehouse_id = pharmacy_id, or generated as net-new with same FK constraints.
2. **writeoff_events**
   - `event_id`, `product_id`, `warehouse_id`, `quantity`, `reason` (expired, damaged, obsolete), `cost`, `timestamp`.
   - Generate synthetically; optionally link to expiry_batches.
3. **purchase_orders**
   - `po_id`, `supplier_id`, `product_id`, `quantity`, `order_date`, `expected_delivery_date`, `actual_delivery_date`, `unit_cost`.
   - Generate POs that reference suppliers and products; can align with order_date and lead_time for realism.
4. **supplier_performance**
   - `supplier_id`, `product_id`, `fill_rate`, `avg_lead_time_days`, `lead_time_std`, `month`.
   - Aggregate from POs and deliveries (or generate synthetic metrics).

**Deliverables**: New generator methods/tables; UC tables; medallion bronze/silver/gold as per EBOS.

---

### Phase 3: Customer Service Agent data (new generator)

**Goal**: Cases, messages, knowledge docs, order-status events; separate bundle that references healthcare identities.

1. **customer_service_generator** (new bundle under `data/customer_service_generator/`).
2. **Tables**: `customer_service_cases`, `case_messages`, `knowledge_documents`, `order_status_events`.
   - **customer_id** in cases = pharmacy_id or hospital_id from healthcare (sample from existing).
   - **order_id** in order_status_events = from healthcare_orders; can reuse or mirror supply_chain_events for status/location.
3. **Knowledge documents**: Synthetic SOPs/FAQs/policies; optionally link `product_ids` to healthcare_products.
4. **case_messages**: Synthetic message_text; add intent labels for training (order_tracking, product_inquiry, etc.) in a separate column or in silver.

**Deliverables**: New DAB bundle; generator script(s); output to UC (e.g. `customer_service_*` tables or a dedicated schema). New dbt project `customer_service_medallion` (bronze/silver/gold) as in EBOS.

---

### Phase 4: Document Intelligence data (new generator)

**Goal**: Synthetic invoice/PO/delivery-note PDFs and metadata for NER/layout; reuse prescription PDF patterns.

1. **document_intelligence_generator** (new under `data/document_intelligence_generator/`).
   - Reuse patterns from `data/prescription_pdf_generator/` (templates, reportlab/faker, output dirs).
2. **Outputs**:
   - Synthetic PDFs: invoices, purchase orders, delivery notes (with supplier, amounts, dates, line items).
   - Metadata table or manifest: `doc_id`, `file_path`, `doc_type`, `upload_timestamp`, `source_system` → can land as `bronze_documents` or equivalent.
   - Ground truth for NER: same as prescription (e.g. JSON per doc) → feeds `gold_doc_labels` after medallion.
3. **Referential consistency**: Use healthcare `supplier_id`, `product_id` (and optionally order_id) in generated docs where relevant.

**Deliverables**: New generator bundle; PDFs + metadata + labels; pipeline to write metadata (and optionally file references) to UC; doc-intelligence medallion or extension of healthcare medallion for document metadata only.

---

### Phase 5: Insights & Analytics data (extend + optional new)

**Goal**: Warehouse costs, competitor data, store/franchise sales and promotions.

1. **warehouse_costs** (extend healthcare generator)
   - Table: e.g. `warehouse_id`, `product_id` or `sku`, `storage_cost`, `handling_cost`, `period`; optional `fulfillment_sla` metrics.
   - Generate from warehouses (or pharmacy_id) and products.
2. **competitor_products** / **competitor_price_history**
   - Synthetic tables: `competitor_id`, `product_name`, `price`, `url`, `scrape_date`; and time series of prices. No real scraping in generator; structure ready for use-case to plug in a scraper later.
3. **store_sales**, **store_attributes**, **promotions**
   - **store_id**: Can align with pharmacy_id (store = pharmacy) or add a separate store dimension for franchise.
   - **store_sales**: `store_id`, `product_id`, `date`, `sales_quantity`, `revenue`.
   - **store_attributes**: `store_id`, `location`, `size_sqm`, `store_type`, `cluster_id`.
   - **promotions**: `promo_id`, `store_id`, `product_id`, `start_date`, `end_date`, `discount_rate`.

**Deliverables**: New tables in healthcare generator (or a small “insights” extension script that uses same Faker/seed and writes to UC); medallion bronze/silver/gold for these as in EBOS.

---

## 4. Implementation order and dependencies

| Phase | Depends on                                 | Delivers                                                                                      |
| ----- | ------------------------------------------ | --------------------------------------------------------------------------------------------- |
| **0** | —                                          | suppliers; product columns; warehouse_id convention                                           |
| **1** | Phase 0                                    | substitution_events, product_interactions, inventory_availability; product enhancements in UC |
| **2** | Phase 0                                    | expiry_batches, writeoff_events, purchase_orders, supplier_performance                        |
| **3** | Healthcare orders/customers in UC          | customer_service_generator + medallion                                                        |
| **4** | Phase 0 (supplier_id, product_id) optional | document_intelligence_generator + PDFs + metadata                                             |
| **5** | Phase 0 (warehouses/products)              | warehouse_costs, competitor_*, store_*, promotions                                            |

Recommended sequence: **0 → 1 → 2** (all in healthcare generator + medallion), then **3** (new bundle), then **4** (new bundle), then **5** (extend healthcare again).

---

## 5. File and bundle layout (after plan)

- **data/healthcare_data_generator/**
  - Extend `src/healthcare_data_generator.py` (or split into modules) with: suppliers, warehouses (optional), product columns, then Phase 1–2–5 tables.
  - Entry point(s): keep `generate_catalog_data_static.py`; optionally add flags or a second job to generate “extension” tables (reco, inventory, insights) so base vs extension can run at different cadences.
- **data/healthcare_data_medallion/**
  - Add bronze/silver/gold models for all new tables; extend sources.yml and silver_products for new columns and supplier_id.
- **data/customer_service_generator/** (new)
  - DAB bundle; `src/generate_cs_data.py` (or similar); outputs to UC.
- **data/customer_service_medallion/** (new)
  - dbt project for customer service bronze/silver/gold.
- **data/document_intelligence_generator/** (new)
  - DAB or script bundle; PDF generation + metadata; outputs to UC/volume as needed.
- **data/document_intelligence_medallion/** (new, or part of healthcare_medallion)
  - dbt for document metadata and gold_doc_labels.

---

## 6. Summary table: source of each new table

| New table                                      | Source                          | Phase |
| ---------------------------------------------- | ------------------------------- | ----- |
| suppliers                                      | healthcare_data_generator       | 0     |
| products (new columns + supplier_id)           | healthcare_data_generator       | 0     |
| warehouses (optional)                          | healthcare_data_generator       | 0     |
| product_interactions                           | healthcare_data_generator       | 1     |
| substitution_events                            | healthcare_data_generator       | 1     |
| inventory_availability                         | healthcare_data_generator       | 1     |
| expiry_batches                                 | healthcare_data_generator       | 2     |
| writeoff_events                                | healthcare_data_generator       | 2     |
| purchase_orders                                | healthcare_data_generator       | 2     |
| supplier_performance                           | healthcare_data_generator       | 2     |
| customer_service_cases                         | customer_service_generator      | 3     |
| case_messages                                  | customer_service_generator      | 3     |
| knowledge_documents                            | customer_service_generator      | 3     |
| order_status_events                            | customer_service_generator      | 3     |
| invoice/PO/delivery PDFs + metadata            | document_intelligence_generator | 4     |
| warehouse_costs                                | healthcare_data_generator       | 5     |
| competitor_products / competitor_price_history | healthcare_data_generator       | 5     |
| store_sales, store_attributes, promotions      | healthcare_data_generator       | 5     |

This keeps one shared healthcare foundation, one customer-service-specific generator, and one document-specific generator, with all EBOS use-case data either coming from the extended healthcare generator or from these two new bundles.

---

## 7. Local development

For local use-case development (model training, feature engineering, evaluation), the following approach is recommended. See also [docs/LOCAL_DEVELOPMENT_REVIEW.md](LOCAL_DEVELOPMENT_REVIEW.md).

**Recommendation**: **Raw CSVs in a gitignored directory** (e.g. `data/local/`) are sufficient for local use-case development—simplest, transparent, and fast. No SQLite is required for data loading or model training; use-case code can read CSVs directly into pandas (or polars) and run offline.

- **Generator output for local**: When running the healthcare (or other) generator locally, write to `data/local/` (or a similar path under `data/` that is in `.gitignore`). Same CSV shape as production; no catalog or Spark needed.
- **Optional — medallion locally**: To replicate the medallion as completely/realistically as possible locally (and speed up dev), run dbt against a **local DB**. Prefer **DuckDB** (dbt-duckdb): analytical SQL closer to Spark/Databricks, and you can point at CSVs directly (views or `read_csv_auto`) so no separate “load CSVs into tables” step. **SQLite** (dbt-sqlite) is fine too; you must populate it from CSVs first (e.g. a small script). Point the medallion’s local dbt profile at that DB; expect minor SQL dialect tweaks for Spark vs DuckDB/SQLite.
- **Production**: The **Databricks profile** is kept for production; `generate_catalog_data_static.py` (and equivalent jobs) write to Unity Catalog. Local CSV output is additive and does not replace the catalog path.
