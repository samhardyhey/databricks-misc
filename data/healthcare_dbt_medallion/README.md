# healthcare_dbt_medallion

The 'healthcare_dbt_medallion' project implements a **Medallion Architecture** for healthcare data processing using dbt and Databricks Asset Bundles. This project transforms raw healthcare data through three layers:

- **Bronze Layer**: Raw data ingestion from Unity Catalog
- **Silver Layer**: Cleaned, validated data with business logic applied
- **Gold Layer**: Analytics-ready datasets optimized for specific use cases

The project follows the standard dbt project structure with an additional `resources` directory to define Databricks resources such as jobs that run dbt models.

* Learn more about dbt and its standard project structure here: https://docs.getdbt.com/docs/build/projects.
* Learn more about Databricks Asset Bundles here: https://docs.databricks.com/en/dev-tools/bundles/index.html
* Learn more about Medallion Architecture here: https://www.databricks.com/glossary/medallion-architecture

The remainder of this file includes instructions for local development (using dbt)
and deployment to production (using Databricks Asset Bundles).

## Medallion Architecture Overview

This project implements a three-layer medallion architecture:

### Bronze Layer (`src/models/bronze/`)
- **Purpose**: Raw data ingestion from Unity Catalog
- **Tables**: `bronze_pharmacies`, `bronze_hospitals`, `bronze_products`, `bronze_orders`, `bronze_inventory`, `bronze_supply_chain_events`
- **Materialization**: Tables
- **Schema**: `bronze`

### Silver Layer (`src/models/silver/`)
- **Purpose**: Data cleaning, validation, and business logic application
- **Tables**: `silver_pharmacies`, `silver_hospitals`, `silver_products`, `silver_orders`, `silver_inventory`, `silver_supply_chain_events`
- **Materialization**: Tables
- **Schema**: `silver`
- **Features**: Data quality checks, business rules, calculated fields

### Gold Layer (`src/models/gold/`)
- **Purpose**: Analytics-ready datasets for specific use cases
- **Tables**: 
  - `gold_pharmacy_performance` - Pharmacy KPIs and metrics
  - `gold_product_performance` - Product analytics and trends
  - `gold_financial_analytics` - Financial reporting and analysis
  - `gold_ml_ready_dataset` - ML-ready features and targets
  - `gold_supply_chain_performance` - Supply chain analytics
- **Materialization**: Tables
- **Schema**: `gold`

## Development setup

1. Install the Databricks CLI from https://docs.databricks.com/dev-tools/cli/databricks-cli.html

2. Authenticate to your Databricks workspace, if you have not done so already:
    ```
    $ databricks configure
    ```

3. Install dbt

   To install dbt, you need a recent version of Python. For the instructions below,
   we assume `python3` refers to the Python version you want to use. On some systems,
   you may need to refer to a different Python version, e.g. `python` or `/usr/bin/python`.

   Run these instructions from the `healthcare_dbt_medallion` directory. We recommend making
   use of a Python virtual environment and installing dbt as follows:

   ```
   $ python3 -m venv .venv
   $ . .venv/bin/activate
   $ pip install -r requirements-dev.txt
   ```

4. Initialize your dbt profile

   Use `dbt init` to initialize your profile.

   ```
   $ dbt init
   ```

   Note that dbt authentication uses personal access tokens by default
   (see https://docs.databricks.com/dev-tools/auth/pat.html).
   You can use OAuth as an alternative, but this currently requires manual configuration.
   See https://github.com/databricks/dbt-databricks/blob/main/docs/oauth.md
   for general instructions, or https://community.databricks.com/t5/technical-blog/using-dbt-core-with-oauth-on-azure-databricks/ba-p/46605
   for advice on setting up OAuth for Azure Databricks.

   To setup up additional profiles, such as a 'prod' profile,
   see https://docs.getdbt.com/docs/core/connect-data-platform/connection-profiles.

5. Activate dbt so it can be used from the terminal

   ```
   $ . .venv/bin/activate
    ```

## Local development with dbt

Use `dbt` to [run this project locally using a SQL warehouse](https://docs.databricks.com/partners/prep/dbt.html):

```bash
# Run the entire medallion pipeline
$ dbt seed
$ dbt run
$ dbt test

# Run specific layers
$ dbt run --select tag:bronze
$ dbt run --select tag:silver  
$ dbt run --select tag:gold

# Run specific models
$ dbt run --model silver_orders
$ dbt run --model gold_pharmacy_performance
```

(Did you get an error that the dbt command could not be found? You may need
to try the last step from the development setup above to re-activate
your Python virtual environment!)

Use `dbt test` to run tests generated from yml files such as `src/models/sources.yml`
and any SQL tests from `src/tests/`

```bash
$ dbt test
```

## Production setup

Your production dbt profiles are defined in dbt_profiles/profiles.yml.
These profiles define the default catalog, schema, and any other
target-specific settings. Read more about dbt profiles on Databricks at
https://docs.databricks.com/en/workflows/jobs/how-to/use-dbt-in-workflows.html#advanced-run-dbt-with-a-custom-profile.

The target workspaces for staging and prod are defined in databricks.yml.
You can manually deploy based on these configurations (see below).
Or you can use CI/CD to automate deployment. See
https://docs.databricks.com/dev-tools/bundles/ci-cd.html for documentation
on CI/CD setup.

## Manually deploying to Databricks with Databricks Asset Bundles

Databricks Asset Bundles can be used to deploy to Databricks and to execute
dbt commands as a job using Databricks Workflows. See
https://docs.databricks.com/dev-tools/bundles/index.html to learn more.

Use the Databricks CLI to deploy a development copy of this project to a workspace:

```
$ databricks bundle deploy --target dev
```

(Note that "dev" is the default target, so the `--target` parameter
is optional here.)

This deploys everything that's defined for this project.
For example, the default template would deploy a job called
`[dev yourname] healthcare_dbt_medallion_job` to your workspace.
You can find that job by opening your workpace and clicking on **Workflows**.

The job will run the complete medallion pipeline:
1. `dbt deps` - Install dependencies
2. `dbt seed` - Load seed data
3. `dbt run` - Execute all models (bronze → silver → gold)
4. `dbt test` - Run data quality tests

You can also deploy to your production target directly from the command-line.
The warehouse, catalog, and schema for that target are configured in databricks.yml.
When deploying to this target, note that the default job at resources/healthcare_dbt_medallion.job.yml
has a schedule set that runs every day. The schedule is paused when deploying in development mode
(see https://docs.databricks.com/dev-tools/bundles/deployment-modes.html).

To deploy a production copy, type:

```
$ databricks bundle deploy --target prod
```

## IDE support

Optionally, install developer tools such as the Databricks extension for Visual Studio Code from
https://docs.databricks.com/dev-tools/vscode-ext.html. Third-party extensions
related to dbt may further enhance your dbt development experience!
