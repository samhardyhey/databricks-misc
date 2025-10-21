### Unity Catalog
Unity Catalog includes a three-level namespace for data objects: catalog.schema.table. In this example, you'll run a notebook that creates a table named department in the workspace catalog and default schema (database).

- difference data warehouse or a data lake.
- pyspark specific new features? pipelines?
- pyspark pipelines > very interesting
  - but why use pipelines at all? how to segment/cut units of work into a pipeline?
      - for data? for modelling? for CI/CD equally?

### Databricks connect
- need to match local python version with the remote version > nightmare alignment?
- generally works great with cursor and databricks free edition > actually connects/configs
- slow to run though; but still more convenient than git commiting/pulling down changes

### Specifics
### Modelling/data gen
- some online tutorials
- DAB > locally, remotely, deploy
    - local extensions/remote usage
- mlflow 3 usage/difference

### Platform
- azure deployment of databricks workspace > terraform?
    - postgres database on azure > databricks workspace
    - DBT

### Policy/organisation/governance
- possible organisation of catalog/schemas/models?
