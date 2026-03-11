# EBOS AI/ML Technical Implementation Shortlist

**Priority Order**: Based on ELT "Business Value vs Complexity" prioritisation  
**Infrastructure**: Databricks + Unity Catalog (`workspace.default` schema)  
**Existing Assets**: 
- Healthcare data generator with medallion architecture (bronze/silver/gold)
- Demand forecasting models (XGBoost, ETS, Prophet) with MLflow tracking
- Spark NLP setup for document intelligence

---

## 1️⃣ Recommendation Engine for Ordering ✅ **TOP PRIORITY**

**Business Value**: ~$4.9m p.a. | Enterprise-wide (Healthcare, MedTech, Animal Care)  
**Use Case**: Recommend similar products and auto-substitutions to reduce sales leakage and increase margins  
**Current Status**: ⚠️ Not implemented

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

### Databricks Architecture

**Training Workflow** (scheduled weekly):
```
jobs/recommendation_engine_training/
├── 1_feature_engineering.py          # DLT pipeline
│   └── bronze_interactions → silver_interactions → gold_reco_features
│   └── Aggregate purchase history, co-occurrence matrices, product embeddings
│
├── 2_model_training.py                # Model training job
│   └── Train item-similarity, ALS, LightGBM models
│   └── Log to MLflow with metrics (precision@5, recall@10, NDCG)
│   └── Register winning model to Unity Catalog (workspace.default.reco_models)
│
└── 3_batch_scoring.py                 # Candidate generation
    └── Score top-50 recommendations per customer
    └── Write to gold_reco_candidates (partitioned by customer_id)
    └── Cache for 7 days, refresh weekly
```

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

**File Structure**:
```
databricks-misc/
├── data/
│   └── healthcare_data_generator/
│       └── src/
│           ├── generate_recommendation_data.py  # NEW: substitutions, interactions
│           └── ...
│
└── modelling/
    └── recommendation_engine/                   # NEW MODULE
        ├── README.md
        ├── requirements.txt                     # implicit, lightgbm, scikit-learn
        ├── item_similarity.py                   # Phase 1
        ├── collaborative_filtering.py           # Phase 2 (ALS)
        ├── hybrid_ranker.py                     # Phase 3 (LightGBM)
        ├── feature_engineering.py
        └── evaluation.py
```

---

## 2️⃣ Inventory Optimisation

**Business Value**: Direct EBIT + working capital benefits | High value across MedTech, TWC, Healthcare  
**Use Case**: Right product at right place/time/price to drive sales growth and reduce write-offs  
**Current Status**: ✅ **Partial** - Demand forecasting exists, optimization layer missing

### Data Requirements

**Extend existing `healthcare_data_generator`**:
- Add `expiry_batches` table: `batch_id`, `product_id`, `warehouse_id`, `expiry_date`, `quantity`, `cost_basis`
- Add `writeoff_events` table: `event_id`, `product_id`, `warehouse_id`, `quantity`, `reason` (expired, damaged, obsolete), `cost`, `timestamp`
- Add `purchase_orders` table: `po_id`, `supplier_id`, `product_id`, `quantity`, `order_date`, `expected_delivery_date`, `actual_delivery_date`, `unit_cost`
- Add `supplier_performance` table: `supplier_id`, `product_id`, `fill_rate`, `avg_lead_time_days`, `lead_time_std`, `month`

**Expected volume**: ~50k inventory transactions/month, ~2k writeoffs/month (synthetic)

**Reuse**: Existing `silver_orders`, `silver_products`, `silver_inventory` tables; leverage demand forecasting models

### Modelling Approach

**Component 1: Demand Forecasting** ✅ **EXISTS** - Reuse existing models
- XGBoost, ETS, Prophet models already implemented in `/modelling/demand_forecasting/`
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

**Training Workflow** (scheduled weekly):
```
jobs/inventory_optimization/
├── 1_demand_forecasting.py            # REUSE existing models
│   └── Run XGBoost/ETS/Prophet models per product × warehouse
│   └── Output: gold_demand_forecast (date, product_id, warehouse_id, forecast_p50, forecast_p75, forecast_p90)
│
├── 2_writeoff_risk_model.py           # NEW: Classification model
│   └── Train RandomForest on historical expiry/writeoff data
│   └── Features: days_to_expiry, inventory_level, forecast_demand, turnover_rate
│   └── Output: gold_writeoff_risk_scores
│
└── 3_replenishment_optimization.py    # NEW: Safety stock or LP solver
    └── Calculate reorder points and optimal order quantities
    └── Apply capacity and MOQ constraints
    └── Output: gold_replenishment_recommendations (product_id, warehouse_id, reorder_qty, priority)
```

**Serving/Application**:
- Batch scoring output to dashboard (Databricks SQL) for inventory planners
- Optional: real-time API for "should I reorder now?" queries
- Alerts: send notifications when inventory falls below reorder point

**File Structure**:
```
databricks-misc/
├── data/
│   └── healthcare_data_generator/
│       └── src/
│           ├── generate_inventory_data.py      # NEW: expiry, writeoffs, POs
│           └── ...
│
└── modelling/
    ├── demand_forecasting/                     # EXISTS - reuse
    └── inventory_optimization/                 # NEW MODULE
        ├── README.md
        ├── requirements.txt                    # scipy, pulp (optional)
        ├── writeoff_risk_classifier.py         # NEW
        ├── replenishment_optimizer.py          # NEW
        └── evaluation.py
```

---

## 3️⃣ AI Customer Service Agents

**Business Value**: Labour cost reduction + scalability | Cross-business (Healthcare, MedTech, TWC)  
**Use Case**: Automate common queries, improve satisfaction, provide order tracking visibility  
**Current Status**: ⚠️ Not implemented

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

**Offline Preparation**:
```
jobs/customer_service_agent/
├── 1_intent_training.py                # Train intent classifier
│   └── Load labeled messages from silver_case_messages
│   └── Train DistilBERT or sklearn model
│   └── Register to Unity Catalog
│
└── 2_knowledge_indexing.py             # Build vector index
    └── Chunk knowledge docs, generate embeddings
    └── Store in Databricks Vector Search (Unity Catalog)
    └── Refresh weekly or on doc updates
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

**File Structure**:
```
databricks-misc/
├── data/
│   └── customer_service_generator/            # NEW DATA BUNDLE
│       ├── databricks.yml
│       └── src/
│           └── generate_cs_data.py            # Cases, messages, knowledge docs
│
└── modelling/
    └── customer_service_agent/                # NEW MODULE
        ├── README.md
        ├── requirements.txt                   # sentence-transformers, openai, fastapi
        ├── intent_classifier.py
        ├── rag_pipeline.py
        ├── agent_orchestrator.py              # Main logic
        └── evaluation.py
```

---

## 4️⃣ Document Intelligence (Finance & Ordering)

**Business Value**: Manual labour reduction | High ROI for P2P, O2C, invoice processing  
**Use Case**: Reduce manual document processing using AI to interpret and integrate into target systems  
**Current Status**: ✅ **Partial** - Spark NLP setup exists, needs implementation

### Data Requirements

**New data pipeline** (synthetic PDFs):
- Reuse/extend `/data/prescription_pdf_generator/` patterns for invoice/PO generation
- Generate synthetic PDFs: invoices, purchase orders, delivery notes
- Add `bronze_documents` table: `doc_id`, `file_path`, `doc_type`, `upload_timestamp`, `source_system`
- Add labeled ground truth: `gold_doc_labels` with extracted fields (supplier, amount, date, line items)

**Document types**:
1. Invoices: supplier name, invoice number, date, line items (product, qty, price), total, GST, payment terms
2. Purchase Orders: PO number, supplier, delivery address, line items, total, delivery date
3. Delivery notes: delivery number, order reference, items delivered, signatures

**Expected volume**: ~1k documents/month (synthetic)

**Existing asset**: Spark NLP setup in `/modelling/document_intelligence/`

### Modelling Approach

**Pipeline**:
1. **OCR** - spark-ocr for PDF → text extraction
2. **Layout Analysis** - Identify document structure (tables, header/footer, line items)
3. **Field Extraction** - spark-nlp NER models fine-tuned for invoices/POs
   - Pre-trained: start with `ner_deid` or general `ner_dl` models
   - Fine-tune on synthetic labeled dataset (500-1000 docs)
   - Extract entities: supplier, date, amounts, product codes, quantities
4. **Post-processing** - Validation rules, entity matching to master data (`silver_products`, `silver_suppliers`)
5. **Confidence Scoring** - Route low-confidence extractions to human review queue

**Libraries**: `spark-ocr`, `spark-nlp`, `spark-nlp-healthcare` (for advanced NER)

**Evaluation**: Field-level F1 score, end-to-end document accuracy, exception rate

### Databricks Architecture

**Batch Processing Pipeline**:
```
jobs/document_intelligence/
├── 1_ingest_documents.py               # Auto Loader
│   └── Monitor blob storage/volume for new PDFs
│   └── Load to bronze_documents (binary + metadata)
│
├── 2_ocr_extraction.py                 # Spark OCR
│   └── Convert PDF → text, extract tables
│   └── Write to silver_doc_pages
│
├── 3_field_extraction.py               # Spark NLP NER
│   └── Apply fine-tuned NER models
│   └── Extract: supplier, invoice_number, date, total, line_items
│   └── Write to silver_doc_fields_extracted
│
└── 4_validation_matching.py            # Post-processing
    └── Validate extracted fields (date formats, amounts)
    └── Match supplier names to silver_suppliers
    └── Route exceptions to gold_doc_exceptions_queue
    └── Route approved to gold_doc_posting_ready
```

**Training Workflow**:
```
jobs/document_intelligence_training/
└── train_ner_model.py                  # Fine-tune NER
    └── Load labeled documents from gold_doc_labels
    └── Fine-tune spark-nlp NER model
    └── Evaluate on test set
    └── Register model to Unity Catalog
```

**Application**:
- Finance team dashboard shows exceptions queue
- Approved documents trigger downstream integration (ERP posting)

**File Structure**:
```
databricks-misc/
├── data/
│   └── document_intelligence_generator/ # NEW: invoice/PO PDF generator
│       └── src/
│           └── generate_documents.py
│
└── modelling/
    └── document_intelligence/           # EXISTS - extend
        ├── setup_spark_nlp.ipynb        # EXISTS
        ├── requirements.spark.txt       # EXISTS
        ├── README.md                    # NEW
        ├── ocr_pipeline.py              # NEW
        ├── ner_field_extraction.py      # NEW
        ├── train_ner.py                 # NEW
        └── evaluation.py                # NEW
```

---

## 5️⃣ AI Powered Insights & Analytics

**Business Value**: Strategic decision support | Multiple sub-initiatives  
**Use Cases**: 
1. Healthcare ranging & consolidation analytics
2. Animal Care market intelligence automation
3. TWC franchise reporting & store-level recommendations

**Current Status**: ⚠️ Not implemented

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

**Each sub-project gets own job**:

```
jobs/ranging_consolidation/
└── ranging_optimizer.py                # Optimization or clustering
    └── Output: gold_range_recommendations (SKU, DC, action, cost_impact)
```

```
jobs/market_intelligence/
├── 1_scrape_competitors.py             # Web scraping
│   └── Scrape competitor sites daily
│   └── Write to bronze_competitor_data
│
├── 2_price_tracking.py                 # Change detection
│   └── Compare today vs yesterday
│   └── Identify significant price changes
│
└── 3_weekly_summary.py                 # LLM summarization
    └── Generate weekly brief with key insights
    └── Store in gold_market_intelligence_reports
```

```
jobs/franchise_analytics/
├── 1_store_clustering.py               # K-means clustering
│   └── Group stores by similarity
│   └── Output: gold_store_clusters
│
├── 2_promo_impact.py                   # Uplift modeling
│   └── Measure promo effectiveness per cluster
│   └── Output: gold_promo_impact
│
└── 3_recommendations.py                # Product recommendations
    └── Reuse recommendation engine models
    └── Output: gold_store_product_recs
```

**Application**:
- Dashboards (Databricks SQL) for each sub-project
- Weekly automated reports (email/Slack integration)

**File Structure**:
```
databricks-misc/
├── data/
│   └── healthcare_data_generator/
│       └── src/
│           ├── generate_ranging_data.py        # NEW
│           └── generate_franchise_data.py      # NEW
│
└── modelling/
    ├── ranging_consolidation/                  # NEW MODULE
    │   ├── README.md
    │   ├── requirements.txt                    # scipy, sklearn
    │   └── ranging_optimizer.py
    │
    ├── market_intelligence/                    # NEW MODULE
    │   ├── README.md
    │   ├── requirements.txt                    # beautifulsoup4, scrapy, openai
    │   ├── competitor_scraper.py
    │   └── summarizer.py
    │
    └── franchise_analytics/                    # NEW MODULE
        ├── README.md
        ├── requirements.txt                    # sklearn, causalml
        ├── store_clustering.py
        ├── promo_impact.py
        └── evaluation.py
```

---

## Implementation Priority & Roadmap

**Immediate (Q1)**:
1. ✅ #1 Recommendation Engine (4-6 weeks) - highest ROI, clear requirements
2. ✅ #2 Inventory Optimization (2-3 weeks) - leverage existing forecasting, add optimization layer

**Next (Q2)**:
3. #4 Document Intelligence (3-4 weeks) - leverage existing Spark NLP setup
4. #3 Customer Service Agents (3-4 weeks) - GenAI experimentation, lower risk

**Strategic (Q3+)**:
5. #5 AI Powered Insights & Analytics - bundle of sub-projects, priority TBD based on stakeholder feedback

---

## Development Patterns

**For all projects**:
- Local development in `databricks-misc/` conda env
- Use Databricks Connect for remote execution
- MLflow tracking for all experiments
- Unity Catalog for data + model governance
- Serverless-compatible implementations (no GPU dependencies unless required)

**Data Generation**:
- Extend existing `healthcare_data_generator` where possible (shared schema)
- Create separate generators for domain-specific data (customer service, documents)
- Use Faker library patterns for synthetic data
- Maintain referential integrity with existing tables

**Modelling**:
- Start with simple baselines (sklearn, heuristics)
- Iterate to more sophisticated models based on evaluation
- Prioritize interpretability and business rule integration
- Keep production models CPU-friendly for cost optimization
