# NetBox Zabbix Plugin - System/Recurring Jobs Documentation

## Overview

The NetBox Zabbix plugin implements a robust job system for managing background tasks that synchronize data between NetBox and Zabbix. System/recurring jobs are automatically scheduled tasks that run at configurable intervals to maintain consistency between the two systems.

## System Job Classes

### SystemJobImportZabbixSettings

This job periodically imports Zabbix settings (templates, proxies, host groups, etc.) into NetBox to keep the local cache up to date.

#### Class Definition
```python
class SystemJobImportZabbixSettings(AtomicJobRunner)
```

#### Key Methods

##### `run(cls, *args, **kwargs)`
Executes the Zabbix settings import process.

**Returns:**
- `dict`: Import summary containing statistics about imported objects

**Raises:**
- `Exception`: If import fails, with details about the failure

##### `schedule(cls, interval=None)`
Schedules the system job at a recurring interval.

**Parameters:**
- `interval` (int): Interval in minutes between job executions

**Returns:**
- `Job`: Scheduled job instance

**Notes:**
- Only one instance of this system job is allowed at a time
- If a job with the same name already exists, it will be deleted and recreated if the interval differs

#### Configuration
The job interval is controlled by the `zabbix_import_interval` setting in the plugin configuration, which can be configured through the NetBox UI.

### SystemJobHostConfigSyncRefresh

This job periodically refreshes the synchronization status of HostConfig objects to ensure they accurately reflect the state in Zabbix.

#### Class Definition
```python
class SystemJobHostConfigSyncRefresh(AtomicJobRunner)
```

#### Key Methods

##### `run(cls, *args, **kwargs)`
Updates HostConfig objects that haven't been checked recently.

**Parameters:**
- `cutoff` (int, optional): Override the default cutoff time in minutes

**Returns:**
- `dict`: Summary containing:
  - `total`: Total number of host configs processed
  - `updated`: Number of host configs successfully updated
  - `failed`: Number of host configs that failed to update
  - `cutoff_in_minutes`: The cutoff time used for this run
  - `cutoff`: Formatted cutoff timestamp

**Raises:**
- `Exception`: If any unexpected error occurs during execution

##### `schedule(cls, interval=None)`
Schedules the system job at a recurring interval.

**Parameters:**
- `interval` (int): Interval in minutes between job executions

**Returns:**
- `Job`: Scheduled job instance

#### Configuration
The job interval is controlled by the `host_config_sync_interval` setting, and the cutoff time is controlled by `cutoff_host_config_sync` in the plugin configuration.

### SystemJobMaintenanceCleanup

This job periodically cleans up expired maintenance windows from both NetBox and Zabbix.

#### Class Definition
```python
class SystemJobMaintenanceCleanup(AtomicJobRunner)
```

#### Key Methods

##### `run(cls, *args, **kwargs)`
Deletes all expired maintenances whose end_time is less than or equal to the current time.

**Returns:**
- `dict`: Summary containing:
  - `deleted`: Number of maintenance windows successfully deleted
  - `checked`: Total number of expired maintenance windows checked
  - `timestamp`: Timestamp of when the cleanup was performed

##### `schedule(cls, interval=None)`
Schedules the system job at a recurring interval.

**Parameters:**
- `interval` (int): Interval in minutes between job executions

**Returns:**
- `Job`: Scheduled job instance

#### Configuration
The job interval is controlled by the `maintenance_cleanup_interval` setting in the plugin configuration.

## Job Registration and Scheduling

### Registry System
System jobs are registered using the `@register_system_job` decorator, which associates each job class with its interval getter function:

```python
@register_system_job(settings.get_zabbix_import_interval)
class SystemJobImportZabbixSettings(AtomicJobRunner):
    # ...
```

### Global Functions

#### `schedule_system_jobs()`
Iterates through all registered system jobs, retrieves their desired intervals, and schedules or reschedules them as needed.

#### `system_jobs_scheduled()`
Checks if all registered system jobs are currently scheduled or running.

#### `get_current_job_interval(job_cls)`
Retrieves the currently scheduled interval for a given system job class.

## Implementation Details

### AtomicJobRunner Base Class
All system jobs inherit from `AtomicJobRunner`, which provides:

1. **Transactional Execution**: All job operations occur within a database transaction, ensuring consistency
2. **Exception Propagation**: Unlike standard NetBox JobRunner, exceptions are re-raised to allow for external failure detection
3. **Automatic Rescheduling**: Periodic jobs are automatically rescheduled based on their interval setting
4. **Event Logging**: Structured event data is logged to the EventLog model when enabled

### Error Handling
Each system job implements robust error handling:
- Exceptions during execution are caught, logged, and re-raised
- Database changes are automatically rolled back on failure
- Detailed error information is preserved in job metadata

### Configuration Intervals
System job intervals are configurable through the plugin settings:
- Import interval: Controls how often Zabbix settings are imported
- Sync interval: Controls how often host configurations are checked for sync status
- Cleanup interval: Controls how often expired maintenances are cleaned up
- Cutoff time: Determines how far back to check for outdated host configurations

## Usage Examples

### Manual Job Scheduling
```python
# Schedule the import job to run every hour
SystemJobImportZabbixSettings.schedule(interval=60)

# Schedule the sync job to run every 30 minutes
SystemJobHostConfigSyncRefresh.schedule(interval=30)

# Schedule the cleanup job to run daily
SystemJobMaintenanceCleanup.schedule(interval=1440)
```

### Checking Job Status
```python
# Check if all system jobs are scheduled
if system_jobs_scheduled():
    print("All system jobs are running")
else:
    print("Some system jobs are missing")

# Get current interval for a specific job
interval = get_current_job_interval(SystemJobImportZabbixSettings)
print(f"Import job runs every {interval} minutes")
```

