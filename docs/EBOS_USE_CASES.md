# EBOS AI/ML Use Cases

**Use-cases**: Equal priority; implementation order may vary.
**Infrastructure**: Databricks + Unity Catalog (`workspace.default` schema)
**Repo layout**: Use-cases live under `use_cases/<name>/`; DAB bundles (jobs, endpoints, interactive) live under each use-case or data component. New data tables (generator/medallion extensions) are planned and will be implemented incrementally.

**Existing Assets**:
- Healthcare data generator with medallion architecture (bronze/silver/gold)
- Inventory optimisation: demand forecasting, write-off risk, replenishment under `use_cases/inventory_optimization/models/`
- Recommendation engine: item_similarity, ALS, LightFM, ranker under `use_cases/recommendation_engine/models/`
- Prescription PDF generator and annotation app for document intelligence

---

## 1️⃣ Recommendation Engine for Ordering

**Business Value**: ~$4.9m p.a. | Enterprise-wide (Healthcare, MedTech, Animal Care)
**Use Case**: Recommend similar products and auto-substitutions to reduce sales leakage and increase margins
**Current Status**: ✅ **Partial** — Item similarity, ALS, LightFM, ranker implemented under `models/`; DAB jobs and endpoints in place.
**Local dev**: Develop locally (data gen, training, saving). Optional full-pipeline entrypoint `models/run_reco.py` runs locally (CSV) or on Databricks; per-model scripts (`models/<name>/train.py`, `predict.py`) and Make targets are the main surface. Data source via config.

### Data Requirements

**Extend existing `healthcare_data_generator`**:
- Add `substitution_events` table: `substitution_id`, `order_id`, `requested_product_id`, `substituted_product_id`, `reason`, `customer_accepted`, `margin_delta`, `timestamp`
- Add `product_interactions` table: `interaction_id`, `customer_id`, `product_id`, `action_type` (viewed, searched, added, purchased), `timestamp`, `session_id`
- Enhance `silver_products` with: `therapeutic_category`, `brand`, `generic_equivalent_id`, `pack_size_variants`, `margin_percentage`
- Add `inventory_availability` table: `product_id`, `warehouse_id`, `quantity_available`, `lead_time_days`, `supplier_id`, `snapshot_date`

**Expected volume**: ~100k interactions/week, ~5k substitution events/week (synthetic)

**Reuse**: `silver_orders`, `silver_products`, `silver_pharmacies`, `silver_hospitals`

### Modelling Approach

**Phase 1: Item-to-Item Similarity** (baseline, 1-2 weeks)
- `sklearn.neighbors.NearestNeighbors` with cosine similarity on product feature vectors
- Features: category, therapeutic class, price tier, pack size, brand, margin
- Training: fit on product catalog, no retraining needed unless catalog changes
- Use case: "Similar products" recommendations

**Phase 2: Collaborative Filtering** (2-3 weeks)
- `implicit.als.AlternatingLeastSquares` on customer-product interaction matrix
- Features: implicit feedback (purchase quantities) with time decay weighting
- Training: weekly batch job on rolling 6-month window
- Use case: "Customers who ordered X also ordered Y"

**Phase 3: Hybrid Recommender** (production target, 3-4 weeks)
- `lightgbm.LGBMRanker` combining content + collaborative features
- Training data: positive (purchases) vs negative (shown but not purchased) examples
- Features: similarity scores, ALS scores, product attributes, customer history, margin, availability
- Business rules layer: regulatory constraints, minimum margin thresholds, stock availability filters

**Evaluation**: Precision@5, Recall@10, NDCG, offline substitution acceptance rate, margin improvement

### Feature ownership (dbt vs ML code)

**Keep in dbt (medallion):** Base, reusable aggregates that many consumers need (e.g. customer × product purchase counts, last order date, product/customer attributes from silver). Think of this as **feature storage / wide tables**, not the full model-specific feature set. Optionally one slim “training base” table (e.g. `gold_reco_training_base`: customer, product, label, key IDs).

**Keep in Python (ML code):** Model-specific feature construction: time windows, normalization, one-hot/target encoding, train/test splits, negative sampling, and any logic used only by this model. **Serving path:** Whatever is computed at request time (or in a real-time pipeline) must use the same logic as in training, implemented in code (e.g. `models/feature_engineering.py`), not only in dbt.

Use dbt for shared, stable, coarse-grained building blocks; do all model-specific and serving-aligned feature engineering in Python, reading from those gold (or silver) tables. This avoids train–serve skew and keeps the medallion from being a dependency for every small ML experiment, while still benefiting from a single, governed data foundation.

### Databricks Architecture

**Data Pipeline** (dbt medallion; use-case prefix `reco_` for recommendation-engine tables):
```
data/healthcare_data_medallion/
├── bronze/
│   ├── bronze_reco_interactions.sql   # Raw interaction events
│   └── bronze_reco_substitutions.sql  # Raw substitution events
│
├── silver/
│   ├── silver_reco_interactions.sql   # Cleansed interactions with joins
│   └── silver_reco_substitutions.sql # Validated substitution events
│
└── gold/
    ├── gold_reco_training_base.sql    # Slim base (customer, product, label) for ML
    ├── gold_reco_features.sql         # Optional: base aggregates / feature storage
    └── gold_reco_candidates.sql       # Batch-scored recommendations (top-50 per customer)
```

**Training Workflow** (scheduled weekly; DAB bundle under use-case):
- Jobs live in `use_cases/recommendation_engine/bundles/job/resources/` (retrain_jobs.yml, batch_apply_jobs.yml). Each model (item_similarity, als, lightfm, ranker) has retrain and batch-apply jobs; entrypoints are `models/<name>/train.py` and `models/<name>/predict.py`. Optional full-pipeline entrypoint: `models/run_reco.py`. Serving endpoints in `bundles/serving/resources/reco_endpoints.yml`.

**Serving Endpoint** (real-time API):
- Databricks Model Serving endpoint: `recommendation-engine-prod`
- Input: `{"customer_id": "C123", "context": {"cart": ["P456"], "out_of_stock": "P789"}}`
- Output: `[{"product_id": "P999", "score": 0.87, "reason": "similar_therapeutic_class", "margin": 0.15}]`
- Fallback logic: if customer has no history → item-similarity only
- SLA: <100ms p95 latency

**Application Workflow**:
1. Ordering system calls REST API when customer adds to cart or item out of stock
2. Log recommendation shown → `silver_recommendation_events`
3. Log acceptance/rejection → feedback loop for retraining

**Databricks App** (Streamlit):
- **Purpose**: Interactive recommendation testing, monitoring, and live demonstration
- **Features**:
  - **Live Predictions**: Real-time model inference via serving endpoint
    - Enter customer ID + optional cart context → invoke model → display recommendations
    - Shows model scores, reasoning, margin impact in real-time
  - **Batch Recommendations**: Query pre-computed `gold_reco_candidates` table
    - Fast lookup for existing cached recommendations
    - Compare batch vs real-time predictions
  - **Model Comparison**: A/B test different model versions (baseline vs challenger)
  - **Performance Dashboard**: Live metrics (precision@K, acceptance rates, margin lift)
  - **Product Similarity Explorer**: Search products → see similar items with feature comparison
- **Tech Stack**: Streamlit + Databricks SQL connector + Model Serving API
- **Deployment**: Databricks App via DAB bundle
- **Users**: ML team, product managers, business stakeholders

**File structure**: Data/medallion as in Data Pipeline above (`data/healthcare_data_generator/`, `data/healthcare_data_medallion/`). Use-case layout:
```
use_cases/recommendation_engine/
├── config.py
├── databricks.yml
├── bundles/
│   ├── job/resources/          # retrain_jobs.yml, batch_apply_jobs.yml (per model)
│   ├── serving/resources/      # reco_endpoints.yml
│   └── app/                    # Streamlit app (optional)
├── models/                     # Per-model: core + train + predict
│   ├── run_reco.py             # Optional full-pipeline entrypoint
│   ├── data_loading.py, evaluation.py, feature_engineering.py
│   ├── item_similarity/        # core.py, train.py, predict.py
│   ├── als/
│   ├── lightfm/
│   └── ranker/
└── app/                        # Databricks App (Streamlit)
```

---

## 2️⃣ Inventory Optimisation

**Business Value**: Direct EBIT + working capital benefits | High value across MedTech, TWC, Healthcare
**Use Case**: Right product at right place/time/price to drive sales growth and reduce write-offs
**Current Status**: ✅ **Partial** — Demand forecasting, write-off risk, replenishment under `models/`; DAB jobs in place.
**Local dev**: Develop locally (data gen, training, saving). Per-model scripts `models/<name>/train.py`, `predict.py` and Make targets.

### Data Requirements

**Extend existing `healthcare_data_generator`**:
- Add `expiry_batches` table: `batch_id`, `product_id`, `warehouse_id`, `expiry_date`, `quantity`, `cost_basis`
- Add `writeoff_events` table: `event_id`, `product_id`, `warehouse_id`, `quantity`, `reason` (expired, damaged, obsolete), `cost`, `timestamp`
- Add `purchase_orders` table: `po_id`, `supplier_id`, `product_id`, `quantity`, `order_date`, `expected_delivery_date`, `actual_delivery_date`, `unit_cost`
- Add `supplier_performance` table: `supplier_id`, `product_id`, `fill_rate`, `avg_lead_time_days`, `lead_time_std`, `month`

**Expected volume**: ~50k inventory transactions/month, ~2k writeoffs/month (synthetic)

**Reuse**: Existing `silver_orders`, `silver_products`, `silver_inventory` tables; leverage demand forecasting models

### Modelling Approach

**Component 1: Demand Forecasting** ✅ **EXISTS**
- XGBoost, ETS, Prophet under `use_cases/inventory_optimization/models/demand_forecasting/`
- Train at product × warehouse granularity
- Generate probabilistic forecasts (P50, P75, P90) for safety stock calculations

**Component 2: Write-off Risk Classification** (NEW - 2 weeks)
- `sklearn.ensemble.RandomForestClassifier` or `lightgbm.LGBMClassifier`
- Target: binary "will expire in next 30 days" or multi-class "risk level"
- Features: days until expiry, current inventory level, forecast demand next 30d, historical turnover rate, product category, seasonality indicators
- Use case: prioritize products for promotions or markdown

**Component 3: Replenishment Optimization** (NEW - 3-4 weeks)
- Option A: Safety stock heuristics (simpler, faster)
  - Calculate reorder points based on lead time, demand forecast variance, target service level
  - Formula: ROP = (avg_demand × lead_time) + (z_score × demand_std × sqrt(lead_time))
- Option B: Constrained optimization (more sophisticated)
  - Use `scipy.optimize.linprog` or `pulp` for linear programming
  - Objective: minimize total cost (holding + ordering + stockout + expiry)
  - Constraints: MOQ, warehouse capacity, budget, supplier lead times, expiry windows

**Evaluation**: Forecast MAE/RMSE/MAPE, reduction in write-offs (%), service level achievement, inventory turnover ratio

### Databricks Architecture

**Training Workflow** (scheduled weekly; DAB bundle under use-case): Jobs in `use_cases/inventory_optimization/bundles/job/resources/`. Entrypoints: `models/demand_forecasting/`, `models/writeoff_risk/`, `models/replenishment/` (each with core.py, train.py, predict.py).

**Serving/Application**:
- Batch scoring output to dashboard (Databricks SQL) for inventory planners
- Optional: real-time API for "should I reorder now?" queries
- Alerts: send notifications when inventory falls below reorder point

**Data Pipeline** (dbt medallion):
```
data/healthcare_data_medallion/
├── bronze/
│   ├── bronze_expiry_batches.sql      # NEW: Raw expiry data
│   └── bronze_writeoffs.sql           # NEW: Raw writeoff events
│
├── silver/
│   ├── silver_inventory_enhanced.sql  # NEW: Inventory with expiry/batch data
│   └── silver_writeoffs.sql           # NEW: Validated writeoff events
│
└── gold/
    ├── gold_demand_forecast.sql       # NEW: Forecasted demand (P50/P75/P90)
    ├── gold_writeoff_risk_scores.sql  # NEW: Expiry risk predictions
    └── gold_replenishment_recommendations.sql  # NEW: Reorder recommendations
```

**File structure**: Data/medallion as in Data Pipeline above. Use-case layout:
```
use_cases/inventory_optimization/
├── config.py
├── databricks.yml
├── bundles/job/resources/     # retrain/batch-apply jobs per model
└── models/                     # Per-model: core + train + predict
    ├── demand_forecasting/
    ├── writeoff_risk/
    └── replenishment/
```

---

## 3️⃣ AI Customer Service Agents

**Business Value**: Labour cost reduction + scalability | Cross-business (Healthcare, MedTech, TWC)
**Use Case**: Automate common queries, improve satisfaction, provide order tracking visibility
**Current Status**: ⚠️ Not implemented
**Local dev**: Cannot be developed locally easily; pass on local development for now.

### Data Requirements

**New synthetic data generator** (separate from healthcare):
- Add `customer_service_cases` table: `case_id`, `customer_id`, `created_date`, `status`, `category`, `priority`, `resolution_time_minutes`, `first_contact_resolution` (bool)
- Add `case_messages` table: `message_id`, `case_id`, `sender` (customer/agent), `message_text`, `timestamp`, `sentiment_score`
- Add `knowledge_documents` table: `doc_id`, `title`, `content`, `doc_type` (SOP, FAQ, policy), `product_ids` (array), `last_updated`
- Add `order_status_events` table: `event_id`, `order_id`, `status`, `location`, `timestamp`, `details`

**Expected volume**: ~10k cases/month, ~50k messages/month, ~500 knowledge docs (synthetic)

**Integration points**: Links to existing `silver_orders`, `silver_products`, `silver_pharmacies`

### Modelling Approach

**Component 1: Intent Classification** (1 week)
- `sklearn` or `transformers` (distilbert) for intent detection
- Classes: order_tracking, product_inquiry, return_request, complaint, billing_question, general_inquiry
- Training data: synthetic labeled messages (500-1000 examples per class)
- Use case: route query to appropriate handler

**Component 2: RAG System** (2-3 weeks)
- Embeddings: `sentence-transformers/all-MiniLM-L6-v2` for knowledge docs and FAQs
- Vector store: Databricks Vector Search (Unity Catalog)
- Retrieval: find top-5 relevant docs based on customer query
- Generation: LLM (Azure OpenAI GPT-4 or Databricks Foundation Models) to synthesize response
- Grounding: cite sources, restrict to retrieved context only

**Component 3: Order Tracking Integration** (non-ML)
- Simple SQL lookup against `silver_orders` and `order_status_events`
- Return structured data: order status, estimated delivery, current location

**Evaluation**: Intent accuracy, RAG relevance (NDCG), response quality (human eval), first contact resolution rate

### Databricks Architecture

**Offline Preparation** (bundle under use-case):
```
use_cases/customer_service_agent/
├── jobs/
│   ├── 1_intent_training.py           # Train intent classifier
│   │   └── Load labeled messages from silver_case_messages
│   │   └── Train DistilBERT or sklearn model
│   │   └── Register to Unity Catalog
│   │
│   └── 2_knowledge_indexing.py         # Build vector index
│       └── Chunk knowledge docs, generate embeddings
│       └── Store in Databricks Vector Search (Unity Catalog)
│       └── Refresh weekly or on doc updates
├── resources/
└── databricks.yml
```

**Serving Architecture**:
- Databricks Model Serving endpoint: `customer-service-agent-prod`
- Agent orchestration logic (Python Flask/FastAPI wrapper):
  1. Receive customer query
  2. Classify intent
  3. IF order_tracking → query DB directly
  4. ELSE → RAG retrieval + LLM generation
  5. Return response + citations
- Conversation history stored in Delta table for audit/retraining

**Application Workflow**:
- Chatbot frontend calls agent endpoint
- Log all conversations to `silver_agent_conversations`
- Human-in-the-loop: escalate to agent if confidence < 0.7

**Databricks App** (Streamlit):
- **Purpose**: Agent administration, knowledge management, and performance monitoring
- **Features**:
  - **Knowledge Base Manager**: Upload/edit/delete FAQ documents, rebuild vector index
  - **Agent Testing Interface**: Enter test queries → see intent classification + RAG retrieval + generated response
  - **Conversation Monitor**: View recent agent interactions with quality scores
  - **Human Review Queue**: Review low-confidence responses before sending to customers
  - **Performance Dashboard**: Resolution rates, escalation rates, customer satisfaction metrics
  - **Intent Debugger**: Test intent classifier with confidence scores
- **Tech Stack**: Streamlit + Vector Search API + Databricks SQL connector
- **Deployment**: Databricks App via DAB bundle
- **Users**: Customer service managers, QA team, ML team

**Data Pipeline** (dbt medallion - separate project):
```
data/customer_service_medallion/                # NEW dbt project
├── bronze/
│   ├── bronze_cases.sql                        # NEW: Raw customer service cases
│   ├── bronze_messages.sql                     # NEW: Raw case messages
│   └── bronze_knowledge_docs.sql               # NEW: Raw knowledge documents
│
├── silver/
│   ├── silver_cases.sql                        # NEW: Validated cases
│   ├── silver_messages.sql                     # NEW: Cleansed messages with sentiment
│   └── silver_knowledge_docs.sql               # NEW: Processed documents for indexing
│
└── gold/
    ├── gold_agent_conversations.sql            # NEW: Anonymized conversation logs
    ├── gold_agent_performance.sql              # NEW: Performance metrics
    └── gold_knowledge_index.sql                # NEW: Document chunks for vector search
```

**File Structure**:
```
databricks-misc/
├── data/
│   ├── customer_service_generator/            # NEW DATA BUNDLE
│   │   ├── databricks.yml
│   │   └── src/
│   │       └── generate_cs_data.py            # Cases, messages, knowledge docs
│   │
│   └── customer_service_medallion/            # NEW dbt project
│       └── src/models/
│           ├── bronze/
│           │   ├── bronze_cases.sql
│           │   ├── bronze_messages.sql
│           │   └── bronze_knowledge_docs.sql
│           ├── silver/
│           │   ├── silver_cases.sql
│           │   ├── silver_messages.sql
│           │   └── silver_knowledge_docs.sql
│           └── gold/
│               ├── gold_agent_conversations.sql
│               ├── gold_agent_performance.sql
│               └── gold_knowledge_index.sql
│
└── use_cases/
    └── customer_service_agent/                 # NEW MODULE
        ├── README.md
        ├── databricks.yml
        ├── resources/
        ├── requirements.txt                   # sentence-transformers, openai, fastapi, streamlit
        ├── intent_classifier.py
        ├── rag_pipeline.py
        ├── agent_orchestrator.py              # Main logic
        ├── evaluation.py
        ├── jobs/
        │   ├── 1_intent_training.py
        │   └── 2_knowledge_indexing.py
        └── app/                               # NEW: Databricks App
            ├── agent_admin_dashboard.py       # Streamlit app
            └── requirements.txt               # streamlit, databricks-sql-connector
```

---

## 4️⃣ Document Intelligence (Prescriptions & Ordering)

**Business Value**: Manual labour reduction | High ROI for prescription processing and order validation
**Use Case**: Reduce manual processing of prescription PDFs using AI to interpret, validate, and integrate into downstream ordering systems
**Current Status**: ✅ **Partial** - Prescription PDF generator and annotation app exist; pipeline (generate → predict → save → review) in progress
**Local dev**: Same patterns as recommendation_engine and inventory_optimization — config-driven local vs remote (DOCINT_BASE_DIR / DOCINT_DATA_SOURCE), modular jobs, single entrypoint; PDF generation, OCR, and annotator run locally with open-source libs (no Spark).

### Pipeline flow (generate → predict → save → review)

Document intelligence is **not** a classic train-then-batch-score modelling use case. The flow is:

1. **Generate documents** — Produce synthetic prescription PDFs (and optional ground-truth JSON for evaluation only) via `data/prescription_pdf_generator/`. Output: `documents/`, optionally `labels/` (ground truth).
2. **Generate predictions** — Run OCR and NER/field extraction on those documents. Output is **model predictions** (OCR text per page, extracted prescription fields per document), not training labels.
3. **Save predictions** — Persist predictions in a known location so the next step and the annotator can consume them.
   - **Local**: e.g. `predictions/ocr/` (per-doc or combined) and `predictions/fields/` (extracted fields as JSON or table).
   - **Remote**: e.g. Unity Catalog tables (silver_doc_pages, silver_doc_fields_extracted) or blob/volume paths; config switches via DOCINT_DATA_SOURCE.
4. **Review predictions (annotator)** — The annotator is an **application** that loads **saved predictions** (and the original PDFs), displays them side-by-side for human review, and allows corrections. Corrected data is saved (e.g. `annotated/` or gold_doc_labels) for downstream use and optionally for future model training.

Ground-truth labels (`labels/`) are used for **evaluation and optional NER training**, not as the primary input to the annotator in the main flow; the annotator’s primary input is **predictions** produced by the pipeline.

### Data Requirements

**Document generation** (synthetic prescription PDFs):
- **Reuse** `data/prescription_pdf_generator/` — no separate finance document generator
- Output: `documents/` (PDFs), optional `labels/` (ground-truth JSON for eval/training)
- Document types: community prescriptions, hospital discharge, repeat prescriptions (same schema as today)

**Predictions storage** (pipeline output):
- **Local**: Under base dir (e.g. `predictions/ocr/`, `predictions/fields/` or single `predictions/fields.parquet`); config exposes `predictions_dir` (or equivalent).
- **Remote**: When DOCINT_DATA_SOURCE=catalog, write to Unity Catalog (e.g. silver_doc_pages, silver_doc_fields_extracted) or a configured volume path.

**Existing assets**:
- Prescription PDF generator: `data/prescription_pdf_generator/`
- Annotator app (review predictions): `use_cases/document_intelligence/annotator/` — to be wired to read **predictions** and write corrected output to `annotated/` (or catalog).

### Modelling / extraction approach

**Pipeline (generate predictions, not “training” in the same sense as reco/inventory)**:
1. **OCR** — Open-source OCR (e.g. `pdfplumber`, Tesseract) for PDF → text/layout. Write results to predictions store (per-doc or table).
2. **Field extraction (NER)** — Extract prescription fields from OCR text (or from structured generator labels as a proxy until NER model is in place). Output: one record per document with patient, prescriber, medication, etc. Write to predictions store.
3. **Validation / confidence** (optional) — Apply rules, match to master data; flag low-confidence or safety-critical items for review. Exceptions can be written to the same store with a status (e.g. `review` vs `approved`).

**Libraries**: OCR (`pdfplumber`, `pytesseract`), NLP (`transformers`, `spacy` or similar for NER when added)

**Evaluation**: When ground-truth `labels/` exist, compute field-level F1, document accuracy, exception rate. Evaluation is separate from the “save predictions” path; it reads predictions + labels and reports metrics.

### Databricks Architecture

**Config and environment switching** (same pattern as inventory_optimization / recommendation_engine):
- **DOCINT_DATA_SOURCE**: `local` | `catalog` | `auto` — where to read documents and where to write predictions.
- **Local**: DOCINT_BASE_DIR (default e.g. `prescription_pdfs/`) holds `documents/`, `predictions/` (and optional `labels/`, `annotated/`). All I/O is file-based.
- **Remote (Databricks)**: When DOCINT_DATA_SOURCE=catalog (or auto on Databricks), read document listing from catalog/volume and write predictions to Unity Catalog tables or configured volume path. Same Python code paths; config switches behaviour.

**Batch jobs** (bundle under use-case; each job runnable locally or as DAB task):
```
use_cases/document_intelligence/
├── config.py                 # get_config(), DOCINT_BASE_DIR, DOCINT_DATA_SOURCE, predictions_dir
├── data_loading.py           # load_document_data(); discover PDFs and prediction paths from config
├── run_document_intelligence.py   # Single entrypoint: load data, run OCR, run field extraction, save predictions
├── jobs/
│   ├── 1_ocr_extraction.py   # OCR only; read PDFs from config, write predictions (OCR text) to predictions store
│   └── 2_field_extraction.py # Field extraction only; read OCR from predictions store, write extracted fields to predictions store
├── resources/                # DAB job definitions
└── bundles/job/databricks.yml
```

Jobs write to a **predictions store** (local dir or catalog) so that the annotator and downstream steps consume the same outputs.

**Annotator application** (review predictions):
- **Reuse**: Streamlit app at `use_cases/document_intelligence/annotator/`
- **Purpose**: **Review model predictions** — load saved predictions (and PDFs), show PDF alongside extracted fields, allow corrections, save to `annotated/` (or catalog).
- **Usage**: Point app at base dir (or config): it reads `documents/` and **predictions/fields/** (or equivalent); user reviews and corrects; app writes to `annotated/labels/`. Optional: show confidence or exception status when available.
- **Integration**: Corrected data in `annotated/` can feed gold_doc_labels for evaluation and optional future NER training; approved records can trigger downstream ordering integration.

**Data / predictions storage** (local today; catalog when medallion exists):
- **Local**: Under DOCINT_BASE_DIR: `documents/`, `predictions/ocr/`, `predictions/fields/`, `labels/` (optional ground truth), `annotated/` (reviewer output).
- **Remote (future)**: dbt medallion or direct table writes — bronze_documents, silver_doc_pages (OCR output), silver_doc_fields_extracted (predictions), gold_doc_labels (from annotator), gold_doc_posting_ready.

**File structure** (current):
```
databricks-misc/
├── data/
│   └── prescription_pdf_generator/      # EXISTS - prescription PDF generation
│
└── use_cases/
    └── document_intelligence/
        ├── config.py                     # get_config(); base_dir, predictions_dir, data_source, on_databricks
        ├── data_loading.py               # load_document_data(); discover PDFs and prediction paths
        ├── ocr_pipeline.py               # run_ocr(); read PDFs, return/write OCR text to predictions
        ├── ner_field_extraction.py      # run_field_extraction(); read OCR/labels, return/write fields to predictions
        ├── run_document_intelligence.py  # Single entrypoint: load → OCR → extract → save predictions
        ├── jobs/
        │   ├── 1_ocr_extraction.py       # Job: OCR only, write predictions
        │   └── 2_field_extraction.py     # Job: field extraction only, write predictions
        ├── annotator/                    # Streamlit app: read predictions + PDFs, review, write annotated/
        ├── resources/                    # DAB job YAML
        └── bundles/job/databricks.yml
```

### Implementation plan (align with inventory / recommendation_engine)

1. **Config** — Extend `config.py` with `predictions_dir` (e.g. `base_dir / "predictions"`), overridable via env. Optional `DOCINT_DATA_SOURCE` = `local` | `catalog` | `auto` for future catalog reads/writes.
2. **Save predictions** — In OCR and field-extraction modules (or a small `predictions_io` helper): after each step, write results to `predictions_dir/ocr/` and `predictions_dir/fields/` (e.g. JSON per doc or single table), using the same schema the annotator expects (nested patient/doctor/facility/medication).
3. **Pipeline entrypoint** — Ensure `run_document_intelligence.py` and job scripts **save** OCR and field-extraction outputs to the predictions dir so the annotator reads from predictions, not from ground-truth labels.
4. **Field extraction input** — Until a NER model exists: either (a) derive fields from OCR with heuristics, or (b) for MVP, copy generator `labels/` into `predictions/fields/` so the annotator has something to review. Later: NER consumes OCR from predictions and writes real extractions.
5. **Annotator** — Point annotator at **predictions**: prefer `predictions/fields/` as the source to display and edit; fall back to `labels/` if predictions missing. Continue writing corrections to `annotated/labels/`.
6. **Data loading** — In `data_loading.py`, discover prediction paths (OCR and field files under `predictions_dir`) and expose them in the returned dict.
7. **Local vs remote** — When adding DOCINT_DATA_SOURCE, branch in data_loading and save logic on `config["data_source"]` to read/write catalog or volume (same pattern as inventory's catalog vs CSV).
8. **Make / README** — Document `make document_intelligence-generate-pdfs`, `make document_intelligence-run`; annotator run with same DOCINT_BASE_DIR so it sees documents + predictions + annotated.

---

## 5️⃣ AI Powered Insights & Analytics

**Business Value**: Strategic decision support | Multiple sub-initiatives
**Use Cases**:
1. Healthcare ranging & consolidation analytics
2. Animal Care market intelligence automation
3. TWC franchise reporting & store-level recommendations

**Current Status**: ⚠️ Not implemented
**Local dev**: Can be developed locally for most part.

### Data Requirements

**Sub-project 1: Ranging & Consolidation** (Healthcare)
- Reuse: `silver_orders`, `silver_products`, `silver_inventory`
- Add: `warehouse_costs` table (DC/SKU storage cost, handling cost), `fulfillment_sla` metrics

**Sub-project 2: Market Intelligence** (Animal Care)
- Add `competitor_products` table: `competitor_id`, `product_name`, `price`, `url`, `scrape_date`
- Add `competitor_price_history` table: time series of competitor pricing
- Web scraping: Python `requests` + `beautifulsoup4` or `scrapy`

**Sub-project 3: Franchise Reporting** (TWC)
- Add `store_sales` table: `store_id`, `product_id`, `date`, `sales_quantity`, `revenue`
- Add `store_attributes` table: `store_id`, `location`, `size_sqm`, `store_type`, `cluster_id`
- Add `promotions` table: `promo_id`, `store_id`, `product_id`, `start_date`, `end_date`, `discount_rate`

### Modelling Approach

**Ranging & Consolidation**:
- Optimization: minimize storage/handling costs subject to SLA constraints
- Alternative: unsupervised clustering (k-means) to group slow-moving SKUs for consolidation
- Python: `sklearn.cluster.KMeans`, `scipy.optimize`

**Market Intelligence**:
- Web scraping pipeline (non-ML)
- Optional: LLM summarization of competitor changes
  - Prompt: "Summarize key pricing changes this week for pet food category"
  - Model: Azure OpenAI or Databricks Foundation Models

**Franchise Reporting**:
- Store clustering: `sklearn.cluster.KMeans` on store attributes (size, location, demographics)
- Promo impact: causal inference or uplift modeling
  - Use `causalml` or difference-in-differences regression
- Product recommendations: reuse recommendation engine from project #1

**Evaluation**: Business KPI tracking (cost reduction %, sales uplift, analyst time saved)

### Databricks Architecture

**Each sub-project gets own use-case** (bundle under use-case):

```
use_cases/ranging_consolidation/
├── jobs/
│   └── ranging_optimizer.py            # Optimization or clustering
│       └── Output: gold_range_recommendations (SKU, DC, action, cost_impact)
├── resources/
└── databricks.yml
```

```
use_cases/market_intelligence/
├── jobs/
│   ├── 1_scrape_competitors.py          # Web scraping
│   │   └── Scrape competitor sites daily
│   │   └── Write to bronze_competitor_data
│   ├── 2_price_tracking.py             # Change detection
│   │   └── Compare today vs yesterday
│   │   └── Identify significant price changes
│   └── 3_weekly_summary.py             # LLM summarization
│       └── Generate weekly brief with key insights
│       └── Store in gold_market_intelligence_reports
├── resources/
└── databricks.yml
```

```
use_cases/franchise_analytics/
├── jobs/
│   ├── 1_store_clustering.py           # K-means clustering
│   │   └── Group stores by similarity
│   │   └── Output: gold_store_clusters
│   ├── 2_promo_impact.py               # Uplift modeling
│   │   └── Measure promo effectiveness per cluster
│   │   └── Output: gold_promo_impact
│   └── 3_recommendations.py            # Product recommendations
│       └── Reuse recommendation engine models
│       └── Output: gold_store_product_recs
├── resources/
└── databricks.yml
```

**Application**:
- Dashboards (Databricks SQL) for each sub-project
- Weekly automated reports (email/Slack integration)

**Data Pipeline** (dbt medallion):
```
data/healthcare_data_medallion/                # EXTEND existing dbt project
├── bronze/
│   ├── bronze_warehouse_costs.sql             # NEW: DC/SKU costs
│   ├── bronze_competitor_products.sql         # NEW: Scraped competitor data
│   └── bronze_store_sales.sql                 # NEW: Store/franchise sales
│
├── silver/
│   ├── silver_warehouse_costs.sql             # NEW: Validated cost data
│   ├── silver_competitor_products.sql         # NEW: Cleansed competitor data
│   └── silver_store_sales.sql                 # NEW: Validated store sales
│
└── gold/
    ├── gold_range_recommendations.sql         # NEW: SKU ranging recommendations
    ├── gold_competitor_price_history.sql      # NEW: Competitor pricing trends
    ├── gold_store_clusters.sql                # NEW: Store similarity clusters
    ├── gold_promo_impact.sql                  # NEW: Promotion effectiveness
    └── gold_store_product_recs.sql            # NEW: Store-level recommendations
```

**File Structure**:
```
databricks-misc/
├── data/
│   ├── healthcare_data_generator/
│   │   └── src/
│   │       ├── generate_ranging_data.py        # NEW
│   │       └── generate_franchise_data.py      # NEW
│   │
│   └── healthcare_data_medallion/              # EXTEND existing dbt project
│       └── src/models/
│           ├── bronze/
│           │   ├── bronze_warehouse_costs.sql  # NEW
│           │   ├── bronze_competitor_products.sql # NEW
│           │   └── bronze_store_sales.sql     # NEW
│           ├── silver/
│           │   ├── silver_warehouse_costs.sql  # NEW
│           │   ├── silver_competitor_products.sql # NEW
│           │   └── silver_store_sales.sql     # NEW
│           └── gold/
│               ├── gold_range_recommendations.sql # NEW
│               ├── gold_competitor_price_history.sql # NEW
│               ├── gold_store_clusters.sql    # NEW
│               ├── gold_promo_impact.sql      # NEW
│               └── gold_store_product_recs.sql # NEW
│
└── use_cases/
    ├── ranging_consolidation/                  # NEW MODULE
    │   ├── README.md
    │   ├── databricks.yml
    │   ├── resources/
    │   ├── requirements.txt                   # scipy, sklearn
    │   ├── ranging_optimizer.py
    │   └── jobs/
    │       └── ranging_optimizer.py
    │
    ├── market_intelligence/                    # NEW MODULE
    │   ├── README.md
    │   ├── databricks.yml
    │   ├── resources/
    │   ├── requirements.txt                   # beautifulsoup4, scrapy, openai
    │   ├── competitor_scraper.py
    │   ├── summarizer.py
    │   └── jobs/
    │       ├── 1_scrape_competitors.py
    │       ├── 2_price_tracking.py
    │       └── 3_weekly_summary.py
    │
    └── franchise_analytics/                    # NEW MODULE
        ├── README.md
        ├── databricks.yml
        ├── resources/
        ├── requirements.txt                   # sklearn, causalml
        ├── store_clustering.py
        ├── promo_impact.py
        ├── evaluation.py
        └── jobs/
            ├── 1_store_clustering.py
            ├── 2_promo_impact.py
            └── 3_recommendations.py
```

---

## Development Patterns

**Local development** (run data gen, medallion, and model training without Databricks):
- **Data generation**: Healthcare generator is pure pandas/Faker; writes CSVs to e.g. `data/local/`. No Spark or DB required. Optional: script to load CSVs into DuckDB/SQLite for a local “raw” DB.
- **Medallion**: Default dbt profile is Databricks (Unity Catalog). To run medallion locally: use dbt-duckdb (or dbt-sqlite) profile, point sources at local DB populated from generator CSVs, and adjust SQL dialect if needed (e.g. `current_timestamp()`).
- **Model training / MLflow**: Training code is pandas + sklearn/xgboost/prophet etc.; no Spark in model code. MLflow uses default tracking (local `./mlruns` when not on Databricks). Add explicit local data path (e.g. `RUN_LOCAL=1`, `DATA_PATH=...` or `use_cases.env_utils.is_running_on_databricks()`) so entrypoints load from CSV/local DB instead of requiring Spark and Unity Catalog; keep `create_sample_data()` as fallback.
- **Use cases**: Recommendation, inventory, insights — core logic and training are local-friendly (DataFrame/CSV input). Customer service — same, with local vector store (e.g. Chroma/FAISS) instead of Databricks Vector Search. Document intelligence — PDF generation, OCR, and annotation are all runnable locally using open-source libraries (no Spark NLP/OCR requirement).

**For all projects**:
- Use Databricks Connect for remote execution
- MLflow tracking for all experiments
- Unity Catalog for data + model governance
- Serverless-compatible implementations (no GPU dependencies unless required)

**Data Generation**:
- **Extend and consolidate** existing `healthcare_data_generator` where possible (shared schema); one data foundation, many use-cases on top — mimics real-life: single medallion, n use-cases consuming it.
- Create separate generators only for domain-specific data (e.g. customer service, document pipelines) where it does not fit the healthcare schema.
- Use Faker library patterns for synthetic data.
- Maintain referential integrity with existing tables.

**Data Transformation**:
- **dbt medallion architecture** for all projects (bronze → silver → gold)
- Extend existing `healthcare_data_medallion` for projects #1, #2, #5
- Create separate dbt projects for projects #3, #4 (orthogonal domains)
- Consistent patterns: data quality checks, incremental models, macro reuse

**Modelling**:
- Start with simple baselines (sklearn, heuristics)
- Iterate to more sophisticated models based on evaluation
- Prioritize interpretability and business rule integration
- Keep production models CPU-friendly for cost optimization
