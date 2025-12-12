# SystemJobHostConfigSyncRefresh Job

## Overview

The `SystemJobHostConfigSyncRefresh` job periodically refreshes HostConfig sync status on a recurring interval. This system job ensures that the synchronization status between NetBox and Zabbix remains current for all monitored hosts.

## Class Definition

```python
class SystemJobHostConfigSyncRefresh(AtomicJobRunner)
```

## Methods

### `run(cls, *args, **kwargs)`

Update HostConfig objects that haven't been checked recently.

**Parameters:**
- `cutoff` (int, optional): Custom cutoff time in minutes.

**Returns:**
- `dict`: Summary of updated hosts.

**Raises:**
- `Exception`: If any unexpected error occurs.

### `schedule(cls, interval=None)`

Schedule this system job at a recurring interval.

**Parameters:**
- `interval` (int): Interval in minutes.

**Returns:**
- `Job`: Scheduled job instance.

## Usage Examples

### Scheduling the System Job

```python
from netbox_zabbix.jobs.system import SystemJobHostConfigSyncRefresh

# Schedule the job to run every 2 hours
job = SystemJobHostConfigSyncRefresh.schedule(interval=120)
print(f"Scheduled job: {job.name}")
```

### Manual Execution

```python
from netbox_zabbix.jobs.system import SystemJobHostConfigSyncRefresh

# Run the job immediately
result = SystemJobHostConfigSyncRefresh.run_now()
print(f"Sync refresh result: Updated {result['updated']}/{result['total']} hosts")
```

## Integration with Other Components

1. **AtomicJobRunner**: Inherits transactional execution and error handling capabilities.
2. **System Job Registry**: Registered with `settings.get_host_config_sync_interval` function.
3. **NetBox Models**: Works with HostConfig objects.
4. **Plugin Settings**: Uses `settings.get_host_config_sync_interval()` and `settings.get_cutoff_host_config_sync()` for scheduling.
5. **Sync Functions**: Uses `HostConfig.update_sync_status()` to check synchronization.
6. **Event Logging**: Logs sync refresh events to the EventLog model.

## Description

The SystemJobHostConfigSyncRefresh job is a recurring system task that automatically updates the synchronization status of HostConfig objects. It ensures that the `in_sync` flag and `last_sync_update` timestamp remain current for all monitored hosts.

The job performs the following operations:
1. Identifies HostConfig objects that haven't been checked recently (based on cutoff time)
2. Updates the sync status for each identified host
3. Records the update time for future reference
4. Tracks success and failure statistics
5. Provides detailed execution summary

This system job is automatically scheduled based on the plugin's configuration and runs at regular intervals to maintain accurate sync status information. It's essential for:
- Providing accurate sync status in the NetBox UI
- Enabling proper filtering of out-of-sync hosts
- Supporting automated remediation workflows
- Maintaining audit trails of configuration consistency

Key features:
- **Targeted Processing**: Only checks hosts that haven't been recently updated
- **Automatic Scheduling**: Self-manages scheduling based on plugin settings
- **Singleton Enforcement**: Ensures only one instance runs at a time
- **Interval Management**: Automatically reschedules with updated intervals
- **Flexible Cutoff**: Uses configurable cutoff time to determine which hosts to check
- **Individual Error Handling**: Continues processing despite individual host failures
- **Detailed Reporting**: Provides statistics on total, updated, and failed hosts

The job interval is controlled by the `host_config_sync_interval` setting in plugin configuration, while the cutoff time is controlled by `cutoff_host_config_sync`. Common configurations include:
- Every hour with 60-minute cutoff
- Every 2 hours with 120-minute cutoff
- Every 4 hours with 180-minute cutoff
- Daily with 1440-minute cutoff

The cutoff mechanism ensures efficient operation by only checking hosts that haven't been recently verified, preventing unnecessary Zabbix API calls while maintaining reasonable sync status accuracy.