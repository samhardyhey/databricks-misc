# Azure Quotas Checklist for Databricks Deployment

This document lists the Azure quotas you'll likely need to increase for your Databricks deployment in **Australia Southeast**.

## Quick Reference: How to Check/Request Quotas

1. **Azure Portal**: Subscriptions → Your Subscription → **Usage + quotas**
2. **Filter by**: Location (`australiasoutheast`) and Resource type
3. **Request increase**: Click quota → "Request increase" → Enter new limit → Submit

---

## 1. VM Family Quotas (Most Critical)

These are the quotas you'll hit most often when creating compute instances and clusters.

### Standard DSv2 Family (Most Common)
**Why needed**: Your examples use `Standard_DS3_v2` for clusters and instance pools.

| VM Size         | vCPUs | RAM   | Quota Needed    | Use Case                   |
| --------------- | ----- | ----- | --------------- | -------------------------- |
| Standard_DS3_v2 | 4     | 14 GB | **8-16 cores**  | Clusters, instance pools   |
| Standard_DS4_v2 | 8     | 28 GB | **8-16 cores**  | Larger clusters            |
| Standard_DS5_v2 | 16    | 56 GB | **16-32 cores** | High-performance workloads |

**Quota Name**: `standardDSv2Family` or `standardDSFamily`

**Recommended**: Start with **16 cores** for `standardDSv2Family` (allows 4x DS3_v2 or 2x DS4_v2)

### Standard DDSv5 Family (Compute Instances)
**Why needed**: Databricks compute instances often default to DDSv5 family.

| VM Size           | vCPUs | RAM   | Quota Needed    | Use Case                 |
| ----------------- | ----- | ----- | --------------- | ------------------------ |
| Standard_D4ds_v5  | 4     | 16 GB | **4-8 cores**   | Small compute instances  |
| Standard_D8ds_v5  | 8     | 32 GB | **8-16 cores**  | Medium compute instances |
| Standard_D16ds_v5 | 16    | 64 GB | **16-32 cores** | Large compute instances  |

**Quota Name**: `standardDDSv5Family`

**Recommended**: Start with **8 cores** for `standardDDSv5Family` (allows 2x D4ds_v5)

### Standard FSv2 Family (Cost-Effective Alternative)
**Why needed**: Cheaper option for development/testing.

| VM Size         | vCPUs | RAM   | Quota Needed   | Use Case               |
| --------------- | ----- | ----- | -------------- | ---------------------- |
| Standard_F4s_v2 | 4     | 8 GB  | **4-8 cores**  | Budget dev clusters    |
| Standard_F8s_v2 | 8     | 16 GB | **8-16 cores** | Budget medium clusters |

**Quota Name**: `standardFSv2Family`

**Recommended**: **8 cores** for `standardFSv2Family` (optional, for cost savings)

### Standard BS Family (Burstable - Optional)
**Why needed**: Very cheap option for low-utilization dev workloads.

| VM Size       | vCPUs | RAM   | Quota Needed  | Use Case             |
| ------------- | ----- | ----- | ------------- | -------------------- |
| Standard_B4ms | 4     | 16 GB | **4-8 cores** | Low-cost dev/testing |

**Quota Name**: `standardBSFamily`

**Recommended**: **4 cores** for `standardBSFamily` (optional)

---

## 2. Storage Quotas

### Managed Disks
**Why needed**: Databricks clusters and compute instances use managed disks.

| Quota Type                     | Default | Recommended    | Notes               |
| ------------------------------ | ------- | -------------- | ------------------- |
| **Premium SSD Managed Disks**  | 35 TB   | **100-500 GB** | For cluster storage |
| **Standard SSD Managed Disks** | 35 TB   | **100-500 GB** | Alternative option  |
| **Total Managed Disks**        | 50,000  | **10-50**      | Total disk count    |

**Quota Names**:
- `PremiumDiskCount` or `PremiumManagedDiskCount`
- `StandardSSDDiskCount`
- `TotalRegionalDisks`

**Recommended**: Request **500 GB** for Premium SSD (usually sufficient for dev)

### Storage Accounts
**Why needed**: Databricks workspace uses storage accounts for DBFS and workspace files.

| Quota Type                      | Default | Recommended | Notes               |
| ------------------------------- | ------- | ----------- | ------------------- |
| **Storage Accounts per Region** | 250     | **2-5**     | Usually sufficient  |
| **Storage Account Capacity**    | 5 PB    | **1-10 TB** | Per storage account |

**Quota Names**: `StorageAccounts`

**Recommended**: Usually not needed (default 250 is plenty)

---

## 3. Network Quotas

### Public IP Addresses
**Why needed**: Databricks clusters and compute instances may need public IPs.

| Quota Type                      | Default | Recommended | Notes                  |
| ------------------------------- | ------- | ----------- | ---------------------- |
| **Static Public IP Addresses**  | 20      | **5-10**    | For clusters/instances |
| **Dynamic Public IP Addresses** | 20      | **5-10**    | Alternative            |

**Quota Names**:
- `StaticPublicIPAddresses`
- `DynamicPublicIPAddresses`

**Recommended**: **10 static** and **10 dynamic** (usually sufficient)

### Network Interfaces
**Why needed**: Each VM requires a network interface.

| Quota Type             | Default | Recommended | Notes              |
| ---------------------- | ------- | ----------- | ------------------ |
| **Network Interfaces** | 2,048   | **20-50**   | Usually sufficient |

**Quota Name**: `NetworkInterfaces`

**Recommended**: Usually not needed (default is high enough)

### Virtual Networks
**Why needed**: Databricks creates VNets in the managed resource group.

| Quota Type                      | Default | Recommended | Notes              |
| ------------------------------- | ------- | ----------- | ------------------ |
| **Virtual Networks per Region** | 50      | **2-5**     | Usually sufficient |

**Quota Name**: `VirtualNetworks`

**Recommended**: Usually not needed (default is sufficient)

---

## 4. SQL Warehouse Quotas (If Using SQL Warehouses)

SQL Warehouses use different VM families. Check these if you're using SQL Warehouses:

| Quota Type               | Recommended | Notes                       |
| ------------------------ | ----------- | --------------------------- |
| **Standard DSv2 Family** | 8-16 cores  | For Small/Medium warehouses |
| **Standard DSv3 Family** | 8-16 cores  | For Large warehouses        |
| **Standard DSv4 Family** | 16-32 cores | For 2X-Large warehouses     |

**Quota Names**: `standardDSv2Family`, `standardDSv3Family`, `standardDSv4Family`

---

## 5. Resource Group Quotas

| Quota Type                           | Default | Recommended | Notes              |
| ------------------------------------ | ------- | ----------- | ------------------ |
| **Resource Groups per Subscription** | 980     | **5-10**    | Usually sufficient |

**Quota Name**: `ResourceGroups`

**Recommended**: Usually not needed (default is high enough)

---

## Priority Order for Quota Requests

### 🔴 **Critical (Request First)**
1. **`standardDSv2Family`** - 16 cores (for clusters)
2. **`standardDDSv5Family`** - 8 cores (for compute instances)

### 🟡 **Important (Request if Needed)**
3. **Premium SSD Managed Disks** - 500 GB
4. **Static Public IP Addresses** - 10 addresses

### 🟢 **Optional (Request Later if Needed)**
5. `standardFSv2Family` - 8 cores (for cost savings)
6. `standardBSFamily` - 4 cores (for budget dev)
7. SQL Warehouse VM families (if using SQL Warehouses)

---

## How to Calculate Your Quota Needs

### For Clusters:
```
Total cores needed = (driver vCPUs) + (num_workers × worker vCPUs)
```

**Example from your config:**
- Cluster with 2 workers using `Standard_DS3_v2` (4 vCPU each)
- Total: 1 driver (4 vCPU) + 2 workers (4 vCPU each) = **12 cores**
- **Request 16 cores** to allow for scaling

### For Compute Instances:
```
Total cores needed = number of compute instances × vCPUs per instance
```

**Example:**
- 1 compute instance using `Standard_D4ds_v5` (4 vCPU)
- Total: **4 cores**
- **Request 8 cores** to allow for future instances

### For Instance Pools:
```
Total cores needed = max_capacity × vCPUs per instance
```

**Example from your config:**
- Instance pool with `max_capacity = 10` using `Standard_DS3_v2` (4 vCPU)
- Total: 10 × 4 = **40 cores**
- **Request 40-48 cores** for the instance pool

---

## Quick Checklist

Before deploying, ensure you have:

- [ ] **`standardDSv2Family`**: 16+ cores (for clusters)
- [ ] **`standardDDSv5Family`**: 8+ cores (for compute instances)
- [ ] **Premium SSD Managed Disks**: 500 GB
- [ ] **Static Public IP Addresses**: 10 addresses
- [ ] (Optional) **`standardFSv2Family`**: 8 cores (for cost savings)

---

## Troubleshooting

### If you get quota errors:

1. **Check current usage**: Azure Portal → Subscriptions → Usage + quotas
2. **Identify the quota**: Look for the VM family name in the error
3. **Request increase**: Use the link in the error message or follow steps above
4. **Wait for approval**: Usually minutes for dev/test, hours for production
5. **Alternative**: Use a different VM size with available quota

### Common Error Messages:

- `standardDDSv5Family Cores quota` → Request `standardDDSv5Family` quota
- `standardDSv2Family Cores quota` → Request `standardDSv2Family` quota
- `PremiumDiskCount quota` → Request Premium SSD Managed Disk quota
- `StaticPublicIPAddresses quota` → Request Static Public IP quota

---

## Additional Resources

- [Azure VM Quota Documentation](https://docs.microsoft.com/en-us/azure/azure-supportability/per-vm-quota-requests)
- [Databricks VM Sizes](https://learn.microsoft.com/en-us/azure/databricks/compute/cluster-configuration#cluster-node-types)
- [Azure Quota Monitoring](https://aka.ms/quotamonitoringalerting)

