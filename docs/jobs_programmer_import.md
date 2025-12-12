# NetBox Zabbix Plugin - Import Jobs Documentation

## Overview

Import jobs handle the transfer of data from Zabbix to NetBox, enabling NetBox to maintain current copies of Zabbix configuration objects and import existing Zabbix hosts into NetBox management. These jobs facilitate integration between existing Zabbix installations and NetBox infrastructure management.

## Import Job Classes

### ImportZabbixSettings

This job synchronizes global Zabbix entities such as templates, proxies, proxy groups, and host groups into NetBox models.

**Note:** For detailed documentation on this job including usage examples and integration details, see [ImportZabbixSettings Job](job_importzabbixsettings.md).

#### Class Definition
```python
class ImportZabbixSettings(AtomicJobRunner)
```

#### Key Methods

##### `run(cls, *args, **kwargs)`
Executes the import of Zabbix settings.

**Returns:**
- `dict`: Imported configuration summary

**Raises:**
- `Exception`: If import fails

##### `run_job(cls, user=None, schedule_at=None, interval=None, immediate=False, name=None)`
Schedules or enqueues the ImportZabbixSettings job.

**Parameters:**
- `user` (User, optional): User triggering the job
- `schedule_at` (datetime, optional): Schedule time
- `interval` (int, optional): Interval in minutes for recurring job
- `immediate` (bool, optional): Run job immediately
- `name` (str, optional): Job name

**Returns:**
- `Job`: The enqueued job instance

### ImportHost

This job imports a single Zabbix host into NetBox, creating or updating a corresponding HostConfig for a Device or VirtualMachine.

**Note:** For detailed documentation on this job including usage examples and integration details, see [ImportHost Job](job_importhost.md).

#### Class Definition
```python
class ImportHost(AtomicJobRunner)
```

#### Key Methods

##### `run(cls, *args, **kwargs)`
Imports a Zabbix host into NetBox using ImportHostContext.

**Required Parameters:**
- `content_type` (ContentType): Content type of the target object
- `id` (int): ID of the target object

**Returns:**
- `dict`: Message confirming import and imported Zabbix host data

**Raises:**
- `Exception`: If instance is invalid or import fails

##### `run_job(cls, instance, request, schedule_at=None, interval=None, immediate=False, name=None)`
Schedules an ImportHost job.

**Parameters:**
- `instance` (Device|VirtualMachine): Target instance
- `request` (HttpRequest): Triggering request
- `schedule_at` (datetime, optional): Schedule time
- `interval` (int, optional): Interval for recurring job
- `immediate` (bool, optional): Run immediately
- `name` (str, optional): Job name

**Returns:**
- `Job`: Enqueued job instance

## Implementation Details

### Import Process
Import jobs perform several operations to ensure data consistency:
1. Retrieve configuration objects from Zabbix
2. Map Zabbix objects to NetBox models
3. Create new objects for previously unknown entities
4. Update existing objects with changed information
5. Report import statistics and any errors encountered

### Data Synchronization
The import process maintains consistency through:
- Transactional execution to ensure all-or-nothing operations
- Conflict resolution for existing objects
- Proper error handling for failed imports
- Detailed logging for audit and troubleshooting

### Error Handling
Import jobs implement comprehensive error handling:
- Zabbix API communication failures are properly handled
- Partial import failures don't stop the overall process
- Detailed error information is preserved for troubleshooting
- Cleanup operations handle partially imported data

## Usage Examples

### Importing Zabbix Settings
```python
# Import Zabbix settings immediately
result = ImportZabbixSettings.run_now()
print(f"Imported {result['templates']} templates")

# Schedule recurring import
job = ImportZabbixSettings.run_job(
    user=request.user,
    interval=60,  # Every hour
    name="Hourly Zabbix Settings Import"
)
```

### Importing a Host
```python
# Import an existing Zabbix host
device = Device.objects.get(name="existing-zabbix-host")
job = ImportHost.run_job(
    instance=device,
    request=request,
    name=f"Import {device.name}"
)

# Run import immediately
result = ImportHost.run_now(instance=device)
print(f"Import result: {result['message']}")
```

## Integration with Other Components

### Relationship to Mapping System
Import jobs work closely with the mapping system by:
- Ensuring referenced Zabbix objects exist in NetBox
- Enabling template-based mapping configurations
- Supporting proxy and host group assignments

### Event Logging
When event logging is enabled, import operations generate detailed logs that can be used for:
- Audit trails of import activities
- Performance analysis
- Troubleshooting import issues
- Compliance verification