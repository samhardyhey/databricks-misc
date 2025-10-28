### How Azure Databricks pricing works
- Databricks uses a “units + cloud infrastructure” cost model. You’re charged for (1) the Databricks service in units called “Databricks Units” (DBUs) and (2) the underlying Azure compute/storage that the clusters use.
- The DBU rate depends on: tier (Standard, Premium, Enterprise), workload type (interactive, jobs, SQL warehouse), and region.
- The infrastructure cost is essentially the Azure VMs/disks/managed-services you spin up via Databricks, so you pay Azure’s standard compute/storage/IOE costs too.
- Region matters: even though the DBU component may not differ wildly by region, the underlying Azure resource cost does vary by region.
- Billing granularity: you pay per second (or per minute) usage for the compute component.

#### Specific calculators
- databricks x azure: https://www.databricks.com/product/pricing/product-pricing/instance-types


| **Factor**                   | **Databricks Model**                                                                                                                                      | **Raw Azure Resources Model**                                                                                                                   |
| ---------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| Service layer cost           | You pay for DBUs + underlying compute/storage. The DBU cost covers Databricks platform features (optimizations, cluster management, interactive tooling). | Pay only for raw resources: VMs, storage, etc. No extra “platform” license cost (may pay for additional software licenses or managed services). |
| Compute cost granularity     | Databricks abstracts some complexity (you choose cluster type, it provisions VMs), but you still pay for those VMs.                                       | Full control: pick VM sizes directly, can stop when idle, scale as needed—more flexibility and responsibility.                                  |
| Operational overhead         | Lower: Databricks handles cluster orchestration, Spark runtime, autoscaling, etc.—can increase productivity.                                              | Higher: Build and maintain more of the infrastructure yourself. Can be costlier in time or due to over-provisioned resources.                   |
| Idle/under-utilised cost     | Still pay for underlying VMs while running. Databricks may autoscale more efficiently.                                                                    | Still pay for idle VMs—need to handle start/stop and autoscaling.                                                                               |
| Region impact                | Region affects both DBU and underlying VM/storage costs; check region-specific Databricks pricing.                                                        | Region significantly affects VM/storage pricing—for instance, Australia East vs Southeast may differ (see VM rates).                            |
| Predictability & discounting | Databricks offers pricing tiers and commitments. Azure also offers reservations/commitments for VMs. [Microsoft Azure][1]                                 | Can reserve VMs or use spot instances. Discounting is possible, but risk and reward are more explicit.                                          |
| Scenario suitability         | Best for rapid analytics, Spark workloads, and data science—less infrastructure management required.                                                      | Best if you already have infra skills, want fine-grained control, or are building highly customized pipelines.                                  |

[1]: https://azure.microsoft.com/en-au/pricing/offers/reservations/?utm_source=chatgpt.com "Azure Reservation Pricing | Microsoft Azure"
