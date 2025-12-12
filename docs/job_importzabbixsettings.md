# ImportZabbixSettings Job

## Overview

The `ImportZabbixSettings` job synchronizes global Zabbix entities such as templates, proxies, proxy groups, and host groups into NetBox models. This job ensures that NetBox maintains an up-to-date copy of Zabbix configuration objects.

## Class Definition

```python
class ImportZabbixSettings(AtomicJobRunner)
```

## Methods

### `run(cls, *args, **kwargs)`

Executes the import of Zabbix settings.

**Returns:**
- `dict`: Imported configuration summary.

**Raises:**
- `Exception`: If import fails.

### `run_job(cls, user=None, schedule_at=None, interval=None, immediate=False, name=None)`

Schedules or enqueues the ImportZabbixSettings job.

**Parameters:**
- `user` (User, optional): User triggering the job.
- `schedule_at` (datetime, optional): Schedule time.
- `interval` (int, optional): Interval in minutes for recurring job.
- `immediate` (bool, optional): Run job immediately.
- `name` (str, optional): Job name.

**Returns:**
- `Job`: The enqueued job instance.

## Usage Examples

### Running Import Immediately

```python
from netbox_zabbix.jobs.imports import ImportZabbixSettings

# Run import immediately
result = ImportZabbixSettings.run_now()
print(f"Imported {result['templates']} templates, {result['proxies']} proxies")
```

### Scheduling Recurring Import

```python
from netbox_zabbix.jobs.imports import ImportZabbixSettings

# Schedule recurring import every hour
job = ImportZabbixSettings.run_job(
    user=request.user,
    interval=60,  # Every 60 minutes
    name="Hourly Zabbix Settings Import"
)
```

## Integration with Other Components

1. **AtomicJobRunner**: Inherits transactional execution and error handling capabilities.
2. **Zabbix API**: Communicates with Zabbix to retrieve configuration objects.
3. **Import Functions**: Uses `import_zabbix_settings` for the actual import logic.
4. **NetBox Models**: Updates Template, Proxy, ProxyGroup, and HostGroup models.
5. **Event Logging**: Logs import events to the EventLog model.

## Description

The ImportZabbixSettings job is crucial for maintaining synchronization between Zabbix and NetBox configuration objects. It performs the following operations:

1. Retrieves templates, proxies, proxy groups, and host groups from Zabbix
2. Updates corresponding NetBox models with the latest information
3. Creates new objects for previously unknown Zabbix entities
4. Updates existing objects with changed information
5. Reports import statistics and any errors encountered

This job is typically run on a recurring schedule to ensure that NetBox stays current with Zabbix configuration changes. It enables features like mapping configurations that reference Zabbix objects by ensuring those objects exist in NetBox.