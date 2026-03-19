# EBOS AI/ML use cases

**Use-cases:** Equal priority; implementation order may vary. **Infrastructure:** Databricks + Unity Catalog. **Repo layout:** Use-cases under `use_cases/<name>/` with DAB bundles (jobs, endpoints, apps) per use-case or data component. Each bundle’s `databricks.yml` uses **`include: resources/*.yml`** next to that file (job/serving/app resources live in a sibling `resources/` directory under the same bundle folder).

**Data & platform** (UC layout, data flow, grants, contracts, generator/medallion scope, local dev): [DATA_AND_PLATFORM.md](DATA_AND_PLATFORM.md).

**Existing Assets**:
- Healthcare data generator with medallion architecture (bronze/silver/gold)
- Inventory optimisation: demand forecasting, write-off risk, replenishment under `use_cases/inventory_optimization/models/`
- Recommendation engine: item_similarity, ALS, LightFM, ranker under `use_cases/recommendation_engine/models/`
- Prescription PDF generator and annotation app for document intelligence

### Current scope: demo vs production

Most implementations here are **intentionally lightweight** for demos, portfolios, and Databricks bundle smoke tests—not production-ready ML without further validation, data contracts, and monitoring. In particular:

- **Recommendation engine** — Comparable offline metrics and `@Champion` registry aliases are in place; ranking models are still simplified (e.g. negatives, catalogue scale) relative to a full production recommender.
- **Inventory optimisation** — Demand is largely a **placeholder baseline**; write-off is a **snapshot classifier** with non-leaky features relative to the label (see inventory section); **replenishment is rule-based only** (no learned policy).
- **Document intelligence** — OCR + **applied** spaCy (`en_core_web_sm`) and regex helpers; **no NER training or benchmarked evaluation** in-repo.

Treat gaps as **future improvements** unless a component is explicitly hardened for a pilot.

---

## 1️⃣ Recommendation Engine for Ordering

**Business Value**: ~$4.9m p.a. | Enterprise-wide (Healthcare, MedTech, Animal Care)
**Use Case**: Recommend similar products and auto-substitutions to reduce sales leakage and increase margins
**Current Status**: ✅ **Partial** — Item similarity, ALS, LightFM, ranker implemented under `models/`; DAB jobs and endpoints in place.
**Local dev**: Develop locally (data gen, training, saving). Optional full-pipeline entrypoint `models/run_reco_smoke.py` runs locally (CSV) or on Databricks; per-model scripts (`models/<name>/train.py`, `predict.py`) and Make targets are the main surface. Data source via config.

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

### Metrics, splits, and comparing models (recommendation)

The four recommenders **solve different sub-problems** (content similarity vs matrix factorisation vs hybrid ranker), so they are not interchangeable as a single “best accuracy” leaderboard without context. What *is* comparable in MLflow is **offline ranking quality on the same protocol**:

| Aspect | Convention in this repo |
|--------|-------------------------|
| **Train/validation split** | **Temporal split on `silver_reco_interactions`**: events sorted by `interaction_timestamp` / `timestamp`; the **last 20% of events** are validation (`reco_val_fraction` = 0.2, overridable in code via `reco_split_eval.DEFAULT_VAL_FRACTION`). Models are fit **only** on the earlier 80%. |
| **K** | **Top-10** everywhere (`RECOMMENDATION_OFFLINE_EVAL_K` = 10) so Precision/Recall/NDCG are aligned. |
| **MLflow metric keys** | **`val_precision_at_k`, `val_recall_at_k`, `val_ndcg_at_k`** — log these in every reco training run for cross-experiment comparison. |
| **Protocol params** | **`reco_eval_protocol`, `reco_eval_k`, `reco_n_train_events`, `reco_n_val_events`** describe the split so runs stay apples-to-apples. |
| **Eval user cap** | **≤500 users** by default for heavy eval paths (`RECO_OFFLINE_MAX_EVAL_USERS`) to keep ranker / scoring jobs bounded; increase when you need tighter estimates. |

**Ground truth for offline metrics:** validation-period **purchases** (`action_type == purchased`) per customer, compared to each model’s top-K recommendations for users who appear in training (standard transductive setup). **Item-to-item similarity** uses the **last product each user touched in the train window** as an anchor, then measures whether similar items match **future** validation purchases — aligned with “signal from past, evaluate on future” like the CF models.

**MLflow tip:** Filter runs by the shared metric names and by `reco_eval_k` / `reco_val_fraction` to compare Champion models across ALS, LightFM, item similarity, and ranker without mistaking incomparable quantities.

### Feature ownership (dbt vs ML code)

**Keep in dbt (medallion):** Base, reusable aggregates that many consumers need (e.g. customer × product purchase counts, last order date, product/customer attributes from silver). Think of this as **feature storage / wide tables**, not the full model-specific feature set. Optionally one slim “training base” table (e.g. `gold_reco_training_base`: customer, product, label, key IDs).

**Keep in Python (ML code):** Model-specific feature construction: time windows, normalization, one-hot/target encoding, train/test splits, negative sampling, and any logic used only by this model. **Serving path:** Whatever is computed at request time (or in a real-time pipeline) must use the same logic as in training, implemented in code (e.g. `models/feature_engineering.py`), not only in dbt.

Use dbt for shared, stable, coarse-grained building blocks; do all model-specific and serving-aligned feature engineering in Python, reading from those gold (or silver) tables. This avoids train–serve skew and keeps the medallion from being a dependency for every small ML experiment, while still benefiting from a single, governed data foundation.

### Databricks architecture

**Data:** Reco reads from medallion silver (e.g. silver_reco_interactions, silver_products, silver_orders); use-case-owned tables (e.g. gold_reco_training_base, gold_item_similarity_candidates) live in `recommendation_engine_<env>`. See [DATA_AND_PLATFORM.md](DATA_AND_PLATFORM.md).

**Training workflow** (scheduled weekly; DAB bundle under use-case):
- Jobs live in `use_cases/recommendation_engine/bundles/job/resources/` (retrain_jobs.yml, batch_apply_jobs.yml, transform_jobs.yml). **Each model** (item_similarity, ALS, LightFM, ranker) has its own **retrain** and **batch-apply** job calling `models/<name>/train.py` and `models/<name>/predict.py`. **`recommendation_engine_retrain`** / **`recommendation_engine_apply`** run `models/run_reco_smoke.py` as an optional **integration/smoke** path (scheduled after per-model jobs). Serving endpoints in `bundles/serving/resources/reco_endpoints.yml`.

**Serving endpoints** (real-time API):
- **One Model Serving endpoint per model family** (item similarity, ALS, LightFM, ranker), e.g. `recommendation-engine-item-similarity`, `recommendation-engine-als`, `recommendation-engine-lightfm`, `recommendation-engine-ranker`. This is intentional: each registered model is deployed separately; **callers** (ordering systems, Streamlit demo, or a future router) choose the endpoint or compose results—there is no single unified multi-model endpoint in this repo.
- Input: `{"customer_id": "C123", "context": {"cart": ["P456"], "out_of_stock": "P789"}}`
- Output: `[{"product_id": "P999", "score": 0.87, "reason": "similar_therapeutic_class", "margin": 0.15}]`
- Fallback logic is currently implemented at the application/orchestration layer rather than a single endpoint contract.
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
├── bundles/
│   ├── job/                    # databricks.yml; resources/retrain_jobs.yml, batch_apply_jobs.yml
│   ├── serving/                # databricks.yml; resources/reco_endpoints.yml
│   └── app/                    # databricks.yml; Streamlit app bundle
├── models/                     # Per-model: core + train + predict
│   ├── run_reco_smoke.py       # Full-pipeline entrypoint (used by DAB retrain job for item_sim + ALS + ranker)
│   ├── data_loading.py, evaluation.py, feature_engineering.py
│   ├── item_similarity/        # core.py, train.py, predict.py
│   ├── als/                    # core.py, train.py, predict.py
│   ├── lightfm/                # core.py, train.py, predict.py
│   └── ranker/                 # core.py, train.py, predict.py (+ DAB retrain/apply jobs)
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

**Component 2: Write-off Risk Classification** ✅ **EXISTS (demo)**
- `lightgbm.LGBMClassifier` or `sklearn.ensemble.RandomForestClassifier` via `models/writeoff_risk/`.
- Target: binary `will_expire_30d` derived from `days_until_expiry` in the training job — **`days_until_expiry` is not used as a model feature** (avoids trivial leakage); signal comes from stock, demand proxy, turnover, calendar month, and optional product category. **Production** should move to event-based labels and an explicit as-of date.
- Training/retrain **job 2** delegates to `models/writeoff_risk/train.py` (MLflow + registry + **`@Champion`**). Batch apply defaults to `models:/inventory_optimization-writeoff_risk@Champion` (`WRITEOFF_RISK_MODEL_URI`).
- Metrics logged include **PR-AUC** (`pr_auc`) where `predict_proba` exists.

**Component 3: Replenishment** ✅ **Rule-based only (demo)**
- **No ML model**: ROP-style heuristics from inventory + orders (`models/replenishment/`). Suitable for demos and planner-style outputs; **not** a learned optimiser.
- Future: constrained optimisation (e.g. `scipy`, `pulp`) or RL would sit behind the same job taxonomy but are out of scope for the current code path.

**Evaluation**: Forecast MAE/RMSE/MAPE, reduction in write-offs (%), service level achievement, inventory turnover ratio

### Metrics, comparability, and MLflow (inventory)

The three inventory components are **structurally different**: demand is **forecast error** (regression over time), write-off is **classification** (precision/recall/F1 on risk), replenishment is a **policy / heuristic** (counts and quantities from ROP-style rules, not ranking accuracy). It is **normal and correct** that they do **not** share a single headline metric; comparing them directly like-for-like would be misleading.

**When you *can* align in MLflow**

- Use **consistent naming prefixes** by task so the UI stays organised, e.g. `forecast_*`, `writeoff_*`, `replenishment_*` (already reflected in separate experiments per component).
- **Demand vs write-off:** You could add auxiliary **business-shaped** metrics on shared slices (e.g. expected € impact, or calibration on a holdout week) — only if defined carefully — but **do not force** MAPE and F1 into one number.
- **Replenishment:** Log **operational summaries** (`below_rop_count`, `total_reorder_qty`, etc.) as metrics; treat them as **KPIs**, not classification metrics.

**Train/test separation (current intent)**

- **Demand (`compare_forecasting_models`):** **Temporal split** on order rows by `order_date`: mean fitted on the early **80%**, MAE/RMSE/MAPE on the **held-out 20%** (see `models/demand_forecasting/core.py`). Full Prophet/XGBoost work should keep the same contract.
- **Write-off:** **Stratified train/test** inside the classifier (`models/writeoff_risk/core.py`); **`days_until_expiry` is excluded from features** when training `will_expire_30d`. Logged metrics include **PR-AUC** (`pr_auc`) on the holdout split.
- **Replenishment:** Uses **current** inventory + orders to compute a policy; there is no classic ML test set unless you simulate forward periods separately.

This keeps MLflow useful for **within-component** comparisons (e.g. two demand models, two write-off checkpoints) while making cross-component comparison **qualitative** (KPIs and business outcomes) rather than a single shared accuracy score.

### Databricks Architecture

**Training Workflow** (scheduled weekly; DAB bundle under use-case): Jobs in `use_cases/inventory_optimization/bundles/job/resources/` (retrain_jobs.yml, batch_apply_jobs.yml). DAB tasks invoke `jobs/1_demand_forecasting.py`, `jobs/2_writeoff_risk_model.py`, `jobs/3_replenishment_optimization.py`, which use code under `models/demand_forecasting/`, `models/writeoff_risk/`, `models/replenishment/` (each with core.py, train.py, predict.py). Single entrypoint for local/scripted run: `run_inventory_smoke.py`.

**Serving/Application**:
- Batch scoring output to dashboard (Databricks SQL) for inventory planners
- Optional: real-time API for "should I reorder now?" queries
- Alerts: send notifications when inventory falls below reorder point

**Data:** Inventory reads from medallion silver/bronze (silver_inventory, silver_orders, silver_expiry_batches, etc.); writes to `inventory_optimization_<env>` (gold_writeoff_risk_scores, gold_replenishment_recommendations, etc.). See [DATA_AND_PLATFORM.md](DATA_AND_PLATFORM.md).

**File structure:** Data/medallion as in Data Pipeline above. Use-case layout:
```
use_cases/inventory_optimization/
├── config.py
├── run_inventory_smoke.py     # Single entrypoint (local or scripted: load → train/apply components)
├── jobs/                      # DAB entrypoints: 1_demand_forecasting.py, 2_writeoff_risk_model.py, 3_replenishment_optimization.py
├── data_loading.py           # Root-level data loading (used by run_inventory / jobs)
├── bundles/job/               # databricks.yml; resources/retrain_jobs.yml, batch_apply_jobs.yml
└── models/                    # Per-model: core + train + predict
    ├── demand_forecasting/
    ├── writeoff_risk/
    ├── replenishment/
    ├── data_loading.py
    └── evaluation.py
```

---

## 3️⃣ AI Customer Service Agents

**Business Value**: Labour cost reduction + scalability | Cross-business (Healthcare, MedTech, TWC)
**Use Case**: Automate common queries, improve satisfaction, provide order tracking visibility
**Current Status**: 🕒 **Future implementation** (planned; not in current delivery scope). There is no `use_cases/customer_service_agent/` tree or customer-service generator in this repo yet—the sections below describe the **intended** design.
**Local dev**: Deferred until implementation is scheduled.

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

**Data:** Separate customer_service generator + medallion (bronze/silver/gold for cases, messages, knowledge docs). See [DATA_AND_PLATFORM.md](DATA_AND_PLATFORM.md) and generator scope.

**File structure:**
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
**Current Status**: ✅ **Partial** — PDF generator, OCR, spaCy/rule field extraction (optional), label fallback, annotator; **no trained NER benchmark** in-repo
**Local dev**: Same patterns as recommendation_engine and inventory_optimization — config-driven local vs remote (DOCINT_BASE_DIR / DOCINT_DATA_SOURCE), modular jobs, single entrypoint; PDF generation, OCR, and annotator run locally with open-source libs (no Spark).

### Pipeline flow (generate → predict → save → review)

Document intelligence is **not** a classic train-then-batch-score modelling use case. The flow is:

1. **Generate documents** — Produce synthetic prescription PDFs (and optional ground-truth JSON for evaluation only) via `data/prescription_pdf_generator/`. Output: `documents/`, optionally `labels/` (ground truth).
2. **Generate predictions** — Run OCR and NER/field extraction on those documents. Output is **model predictions** (OCR text per page, extracted prescription fields per document), not training labels.
3. **Save predictions** — Persist predictions in a known location so the next step and the annotator can consume them.
   - **Local**: e.g. `predictions/ocr/` (per-doc or combined) and `predictions/fields/` (extracted fields as JSON or table).
   - **Remote (catalog mode)**: when `DOCINT_DATA_SOURCE` resolves to `catalog` on Databricks, OCR and field outputs are written to Unity Catalog tables (`silver_doc_pages`, `silver_doc_fields_extracted` by default; overridable via env). Implemented in `predictions_io.py` (`write_ocr_output` / `write_field_output`). PDFs for remote runs are expected on the configured UC volume path (`get_config()` / `DOCINT_DOCUMENTS_VOLUME`).
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
1. **OCR** — `pdfplumber` for PDF → text per page. Write results to predictions store (local JSON under `predictions/ocr/` or UC `silver_doc_pages`).
2. **Field extraction** — **Applied** NLP on OCR text:
   - **spaCy** + **`en_core_web_sm`** — both are declared under the **`document_intelligence`** optional extra in `pyproject.toml` (model installed as a pinned wheel via `uv sync --extra document_intelligence`; DAB pipeline env lists the same wheel URL).
   - **Regex / rules** in `spacy_ner_pipeline.py` for AU-oriented patterns (Medicare-style numbers, ABN, phone, Rx/script hints, AHPRA-style text).
   - **No model training or held-out evaluation** in this path — only inference. Env: `DOCINT_FIELD_SOURCE` = `auto` (try OCR+spaCy first) | `ocr` | `labels`.
   - If spaCy/OCR is missing or empty, **`auto` falls back to generator JSON labels** (demo parity with the annotator).
3. **Validation / confidence** (optional) — Rules and master-data checks remain future work.

**Libraries**: OCR (`pdfplumber`); NLP (`spacy` optional extra). Heavier `transformers`-based NER is a possible future swap behind the same `run_field_extraction` interface.

**Evaluation**: Not run automatically for the spaCy path. When ground-truth `labels/` exist, ad-hoc field-level metrics can be computed offline; that is separate from the “save predictions” job.

### Databricks Architecture

**Config and environment switching** (same pattern as inventory_optimization / recommendation_engine):
- **DOCINT_DATA_SOURCE**: `local` | `catalog` | `auto` — where to read documents and where to write predictions.
- **Local**: DOCINT_BASE_DIR (default e.g. `data/local/prescription_pdfs/`) holds `documents/`, `predictions/` (and optional `labels/`, `annotated/`). All I/O is file-based.
- **Remote (Databricks)**: When DOCINT_DATA_SOURCE=catalog (or auto on Databricks), read document listing from catalog/volume and write predictions to Unity Catalog tables or configured volume path. Same Python code paths; config switches behaviour.

**Remote / cluster:** Include `spacy` and the **`en_core_web_sm`** wheel in the cluster environment (see `document_intelligence_job.yml` `pipeline_env` dependencies); locally they come from `uv sync --extra document_intelligence`. If the model package is missing, the code falls back to `blank:en` (regex-only entities, no PERSON/ORG from spaCy).

**Batch jobs** (bundle under use-case; each job runnable locally or as DAB task):
```
use_cases/document_intelligence/
├── config.py                     # get_config(), DOCINT_BASE_DIR, DOCINT_DATA_SOURCE, predictions_dir
├── data_loading.py               # load_document_data(); discover PDFs and prediction paths from config
├── ocr_pipeline.py               # run_ocr(); read PDFs, write OCR text to predictions store
├── ner_field_extraction.py       # run_field_extraction(); OCR+spaCy or labels → fields
├── spacy_ner_pipeline.py         # Pretrained spaCy + regex; apply-only (no training loop)
├── predictions_io.py             # Save/load predictions (OCR and fields) to predictions_dir
├── jobs/
│   ├── 1_generate_data.py        # Generate prescription PDFs + labels (documents/, labels/)
│   ├── 2_ocr_extraction.py       # OCR only; write predictions to predictions store
│   └── 3_field_extraction.py     # Field extraction only; write extracted fields to predictions store
└── bundles/job/                  # databricks.yml; resources/document_intelligence_job.yml
```

Jobs write to a **predictions store** (local dir or catalog) so that the annotator and downstream steps consume the same outputs.

**Annotator application** (review predictions):
- **Reuse**: Streamlit app at `use_cases/document_intelligence/annotator/`
- **Purpose**: **Review model predictions** — load saved predictions (and PDFs), show PDF alongside extracted fields, allow corrections, save to `annotated/` (or catalog).
- **Usage**: Point app at base dir (or config): it reads `documents/` and **predictions/fields/** (or equivalent); user reviews and corrects; app writes to `annotated/labels/`. Optional: show confidence or exception status when available.
- **Integration**: Corrected data in `annotated/` can feed gold_doc_labels for evaluation and optional future NER training; approved records can trigger downstream ordering integration.

**Data / predictions:** Local = DOCINT_BASE_DIR (documents/, predictions/, annotated/). Remote = UC volume for PDFs, use-case schema for tables (silver_doc_pages, silver_doc_fields_extracted). See [DATA_AND_PLATFORM.md](DATA_AND_PLATFORM.md).

**File structure** (current):
```
use_cases/document_intelligence/
├── config.py                     # get_config(); base_dir, predictions_dir, data_source, on_databricks
├── data_loading.py               # load_document_data(); discover PDFs and prediction paths
├── ocr_pipeline.py               # run_ocr(); read PDFs, write OCR text to predictions
├── ner_field_extraction.py       # run_field_extraction(); OCR+spaCy or labels → fields
├── spacy_ner_pipeline.py         # spaCy + regex; apply-only
├── predictions_io.py             # Save/load predictions (OCR, fields) to predictions_dir
├── jobs/
│   ├── 1_generate_data.py        # Job: generate prescription PDFs + labels
│   ├── 2_ocr_extraction.py       # Job: OCR only, write predictions
│   └── 3_field_extraction.py     # Job: field extraction only, write predictions
├── annotator/                    # Streamlit app: read predictions + PDFs, review, write annotated/
└── bundles/job/                  # databricks.yml; resources/document_intelligence_job.yml
```
Data: prescription PDFs from `data/prescription_pdf_generator/`.

### Implementation plan (align with inventory / recommendation_engine)

1. **Config** — Extend `config.py` with `predictions_dir` (e.g. `base_dir / "predictions"`), overridable via env. Optional `DOCINT_DATA_SOURCE` = `local` | `catalog` | `auto` for future catalog reads/writes.
2. **Save predictions** — In OCR and field-extraction modules (or a small `predictions_io` helper): after each step, write results to `predictions_dir/ocr/` and `predictions_dir/fields/` (e.g. JSON per doc or single table), using the same schema the annotator expects (nested patient/doctor/facility/medication).
3. **Pipeline entrypoint** — Ensure `jobs/2_ocr_extraction.py` and `jobs/3_field_extraction.py` **save** OCR and field-extraction outputs to the predictions dir so the annotator reads from predictions, not from ground-truth labels.
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

**Current Status**: ✅ **Partial** — Streamlit router (`use_cases/ai_powered_insights/app/`), DAB bundles under `use_cases/ai_powered_insights/bundles/{app,genie_spaces,dashboards}/`. **Not deploy-ready by default:** Genie Space IDs, SQL warehouse ID, service principal names (`<TBD-...>` in bundle variables), and dashboard deep-link URLs must be set per workspace—see those YAML files and `technical_design.md`.
**Local dev**: Streamlit app runs locally; Genie/dashboard resources target Databricks.

**New (proposed) UX layer**: Databricks Genie + Streamlit “data chat”
- Build multiple domain-specific Genie Spaces (Healthcare, Animal Care, TWC) rather than one large general-purpose space.
- Host a single Streamlit app that routes chat prompts to the selected Genie Space and renders both text + tabular query results.

**Data:** Genie and dashboards read from medallion bronze/silver (e.g. silver_orders, bronze_competitor_price_history, bronze_promotions). Use-case schema `ai_powered_insights_<env>` reserved for future marts. See [DATA_AND_PLATFORM.md](DATA_AND_PLATFORM.md).

### Genie Chat Experience (domain-scoped Genie Spaces + Streamlit router)

**Goal**: Let analysts ask natural-language questions over the same governed medallion outputs (silver/gold), while keeping domain semantics isolated via separate Genie Spaces.

**Multiple specialized Genie Spaces (recommended; 1 per domain)**:
- `healthcare_insights`:
  - Knowledge Store scope: healthcare silver/gold tables required for ranging & consolidation KPIs.
  - Add domain metadata + synonyms (DC naming, SKU naming, KPI definitions).
- `animal_care_insights`:
  - Knowledge Store scope: competitor product + price history + market-intelligence outputs.
  - Add trusted SQL expressions / "gold standard" KPI definitions used by your reports.
- `twc_franchise_insights`:
  - Knowledge Store scope: store attributes + promotion impact + store-level recommendations.
  - Add business semantics (cluster naming, promo identifiers, sales/revenue KPI definitions).

**Governance & isolation**:
- Use Unity Catalog permissions (table-level access + Genie Space permissions) so users only see permitted results.
- Keep each Space’s table list small (focus on ~5–10 tables per domain) to reduce ambiguity and prevent conflicting KPI definitions.

**Streamlit router (hosted as a Databricks App)**:
- A single Streamlit app provides a domain selector and maps the selected domain to the corresponding Genie Space ID.
- Use `databricks-sdk` `WorkspaceClient()` to call the Genie Conversation APIs.
- Render Genie attachments:
  - plain text explanations
  - generated SQL (optional) inside an expander
  - tabular results (retrieved by statement/statement_id) displayed as a DataFrame
- Optionally collect feedback with `st.feedback` and send it back to Genie (`w.genie.send_message_feedback`).

**Target “product shape”** (as requested):
- 3x domain Genie Spaces (`healthcare_insights`, `animal_care_insights`, `twc_franchise_insights`)
- 1x Streamlit router app (hosted as a Databricks App) that switches which Genie Space is used based on domain
- 1x BI dashboard per domain (Databricks SQL), each built on the corresponding medallion gold outputs

**Genie configuration**:
- For each Genie Space, set the Knowledge Store scope to only the relevant silver/gold tables, plus the KPI definitions/synonyms used by that domain’s dashboard.

**Router behavior**:
- Router app shows a domain selector.
- Router app maps domain -> Genie Space ID and sends the user prompt to the selected Space.
- Render attachments: text + optional SQL + tabular results.

**Example logical structure**:
```
use_cases/ai_powered_insights/
├── app/
│   └── app.py                               # router: select domain -> call selected Genie Space
├── app/requirements.txt
└── bundles/app/databricks.yml              # Databricks Apps bundle
```

**Domain dashboards (Databricks SQL)**:
- Healthcare dashboard: reads from `silver_orders` (inventory + order performance derived)
- Animal Care dashboard: reads from `bronze_competitor_price_history`
- TWC dashboard: reads from `bronze_store_sales`, `bronze_store_attributes`, and `bronze_promotions`

### ⚠️ Technical Limits & Considerations

**The "Cross-Domain" Gap**:
- If a user in the Healthcare space asks a question about Animal Care, the app may fail or return an irrelevant answer.
- Recommendation (Streamlit UI): include a clear “Capabilities” list for the active domain so users know the boundaries.
  - Add a capabilities list for each selected domain.
  - Ensure the current domain is actively flagged/state-maintained (persist the `active_domain` in `st.session_state` across reruns).

**Latency**:
- `start_conversation_and_wait_for_answer` is synchronous and can take ~10–30 seconds.
- Recommendation: show a spinner/status (e.g. `st.status` during conversation start and SQL generation) to manage user expectations.

**API Rate Limits**:
- Genie currently has a concurrency limit (often ~5–10 requests per minute depending on workspace tier).
- Recommendation: handle 429s gracefully (retry with backoff + friendly error message).

**Statement Execution Logic**:
- When rendering tabular results, `statement_execution` results can expire.
- Recommendation: do not rely on long-lived “download later” links; render immediate downloads from the retrieved DataFrame, and provide a “try again” fallback if needed.

### 🛠 Suggested Enhancements

**Thread Persistence**:
- Use `conversation_id` (or `thread_id`) mapped to the Streamlit session (`st.session_state`) so users can ask follow-ups without losing context (e.g. “Now show me that by region”).

**Hybrid UI (Deep Linking)**:
- After Genie identifies a high-level analytics intent, provide a “View full dashboard” deep-link for a full-screen BI experience.

**Supervisor / Auto-routing (optional)**:
- Replace manual domain selection with a lightweight supervisor classifier:
  - Use a Databricks-hosted foundational model (Model Serving) to predict domain from the user prompt.
  - If confidence is low, fall back to the manual domain selector.

Implementation details live in `use_cases/ai_powered_insights/technical_design.md`.

---

## Development patterns

**Local vs remote, data generation, medallion, grants:** [DATA_AND_PLATFORM.md](DATA_AND_PLATFORM.md) and [data/README.md](../data/README.md).

**Modelling (summary):**
- (See DATA_AND_PLATFORM.md for data generation.) No Spark or DB required. Optional: script to load CSVs into DuckDB/SQLite for a local “raw” DB.
- **Model training / MLflow**: Training code is pandas + sklearn/xgboost/prophet etc.; no Spark in model code. MLflow uses default tracking (local `./mlruns` when not on Databricks). Add explicit local data path (e.g. `RUN_LOCAL=1`, `DATA_PATH=...` or `utils.env_utils.is_running_on_databricks()`) so entrypoints load from CSV/local DB instead of requiring Spark and Unity Catalog; keep `create_sample_data()` as fallback.
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

**Modelling:** Start with simple baselines; iterate from evaluation; prefer interpretability and business rules; keep production models CPU-friendly.
