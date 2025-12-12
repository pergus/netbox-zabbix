# SystemJobMaintenanceCleanup Job

## Overview

The `SystemJobMaintenanceCleanup` job periodically cleans up expired Zabbix Maintenance windows from both NetBox and Zabbix. This system job ensures that completed maintenance schedules are properly removed from the system.

## Class Definition

```python
class SystemJobMaintenanceCleanup(AtomicJobRunner)
```

## Methods

### `run(cls, *args, **kwargs)`

Delete all expired maintenances whose end_time <= now.

**Returns:**
- `dict`: Summary of cleanup operations.

### `schedule(cls, interval=None)`

Schedule this system job at a recurring interval.

**Parameters:**
- `interval` (int): Interval in minutes.

**Returns:**
- `Job`: Scheduled job instance.

## Usage Examples

### Scheduling the System Job

```python
from netbox_zabbix.jobs.system import SystemJobMaintenanceCleanup

# Schedule the job to run daily
job = SystemJobMaintenanceCleanup.schedule(interval=1440)
print(f"Scheduled job: {job.name}")
```

### Manual Execution

```python
from netbox_zabbix.jobs.system import SystemJobMaintenanceCleanup

# Run the job immediately
result = SystemJobMaintenanceCleanup.run_now()
print(f"Cleanup result: Deleted {result['deleted']}/{result['checked']} maintenances")
```

## Integration with Other Components

1. **AtomicJobRunner**: Inherits transactional execution and error handling capabilities.
2. **System Job Registry**: Registered with `settings.get_maintenance_cleanup_interval` function.
3. **NetBox Models**: Works with Maintenance objects.
4. **Plugin Settings**: Uses `settings.get_maintenance_cleanup_interval()` for scheduling.
5. **Zabbix API**: Communicates with Zabbix to clean up maintenance windows.
6. **Event Logging**: Logs cleanup events to the EventLog model.

## Description

The SystemJobMaintenanceCleanup job is a recurring system task that automatically removes expired maintenance windows from both NetBox and Zabbix. It prevents the accumulation of obsolete maintenance schedules and keeps the maintenance database clean.

The job performs the following operations:
1. Identifies Maintenance objects with end_time in the past and status "pending" or "active"
2. Deletes each expired maintenance from NetBox
3. Removes corresponding maintenance windows from Zabbix
4. Logs successful deletions and any failures
5. Provides detailed execution summary

This system job is automatically scheduled based on the plugin's configuration and runs at regular intervals to maintain a clean maintenance database. It's essential for:
- Preventing database bloat from expired maintenances
- Maintaining accurate maintenance listings in UI
- Freeing up resources in both NetBox and Zabbix
- Ensuring compliance with data retention policies

Key features:
- **Automatic Cleanup**: Self-manages expired maintenance removal
- **Dual System Cleanup**: Removes maintenances from both NetBox and Zabbix
- **Automatic Scheduling**: Self-manages scheduling based on plugin settings
- **Singleton Enforcement**: Ensures only one instance runs at a time
- **Interval Management**: Automatically reschedules with updated intervals
- **Individual Error Handling**: Continues processing despite individual deletion failures
- **Detailed Reporting**: Provides statistics on total checked and deleted maintenances
- **Logging**: Records cleanup operations for audit purposes

The job interval is controlled by the `maintenance_cleanup_interval` setting in plugin configuration. Common intervals include:
- Daily (1440 minutes)
- Weekly (10080 minutes)
- Bi-weekly (20160 minutes)
- Monthly (43200 minutes)

The cleanup process respects the maintenance deletion settings configured in the plugin:
- For hard deletion: Maintenance windows are permanently removed
- For soft deletion: Behavior depends on specific implementation

This job helps maintain system performance by preventing the accumulation of obsolete maintenance records while ensuring that historical maintenance data can still be accessed through NetBox's changelog and event log features.