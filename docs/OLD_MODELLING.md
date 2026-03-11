# OLD_MODELLING — Pre–EBOS shortlist option space

*This document is historical: a broad landscape of possible modelling areas. The active implementation plan is the **EBOS AI/ML Technical Implementation Shortlist** (see root [EBOS_SHORTLIST.md](../EBOS_SHORTLIST.md) and [README.md](../README.md)).*

---

### Possible Modelling
## 1. **Supply Chain & Logistics Optimisation**
- **Demand Forecasting Models**
	- What: Predict future units sold per SKU at a specific pharmacy/hospital.
	- Why: Drives ordering, reduces stockouts/overstock and expiry.
	- Modelling note: start with tree models (XGBoost) and ETS/Prophet for seasonality; scale to TFT/LSTM for many SKUs; feature engineering: promotions, season, local events, PBS listing changes.
    - Time-series forecasting (Prophet, ARIMA, LSTM, Temporal Fusion Transformers).
    - Likely at SKU × pharmacy/hospital granularity.
    - Comparable: McKesson deploys advanced demand forecasting to handle flu season surges.
- **Inventory Optimisation / Stock Replenishment**
	- What: Calculate when and how much to reorder given lead times, shelf life, and storage constraints.
	- Why: Pharmaceuticals have expiries, cold-chain needs, and tight margin for waste.
	- Modelling note: combine forecast + constrained optimisation (linear/integer programming) or RL for dynamic policies; incorporate expiry-aware costs.
    - Predictive restocking models using reinforcement learning or optimisation with constraints (expiry dates, cold-chain requirements).
    - Evidence: AmerisourceBergen has reported ML-based "smart replenishment" for critical medicines.
- **Logistics / Routing Models**
	- What: Plan deliveries (vehicles, routes, time windows) under stochastic demand and travel times.
	- Why: Last-mile costs and timeliness matter for hospital/clinic deliveries and temperature-sensitive items.
	- Modelling note: vehicle routing + stochastic demand; use ML to predict ETA/traffic and hybrid metaheuristic solvers for scheduling.
    - Vehicle routing problems solved with metaheuristics + ML heuristics (e.g. demand clustering, stochastic travel times).
    - Large-scale distribution (warehouses → pharmacies → hospitals → vets) is a common use case.
## 2. **Healthcare Customer / Market Analytics**
- **Sales & Market Forecasting**
	- What: Predict overall category or SKU uptake by region/segment.
	- Why: Helps stocking decisions, promotional allocation, commercial strategy.
	- Modelling note: gradient-boosted trees for tabular predictors; include policy/therapy changes (e.g., PBS listing) as exogenous features.
    - Gradient boosted trees (XGBoost/LightGBM) predicting SKU uptake by region.
    - Used for targeting promotions or anticipating PBS / MedsCheck impact.
- **Churn & Retention Models**
	- What: Predict which pharmacies/customers might switch suppliers or reduce purchases.
	- Why: Key for account management and contract retention — large customers = concentrated revenue risk.
	- Modelling note: classification with explainability (SHAP) so commercial teams can act.
    - Predicting which pharmacies or vets may switch suppliers.
    - Seen at Zuellig Pharma — "customer loyalty prediction" ML models.
- **Recommender Systems**
	- What: Suggest products or bundles for pharmacy/retail customers.
	- Why: Improves basket size, cross-sell of consumer brands.
	- Modelling note: collaborative filtering or ranking models that combine product attributes and business rules (expiry, regulation).
    - Cross-sell/upsell engines for B2B ecommerce portals (e.g. TerryWhite Chemmart, pet products).
## 3. **Operational Efficiency**
- **Warehouse Vision Systems**
	- What: CV systems to check pick/pack accuracy, read expiry dates, detect damaged goods.
	- Why: Reduces human error, improves recalls and traceability.
	- Modelling note: small-scale CV prototypes feasible (barcode/expiry OCR + classification for damage), but production needs integration with WMS.
    - Computer vision to monitor picking/packing accuracy, expiry date scanning.
    - Similar systems deployed by DHL Healthcare and UPS Pharma Logistics.
- **Process Anomaly Detection**
	- What: Detect outliers in temperature logs, shipping times, or suspicious order patterns.
	- Why: Temperature excursions can spoil vaccines; anomalous orders can signal fraud/non-compliance.
	- Modelling note: unsupervised / semi-supervised methods + thresholding; pair with alerting/agent flows.
    - ML models monitoring distribution events (temperature, shipping delays) for anomaly alerts.
    - Especially relevant for vaccines, cold chain pharmaceuticals.
## 4. **Regulatory, Fraud & Risk**
- **Prescription Fraud Detection**
	- What: Spot suspicious orders or claims (e.g., controlled substances).
	- Why: Heavy regulatory exposure; distributors are often obliged to report suspicious activity.
	- Modelling note: rule + ML hybrid systems; maintain high precision to avoid false alarms.
    - Supervised anomaly detection on claims, orders, controlled substances.
    - Comparable: US distributors use ML to flag "suspicious opioid orders" as required by DEA.
- **Compliance / Governance Models**
	- What: OCR + NLP for invoices, purchase orders, prescriptions and call transcripts.
	- Why: Pharmacies and hospitals produce lots of semi-structured documents; automating reduces manual work and improves auditability.
	- Modelling note: use OCR → extractor pipelines; LLMs/RAG useful for summarisation and extraction but need PII controls and logging.
	    - NLP to automatically check supplier or pharmacy documentation against compliance rules.
    - Job descriptions often mention audit automation
        — so ML/NLP likely applied here.
## 5. **Natural Language / Clinical Text**
- **NLP for Call Centres / Support**
    - Call summarisation (similar to your Azure OpenAI call-wrap work
    - B2B customer support for pharmacies/hospitals is a common use case.
- **Document Processing**
    - OCR + NLP for invoices, shipping documents, prescriptions.
    - Already standard in pharma distribution (reduces manual data entry).
- **Document Intelligence / Field Extraction from PDFs**
	- What: Automated OCR and structured field extraction from PDF documents (invoices, purchase orders, prescriptions, shipping manifests) using spark-nlp and spark-ocr.
	- Why: High-volume document processing requires scalable, distributed OCR and NLP pipelines; manual data entry is error-prone and expensive; structured extraction enables downstream automation (AP, compliance checks, inventory updates).
	- Modelling note: use spark-ocr for PDF → text conversion and image preprocessing; spark-nlp for named entity recognition (NER) and field extraction (dates, amounts, SKUs, supplier info); combine with rule-based post-processing for validation; leverage Spark's distributed processing for batch document pipelines; consider fine-tuning NER models on domain-specific documents (pharma invoices, prescriptions).
    - Technical stack: spark-nlp for transformer-based NER and field extraction, spark-ocr for scalable OCR operations on PDF/image inputs.
    - Use cases: automated invoice processing, prescription digitization, shipping document parsing, purchase order extraction.
- **Medical Product Classification**
    - Mapping supplier SKUs → internal catalogues, often via multi-label classification.
## 6. **Animal Health / Pet Care**
- **Demand & Trend Modelling for Pet Food / Care Products**
    - Predicting seasonal pet product sales, optimizing marketing.
- **E-commerce Personalisation** (VitaPet, Black Hawk brands).
    - Recommender engines (collaborative filtering, deep learning ranking).
    - Analogous to Mars Petcare's ML-based pet food personalization.
## 7. **Likely Tech/ML Patterns**
Given typical job requirements and stack (Azure, Databricks
Senior Machine Learning Enginee…
- Heavy use of **Spark MLlib / MLflow** for pipeline management.
- Azure ML + Databricks for orchestration.
- Expect mix of **tree-based methods** (XGBoost/LightGBM) for tabular ops data, plus **transformers** for NLP tasks.
- Early experimentation with **agentic AI** (JD mentions this) → e.g. AI agents managing supply chain alerts end-to-end.

✅ **Bottom Line**
Most probable ML models = **demand forecasting, replenishment optimisation, fraud/compliance detection, NLP for customer/ops data, and recommenders for B2B retail**. This is highly consistent with peers in health logistics, and matches the "platform-first, greenfield MLOps" flavour in typical job descriptions.
