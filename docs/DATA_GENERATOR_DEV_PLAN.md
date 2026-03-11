# Data generator and medallion — EBOS use cases

This document specifies **all tabular data** generated and medallion-built for the EBOS use cases ([docs/EBOS_USE_CASES.md](EBOS_USE_CASES.md)). We implement **all of it**: foundation tables, use-case-specific raw tables, and the corresponding medallion layers (bronze/silver/gold) so each use case has the data needed to train models and run pipelines.

**Local/remote workflow**: See [data/README.md](../data/README.md) for generator → CSVs → DuckDB/dbt locally and Databricks in production.

---

## 1. Scope: generators and medallions

### 1.1 Healthcare data generator + medallion

**Generator** (`data/healthcare_data_generator/`): Produces all base and use-case-specific healthcare tabular data. Output: CSVs (local) or Unity Catalog (production).

**Base tables** (existing): pharmacies, hospitals, products, orders, inventory, supply_chain_events.

**Foundation** (required by multiple use cases):
- **suppliers** — `supplier_id`, `name`, `region`, `lead_time_days`; products reference `supplier_id`.
- **warehouses** — `warehouse_id`, `name`, `region`; 1:1 with pharmacies (pharmacy as stock location) so existing inventory can use `pharmacy_id` as `warehouse_id`.
- **products** extended with: `therapeutic_category`, `brand`, `generic_equivalent_id`, `pack_size_variants`, `margin_percentage`, `supplier_id`.

**Use-case 1 — Recommendation Engine**: product_interactions, substitution_events, inventory_availability (plus product extensions above).

**Use-case 2 — Inventory Optimisation**: expiry_batches, writeoff_events, purchase_orders, supplier_performance.

**Use-case 5 — Insights & Analytics**: warehouse_costs, competitor_products, competitor_price_history, store_sales, store_attributes, promotions (store_id aligned with pharmacy_id).

**Medallion** (`data/healthcare_data_medallion/`): Bronze → silver → gold for all of the above; sources and models for every new table so training and jobs can read from silver/gold.

### 1.2 Customer Service data (separate generator + medallion)

**Generator** (`data/customer_service_generator/`): customer_service_cases, case_messages, knowledge_documents, order_status_events. Links to healthcare (customer_id = pharmacy_id/hospital_id, order_id from healthcare_orders).

**Medallion** (`data/customer_service_medallion/`): Bronze/silver/gold for cases, messages, knowledge docs; gold for agent conversations and knowledge index.

### 1.3 Document Intelligence (generator + medallion)

**Generator** (`data/document_intelligence_generator/`): Synthetic invoice/PO/delivery PDFs; metadata table (doc_id, file_path, doc_type, upload_timestamp, source_system); ground-truth labels for NER. Uses healthcare supplier_id, product_id for referential consistency.

**Medallion** (extension of healthcare or separate): bronze_documents, silver/gold for doc metadata and gold_doc_labels for training.

---

## 2. Use-case → data mapping

| EBOS use case | Raw / extended tables | Generator | Medallion |
|---------------|------------------------|-----------|-----------|
| **1. Recommendation Engine** | substitution_events, product_interactions, inventory_availability; products + therapeutic_category, brand, generic_equivalent_id, pack_size_variants, margin_percentage; suppliers | healthcare_data_generator | healthcare_data_medallion |
| **2. Inventory Optimisation** | expiry_batches, writeoff_events, purchase_orders, supplier_performance; suppliers; warehouses | healthcare_data_generator | healthcare_data_medallion |
| **3. Customer Service Agents** | customer_service_cases, case_messages, knowledge_documents, order_status_events | customer_service_generator | customer_service_medallion |
| **4. Document Intelligence** | Invoice/PO/delivery PDFs + metadata; bronze_documents; gold_doc_labels; suppliers (matching) | document_intelligence_generator | healthcare or doc medallion |
| **5. Insights & Analytics** | warehouse_costs; competitor_products, competitor_price_history; store_sales, store_attributes, promotions | healthcare_data_generator | healthcare_data_medallion |

All use cases that need `silver_orders`, `silver_products`, `silver_pharmacies`, `silver_inventory`, or `silver_supply_chain_events` get them from the healthcare medallion. Foundation (suppliers, product columns, warehouses) is implemented in the healthcare generator and medallion so use cases 1, 2, 4, and 5 have the keys they need.

---

## 3. Healthcare generator: table specs

### 3.1 Foundation

- **suppliers**: `supplier_id`, `name`, `region`, `lead_time_days` (default). Generated first; products reference `supplier_id`.
- **warehouses**: `warehouse_id`, `name`, `region` — one row per pharmacy (warehouse_id = pharmacy_id, name/region from pharmacy).
- **products** (extended): add `supplier_id` (FK), `therapeutic_category`, `brand`, `generic_equivalent_id`, `pack_size_variants`, `margin_percentage`; keep existing `supplier` string for backward compatibility in silver.

### 3.2 Recommendation Engine

- **product_interactions**: `interaction_id`, `customer_id`, `product_id`, `action_type` (viewed, searched, added, purchased), `timestamp`, `session_id`. Derive “purchased” from orders; generate viewed/searched/added synthetically.
- **substitution_events**: `substitution_id`, `order_id`, `requested_product_id`, `substituted_product_id`, `reason`, `customer_accepted`, `margin_delta`, `timestamp`. Link to orders; generate for a subset of orders.
- **inventory_availability**: `product_id`, `warehouse_id`, `quantity_available`, `lead_time_days`, `supplier_id`, `snapshot_date`. Derived from inventory + products (pharmacy_id as warehouse_id).

### 3.3 Inventory Optimisation

- **expiry_batches**: `batch_id`, `product_id`, `warehouse_id`, `expiry_date`, `quantity`, `cost_basis`. From inventory (batch_number, expiry_date, etc.) with warehouse_id = pharmacy_id.
- **writeoff_events**: `event_id`, `product_id`, `warehouse_id`, `quantity`, `reason` (expired, damaged, obsolete), `cost`, `timestamp`. Synthetic.
- **purchase_orders**: `po_id`, `supplier_id`, `product_id`, `quantity`, `order_date`, `expected_delivery_date`, `actual_delivery_date`, `unit_cost`. Reference suppliers and products.
- **supplier_performance**: `supplier_id`, `product_id`, `fill_rate`, `avg_lead_time_days`, `lead_time_std`, `month`. Synthetic or derived from POs.

### 3.4 Insights & Analytics

- **warehouse_costs**: `warehouse_id`, `product_id`, `storage_cost`, `handling_cost`, `period`.
- **competitor_products**: `competitor_id`, `product_name`, `price`, `url`, `scrape_date`. Synthetic (no real scraping).
- **competitor_price_history**: time series of competitor prices (competitor_id, product_name, price, date).
- **store_sales**: `store_id`, `product_id`, `date`, `sales_quantity`, `revenue`. store_id = pharmacy_id.
- **store_attributes**: `store_id`, `location`, `size_sqm`, `store_type`, `cluster_id`. store_id = pharmacy_id.
- **promotions**: `promo_id`, `store_id`, `product_id`, `start_date`, `end_date`, `discount_rate`.

---

## 4. Customer Service generator: table specs

- **customer_service_cases**: `case_id`, `customer_id` (pharmacy_id or hospital_id), `created_date`, `status`, `category`, `priority`, `resolution_time_minutes`, `first_contact_resolution`.
- **case_messages**: `message_id`, `case_id`, `sender` (customer/agent), `message_text`, `timestamp`, `sentiment_score`; intent labels for training.
- **knowledge_documents**: `doc_id`, `title`, `content`, `doc_type` (SOP, FAQ, policy), `product_ids` (array), `last_updated`.
- **order_status_events**: `event_id`, `order_id`, `status`, `location`, `timestamp`, `details`. Can mirror or derive from healthcare supply_chain_events.

---

## 5. Document Intelligence generator: outputs

- Synthetic PDFs: invoices, purchase orders, delivery notes (supplier, amounts, dates, line items).
- Metadata: `doc_id`, `file_path`, `doc_type`, `upload_timestamp`, `source_system` → bronze_documents.
- Ground truth: JSON per doc → gold_doc_labels for NER training.

---

## 6. File and bundle layout

- **data/healthcare_data_generator/** — Extended with all foundation and use-case tables above; single `generate_all_datasets()` (and save) produces everything. Entry point: `generate_catalog_data_static.py` (Databricks) and `generate_local.py` (CSVs).
- **data/healthcare_data_medallion/** — Sources and bronze/silver/gold for every healthcare table (base + suppliers, warehouses, product_interactions, substitution_events, inventory_availability, expiry_batches, writeoff_events, purchase_orders, supplier_performance, warehouse_costs, competitor_products, competitor_price_history, store_sales, store_attributes, promotions). Silver products extended with new columns and supplier_id.
- **data/customer_service_generator/** — New bundle; outputs customer_service_cases, case_messages, knowledge_documents, order_status_events.
- **data/customer_service_medallion/** — New dbt project for customer service bronze/silver/gold.
- **data/document_intelligence_generator/** — New bundle; PDFs + metadata + labels.
- **data/document_intelligence_medallion/** (or extend healthcare_medallion) — bronze_documents, gold_doc_labels, etc.

---

## 7. Local development

- **Generator output**: Run generator locally; write CSVs to `data/local/` (same shapes as production). Use `make data-local-generate` or `make data-local-generate-quick`.
- **Medallion locally**: Load CSVs into DuckDB via `make data-local-duckdb-load`; run dbt with `make data-local-dbt-run`. Production: Databricks profile and Unity Catalog.

See [docs/LOCAL_DEVELOPMENT_REVIEW.md](LOCAL_DEVELOPMENT_REVIEW.md) for use-case-level local dev notes.
