✅ Top 5 priority projects (excluding HPS)
1️⃣ Recommendation Engine for Ordering ✅ Top overall priority
 [Data Worki...ember 2024 | PowerPoint]
Why it ranks #1 (explicit):

Ranked #1 in the ELT “Business Value vs Complexity” prioritisation.
Highest enterprise-wide value (~$4.9m p.a.).
Applicable across Healthcare, MedTech, Animal Care.
Strong commercial impact (sales leakage prevention + margin uplift).

ELT framing (explicit):

“Implementing AI powered recommendation engine for recommending similar products and auto-substitute for out-of-stocks.” [Data Worki...ember 2024 | PowerPoint]

➡️ This is unambiguously the top non‑HPS AI initiative.

# 2) **Recommendation Engine for Ordering** (Healthcare / MedTech / Animal Care)

## 2A) What sources explicitly say

*   Use case: AI recommendation engine to recommend similar products and auto-substitute out-of-stocks to reduce sales leakage and increase margins; it’s listed as an enterprise use case. [\[Data Worki...nuary 2025 \| PowerPoint\]](https://ebosgroup.sharepoint.com/sites/DataPractitionersWorkingGroup9/_layouts/15/Doc.aspx?sourcedoc=%7B7D3B11EE-951B-44A9-AF04-67B62A7D4062%7D&file=Data%20Working%20Group%20Presentation%20January%202025.pptx&action=edit&mobileredirect=true&DefaultItemOpen=1), [\[Data Team...io 2025-09 \| PowerPoint\]](https://ebosgroup.sharepoint.com/sites/GroupITSharepointSite/ITEnterpriseDataandAnalytics/_layouts/15/Doc.aspx?sourcedoc=%7B3FE91ECF-9492-4C2C-8E49-AF0493565DA3%7D&file=Data%20Team%20Portfolio%202025-09.pptx&action=edit&mobileredirect=true&DefaultItemOpen=1)

## 2B) Suggested data requirements (shape/form/volume; tables)

**Recommended**

*   **Transactional**: orders, order lines, substitutions, cancellations, fulfilment outcomes.
*   **Catalog**: product master, attributes, brand, margins, therapeutic category (Healthcare), pack sizes.
*   **Inventory/availability**: stock on hand, ATP, lead times, supplier constraints.
*   **Customer**: account segment, location, ordering patterns.
*   **Interaction**: search/browse logs (if eComm), “recommended\_shown” and “accepted/declined” events.

**Suggested tables**

*   `silver_orders`, `silver_order_lines`, `silver_product_master`, `silver_inventory_snapshot`, `silver_customer`, `silver_substitution_events`
*   `gold_reco_training_set` (user-item interactions + context)
*   `gold_reco_candidates` (top-N per customer/session)
*   `gold_reco_outcomes` (acceptance, margin delta, fulfilment improvement)

## 2C) Likely modelling techniques

**Recommended**

*   Classic recommenders: collaborative filtering, matrix factorisation, item2item similarity.
*   Hybrid recommenders: content-based + collaborative, rules for compliance constraints.
*   Contextual bandits for online optimisation (if real-time channels exist).

## 2D) Is ML used?

*   **Very likely** (recommenders are typically ML-based).  
    **Recommended split**
*   Classical ML: ranking/recommendation.
*   Optional GenAI: explanation generation (“why recommended”) and customer-service assist, but keep scoring/ranking deterministic + testable.

## 2E) Databricks components (rough)

**Recommended**

*   Feature pipelines in Delta (DLT), MLflow experiments, batch scoring jobs, online serving (Model Serving), A/B test tracking tables, Unity Catalog for controlled access.

***



2️⃣ Inventory Optimisation
 [Data Worki...ember 2024 | PowerPoint]
Why it ranks #2 (explicit):

Ranked #2 in ELT prioritisation.
High value across MedTech and TWC (and potentially Healthcare).
Direct EBIT + working capital benefits.
Classic, well‑understood AI use case → lower execution risk.

ELT framing (explicit):

“Using AI to have the right product at the right place at the right time and right price.” [Data Worki...ember 2024 | PowerPoint]

➡️ Clear second‑highest priority once recommendations are done.

# 3) **Inventory Optimisation** (MedTech / TWC / enterprise theme)

## 3A) What sources explicitly say

*   Use case theme: “right product at right place/time/price” to drive sales growth and reduce write-offs; appears as an enterprise use case and in the ELT pack. [\[Data Worki...nuary 2025 \| PowerPoint\]](https://ebosgroup.sharepoint.com/sites/DataPractitionersWorkingGroup9/_layouts/15/Doc.aspx?sourcedoc=%7B7D3B11EE-951B-44A9-AF04-67B62A7D4062%7D&file=Data%20Working%20Group%20Presentation%20January%202025.pptx&action=edit&mobileredirect=true&DefaultItemOpen=1), [\[Data Team...io 2025-09 \| PowerPoint\]](https://ebosgroup.sharepoint.com/sites/GroupITSharepointSite/ITEnterpriseDataandAnalytics/_layouts/15/Doc.aspx?sourcedoc=%7B3FE91ECF-9492-4C2C-8E49-AF0493565DA3%7D&file=Data%20Team%20Portfolio%202025-09.pptx&action=edit&mobileredirect=true&DefaultItemOpen=1)
*   MedTech-specific framing includes reducing expired stock/write-offs and working capital benefits. [\[Data Worki...nuary 2025 \| PowerPoint\]](https://ebosgroup.sharepoint.com/sites/DataPractitionersWorkingGroup9/_layouts/15/Doc.aspx?sourcedoc=%7B7D3B11EE-951B-44A9-AF04-67B62A7D4062%7D&file=Data%20Working%20Group%20Presentation%20January%202025.pptx&action=edit&mobileredirect=true&DefaultItemOpen=1)

## 3B) Suggested data requirements (shape/form/volume; tables)

**Recommended**

*   Inventory snapshots (daily), inbound POs, lead times, supplier fill rates.
*   Demand signals: sales, seasonality, promos, customer segments.
*   Shelf-life/expiry (MedTech), wastage/write-off records.
*   Constraints: MOQ, pack sizes, capacity, service levels.

**Suggested tables**

*   `silver_inventory_daily`, `silver_sales_daily`, `silver_purchase_orders`, `silver_supplier_performance`, `silver_expiry_batches`
*   `gold_demand_forecast`, `gold_replenishment_recommendations`, `gold_writeoff_risk`

## 3C) Likely modelling techniques

**Recommended**

*   Time-series forecasting (classical + ML), probabilistic forecasts.
*   Optimisation layer (MILP/heuristics) for reorder quantities and allocation.
*   Classification/regression for “write-off risk” and “stockout risk.”

## 3D) Is ML used?

*   **Likely yes**, plus an optimisation component (often not “ML”).
*   GenAI typically not required except for narrative insights.

## 3E) Databricks components (rough)

**Recommended**

*   Forecast training notebooks/jobs, feature stores for demand drivers, scheduled batch scoring, Delta Live Tables for curated demand/inventory marts, dashboards (Databricks SQL/BI), MLflow registry.

***




3️⃣ AI Customer Service Agents
 [Data Worki...ember 2024 | PowerPoint]
Why it ranks #3 (explicit):

Ranked #3 in the ELT pack.
Cross‑business applicability: Healthcare, MedTech, TWC.
Strong productivity narrative (labour cost reduction, scalability).
Fits the “AI‑assisted operations” theme highlighted by ELT.

ELT framing (explicit):

“Improve customer satisfaction and reduce customer queries by automating and creating visibility of order tracking for customers.” [Data Worki...ember 2024 | PowerPoint]

➡️ Third priority, particularly attractive as GenAI maturity improves.

# 5) **AI Customer Service Agents** (Healthcare / MedTech / TWC)

## 5A) What sources explicitly say

*   Use case: automate common queries, improve satisfaction, reduce labour, provide order tracking visibility; appears across divisions. [\[Data Worki...nuary 2025 \| PowerPoint\]](https://ebosgroup.sharepoint.com/sites/DataPractitionersWorkingGroup9/_layouts/15/Doc.aspx?sourcedoc=%7B7D3B11EE-951B-44A9-AF04-67B62A7D4062%7D&file=Data%20Working%20Group%20Presentation%20January%202025.pptx&action=edit&mobileredirect=true&DefaultItemOpen=1), [\[Data Team...io 2025-09 \| PowerPoint\]](https://ebosgroup.sharepoint.com/sites/GroupITSharepointSite/ITEnterpriseDataandAnalytics/_layouts/15/Doc.aspx?sourcedoc=%7B3FE91ECF-9492-4C2C-8E49-AF0493565DA3%7D&file=Data%20Team%20Portfolio%202025-09.pptx&action=edit&mobileredirect=true&DefaultItemOpen=1)

## 5B) Suggested data requirements

*   Knowledge corpus: SOPs, policies, product info, FAQs, order tracking docs.
*   Operational: CRM cases, call/chat transcripts, disposition codes.
*   Systems integration: order status, shipment tracking, returns.

**Suggested tables**

*   `silver_cases`, `silver_case_messages`, `silver_order_status_events`
*   `gold_agent_knowledge_index` (document chunks + metadata)
*   `gold_agent_conversations` (anonymised logs + outcomes)

## 5C) Likely modelling techniques

*   Retrieval-Augmented Generation (RAG): vector search + grounding + response generation.
*   Intent classification + routing; summarisation; extraction of required fields for case creation.

## 5D) ML usage

*   **Likely GenAI/LLM** for conversation; **classical ML** for intent/routing and quality signals.

## 5E) Databricks components

*   Vector index / embedding jobs, model serving endpoints, conversation telemetry Delta tables, evaluation harness (offline scoring), Unity Catalog governance.

***



4️⃣ Document Intelligence (Finance & Ordering)
 [Data Worki...ember 2024 | PowerPoint]
Why it ranks #4 (explicit):

Ranked #4 in the ELT prioritisation.
High value in Healthcare finance & operations.
Clear automation ROI (manual labour reduction).
Enterprise‑reusable capability (P2P, O2C, invoices, orders).

ELT framing (explicit):

“Reduce manual labour processing of documents, using AI to interpret and integrate directly into target systems.” [Data Worki...ember 2024 | PowerPoint]

➡️ Slightly lower than customer service due to integration complexity, but still core.

# 4) **Document Intelligence** (P2P / O2C; finance & ordering documents)

## 4A) What sources explicitly say

*   Use case: reduce manual labour processing documents using AI to interpret and integrate into target systems; called out in ELT pack and portfolio. [\[Data Worki...nuary 2025 \| PowerPoint\]](https://ebosgroup.sharepoint.com/sites/DataPractitionersWorkingGroup9/_layouts/15/Doc.aspx?sourcedoc=%7B7D3B11EE-951B-44A9-AF04-67B62A7D4062%7D&file=Data%20Working%20Group%20Presentation%20January%202025.pptx&action=edit&mobileredirect=true&DefaultItemOpen=1), [\[Data Team...io 2025-09 \| PowerPoint\]](https://ebosgroup.sharepoint.com/sites/GroupITSharepointSite/ITEnterpriseDataandAnalytics/_layouts/15/Doc.aspx?sourcedoc=%7B3FE91ECF-9492-4C2C-8E49-AF0493565DA3%7D&file=Data%20Team%20Portfolio%202025-09.pptx&action=edit&mobileredirect=true&DefaultItemOpen=1)

## 4B) Suggested data requirements

*   Input docs: invoices, POs, order forms, remittances (PDF/images/email attachments).
*   Master/reference: suppliers, customers, GL codes, product master, contract terms.
*   Labels: historical keyed entries + exception reasons.

**Suggested tables**

*   `bronze_documents` (binary + metadata)
*   `silver_doc_pages`, `silver_doc_ocr_text`, `silver_doc_fields_extracted`
*   `gold_doc_exceptions_queue`, `gold_doc_posting_ready`

## 4C) Likely modelling techniques

*   OCR + layout extraction; field classification; entity matching to master data.
*   Confidence scoring + human-in-the-loop review (queue).

## 4D) ML usage

*   **Yes (applied AI)**; GenAI optional for messy formats, but keep deterministic extraction where possible.

## 4E) Databricks components

*   Auto Loader for ingest, Delta tables, Workflows, MLflow tracking; optional vector search for template-less extraction.

***





5️⃣ AI Powered Insights & Analytics (Ranging, Franchise, Market Intelligence)
 [Data Worki...ember 2024 | PowerPoint]
Why it ranks #5 (explicit):

Ranked #5 in ELT pack.
Covers multiple initiatives:

Healthcare ranging & consolidation
Animal Care market intelligence
TWC franchise reporting


Strong value but less tightly defined than top four.
More analytics‑heavy vs “hard automation”.

ELT framing (explicit):

“AI-driven initiatives to optimise ranging, analyse and boost store-level sales, and automate market intelligence.” [Data Worki...ember 2024 | PowerPoint]

➡️ Strategically important, but follows the more operational AI wins.

# 6) **AI Powered Insights & Analytics**

*(Healthcare Ranging & Consolidation; Animal Care market intelligence; TWC franchise reporting)*

## 6A) What sources explicitly say

*   This bucket includes initiatives to optimise ranging, boost store-level sales, and automate market intelligence; explicitly listed in ELT pack and portfolio. [\[Data Worki...nuary 2025 \| PowerPoint\]](https://ebosgroup.sharepoint.com/sites/DataPractitionersWorkingGroup9/_layouts/15/Doc.aspx?sourcedoc=%7B7D3B11EE-951B-44A9-AF04-67B62A7D4062%7D&file=Data%20Working%20Group%20Presentation%20January%202025.pptx&action=edit&mobileredirect=true&DefaultItemOpen=1), [\[Data Team...io 2025-09 \| PowerPoint\]](https://ebosgroup.sharepoint.com/sites/GroupITSharepointSite/ITEnterpriseDataandAnalytics/_layouts/15/Doc.aspx?sourcedoc=%7B3FE91ECF-9492-4C2C-8E49-AF0493565DA3%7D&file=Data%20Team%20Portfolio%202025-09.pptx&action=edit&mobileredirect=true&DefaultItemOpen=1)
*   Healthcare has a specific “Ranging and Consolidation Analytics” use case described. [\[Data Worki...nuary 2025 \| PowerPoint\]](https://ebosgroup.sharepoint.com/sites/DataPractitionersWorkingGroup9/_layouts/15/Doc.aspx?sourcedoc=%7B7D3B11EE-951B-44A9-AF04-67B62A7D4062%7D&file=Data%20Working%20Group%20Presentation%20January%202025.pptx&action=edit&mobileredirect=true&DefaultItemOpen=1)
*   Animal Care includes market research agent / competitor repository described. [\[Data Worki...nuary 2025 \| PowerPoint\]](https://ebosgroup.sharepoint.com/sites/DataPractitionersWorkingGroup9/_layouts/15/Doc.aspx?sourcedoc=%7B7D3B11EE-951B-44A9-AF04-67B62A7D4062%7D&file=Data%20Working%20Group%20Presentation%20January%202025.pptx&action=edit&mobileredirect=true&DefaultItemOpen=1)
*   TWC includes franchise reporting/store-level recommendations described. [\[Data Worki...nuary 2025 \| PowerPoint\]](https://ebosgroup.sharepoint.com/sites/DataPractitionersWorkingGroup9/_layouts/15/Doc.aspx?sourcedoc=%7B7D3B11EE-951B-44A9-AF04-67B62A7D4062%7D&file=Data%20Working%20Group%20Presentation%20January%202025.pptx&action=edit&mobileredirect=true&DefaultItemOpen=1)

## 6B) Suggested data requirements

**Ranging/consolidation (Healthcare)**

*   DC/SKU demand, fulfilment SLAs, logistics costs, stockouts, SKU attributes.

**Market intelligence (Animal Care)**

*   External web sources (competitor sites, pricing pages), internal product catalog, campaign calendars.
*   If web scraping is used: store raw HTML snapshots + extracted structured price tables.

**Franchise reporting (TWC)**

*   Store sales, promotions, local demographics proxies (if allowed), planograms, inventory, store clusters.

**Suggested tables**

*   `gold_range_recommendations`, `gold_store_clusters`, `gold_competitor_price_history`

## 6C) Likely modelling techniques

*   Unsupervised clustering (store similarity), causal uplift / promo impact models, forecasting.
*   NLP summarisation for market intelligence briefs.
*   Web extraction: parsers + change detection; optional LLM summarisation of deltas.

## 6D) ML usage

*   **Yes** for analytics/recommendations; **GenAI** useful for summarising findings and generating weekly briefs.

## 6E) Databricks components

*   Scheduled pipelines, Delta marts for store/DC analytics, notebooks for modelling, MLflow for experiments, BI layer integration.

***
