# Lunch & Learn — To be aligned with EBOS use cases

*Standalone session plan. Will be revisited and aligned with the EBOS AI/ML use cases (see [EBOS_SHORTLIST.md](../EBOS_SHORTLIST.md) and [README.md](../README.md)) so demos draw on implemented use cases.*

---

# "From Synthetic Data to Smart Insights: A Modern Healthcare Analytics Pipeline"

**Duration:** 45-60 minutes | **Audience:** Moderately technical stakeholders

## Session Overview
This interactive walkthrough showcases how Databricks enables end-to-end healthcare analytics while addressing real-world challenges like data sensitivity and compliance. We'll explore existing code, processes, and implementations that demonstrate the journey from generating synthetic data to delivering actionable insights through AI-powered dashboards.

## Session

### Topic 1: Data Generation & Lineage
- **Data Lineage Visualization:** Show how Unity Catalog tracks data from synthetic generation → medallion → ML models
- **Automated PII Detection:** Demo how sensitive healthcare data gets automatically classified and masked
- **Audit Trail:** Show who accessed what data when (great for healthcare compliance)

### Topic 2: Dashboarding & Access
- **Databricks Dashboards:** Interactive analytics interfaces for different user types
- **Databricks Genie Powered Dashboards:** Self-serve analytics using LLMs to answer analytical questions
- **Guardrails Implementation:** Injecting domain knowledge into stored queries/procedures for reliable insights

### Topic 3: Data Applications
- **Genie Dashboard Apps:** Wrapping analytical dashboards as presentable business applications
- **Prediction Serving Apps:** Applications that serve ML model predictions directly to end users
- **Synthetic Data Generator:** Just another data app example; repackaging data generators used for this presentation within a hosted streamlit app

## What You'll See
- **Code Walkthrough:** Examine real implementations across all three topic areas
- **Live System Exploration:** Navigate through existing Databricks environments and applications
- **Architecture Deep-Dive:** Understand how components connect from data generation to insight delivery

## Key Takeaways
- How synthetic data generation removes the "sensitive data" blocker that often prevents innovation
- How AI-assisted analytics democratizes data insights across your organization
- Practical next steps for implementing similar capabilities in your domain

## Interactive Elements
- Share dashboards/applications to users > query/test etc.
- Examine real code implementations and architecture decisions
- Explore live data lineage and governance features
