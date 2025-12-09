# NetBox Zabbix Plugin - Maintenance Model Documentation

The Maintenance model in the NetBox Zabbix plugin represents scheduled maintenance windows for Zabbix hosts. This document explains the Maintenance model's structure, fields, properties, methods, and usage.

## Overview

The Maintenance model (`netbox_zabbix.models.Maintenance`) defines time periods during which one or more hosts are put into maintenance mode in Zabbix. Maintenance windows can target hosts derived from Sites, HostGroups, ProxyGroups, Clusters, or specific HostConfig objects.

## Model Fields

| Field | Type | Description | Notes |
|-------|------|-------------|-------|
| `name` | CharField (max_length=200) | Maintenance window name | Human-readable identifier |
| `start_time` | DateTimeField | Maintenance start time | Default: timezone.now() |
| `end_time` | DateTimeField | Maintenance end time | Required |
| `disable_data_collection` | BooleanField | Disable data collection | Default: False |
| `host_configs` | ManyToManyField (HostConfig) | Direct host targets | Specific host configurations |
| `sites` | ManyToManyField (Site) | Site targets | Sites whose hosts are included |
| `host_groups` | ManyToManyField (HostGroup) | Host group targets | Host groups whose hosts are included |
| `proxies` | ManyToManyField (Proxy) | Proxy targets | Proxies whose hosts are included |
| `proxy_groups` | ManyToManyField (ProxyGroup) | Proxy group targets | Proxy groups whose hosts are included |
| `clusters` | ManyToManyField (Cluster) | Cluster targets | Clusters whose hosts are included |
| `zabbix_id` | CharField (max_length=50) | Zabbix maintenance ID | Assigned by Zabbix when synced |
| `status` | CharField | Maintenance status | Default: 'pending'. Options: 'pending', 'active', 'expired', 'failed' |
| `description` | TextField | Maintenance description | Optional detailed description |

## Properties

### `is_active`
Returns `True` if the maintenance window is currently active (current time is between start_time and end_time).

### `disable_data_collection_value`
Returns a formatted HTML string with a green checkmark if data collection is disabled during maintenance, or a red X if it's enabled.

## Methods

### `__str__()`
Returns a human-readable string representation of the maintenance window in the format: `{name} ({local_start_time})`.

### `get_absolute_url()`
Returns the canonical URL for this maintenance window within the NetBox plugin UI:
```
/plugins/netbox_zabbix/maintenances/{pk}/
```

### `get_matching_host_configs()`
Returns a queryset of HostConfig objects that match this maintenance window based on the configured targets (sites, host groups, proxies, proxy groups, clusters, or direct host assignments).

### `_build_params()`
Constructs the parameters dictionary for Zabbix API create/update maintenance calls. This method resolves all target hosts and builds the appropriate Zabbix API parameters.

### `create_maintenance_window()`
Creates a new maintenance window in Zabbix with the current configuration and updates the `zabbix_id` and `status` fields.

### `update_maintenance_window()`
Updates an existing maintenance window in Zabbix. Requires that the `zabbix_id` field is already populated.

### `delete(*args, **kwargs)`
Attempts to delete the maintenance window from Zabbix. If successful, also removes it from NetBox. If Zabbix deletion fails, returns a warning but still removes from NetBox.

## Field Details

### `name`
A human-readable name for the maintenance window that helps identify its purpose.

### `start_time` and `end_time`
Define the time period during which the maintenance window is active. These times are used both in NetBox and when creating the maintenance window in Zabbix.

### `disable_data_collection`
When set to `True`, Zabbix will not collect data from hosts during the maintenance window. When `False`, monitoring continues but problems are suppressed.

### Target Fields
Multiple targeting options allow flexible maintenance window creation:
- `host_configs`: Direct assignment of specific host configurations
- `sites`: All hosts associated with specified sites
- `host_groups`: All hosts belonging to specified host groups
- `proxies`: All hosts monitored by specified proxies
- `proxy_groups`: All hosts monitored by specified proxy groups
- `clusters`: All virtual machines in specified clusters

### `status`
Tracks the current state of the maintenance window:
- `pending`: Maintenance is scheduled but not yet active
- `active`: Maintenance is currently in progress
- `expired`: Maintenance period has passed
- `failed`: An error occurred during maintenance operations

## Usage Examples

### Creating a Maintenance Window
```python
from netbox_zabbix.models import Maintenance
from django.utils import timezone
from datetime import timedelta

# Create a maintenance window
maintenance = Maintenance.objects.create(
    name="Database Server Maintenance",
    start_time=timezone.now(),
    end_time=timezone.now() + timedelta(hours=2),
    disable_data_collection=True,
    description="Scheduled maintenance for database servers"
)
```

### Targeting Specific Hosts
```python
from netbox_zabbix.models import HostConfig, HostGroup

# Add specific host configs to maintenance
host1 = HostConfig.objects.get(name="db-server-01")
host2 = HostConfig.objects.get(name="db-server-02")
maintenance.host_configs.add(host1, host2)

# Add host groups to maintenance
prod_db_group = HostGroup.objects.get(name="Production Database Servers")
maintenance.host_groups.add(prod_db_group)
```

### Targeting by Site or Cluster
```python
from dcim.models import Site
from virtualization.models import Cluster

# Target all hosts in specific sites
datacenter_site = Site.objects.get(name="Datacenter A")
maintenance.sites.add(datacenter_site)

# Target all VMs in specific clusters
database_cluster = Cluster.objects.get(name="Database Cluster")
maintenance.clusters.add(database_cluster)
```

### Synchronizing with Zabbix
```python
# Create the maintenance window in Zabbix
try:
    maintenance.create_maintenance_window()
    print(f"Maintenance created in Zabbix with ID: {maintenance.zabbix_id}")
except Exception as e:
    print(f"Failed to create maintenance in Zabbix: {e}")

# Update an existing maintenance window
maintenance.description = "Extended maintenance due to complications"
maintenance.end_time = maintenance.end_time + timedelta(hours=1)
maintenance.update_maintenance_window()
```

### Checking Maintenance Status
```python
# Check if maintenance is currently active
if maintenance.is_active:
    print("Maintenance is currently active")

# Check data collection status
if maintenance.disable_data_collection:
    print("Data collection is disabled during this maintenance")
```

## Best Practices

1. **Descriptive Naming**: Use clear, descriptive names for maintenance windows to facilitate identification and reporting.

2. **Appropriate Duration**: Set realistic maintenance window durations to avoid unnecessarily long periods of reduced monitoring.

3. **Target Precision**: Use the most specific targeting method possible to avoid affecting unintended hosts.

4. **Data Collection Decision**: Carefully consider whether to disable data collection based on the nature of the maintenance work.

5. **Status Monitoring**: Regularly check maintenance status to ensure windows are progressing as expected.

6. **Documentation**: Use the description field to document the purpose, scope, and any special considerations for each maintenance window.