# SyncHostsNow Job

## Overview

The `SyncHostsNow` job synchronizes all NetBox HostConfig objects with their corresponding hosts in Zabbix immediately. This job provides on-demand synchronization of the entire host configuration database.

## Class Definition

```python
class SyncHostsNow(AtomicJobRunner)
```

## Methods

### `run(cls, *args, **kwargs)`

Execute the host synchronization.

**Parameters:**
- `user` (User, optional): The triggering user.
- `request_id` (str, optional): Request identifier for logging.

**Returns:**
- `dict`: Summary of host sync results.

### `run_job_now(cls, request)`

Immediately execute the job in the current process.

**Parameters:**
- `request` (HttpRequest): The triggering request.

**Returns:**
- `dict`: Job execution summary.

## Usage Examples

### Running Full Synchronization

```python
from netbox_zabbix.jobs.synchosts import SyncHostsNow

# Run full synchronization immediately
result = SyncHostsNow.run_job_now(request)
print(f"Sync result: {result['message']}")
print(f"Updated: {result['updated']}/{result['total']} hosts")
```

### Using run_now Method

```python
from netbox_zabbix.jobs.synchosts import SyncHostsNow

# Run full synchronization using run_now
result = SyncHostsNow.run_now(
    user=request.user,
    request_id=request.id
)
print(f"Sync completed: {result}")
```

## Integration with Other Components

1. **AtomicJobRunner**: Inherits transactional execution and error handling capabilities.
2. **Zabbix Hosts**: Uses `update_zabbix_host` to synchronize each host.
3. **NetBox Models**: Works with HostConfig objects.
4. **Plugin Settings**: Respects event logging configuration.
5. **Event Logging**: Logs synchronization events to the EventLog model.

## Description

The SyncHostsNow job provides comprehensive synchronization of all NetBox HostConfig objects with their corresponding Zabbix hosts. Unlike recurring system jobs, this job runs on-demand and processes all hosts immediately.

The job performs the following operations:
1. Iterates through all HostConfig objects in NetBox
2. Updates each host in Zabbix to match current NetBox configuration
3. Updates sync status for each host
4. Tracks success and failure statistics
5. Provides detailed execution summary

This job is typically used when:
- Performing initial synchronization after plugin installation
- Recovering from widespread configuration drift
- Validating that all hosts are properly configured
- Running comprehensive maintenance operations
- Troubleshooting synchronization issues across multiple hosts

Key features:
- **Comprehensive Coverage**: Processes all HostConfig objects
- **Individual Error Handling**: Continues processing despite individual host failures
- **Detailed Reporting**: Provides statistics on total, updated, and failed hosts
- **Transaction Safety**: Executes within a database transaction
- **Progress Tracking**: Logs progress for large host populations
- **Error Logging**: Records individual host failure details

The job ensures that all Zabbix host configurations remain synchronized with NetBox, including:
- Host names and descriptions
- Template assignments
- Host group memberships
- Interface configurations
- Proxy or proxy group assignments
- Host status (enabled/disabled)
- Custom tags and inventory data

Unlike scheduled system jobs that process subsets of hosts, SyncHostsNow provides a complete synchronization pass, making it ideal for maintenance windows or post-migration validation.