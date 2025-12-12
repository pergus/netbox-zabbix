# SystemJobImportZabbixSettings Job

## Overview

The `SystemJobImportZabbixSettings` job periodically imports Zabbix settings into NetBox on a configurable recurring interval. This system job ensures that NetBox maintains an up-to-date copy of global Zabbix configuration objects.

## Class Definition

```python
class SystemJobImportZabbixSettings(AtomicJobRunner)
```

## Methods

### `run(cls, *args, **kwargs)`

Imports Zabbix settings.

**Returns:**
- `dict`: Import summary.

**Raises:**
- `Exception`: If import fails.

### `schedule(cls, interval=None)`

Schedules the system job at a recurring interval.

**Parameters:**
- `interval` (int): Interval in minutes.

**Returns:**
- `Job`: Scheduled job instance.

## Usage Examples

### Scheduling the System Job

```python
from netbox_zabbix.jobs.system import SystemJobImportZabbixSettings

# Schedule the job to run every hour
job = SystemJobImportZabbixSettings.schedule(interval=60)
print(f"Scheduled job: {job.name}")
```

### Manual Execution

```python
from netbox_zabbix.jobs.system import SystemJobImportZabbixSettings

# Run the job immediately
result = SystemJobImportZabbixSettings.run_now()
print(f"Import result: {result['message']}")
```

## Integration with Other Components

1. **AtomicJobRunner**: Inherits transactional execution and error handling capabilities.
2. **System Job Registry**: Registered with `get_zabbix_import_interval` function.
3. **Zabbix API**: Communicates with Zabbix to retrieve configuration objects.
4. **Import Functions**: Uses `import_zabbix_settings` for the actual import logic.
5. **NetBox Models**: Updates Template, Proxy, ProxyGroup, and HostGroup models.
6. **Plugin Settings**: Uses `settings.get_zabbix_import_interval()` for scheduling.
7. **Event Logging**: Logs import events to the EventLog model.

## Description

The SystemJobImportZabbixSettings job is a recurring system task that automatically synchronizes global Zabbix configuration objects with NetBox. It ensures that NetBox stays current with Zabbix templates, proxies, proxy groups, and host groups without manual intervention.

The job performs the following operations:
1. Retrieves templates, proxies, proxy groups, and host groups from Zabbix
2. Updates corresponding NetBox models with the latest information
3. Creates new objects for previously unknown Zabbix entities
4. Updates existing objects with changed information
5. Reports import statistics and any errors encountered

This system job is automatically scheduled based on the plugin's configuration and runs at regular intervals to maintain synchronization. It's essential for:
- Keeping mapping configurations valid (they reference Zabbix objects)
- Ensuring accurate template and proxy selections in UI
- Maintaining up-to-date host group information
- Supporting proper proxy group functionality

Key features:
- **Automatic Scheduling**: Self-manages scheduling based on plugin settings
- **Singleton Enforcement**: Ensures only one instance runs at a time
- **Interval Management**: Automatically reschedules with updated intervals
- **Conflict Resolution**: Handles job replacement when intervals change
- **Error Resilience**: Continues operation despite individual object failures
- **Detailed Reporting**: Provides import statistics and error information

The job interval is controlled by the `zabbix_import_interval` setting in plugin configuration, which can be configured through the NetBox UI. Common intervals include:
- Hourly (60 minutes)
- Every 2 hours (120 minutes)
- Daily (1440 minutes)
- Weekly (10080 minutes)

This job enables features like template-based mapping, proxy assignments, and host group organization by ensuring that all referenced Zabbix objects exist and are current in NetBox.