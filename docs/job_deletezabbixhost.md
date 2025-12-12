# DeleteZabbixHost Job

## Overview

The `DeleteZabbixHost` job deletes a Zabbix host, supporting both soft and hard deletion modes. This job removes hosts from Zabbix monitoring and handles the corresponding cleanup in NetBox based on plugin configuration.

## Class Definition

```python
class DeleteZabbixHost(AtomicJobRunner)
```

## Methods

### `run(cls, *args, **kwargs)`

Executes the deletion of the Zabbix host.

**Returns:**
- `dict`: Result of deletion.

**Raises:**
- `Exception`: If deletion fails.

### `run_job(cls, hostid, user=None, schedule_at=None, interval=None, immediate=False, name=None, signal_id=None)`

Enqueues a job to delete a Zabbix host.

**Parameters:**
- `hostid` (int): Zabbix host ID to delete.
- `user` (User, optional): User initiating the deletion.
- `schedule_at` (datetime, optional): Schedule time.
- `interval` (int, optional): Interval for recurring job.
- `immediate` (bool, optional): Run job immediately.
- `name` (str, optional): Job name.
- `signal_id` (str, optional): Signal identifier for event correlation.

**Returns:**
- `Job`: Enqueued job instance.

## Usage Examples

### Deleting a Zabbix Host

```python
from netbox_zabbix.jobs.host import DeleteZabbixHost

# Delete a host from Zabbix
job = DeleteZabbixHost.run_job(
    hostid=12345,
    user=request.user,
    name="Delete host 12345 from Zabbix"
)
```

### Immediate Host Deletion

```python
from netbox_zabbix.jobs.host import DeleteZabbixHost

# Delete host immediately
result = DeleteZabbixHost.run_now(
    hostid=12345,
    user=request.user
)
print(f"Host deletion result: {result['message']}")
```

## Integration with Other Components

1. **AtomicJobRunner**: Inherits transactional execution and error handling capabilities.
2. **Zabbix Hosts**: Uses `delete_zabbix_host_hard` and `delete_zabbix_host_soft` for deletion.
3. **Plugin Settings**: Respects `get_delete_setting()` for deletion mode selection.
4. **Event Logging**: Logs host deletion events to the EventLog model.

## Description

The DeleteZabbixHost job removes Zabbix hosts from monitoring, supporting both hard and soft deletion modes based on plugin configuration. It performs the following operations:

1. Determines the deletion mode (hard or soft) from plugin settings
2. Deletes the host from Zabbix using the appropriate deletion method
3. Handles cleanup and error reporting

This job supports two deletion modes:

**Hard Deletion**: Completely removes the host from Zabbix, making recovery only possible through Zabbix backup restoration.

**Soft Deletion**: Moves the host to a designated "graveyard" host group and appends a suffix to the host name, allowing for easier recovery.

This job is typically used when:
- Decommissioning devices or virtual machines from monitoring
- Cleaning up test or temporary hosts
- Removing hosts that are no longer needed
- Correcting accidentally created hosts

Key features:
- **Configurable Deletion**: Respects plugin settings for deletion behavior
- **Transaction Safety**: Executes within a database transaction
- **Error Handling**: Provides clear error messages on deletion failures
- **Audit Trail**: Logs deletion events for compliance and tracking
- **Flexible Scheduling**: Supports both immediate and scheduled deletions
- **User Tracking**: Preserves user information for audit purposes

The deletion mode is controlled by the plugin's delete setting:
- `hard`: Permanently deletes hosts from Zabbix
- `soft`: Moves hosts to graveyard host group with archived suffix

The graveyard host group name and archived suffix are configurable in plugin settings, defaulting to "graveyard" and "_archived" respectively.