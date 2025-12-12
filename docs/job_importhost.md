# ImportHost Job

## Overview

The `ImportHost` job imports a single Zabbix host into NetBox, creating or updating a corresponding HostConfig for a Device or VirtualMachine. This job enables administrators to bring existing Zabbix hosts under NetBox management.

## Class Definition

```python
class ImportHost(AtomicJobRunner)
```

## Methods

### `run(cls, *args, **kwargs)`

Imports a Zabbix host into NetBox using ImportHostContext.

**Returns:**
- `dict`: Message confirming import and imported Zabbix host data.

**Raises:**
- `Exception`: If instance is invalid or import fails.

### `run_job(cls, instance, request, schedule_at=None, interval=None, immediate=False, name=None)`

Schedules an ImportHost job.

**Parameters:**
- `instance` (Device|VirtualMachine): Target instance.
- `request` (HttpRequest): Triggering request.
- `schedule_at` (datetime, optional): Schedule time.
- `interval` (int, optional): Interval for recurring job.
- `immediate` (bool, optional): Run immediately.
- `name` (str, optional): Job name.

**Returns:**
- `Job`: Enqueued job instance.

## Usage Examples

### Importing a Host

```python
from netbox_zabbix.jobs.imports import ImportHost
from dcim.models import Device

# Get a device to import
device = Device.objects.get(name="existing-zabbix-host")

# Import the host from Zabbix
job = ImportHost.run_job(
    instance=device,
    request=request,
    name=f"Import {device.name} from Zabbix"
)
```

### Running Import Immediately

```python
from netbox_zabbix.jobs.imports import ImportHost
from dcim.models import Device

# Get a device to import
device = Device.objects.get(name="existing-zabbix-host")

# Run import immediately
result = ImportHost.run_now(instance=device)
print(f"Imported host: {result['message']}")
```

## Integration with Other Components

1. **AtomicJobRunner**: Inherits transactional execution and error handling capabilities.
2. **Zabbix API**: Uses `get_host` to retrieve Zabbix host information.
3. **Import Functions**: Uses `import_zabbix_host` and `ImportHostContext` for import logic.
4. **NetBox Models**: Works with Device, VirtualMachine, and HostConfig objects.
5. **Event Logging**: Logs import events to the EventLog model.

## Description

The ImportHost job facilitates the migration of existing Zabbix hosts into NetBox management. It performs the following operations:

1. Retrieves the target NetBox instance (Device or VirtualMachine)
2. Fetches the corresponding host from Zabbix
3. Creates or updates a HostConfig object in NetBox
4. Associates Zabbix interfaces with NetBox interfaces
5. Establishes the link between NetBox objects and Zabbix hosts

This job is particularly useful when:
- Bringing existing Zabbix-monitored infrastructure under NetBox management
- Recovering from configuration issues by re-importing Zabbix data
- Synchronizing NetBox with changes made directly in Zabbix
- Onboarding new devices that were manually added to Zabbix

The job ensures that all relevant Zabbix host configuration is captured in NetBox, including interfaces, templates, host groups, and monitoring settings.