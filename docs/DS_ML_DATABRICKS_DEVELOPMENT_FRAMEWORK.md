# DS/ML Databricks Development Framework

## Document Scope & Purpose

This specification establishes foundational patterns for organizing Databricks infrastructure across a multi-workspace environment. The focus is on common components, their organization, and integration into the development experience.

### What This Document Covers

- **Foundational Infrastructure:** Multi-workspace architecture, compute strategies, resource management
- **Common Development Patterns:** CI/CD workflows, artifact sharing, testing approaches
- **Project Organization:** Catalog structures, cluster management, access control patterns
- **Developer Experience:** Interactive development through production deployment workflows
- **Cost & Operations:** Resource tagging, monitoring, alerting strategies

### What This Document Does NOT Cover

- **Advanced Databricks Services:** Foundation Model APIs, LLM serving, document comprehension, or other specialized services
- **Project-Specific Requirements:** Each project may require additional services and configurations beyond this baseline
- **Platform-Level Decisions:** Managed by platform, cloud, and security teams:
  - Network & Security Infrastructure: VNet integration, private endpoints, firewall rules
  - Enterprise Security: Advanced security configurations beyond basic access control
  - Compliance Frameworks: Detailed PHI handling, data residency controls
  - Backup & Disaster Recovery: Workspace recovery strategies
  - Migration Planning: Transition from current single workspace setup
  - Enterprise Integration: Advanced Entra ID group hierarchies and naming standards
  - Emerging Capabilities: New Databricks features released after this specification

### Future Evolution

Projects may require additional Databricks services (e.g., Foundation Model serving, Document Intelligence, Vector Search) that will be evaluated and integrated as needed, following the organizational patterns and governance frameworks established in this specification.

> **Document Status:** Living specification - will evolve as organizational requirements and platform capabilities mature.

### Team Context

- **Size:** 3-person team (1x Data Engineer, 1x MLE, 1x Data Scientist)
- **Focus:** Minimal setup that scales with additional team members/projects
- **Current State:** Moving from single prod workspace to proper multi-workspace architecture

---

## Quick Reference

**Core Patterns:**
- **Repository → Catalog Mapping:** `{company}-{project}` (repo) → `{company}_{project}_{env}` (catalog)
- **Environment Isolation:** Shared metastore, environment-specific catalogs
- **Naming Conventions:** Kebab-case (Azure resources), snake_case (Unity Catalog objects)
- **Model Strategy:** Code deployment + retrain (preferred) > artifact promotion

**Key Resources per Project:**
- 1 Azure DevOps repository
- 3 environment catalogs (dev/test/prod in shared metastore)
- Interactive clusters (dev workspace, as needed)
- Job clusters + workflows (all environments, as needed)
- Model serving endpoints (as needed)

**Access Control:**
- Persona groups (cross-project) + Project groups (catalog-level isolation)
- Service principals for production workloads
- Manual approval gates for test/prod deployments

---

## Workspace Architecture

### Environment Strategy

| Environment | Purpose | Characteristics | Access Pattern |
|-------------|---------|-----------------|----------------|
| **dev** | Interactive development, prototyping | Bursty usage, user-owned experiments + SP-executed jobs | Full team access + SP workloads |
| **test** | Pre-production validation | SP-executed workloads, deployment testing | Review/approval gates, SP-only |
| **prod** | Production deployment | Hands-off operation, production data | SP-only, manual approval |

### Infrastructure Components

- **Separate Workspaces:** Full isolation between dev, test, prod
- **Service Principals:** Runtime agents for executing deployed workloads and orchestrating CRUD operations
  - All DAB-deployed jobs execute as SPs (not individual users)
  - Production artifacts owned by SPs for stability across team changes
- **Azure DevOps:** Repository management and CI/CD pipelines
- **Key Vaults:** Environment-scoped secret storage (one per workspace)
  - Integration: Environment variables via DAB bundle variables (e.g., `${var.spark_nlp_license}`)
- **Entra ID Groups:** Two-layer group architecture for access control
  - Persona-based groups (cross-project access)
  - Project-specific groups (catalog-level isolation)
- **Docker Registries:** Environment-specific container registries for custom images
  - Required for projects needing custom runtime environments
  - Examples: JSL library optimization, web scraping with bundled drivers

### Unity Catalog Architecture

- **Shared Metastore:** Single Unity Catalog metastore across all workspaces (dev, test, prod)
- **Governance Boundary:** Catalogs provide environment isolation, not workspaces
- **Catalog Naming:** Environment-specific catalog names: `{project}_{env}` (e.g., `hps_clinical_notes_dev`, `hps_clinical_notes_test`, `hps_clinical_notes_prod`)
  - **Note:** Snake_case preferred for catalogs to maintain consistency with schemas/tables and avoid SQL escaping friction
- **Service Principal Context:** All production workloads execute as service principals (see Artifact Sharing Strategy for details)
  - MLflow artifacts in `/Workspace/<SP-UID>/mlflow-experiments/`
  - User-agnostic ownership ensures stability
  - Per-environment SPs (dev/test/prod)
- **DAB-Managed UC Objects:** (Subject to testing/viability)
  - Modern Databricks Asset Bundles (DABs) now support declarative creation of catalogs, schemas, and volumes
  - Enables "single deploy" experience without separate Terraform runs for UC infrastructure
  - Volume support added in Databricks CLI 0.236.0
  - Artifacts (e.g., Python wheels) can be automatically uploaded to UC volumes during bundle deployment
  - **Status:** Evolving capability - validate against current CLI version and organizational policies before adoption

### Databricks Resource Standards

- **Catalog Pattern:** 1:1 mapping (repo → catalog per environment)
  - Example: `hps-clinical-notes` (repo) → `hps_clinical_notes_dev`, `hps_clinical_notes_test`, `hps_clinical_notes_prod` (catalogs)
  - Each environment has its own catalog with identical schema structure
- **Project Standard:** Each project requires:
  - Dedicated repository in Azure DevOps
  - Environment-specific catalog in each workspace (dev, test, prod)
  - Additional Databricks resources as needed:
    - Interactive clusters (for dev workspace)
    - Job clusters (ephemeral or all-purpose)
    - Workflows and jobs (for orchestration)
    - Model serving endpoints (for inference)
- **Library Management:** Mixed storage approach
  - **Workspace Libraries:** Python wheels (`.whl`) stored in `/Workspace/` paths
  - **Volume Libraries:** JAR files (`.jar`) stored in Unity Catalog volumes
  - **PyPI Packages:** Version-pinned dependencies in DAB configurations

---

## Unity Catalog Organization

### Core Pattern: Repository to Catalog Mapping

**Pattern:** `repo_name` → `catalog_{env}`

**Project Name Composition:** `{company}-{project}` (kebab-case) → `{company}_{project}_{env}` (snake_case for UC catalogs)

**Example:** Repository `hps-clinical-notes` → Catalogs: `hps_clinical_notes_dev`, `hps_clinical_notes_test`, `hps_clinical_notes_prod`

**Rationale:** With a shared Unity Catalog metastore across all workspaces, catalogs are the governance boundary. Environment-specific catalog names provide strong isolation, prevent accidental cross-environment writes, and enable clean privilege boundaries per environment.

**Naming Convention Note:** While Databricks technically supports kebab-case for catalog names (e.g., `hps-clinical-notes-dev`), snake_case is strongly recommended for all Unity Catalog objects. Using hyphens in SQL identifiers requires constant backtick escaping in queries (`` SELECT * FROM `hps-prod`.data.table ``), which creates unnecessary friction for data scientists and analysts. Snake_case provides SQL compatibility without escaping requirements.

---

### Baseline Catalog Structure

> **Note:** Traditionally managed via Terraform, Unity Catalog objects can now be declared directly in Databricks Asset Bundles (databricks.yml) for unified deployment. Volume support requires Databricks CLI ≥0.236.0.

Every project catalog receives this baseline structure across all environments:

```
{project_catalog}/                          # Catalog (snake_case for UC)
├── data/                                   # Schema: Project data tables
│   ├── exploration/                       # Volume: Exploratory datasets (dev only)
│   │   # Ad-hoc analysis, prototyping, experimental data prep
│   └── reference/                         # Volume: Lookup tables, mappings, static reference files
│       # medicine_mapping_table.xlsx, ground_truth_labels/, feature_schemas/
│
├── models/                                 # Schema: ML models & experiments (UC model registry)
│   ├── <UC Registered Models>            # Models registered in metastore (moisture_predictor, etc.)
│   ├── artifacts/                         # Volume: Model binaries, checkpoints, custom files
│   │   # preprocessing/, fonts/, jsl_cv_models/, signature_siamese/
│   └── libraries/                         # Volume: Project libraries (optional)
│       # custom_preprocessing.whl, internal_utils.jar, chrome_drivers/
│
├── monitoring/                             # Schema: Observability & drift
│   # extraction_quality/, pipeline_runs/, predictions/, drift_metrics/
│   # System tables accessed separately: system.access.audit, system.billing.usage
│
└── archive/                                # Schema: Historical artifacts
    ├── models/                            # Volume: Deprecated model versions
    └── datasets/                          # Volume: Historical data snapshots
```

### The `default` Schema

Every Unity Catalog automatically creates a `default` schema. **Recommendation:** Use it for ephemeral/scratch work only.

**Suggested Usage:**
- Temporary tables during interactive development
- Quick data exploration and prototyping
- One-off analyses that don't require persistence
- Scratch outputs that will be deleted after sessions

**Not Recommended:**
- Production tables or workflows
- Shared assets across team members
- Any data requiring governance or lineage tracking

---

### Schema & Volume Design Patterns

#### Design Rationale

| Decision | Rationale |
|----------|-----------|
| **Single `models/` schema** | Consolidates UC model registry and MLflow experiments in one place. Simpler than separate `models/` and `experiments/` schemas for small teams. Prefer UC-registered models over volume storage. |
| **Single `data/` schema** | Start simple - projects add medallion layers (bronze/silver/gold) as schemas only when needed. Houses both transactional data and reference data. |
| **`reference/` under `data/`** | Reference data (lookup tables, mappings) is business data, not operational config. Logically belongs with other data assets. |
| **No `config/` baseline** | Most configuration lives in source code (repo) or secrets (Key Vault). Projects add volumes under `models/` for libraries/dependencies as needed. |
| **`archive/` as dedicated schema** | Enables moving entire tables/volumes between active and archived state. Separates retention policies and access controls for historical data. |
| **Volumes nested under schemas** | Follows Unity Catalog hierarchy: `catalog → schema → volume`. Volumes provide file-system access; schemas organize logical data domains. |

#### Monitoring: System Tables vs Custom Metrics

**Use Databricks System Tables For** (Platform-Level Observability):
- **Audit Logs:** `system.access.audit` - User actions, permission changes, data access
- **Billing:** `system.billing.usage` - Cost tracking, resource consumption
- **Compute:** `system.compute.clusters` - Cluster utilization, autoscaling events
- **Query Performance:** `system.query.history` - SQL query execution times, bottlenecks

**Use `monitoring/` Schema For** (Project-Specific Custom Metrics):
- **Model Performance:** Prediction accuracy, drift detection, A/B test results
- **Business KPIs:** SLA compliance, throughput rates, error rates by endpoint
- **Pipeline Metrics:** Stage execution times, data quality checks, row counts
- **Endpoint Logs:** Request/response latency, payload sizes, custom business logic

**Pattern:** Reference system tables in SQL dashboards, store project-specific metrics as tables in `{catalog}_{env}.monitoring/`

#### Volumes vs Tables Best Practices

**Use Volumes For:**
- **Unstructured Data:** PDFs, images, audio files, video, binaries
- **Model Artifacts:** Checkpoints, ONNX exports, custom model formats, serialized objects
- **Configuration Files:** Non-tabular configs, JSON/YAML that need file-system access
- **Libraries & Drivers:** .whl, .jar, custom binaries requiring file-level access
- **Raw Documents:** Medical documents, scanned images (as in HPS project)

**Use Tables For:**
- **Structured/Semi-Structured Data:** CSV, JSON, Parquet, Delta Lake formats
- **Queryable Data:** Anything requiring SQL interface or Spark DataFrame operations
- **Governed Data:** Data needing lineage tracking, access audits, ACID guarantees
- **Feature Engineering:** Transformed datasets, feature tables, training/validation sets
- **Business Logic:** Lookup tables, mappings, reference data requiring joins
- **Pipeline Outputs:** Structured results from ML/data processing workflows

**Rule of Thumb:** If you need to query it with SQL or track lineage, use a table. If you need file-level access or it's binary/unstructured, use a volume.

---

## External Collaborator Access

### Access Pattern

**Use Case:** Granting external collaborators (e.g., TCS internal teams, vendor specialists, partner organizations) access to specific project artifacts or datasets without full catalog access.

**Governance Boundary (Least Privilege Principle):** Choose the minimal access level required:

**Option 1: Volume-Level Access** (Most Restrictive)
- **Pattern:** Create dedicated volumes under `models/` schema for external collaboration, grant READ_VOLUME permissions via UC
- **Use Case:** Sharing specific files, libraries, or artifacts (e.g., .whl files, model checkpoints)
- **Example:** HPS JSL External Volume (below)

**Option 2: Schema-Level Access** (Broader Access)
- **Pattern:** Grant READ permissions to specific schemas for external collaborators
- **Use Case:** Sharing entire data domains (e.g., all monitoring tables, all reference data)
- **Example:** Grant `USE SCHEMA` and `SELECT` on `{catalog}.monitoring` for external analytics teams

**Option 3: Delta Sharing** (Cross-Organization Sharing)
- **Pattern:** Use Delta Sharing for secure, governed data sharing across organizational boundaries
- **Use Case:** Sharing datasets with external organizations without granting direct workspace access
- **Benefits:** No Unity Catalog credentials needed for recipients, protocol-level access control, audit logging
- **Reference:** [Delta Sharing documentation](https://docs.databricks.com/en/delta-sharing/index.html)

**Example** (HPS JSL External Volume):

```
hps_clinical_notes_jsl_prod/
├── models/
│   ├── artifacts/                         # Internal only - no external access
│   ├── libraries/                         # Project team - READ/WRITE
│   └── jsl_external/                      # ✨ External collaborator volume
│       ├── spark_nlp_jsl-6.3.0-py3-none-any.whl
│       ├── spark-nlp-assembly-6.3.1.jar
│       ├── spark-ocr-assembly-6.3.0.jar
│       └── spark-nlp-jsl-6.3.0.jar
```

**Access Control Strategy:**
- Grant external collaborators READ_VOLUME privileges on `jsl_external/` volume only
- Project team receives ALL_PRIVILEGES on all volumes under `models/` schema
- No external grants on `artifacts/` or `libraries/` volumes (implicit deny)

**Key Principle:** Apply least privilege - use volumes for file-level access, schemas for domain-level access, Delta Sharing for cross-organizational data sharing. Use schemas for logical organization, volumes/schemas for access control based on sharing requirements.

---

## Data Management Patterns

### Environment-Specific Variations

Some volumes are excluded per environment to reduce clutter:

| Volume | Dev | Test | Prod |
|--------|-----|------|------|
| `data/exploration/` | ✅ | ✅ | ❌ |
| `models/artifacts/` | ✅ | ✅ | ✅ |
| `archive/*` | ⚠️ Light | ⚠️ Medium | ✅ Heavy |

---

### Per-Project Extensions

Projects extend the baseline with domain-specific schemas and volumes:

**Data Engineering Projects:**
- Add medallion schemas: `bronze/`, `silver/`, `gold/` for multi-stage data pipelines
- Add domain schemas as needed: `raw_documents/`, `unstructured_data/`

**ML Projects:**
- Add `features/` schema for feature store tables
- Add volumes under `models/` for model-specific files (e.g., `libraries/`, project-specific volumes)

**Data Collection Projects:**
- Add volumes under `models/libraries/` for drivers, scrapers, custom binaries
- Minimal UC model usage

---

### Data Access & Primary Sources

- **Primary Source:** Enterprise data infrastructure (via central data engineering team integration)
- **Data Access:** Cross-workspace references (not replication; drawn from upstream data platform)
- **Data Versioning:** Handled by upstream data platform medallion architecture for traditional "data mart" style data
- **Unstructured Data:** ML projects store documents in catalog volumes
- **Lineage:** Handled by upstream data platform integration
- **Access Control:** Project-specific Entra ID groups required for catalog access
- **Compliance:** No specific PHI handling or data residency requirements identified

---

## Resource Management

### Compute Strategy

**Shared Clusters:**

- Project-specific labeled clusters (e.g., `hps-clinical-notes-jsl`)
- **Runtime:** 16.4 LTS (Spark 3.5.2) or latest stable LTS
- **Mode:** Shared Compute for development, Single Node for specialized workloads
- **Instance Types:** Start small and scale based on workload requirements
  - Recommended starting point: Standard D4s/D8s v3 series
  - Scale up based on actual compute/memory needs observed during development
- **Scaling:** Instance types and count vary per project based on:
  - Compute requirements
  - Developer collaboration needs
  - Library compatibility constraints

**Job Clusters:**

- Used within deployed workflows, project-specific labeled/tagged
- **Configuration:** Defined per job requirements (single node vs multi-node based on workload)
- **Naming:** Inherit from workflow naming conventions (project-specific)
- **Preference:** Job-based compute for deployed workflows where possible

**GPU Strategy:**

- **Philosophy:** Minimum GPU usage, avoided where possible
- **Types:** Start with lower tiers (T4/A100), H100 usage exceptional
- **Availability:** Required across all workspaces for MLE work
- **Workload Patterns:** Primarily CPU-heavy processing for model development

### Cost Controls

- **Resource Tagging:** Standardized project-specific tags for cost allocation
  - `stage`: Environment identifier (Dev, Test, Production)
  - `business_unit`: HPS
  - `division`: Healthcare
  - `workspace`: Project name
  - `environment`: Environment type
  - `workload`: MLAI
- **Auto-scaling:** Scale-to-zero policies on endpoints
- **Timeouts:** 60-minute cluster auto-termination
- **Deployment Strategy:** Job-based compute for deployed workflows where possible

### Naming Conventions

| Resource Type | Scope | Pattern | Example | Notes |
|--------------|-------|---------|---------|-------|
| **AZURE RESOURCES** (kebab-case) |||||
| Repository | Project | `{company}-{project}` | `hps-clinical-notes` | Base for all resources |
| Storage Account | Env | `st{project}{env}{instance}` | `sthpsclindev01` | Alphanumeric only, max 24 chars, 2-digit suffix |
| Key Vault | Env | `kv-{project}-{env}-{instance}` | `kv-hps-clin-dev-01` | 2-digit suffix |
| Container Registry | Env | `cr{project}{env}{instance}` | `crhpsclindev01` | 2-digit suffix |
| Subnet | Purpose | `snet-{purpose}-{instance}` | `snet-databricks-01` | 2-digit suffix |
| Interactive Cluster | Project | `{project}-interactive-{instance}` | `hps-clinical-notes-interactive-01` | Always include "interactive" |
| All-Purpose Cluster | Project | `{project}-{purpose}-cluster-{instance}` | `hps-clinical-notes-batch-cluster-01` | Distinguish from ephemeral |
| Job Cluster | Ephemeral | Inline in workflow definition | N/A | Managed by DABs |
| Model Endpoint | Purpose | `{project}-{model_purpose}-{instance}` | `hps-clinical-notes-vlm-01` | Semantic purpose |
| Workflow | Purpose | `{project}-{purpose}` | `hps-clinical-notes-batch-processing` | Descriptive purpose |
| **UNITY CATALOG** (snake_case) |||||
| Catalog | Env | `{company}_{project}_{env}` | `hps_clinical_notes_dev` | Avoid SQL escaping, env suffix |
| External Catalog | Purpose+Env | `{company}_{project}_{purpose}_{env}` | `hps_clinical_notes_pending_dev` | Purpose before environment |
| Schema | Logical | `{functional_area}` | `data`, `models`, `monitoring` | SQL compatible |
| Volume | Artifact | `{artifact_type}` | `libraries`, `artifacts` | SQL compatible |
| Table | Purpose | `{table_purpose}` | `extraction_quality` | SQL compatible |
| Registered Model | Semantic | `{model_purpose}` | `moisture_predictor` | No algorithm suffix |

**Consistency Rules:**

- **Azure Resources:** Use lowercase kebab-case with mandatory 2-digit instance suffix (e.g., `-01`, `-02`) to prevent naming collisions and align with [Microsoft Cloud Adoption Framework best practices](https://learn.microsoft.com/en-us/azure/cloud-adoption-framework/ready/azure-best-practices/resource-naming)
- **Unity Catalog Objects:** Use snake_case for all UC objects (catalogs, schemas, tables, volumes, models) to avoid SQL escaping issues. While Databricks technically supports kebab-case for catalogs, using hyphens in SQL identifiers requires constant backtick escaping (`` SELECT * FROM `hps-prod`.schema.table ``), which adds significant development friction
- **Storage Accounts:** Alphanumeric only, lowercase, max 24 characters (Azure constraint)

**Shared Metastore Architecture:** All workspaces (dev, test, prod) are attached to a single Unity Catalog metastore. Catalogs are the governance boundary, requiring environment-specific catalog names (`{project}_dev`, `{project}_test`, `{project}_prod`) to ensure strong isolation and prevent accidental cross-environment data access.

**External Storage Catalogs:** External catalogs follow a modified pattern with purpose before environment: `{project}_{purpose}_{env}` (e.g., `hps_clinical_notes_pending_dev`).

**Model Naming Convention:** Use simple semantic names for UC-registered models (e.g., `moisture_predictor`, `signature_classifier`). Rely on version aliases (champion/challenger/latest) for model lifecycle management rather than encoding algorithm details in the name. This provides cleaner versioning and easier model swap-outs without name changes.

---

## Access Control & Permissions

> **Note:** This section is subject to platform team specifications. Final implementation may vary based on enterprise identity management standards.

### Group Architecture

Two-layer Entra ID group structure:

#### Persona-Based Groups (Cross-Project Access)

- **MLE/Data Scientists:** Full CRUD permissions across environments
  - **Dev:** Full access (volumes, catalogs, schemas, compute)
  - **Test:** Same as dev environment
  - **Prod:** Restricted access via service principals only

#### Project-Specific Groups (Resource Isolation)

- **Purpose:** Catalog-level access control for data governance
- **Integration:** Works alongside persona-based groups
- **Required:** For accessing project-specific catalogs (e.g., `hps-clinical-notes-jsl`)
- **Pattern:** Complete catalog isolation between projects

### Entra ID Integration

- **Onboarding:** Automatic provisioning via Entra ID group membership
- **Inheritance:** Project groups complement persona groups for fine-grained access
- **Group Naming Convention:** `{project-name}-{function}` pattern (suggested)
  - Example: `hps-clinical-notes-jsl-contributors`, `hps-clinical-notes-jsl-readers`
- **Platform Responsibility:** Final naming conventions and group hierarchies determined by platform team

---

## Development Patterns & Deployment

### Development Workflow

- **Interactive Development:** Git folders in user-specific directories
- **Initial Development:** Databricks notebooks
- **Feature Testing:** Interactive development environment used for:
  - Feature branch deployment testing
  - DevOps pattern validation
  - Feasibility assessment
- **Productionization:** Databricks Asset Bundles (DABs) as "on-ramp"
  - Alternative: Databricks SDK for custom deployment, scheduling, resource requirements

### CI/CD Pipeline

- **Repository Strategy:** GitFlow with protected branches
  - **Branch → Workspace Mapping:**
    - `dev` branch → dev workspace deployment
    - `test` branch → test workspace deployment
    - `main` branch → prod workspace deployment
  - **Feature Branch Convention:**
    - Start feature branches from `dev` branch
    - Use pattern: `<initials>/<feature-name>` (e.g., `sh/add-model-monitoring`, `jd/fix-pipeline-error`)
    - Merge back to `dev` via PR for deployment testing
  - **Branch Protection:**
    - All three branches (`dev`, `test`, `main`) are protected and require PR approval
    - Direct commits to protected branches are blocked
  - **Deployment Triggers:**
    - `dev` branch: PR merge triggers automatic deployment to dev workspace
    - `test` branch: PR merge triggers deployment to test workspace (manual approval gate)
    - `main` branch: PR merge triggers deployment to prod workspace (manual approval gate)
  - **Hotfix Strategy:** Standard GitFlow hotfix branching from `main`, merged back to `main`, `test`, and `dev`
- **Deployment Tools:** Databricks SDK scripts + DAB commands
  - **Custom Deployment:** Databricks SDK option for custom deployment, scheduling, resource requirements
- **Triggers:** PR merge + manual pipeline triggers
- **Approval Gates:** Manual approval for both dev and prod deployments
- **Rollback Strategy:** Deploy main DevOps pipeline from specific branch/commit
- **Deployment Approach:** Direct updates with manual approval gates (blue/green for future consideration)

### Testing Strategy

- **Unit Testing:** Python-based testing with pytest framework
- **Integration Testing:** DAB deployment validation in dev environment
- **Environment Validation:** Automated deployment testing before production promotion
- **Code Quality:** Standard Python linting and formatting tools

---

## Artifact Sharing Strategy & Model Registry

### Model Registry Strategy

**Philosophy:** Prefer retraining models in each environment over artifact promotion. This "Code Deployment First" approach ensures production models are optimized for production data while maintaining clean, automated lineage.

#### Asset Organization: Workspace vs Unity Catalog

**Strict Separation for Governance:**

**MLflow Experiments (Workspace Paths)**:
- **Location:** `/Users/<email>/experiments/` or `/Shared/projects/<project>/experiments/`
- **Purpose:** Track messy development iterations, hyperparameter tuning, exploratory training
- **Governance:** No UC governance required - ephemeral development artifacts
- **Lifecycle:** Can be deleted, archived, or retained per project needs

**Unity Catalog Models (Catalog Namespace)**:
- **Location:** `{catalog}_{env}.models.{model_name}`
- **Purpose:** Only register "candidate" or "production-ready" models
- **Governance:** Full UC access control, lineage tracking, auditing
- **Registration:** Service principal logs to UC-integrated experiment, registers model to UC catalog

**Unity Catalog Volumes (Managed Storage)**:
- **Location:** `{catalog}_{env}.models.artifacts/`
- **Purpose:** Custom binaries, large non-tabular assets not in MLflow format
- **Benefits:** UC built-in access control and lineage for non-standard artifacts
- **Examples:** Custom preprocessing pipelines, ONNX exports, proprietary model formats

#### Deployment Patterns: Tiered Preference

**1. Code Deployment + Environment-Specific Training** (Recommended)

**Implementation:**
- Deploy training code via Databricks Asset Bundles (DABs)
- Service principal executes training job in each environment
- Model logged to UC-integrated experiment
- Model registered to UC namespace: `{catalog}_{env}.models.{model_name}`
- UC manages physical artifact storage (abstracted from user)

**Benefits:**
- Production models trained on production data distributions
- Eliminates "environment skew" (dev model failing on prod data)
- Full reproducibility with automated lineage
- Service principal ownership ensures stability (no individual dependency)

**Service Principal Behavior:**
- **Execution:** DAB-orchestrated jobs run as service principal, not individual users
- **Artifact Location:** MLflow artifacts saved to `/Workspace/<SP-UID>/mlflow-experiments/`
- **User-Agnostic:** Experiments persist independent of individual team member access/departure
- **Ownership:** Models registered in UC are owned by service principal, ensuring stable production lineage
- **Benefits:** No broken links if data scientists leave; clear separation between development (user-owned) and production (SP-owned) artifacts

**Use Cases:** All standard ML workflows, regulatory compliance scenarios, cost-sensitive environments

**2. Unity Catalog Model Promotion** (Alternative Option)

**Implementation:**
- Train once in dev environment
- Promote via MLflow API from dev catalog to test/prod catalogs
- Copy registered model version between UC catalogs

**Use Cases:**
- Extremely expensive training (multi-day GPU jobs, LLMs)
- Pre-trained/foundation models
- Cost-prohibitive retraining scenarios

**Trade-offs:**
- Model not optimized for prod data distribution
- Potential drift risks over time
- No guarantee of reproducibility in prod environment

**3. Manual Artifact Transfer** (Specific Use Cases)

**Purpose:** Transfer non-MLflow compatible artifacts that require file-level access

**Valid Use Cases:**
- **Proprietary Libraries:** JSL .whl/.jar files not in PyPI/Maven
- **Custom Model Formats:** Framework-specific binaries not supported by MLflow
- **Preprocessing Artifacts:** Fitted scalers, encoders, tokenizers as standalone files
- **External Dependencies:** Compiled binaries, custom drivers, specialized configs

**Implementation:**
- Use UC-managed volumes for governed file storage
- Script-based transfer with version tracking
- Store in `{catalog}_{env}.models.libraries/` or `{catalog}_{env}.models.artifacts/`

**Governance:**
- Volume-level access control via UC
- Manual version tracking in deployment configs
- Audit trail through transfer scripts

**Not Recommended For:**
- MLflow-compatible models (use options 1 or 2)
- Tabular data (use Delta tables)
- Emergency hotfixes without review

#### Model Lifecycle Management

**Aliases (Recommended):**
- `champion`: Current production model serving traffic
- `challenger`: A/B testing candidate for gradual rollout
- `latest`: Most recent development model

**Benefits over Stages:** More flexible for Blue/Green deployments, canary releases, multi-variant testing

#### Strategic Comparison

| Feature | Code Deployment (Retrain) | Artifact Promotion (Copy) | Best Practice Alignment |
|---------|---------------------------|---------------------------|------------------------|
| **Model Movement** | Deploy code, retrain in each env | Copy trained artifacts | ✅ High: Reduces environment skew |
| **Identity** | Service Principal | Individual DS user | ✅ High: Production stability |
| **Optimization** | Trained on env-specific data | Trained once on dev data | ✅ High: Production data fit |
| **Lifecycle** | Model Aliases (@champion) | Model Stages (Staging/Prod) | ✅ High: Flexible deployment |
| **Cost** | Retraining cost per environment | One-time training cost | ⚠️ Trade-off based on scenario |
| **Alternative Approach** | UC model promotion available | Manual file transfer | ✅ High: Multiple deployment options |

#### Integration with DABs

**Pattern:** Package training code, configuration, and workflow definitions in Databricks Asset Bundles

**Multi-Environment Deployment:**
- **Same Bundle, All Environments:** Identical DAB deployed to dev, test, and prod workspaces
- **Environment-Specific Execution:** Training job runs independently in each environment
- **Retrain on Local Data:** Each environment trains on its own data (dev data in dev, prod data in prod)
- **Model Registration:** Each environment registers model to its own catalog: `{project}_{env}.models.{model_name}`
- **CI/CD Flow:** Code promotion triggers retraining in target environment (dev branch → test retrain, main → prod retrain)

**Benefits:**
- Same training logic deployed across all environments
- Only difference between dev/test/prod models is the data consumed
- Version-controlled, automated deployment via CI/CD
- Service principal authentication built into bundle

**Service Principal Orchestration:** See Unity Catalog Architecture section for service principal behavior details. DAB-deployed jobs execute as SPs, storing artifacts in `/Workspace/<SP-UID>/mlflow-experiments/` for user-agnostic ownership.

---

## Implementation Considerations

### Multi-Project Architecture

- **Resource Sharing:** Minimal - prefer project isolation
- **Catalog Strategy:** Complete isolation per project with dedicated catalogs
- **Cross-Project Dependencies:**
  - Shared foundation models via Unity Catalog
  - Common utility libraries via package management
  - Reference data sets (lookup tables, mappings)
- **Cost Allocation:** Project-level tracking via standardized resource tagging

---

## Monitoring & Operations

### Alerting Strategy

- **Job Failures:** Databricks Workflow built-in alerting for failures and retries
  - Email notifications for job failures (configurable per workflow)
  - Automatic retry policies for transient failures
- **Cost Management:** Generic Databricks cost dashboards
  - Workspace-level resource usage monitoring
  - Environment-specific cost tracking via resource tags
  - Cross-workspace cost comparison and trending

### Performance Monitoring

- **Cluster Utilization:** Built-in Databricks cluster metrics
- **Job Performance:** Workflow execution time and resource consumption tracking
- **Cost Optimization:** Regular review of resource usage patterns for right-sizing

---

## Open Questions & Future Decisions

### Unity Catalog Management

**Archive Schema Retention Policy:**
Currently included in all environments, but may be superseded by formal corporate archival policies. Review with platform/compliance teams to determine retention strategy and lifecycle policies.

**Default Schema Governance:**
Cannot prevent UC from creating `default` schema. Options include Terraform deprecation comments, restrictive grants, or periodic cleanup jobs. To be determined based on team preferences and platform policy.

### Identity & Access

**Managed Identity vs Service Principal:**
MIs offer tighter Azure integration and external secret-free authentication. SPs provide cross-cloud portability and explicit credential rotation. To be determined based on Azure governance policies and multi-cloud strategy.

### Platform Integration

**DAB-Managed UC Objects:**
Subject to testing/viability with Databricks CLI ≥0.236.0. Need to validate declarative catalog/schema/volume creation in production workflows before full adoption.

---

## Appendix A: Project Implementation Examples

> **Purpose:** These examples demonstrate how projects augment the baseline Unity Catalog structure (data/models/monitoring/archive schemas) with domain-specific extensions. They illustrate real-world patterns for extending the framework while maintaining organizational consistency.

### A1: HPS Clinical Notes (Heavy ML/Complex Dependencies)

**Baseline Extensions:**
- Volumes: Custom JSL model artifacts, specialized processing pipelines
- External Storage Catalogs: Azure Blob Storage integration for document ingestion pipeline

**Catalog Structure (Dev Workspace):**

```
hps_clinical_notes_dev/                    # Dev catalog (shared metastore)
├── data/                                  # Baseline schema
│   ├── exploration/                       # Baseline volume (dev only)
│   ├── reference/                         # Baseline volume
│   │   ├── medicine_mapping_table.xlsx    # Medicine name standardization
│   │   └── ground_truth_labels/           # Pharmacist-reviewed evaluation datasets
│   └── processed_extractions/             # PROJECT: Structured medical data tables (pipeline outputs)
│
├── models/                                # Baseline schema
│   ├── artifacts/                         # Baseline volume
│   │   ├── fonts/                         # PROJECT: DejaVuSans.ttf for image rendering
│   │   ├── jsl_cv_models/                 # PROJECT: JSL computer vision detectors
│   │   │   ├── image_signature_detector_jsl_V1_en_6.1.0_3.0_1757371080567/
│   │   │   └── image_preescriber_crossout_detector_jsl_V1_en_6.0.1_3.0_1757371080567/
│   │   └── signature_siamese/             # PROJECT: PyTorch Siamese network for signature matching
│   │       └── triplet_resnet18_model.pth
│   ├── libraries/                         # PROJECT: Internal team libraries (Python/Java)
│   │   ├── custom_preprocessing.whl
│   │   └── internal_utils.jar
│   └── jsl_external/                      # PROJECT: External collaborator volume (TCS access)
│       ├── spark_nlp_jsl-6.3.0-py3-none-any.whl
│       ├── spark-nlp-assembly-6.3.1.jar
│       ├── spark-ocr-assembly-6.3.0.jar
│       └── spark-nlp-jsl-6.3.0.jar
│
├── monitoring/                            # Baseline schema
│   ├── extraction_quality/                # PROJECT: Tables for OCR/LLM quality metrics, success rates
│   └── pipeline_runs/                     # PROJECT: Tables for execution logs, SLA tracking
│
└── archive/                               # Baseline schema
    ├── models/                            # Baseline volume
    └── datasets/                          # Baseline volume
```

**External Storage Catalogs:**

```
hps_clinical_notes_pending_dev/            # External catalog → Azure Storage: sthpsclinpenddev01
hps_clinical_notes_processed_dev/          # External catalog → Azure Storage: sthpsclinprocdev01
hps_clinical_notes_feedback_dev/           # External catalog → Azure Storage: sthpsclinfeeddev01
```

> **Note:** Azure Storage Account names shown use the updated naming convention with 2-digit instance suffixes (e.g., `sthpsclinpenddev01`). The Unity Catalog external catalog names remain unchanged (`hps_clinical_notes_pending_dev`) and reference these storage accounts.

> **Note:** In test and prod workspaces, equivalent catalogs exist: `hps_clinical_notes_test`, `hps_clinical_notes_prod` etc. All catalogs live in the shared metastore with environment-specific names for isolation.

**Key Resources:**
- **Repository:** `azure-devops/hps-clinical-notes`
- **Catalogs:** 
  - Dev: `hps_clinical_notes_dev` (+ 3 external catalogs)
  - Test: `hps_clinical_notes_test` (+ 3 external catalogs)
  - Prod: `hps_clinical_notes_prod` (+ 3 external catalogs)
- **Compute:**
  - Interactive: `hps-clinical-notes-interactive-01` (Standard_D8s_v3, Dedicated mode for JSL libraries)
  - Jobs: `hps-clinical-notes-batch-processing`, `hps-clinical-notes-evaluation` (Standard_E16_v3, single node)
  - Endpoints: `hps-clinical-notes-vlm-01` (A100 GPU, scale-to-zero)

**Project-Specific Requirements:**
- Proprietary JSL libraries in `models/jsl_external/` (external collaborator volume with READ grants for TCS)
- Internal team libraries in `models/libraries/` (full team access)
- JSL CV detectors in `models/artifacts/jsl_cv_models/` (signature/prescriber detection)
- Custom Siamese network in `models/artifacts/signature_siamese/` (PyTorch model)
- Medicine mapping table and ground truth labels in `data/reference/` (baseline volume)
- External storage catalogs for Azure Blob integration (pending/processed/feedback document queues)
- Pipeline outputs written to `data/processed_extractions/` (structured medical data)

**Artifact Sharing Strategy:**
- **Models:** Code deployment + retraining preferred; UC promotion for expensive GPU models
- **Code:** CI/CD via DABs (dev branch → test, main → prod)
- **Libraries:** Version-pinned in deployment configs, stored in volumes

---

### A2: Masterpet Competitor Analysis (Lightweight Data Collection)

**Baseline Extensions:**
- Schemas: `bronze/`, `silver/`, `gold/` - medallion architecture for data pipeline
- Volumes: Web scraping infrastructure (drivers, configs)

**Catalog Structure:**

```
masterpet_competitor_analysis_{env}/       # Environment-specific catalog
├── data/                                  # Baseline schema
│   ├── exploration/                       # Baseline volume (dev only)
│   └── reference/                         # Baseline volume → site scraping configs
│
├── models/                                # Baseline schema (minimal usage - no ML)
│   └── libraries/                         # PROJECT: Chrome driver binaries for web scraping
│
├── monitoring/                            # Baseline schema
│   ├── scraping_success/                  # PROJECT: Tables for scrape completion rates
│   └── pipeline_runs/                     # PROJECT: Tables for workflow execution tracking
│
├── archive/                               # Baseline schema
│   └── datasets/                          # Baseline volume → historical scrapes
│
├── bronze/                                # PROJECT SCHEMA: Raw scraped HTML/JSON
├── silver/                                # PROJECT SCHEMA: Cleaned, structured product data
└── gold/                                  # PROJECT SCHEMA: Business-level competitor insights
```

**Key Resources:**
- **Repository:** `azure-devops/masterpet-competitor-analysis`
- **Catalogs:** `masterpet_competitor_analysis_dev`, `masterpet_competitor_analysis_test`, `masterpet_competitor_analysis_prod`
- **Compute:**
  - Interactive: `masterpet-competitor-analysis-interactive-01` (Standard_D4s_v3, cost-optimized)
  - Jobs: `masterpet-competitor-analysis-daily-scraping`, `masterpet-competitor-analysis-weekly-analysis` (Standard_D4s_v3, Docker with Chrome)

**Project-Specific Requirements:**
- Docker image with bundled Chrome drivers stored in `models/libraries/`
- Medallion architecture: bronze (raw scrapes) → silver (cleaned data) → gold (business insights)
- No ML models - `models/` schema used only for driver storage

**Artifact Sharing Strategy:**
- **Code Deployment:** Re-scrape in each environment (no data promotion)
- **Docker Images:** Built once, promoted across environment registries

---

### A3: Pet Care Kitchen Moisture Optimization (ML Endpoints)

**Baseline Extensions:**
- Schema: `features/` - ML feature store for training/inference consistency
- Integration: References upstream data platform medallion for source data (no replication)

**Catalog Structure:**

```
pck_moisture_optimization_{env}/           # Environment-specific catalog
├── data/                                  # Baseline → links to upstream data platform (no local tables)
│   ├── exploration/                       # Baseline volume (dev only)
│   └── reference/                         # Baseline volume → feature schemas, encodings
│
├── models/                                # Baseline (UC-registered models)
│   ├── <UC Models - Registered in Metastore>
│   │   ├── moisture_predictor             # Main prediction model
│   │   │   ├── Version 5 (alias: champion)
│   │   │   ├── Version 6 (alias: challenger)
│   │   │   └── Version 7 (alias: latest)
│   │   ├── feature_importance_explainer   # Supporting model for SHAP explanations
│   │   │   └── Version 2 (alias: champion)
│   │   └── drift_detector                 # Model monitoring
│   │       └── Version 1 (alias: champion)
│   └── artifacts/                         # Baseline volume (lightweight usage)
│       └── preprocessing/                 # Custom scalers, encoders
│
├── monitoring/                            # Baseline
│   ├── predictions/                       # PROJECT: Tables for inference logging
│   ├── drift_metrics/                     # PROJECT: Tables for feature/target drift
│   └── endpoint_performance/              # PROJECT: Tables for latency, throughput metrics
│
├── archive/                               # Baseline
│   ├── models/                            # Baseline volume → deprecated models
│   └── datasets/                          # Baseline volume → training snapshots
│
└── features/                              # PROJECT SCHEMA: Feature store tables
    ├── manufacturing_features/            # PROJECT: Engineered features
    └── target_labels/                     # PROJECT: Training targets
```

**Key Resources:**
- **Repository:** `azure-devops/pck-moisture-optimization`
- **Catalogs:** `pck_moisture_optimization_dev`, `pck_moisture_optimization_test`, `pck_moisture_optimization_prod`
- **Compute:**
  - Interactive: `pck-moisture-optimization-interactive-01` (Standard_D4s_v3, Shared Compute)
  - Jobs: `pck-moisture-optimization-training`, `pck-moisture-optimization-monitoring` (Standard_D8s_v3)
  - Endpoints: `pck-moisture-optimization-predictor-01` (CPU-based Standard_DS3_v2, scale-to-zero)

**Project-Specific Requirements:**
- UC-registered models for serving (moisture_predictor, supporting models)
- Model aliases for lifecycle management (champion/challenger/latest)
- Feature store schema for ML feature consistency
- Upstream data platform integration (cross-workspace data reference)
- Model serving endpoint for PCK manufacturing consumption
- Custom preprocessing artifacts in `models/artifacts/preprocessing/`

**Artifact Sharing Strategy:**
- **Code Deployment:** Training code runs in each environment on environment-specific data
- **Model Retraining:** Weekly retraining on production data from upstream platform
- **Feature Consistency:** `features/` schema ensures training/inference parity

---

### A4: Cross-Project Comparison

| Aspect | HPS Clinical Notes | Masterpet Competitor | PCK Moisture |
|--------|-------------------|---------------------|--------------|
| **Project Focus** | Medical document extraction | Web scraping/data collection | ML model serving |
| **Extra Schemas** | None (baseline only) | `bronze/`, `silver/`, `gold/` | `features/` |
| **External Catalogs** | 3 (Azure Blob integration) | None | None |
| **Volume Extensions** | Heavy (JSL models, custom libraries) | Light (drivers, configs) | Light (encoders, feature schemas) |
| **Baseline Usage** | Full (all schemas + volumes) | Partial (`models/` unused) | Full (all schemas + volumes) |
| **Data Source** | Azure Blob (external catalogs) | Web scraping (generated) | Upstream data platform (cross-ref) |
| **Compute** | E16_v3 + GPU endpoints | D4s_v3 (cost-optimized) | D4s/D8s + CPU endpoint |
| **Artifact Strategy** | UC model sharing | Code only | Code + retrain per env |
