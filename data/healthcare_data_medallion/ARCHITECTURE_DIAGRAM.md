# Healthcare Data Medallion Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           HEALTHCARE DATA MEDALLION ARCHITECTURE                │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   DATA SOURCE   │    │   BRONZE LAYER  │    │  SILVER LAYER  │    │   GOLD LAYER    │
│                 │    │                 │    │                │    │                 │
│ healthcare_data │───▶│ Raw Data       │───▶│ Business Logic │───▶│ Analytics       │
│ Asset Bundle    │    │ Ingestion      │    │ & Data Quality │    │ Ready Datasets  │
│                 │    │                │    │                │    │                 │
│ • Pharmacies    │    │ • bronze_      │    │ • silver_      │    │ • Customer      │
│ • Hospitals     │    │   pharmacies   │    │   pharmacies   │    │   Analytics     │
│ • Products      │    │ • bronze_      │    │ • silver_      │    │ • Product       │
│ • Orders        │    │   hospitals    │    │   hospitals    │    │   Analytics     │
│ • Inventory     │    │ • bronze_      │    │ • silver_      │    │ • Supply Chain  │
│ • Events        │    │   products     │    │   products     │    │   Analytics     │
│                 │    │ • bronze_      │    │ • silver_      │    │ • Financial     │
│                 │    │   orders       │    │   orders       │    │   Analytics     │
│                 │    │ • bronze_      │    │ • silver_      │    │ • ML-Ready      │
│                 │    │   inventory    │    │   inventory    │    │   Datasets      │
│                 │    │ • bronze_      │    │ • silver_      │    │                 │
│                 │    │   events       │    │   events       │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │                       │
         │                       │                       │                       │
         ▼                       ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   UNITY CATALOG │    │   DATA LINEAGE  │    │  DATA QUALITY   │    │   USE CASES     │
│                 │    │                 │    │                │    │                 │
│ workspace.      │    │ • _ingestion_   │    │ • Validation    │    │ • BI Dashboards│
│ default.        │    │   timestamp     │    │ • Business      │    │ • ML Models    │
│ healthcare_*    │    │ • _source       │    │   Rules         │    │ • Reports      │
│                 │    │ • _batch_id     │    │ • Standardization│    │ • Analytics    │
│                 │    │ • bronze_       │    │ • Deduplication │    │ • Compliance   │
│                 │    │   processed_at  │    │ • Data Cleaning │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│                              KEY FEATURES                                      │
├─────────────────────────────────────────────────────────────────────────────────┤
│ 🥉 BRONZE LAYER: Raw data ingestion with minimal transformations               │
│    • Data lineage tracking                                                      │
│    • Ingestion timestamps                                                       │
│    • Source metadata                                                             │
│                                                                                 │
│ 🥈 SILVER LAYER: Business logic and data quality                               │
│    • Data validation and quality checks                                         │
│    • Business rule application                                                  │
│    • Standardized naming conventions                                            │
│    • Data type standardization                                                  │
│                                                                                 │
│ 🥇 GOLD LAYER: Analytics-ready datasets                                        │
│    • Customer Analytics: Pharmacy/hospital performance metrics                  │
│    • Product Analytics: Product performance and demand patterns                │
│    • Supply Chain Analytics: Order fulfillment and logistics metrics           │
│    • Financial Analytics: Revenue, discounts, and profitability analysis      │
│    • ML-Ready Datasets: Feature-engineered data for machine learning           │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│                              DATA FLOW                                         │
├─────────────────────────────────────────────────────────────────────────────────┤
│ healthcare_data bundle → Unity Catalog → DBT Medallion Architecture             │
│         ↓                        ↓                    ↓                        │
│ Raw Data Generation    Raw Tables (Bronze)   Analytics Tables (Gold)           │
│         ↓                        ↓                    ↓                        │
│ workspace.default.      workspace.healthcare_   workspace.healthcare_           │
│ healthcare_*            medallion_dev.bronze.*  medallion_dev.gold.*           │
└─────────────────────────────────────────────────────────────────────────────────┘
