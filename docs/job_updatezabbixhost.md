# UpdateZabbixHost Job

## Overview

The `UpdateZabbixHost` job updates an existing Zabbix host using HostConfig. This job synchronizes changes made to NetBox HostConfig objects with their corresponding Zabbix hosts, ensuring that monitoring configurations remain consistent.

## Class Definition

```python
class UpdateZabbixHost(AtomicJobRunner)
```

## Methods

### `run(cls, *args, **kwargs)`

Updates the host in Zabbix with the current HostConfig.

**Returns:**
- `dict`: Updated host information.

**Raises:**
- `Exception`: If update fails.

### `run_job(cls, host_config, request, user=None, schedule_at=None, interval=None, immediate=False, name=None, signal_id=None)`

Enqueues an UpdateZabbixHost job.

**Parameters:**
- `host_config` (HostConfig): Host to update.
- `request` (HttpRequest): Triggering request.
- `user` (User, optional): User initiating the update.
- `schedule_at` (datetime, optional): Schedule time.
- `interval` (int, optional): Interval for recurring job.
- `immediate` (bool, optional): Run immediately.
- `name` (str, optional): Job name.
- `signal_id` (str, optional): Signal identifier for event correlation.

**Returns:**
- `Job`: Enqueued job instance.

### `run_job_now(cls, host_config, request, name=None)`

Immediately updates a Zabbix host.

**Parameters:**
- `host_config` (HostConfig): Host to update.
- `request` (HttpRequest): Triggering request.
- `name` (str, optional): Job name.

**Returns:**
- `dict`: Result of immediate update.

## Usage Examples

### Updating a Zabbix Host

```python
from netbox_zabbix.jobs.host import UpdateZabbixHost
from netbox_zabbix.models import HostConfig

# Get a host configuration to update in Zabbix
host_config = HostConfig.objects.get(name="web-server-01")

# Update the host in Zabbix
job = UpdateZabbixHost.run_job(
    host_config=host_config,
    request=request,
    name=f"Update host {host_config.name} in Zabbix"
)
```

### Immediate Host Update

```python
from netbox_zabbix.jobs.host import UpdateZabbixHost
from netbox_zabbix.models import HostConfig

# Get a host configuration
host_config = HostConfig.objects.get(name="web-server-01")

# Update host immediately
result = UpdateZabbixHost.run_job_now(
    host_config=host_config,
    request=request
)
print(f"Host update result: {result['message']}")
```

## Integration with Other Components

1. **AtomicJobRunner**: Inherits transactional execution and error handling capabilities.
2. **Zabbix Hosts**: Uses `update_zabbix_host` to synchronize host configuration.
3. **NetBox Models**: Works with HostConfig objects.
4. **Event Logging**: Logs host update events to the EventLog model.

## Description

The UpdateZabbixHost job synchronizes NetBox HostConfig objects with their corresponding Zabbix hosts. It performs the following operations:

1. Retrieves the HostConfig object from NetBox
2. Updates the corresponding host in Zabbix with current configuration
3. Synchronizes templates, host groups, interfaces, and other settings
4. Ensures Zabbix host configuration matches NetBox definitions

This job is typically used when:
- HostConfig objects have been modified in NetBox
- Template or host group assignments have changed
- Interface configurations have been updated
- Proxy or proxy group assignments have changed
- Host status (enabled/disabled) has been modified
- Recovering from configuration drift between NetBox and Zabbix

Key features:
- **Transaction Safety**: Executes within a database transaction to ensure consistency
- **Comprehensive Sync**: Updates all host configuration aspects
- **Flexible Scheduling**: Supports both immediate and scheduled updates
- **User Tracking**: Preserves user information for audit purposes
- **Signal Correlation**: Supports signal ID tracking for event correlation
- **Error Handling**: Provides clear error messages on update failures

The job ensures that all Zabbix host configuration remains synchronized with NetBox, including:
- Host name and description
- Template assignments based on current mapping configurations
- Host group memberships
- Interface configurations (adding, removing, or updating interfaces)
- Proxy or proxy group assignments
- Host status (enabled/disabled)
- Custom tags and inventory data
- Maintenance window associations