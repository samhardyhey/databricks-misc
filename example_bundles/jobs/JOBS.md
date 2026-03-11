# HPS Clinical Notes Jobs Bundle

This bundle deploys:
- The batch processing pipeline for HPS Clinical Notes JSL processing
- Endpoint scheduling and cost optimization jobs (morning startup, evening shutdown) for the VLM endpoint

## Endpoint Scheduling & Cost Optimization Jobs
These jobs automate scaling of the VLM endpoint to optimize GPU costs and ensure SLA compliance:
- **Morning Startup (6 AM AEST)**: Scales the endpoint up to minimum production concurrency before business hours
- **Evening Shutdown (10 PM AEST)**: Scales the endpoint down to zero for overnight cost savings

Scheduling, notification, and environment-specific configuration for these jobs is managed here (not in the endpoints bundle). See the endpoint bundle for details on the VLM endpoint itself.

## Resources
- **Batch Job**: End-to-end modular JSL processing pipeline
- **Endpoint Management Jobs**: Morning startup and evening shutdown for VLM endpoint
- **Compute**: Standard_E16_v3 single node cluster with JSL libraries
- **Runtime**: Databricks Runtime 16.4.x-cpu-ml-scala2.12

## Deployment Targets
- `dev-sp`: Development environment (when available)
- `test-sp`: Testing environment (when available)  
- `prod-sp`: Production environment (default)

## Quick Deploy
```bash
cd bundles/jobs
databricks bundle deploy --target prod-sp --profile prod-sp
databricks bundle validate --target prod-sp --profile prod-sp
databricks bundle run hps_clinical_notes_batch_pipeline --target prod-sp --profile prod-sp
databricks bundle destroy --target prod-sp --profile prod-sp
``

## Dependencies
- Shared source code in `../../src/`
- Notebook entry point: `../../notebooks/production/end_to_end_modular_batch.py`
- JSL libraries: Available in workspace and volumes
- Key vault secrets: License keys and AWS credentials