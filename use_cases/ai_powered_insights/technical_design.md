## Technical Design: AI Powered Insights (Genie Spaces + Streamlit)

### Scope
Domain-scoped Databricks Genie Spaces (Healthcare, Animal Care, TWC) and a single Streamlit router app that powers **AI Powered Insights**:
- Presents a domain selector to the user
- Routes each prompt to the selected Genie Space
- Renders Genie responses (text, optional generated SQL, and tabular results)
- Provides UX guardrails for known Genie constraints (cross-domain gap, latency, rate limiting, and statement expiration)

### Assumptions
- Domain Genie Spaces are pre-configured in Databricks with Unity Catalog table scopes and a Knowledge Store per domain.
- The Streamlit app is hosted as a Databricks App, and can authenticate via the Databricks SDK.
- Responses may include attachments with a statement/statement_id that can be used to fetch query results for tabular display.

### Architecture (logical)
- Databricks Genie Spaces:
  - `healthcare_insights`
  - `animal_care_insights`
  - `twc_franchise_insights`
- Streamlit router (Databricks App):
  - Domain selector
  - domain -> Genie Space ID mapping
  - Conversation APIs + attachment rendering
  - Optional deep-links to domain dashboards
- Databricks SQL dashboards:
  - Healthcare dashboard (reads relevant `gold_*` outputs)
  - Animal Care dashboard (reads relevant `gold_*` outputs)
  - TWC dashboard (reads relevant `gold_*` outputs)

Dashboard integration requirement:
- The Streamlit router should provide deep-links into these traditional Databricks SQL dashboards so users can switch from conversational answers to full-page visual analytics.

### Domain routing & “capabilities” UX (cross-domain gap mitigation)
The “Cross-Domain” gap means a user asking a Healthcare question while in the Animal Care domain may receive irrelevant results (or the app may fail).

Requirements:
1. Maintain an explicit `active_domain` in `st.session_state` (and persist across reruns).
2. Show a visible “Capabilities” list for the active domain before sending prompts.
3. Keep the active domain flagged in UI (e.g., a pill/badge + the capabilities list).
4. Include guardrails in the prompt:
   - The router should prepend or accompany the user prompt with a short domain context sentence
   - Example: “Active domain: Healthcare. Answer using healthcare KPI definitions and tables.”

Capabilities content (examples, to be curated):
- `healthcare_insights`:
  - Ranging & consolidation KPIs and related time windows
  - Allowed tables are limited to healthcare silver/gold inputs/outputs
- `animal_care_insights`:
  - Competitor product/price history and market intelligence trends
- `twc_franchise_insights`:
  - Store clusters, promotion impact, and store-level recommendations

### Session persistence & follow-ups (thread persistence)
Requirements:
- Use `conversation_id` (or `thread_id`) persisted in `st.session_state`.
- Maintain a mapping between Streamlit session and Genie conversation state so follow-ups don’t lose context.

Implementation notes:
- On first user prompt, start a new Genie conversation and store `conversation_id` in session_state.
- For subsequent prompts, call the “send message” / “continue conversation” API using the stored `conversation_id`.

### Latency management
Constraints:
- `start_conversation_and_wait_for_answer` is synchronous and can take 10–30 seconds.

UI requirements:
- Use `st.status()` or `st.spinner()` during:
  - conversation start
  - SQL generation phase (if you can detect/approximate it)
  - statement execution / result retrieval
- Avoid blocking UI without feedback; always show progress indicators.

### API rate limits (429 handling)
Constraints:
- Genie has a concurrency limit (often ~5–10 requests per minute depending on tier).

Requirement:
- Handle 429 responses gracefully and surface a retry/backoff message.

Implementation outline:
- Wrap Genie calls in retry logic:
  - exponential backoff with jitter
  - cap retries (e.g., 2–3)
- If still failing, show:
  - “Too many concurrent requests. Please retry in a moment.”
  - Keep user’s prompt visible so they can retry easily.

### Statement execution & result expiration
Constraints:
- `statement_execution` results may expire; links to data may not remain valid for hours.

UX/logic requirements:
- When rendering tabular results, also provide an immediate “Download CSV” that is generated from the DataFrame immediately (not via a long-lived statement link).
- If a user tries to “download later” (or after a long idle period), fall back to re-running the statement (if feasible) or show an error with a “Try again” action.

### Hybrid UI (deep-link to dashboards)
Enhancement:
- If Genie detects a high-level question, it can provide a deep link to the relevant Databricks SQL dashboard.

Implementation approach:
- Maintain a domain -> dashboard URL/name mapping.
- After Genie responds, if attachments indicate a high-level analytics intent, render a “View full dashboard” button.

### Optional: “Supervisor” auto-routing (foundational model)
Enhancement:
- Instead of a manual domain selector, use an auto-router (supervisor) that classifies the prompt into the correct domain Genie Space.

Implementation approach:
- Use a Databricks-hosted foundational model (Model Serving) for classification.
- The supervisor returns:
  - predicted domain
  - confidence score
- If confidence is below threshold:
  - fall back to manual domain selector
  - show “We detected this looks like Animal Care. Continue?” with an option to switch.

### Observability & debugging
Requirements:
- Log (via `loguru`) domain routing decisions, Genie conversation IDs, statement IDs, and API error codes.
- Include correlation IDs per Streamlit request to trace retries and failures.

### Security & governance
Requirements:
- The Genie Spaces must be configured with least-privilege Unity Catalog table scopes per domain.
- The router app should not override permissions; it should only select the Space configured with the correct scopes.

### Deployment & management with Databricks Asset Bundles (DABs)
This section describes how to deploy/manage the following “main artifacts” using DABs:
- Domain-scoped Genie Spaces (`genie_spaces` resource type)
- The traditional Databricks SQL / AI-BI dashboards (`dashboards` resource type, via exported `.lvdash.json`)

#### Genie Spaces deployment (DABs)
As of March 2026, Genie Spaces can be managed via Databricks Asset Bundles, but **only in “direct deploy” mode** (i.e. `databricks bundle deploy`).

Key considerations:
- Resource type: define Genie Spaces under `resources: genie_spaces:` in `databricks.yml`. (Supported as a resource type within the bundle framework.)
- Direct deploy only: Genie Space resources are not yet supported in Terraform mode because the matching Terraform provider resource does not exist.
- Supported operations: standard bundle lifecycle CRUD is supported (create/update/delete) as part of bundle deploy/rollback workflows.
- Permissions: map bundle-level permissions (like `CAN_VIEW` / `CAN_RUN`) directly to the Genie space resource.

Example bundle snippet (conceptual):
```yaml
resources:
  genie_spaces:
    healthcare_insights:
      title: "Healthcare Insights Space"
      description: "Genie space for ranging & consolidation analytics"
      warehouse_id: ${var.sql_warehouse_id}
      # Knowledge Store + allowed tables/KPIs would be configured here
      # (exact keys depend on the Genie space schema supported by DAB)
      permissions:
        - group_name: analytics-healthcare
          permission: CAN_RUN
```

Operational recommendation:
- Promote a “golden” Genie Space configuration from dev -> test -> prod by deploying the same bundle with environment-specific variables (table scopes, groups, and warehouse IDs).

#### Dashboards deployment (AI/BI Dashboards)
For the main dashboards, use the DAB `dashboards` resource type and store dashboard definitions as exported `.lvdash.json` files in the repo.

Key considerations:
- Dashboards are parameterized using bundle variables (e.g. `dataset_catalog`, `dataset_schema`, and/or dataset catalog pointers), so the same dashboard layout/logic can be deployed across environments without editing SQL each time.
- Deep-linking requirement: when the app is deployed to a new environment, dashboard IDs may be regenerated. The router must receive the final dashboard ID/URL via environment variables populated from the bundle deploy outputs/substitutions.
- Legacy dashboards: only dashboards compatible with the modern AI/BI DAB workflow should be used for this router deep-link pattern.

Example bundle snippet (conceptual):
```yaml
resources:
  dashboards:
    healthcare_ops_dashboard:
      display_name: "Healthcare Ranging Overview"
      file_path: ./src/dashboards/healthcare.lvdash.json
      warehouse_id: ${var.sql_warehouse_id}
      dataset_catalog: ${var.catalog}
      dataset_schema: ${var.schema}
      permissions:
        - group_name: analytics-healthcare
          permission: CAN_READ
```

Deployment-to-router wiring:
- Add an env var per domain in the Streamlit app configuration, e.g.:
  - `HEALTHCARE_DASHBOARD_ID`
  - `ANIMAL_CARE_DASHBOARD_ID`
  - `TWC_DASHBOARD_ID`
- These values should be populated by the bundle (or substitution variables) at deploy time, so deep links always target the correct environment-specific dashboard IDs.

#### Recommended repository organization for DABs
- `src/dashboards/*.lvdash.json`: exported dashboard definitions per domain.
- `bundles/`: bundle YAML files for:
  - Genie spaces (resources + permissions)
  - Streamlit app hosting (databricks app resource)
  - dashboards (AI/BI dashboards resource)


