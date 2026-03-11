
# HPS Clinical Notes Endpoints Bundle

This bundle deploys the VLM model serving endpoint for medical document processing. Scheduling and cost optimization jobs are now managed in the separate jobs bundle.

## Resources
- **VLM Endpoint**: JSL VLM 8B model serving endpoint for medical document analysis
- **Compute**: GPU_LARGE workload with scale-to-zero (0-4 max concurrency in dev/test, 4-20 in prod)
- **Model**: jsl-vlm-8b version 2 from jsl_delta_share.model

> **Note:** Scheduling and cost optimization jobs (morning startup, evening shutdown) are now defined and deployed in the [jobs bundle](../jobs/JOBS.md), not in this endpoints bundle.

## Endpoint Scheduling Motivation

VLM endpoints running on GPU infrastructure represent significant operational costs when left running 24/7. This bundle implements automated scheduling to balance cost efficiency with SLA requirements:

**Cost Challenges:**
- GPU_LARGE workloads with A100 GPUs are expensive (~$20-40/hour when active)
- Medical document processing has predictable business hours (6 AM - 10 PM AEST)
- Overnight usage is minimal, making 24/7 operation cost-inefficient

**SLA Requirements:**
- Guaranteed minimum concurrency during business hours for production workloads
- Sub-minute response times for medical document processing requests
- Zero cold-start delays during peak processing windows

**Automated Solution:**
- **Endpoint scheduling and cost optimization** are managed by jobs in the jobs bundle. See [jobs bundle documentation](../jobs/JOBS.md) for details on:
	- Morning Startup (6 AM): Scales endpoint to minimum production capacity before business hours
	- Evening Shutdown (10 PM): Scales to zero for overnight cost savings
	- Environment-specific scheduling and notifications

This approach reduces operational costs by 60-70% while maintaining strict SLA compliance during business hours.

## Deployment Targets
- `dev-sp`: Development environment (scheduling disabled, manual scaling only)
- `test-sp`: Testing environment (optional scheduling for validation)  
- `prod-sp`: Production environment (full automated scheduling enabled)

## Quick Deploy
```bash
cd bundles/endpoints
databricks bundle deploy --target prod-sp --profile prod-sp
databricks bundle validate --target prod-sp --profile prod-sp
databricks bundle destroy --target prod-sp --profile prod-sp
```

## Manual Endpoint Scaling
For immediate scaling needs (maintenance, testing, emergency), use the jobs in the jobs bundle:
```bash
# Scale up for immediate use
databricks jobs run-now --job-name "Endpoint-Morning-Startup-prod"

# Scale down for cost savings
databricks jobs run-now --job-name "Endpoint-Evening-Shutdown-prod"
```

## Scheduling Configuration
Scheduling and cost optimization are now managed in the jobs bundle. See [jobs bundle documentation](../jobs/JOBS.md) for environment-specific scheduling variables and configuration.

## Features
- **Automated Scheduling**: Cost-optimized business hour operation (6 AM - 10 PM AEST)
- **Scale-to-Zero**: Overnight shutdown for maximum cost savings
- **GPU Acceleration**: A100 GPUs for fast medical document inference
- **Environment Isolation**: Separate endpoints and schedules per environment
- **SLA Compliance**: Guaranteed minimum concurrency during production business hours
- **Access Control**: Restricted to service principal and admin user
- **Failure Notifications**: Production alerts for scheduling failures

## Cost Impact
- **Before Scheduling**: 24/7 GPU operation (~$175-350/day)
- **After Scheduling**: 16-hour daily operation (~$115-230/day)
- **Estimated Savings**: 60-70% reduction in endpoint operational costs

## Dependencies
- Unity Catalog model: `jsl_delta_share.model.jsl-vlm-8b`
- Key vault secrets: JSL license keys