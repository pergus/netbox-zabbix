# ValidateHost Job

## Overview

The `ValidateHost` job validates a Zabbix host configuration against a NetBox device or virtual machine. This job ensures that host configurations in Zabbix match the expected state in NetBox, helping to detect configuration drift or inconsistencies.

## Class Definition

```python
class ValidateHost(AtomicJobRunner)
```

## Methods

### `run(cls, *args, **kwargs)`

Validates the Zabbix host configuration for a given instance.

**Returns:**
- `bool`: True if validation passes.

**Raises:**
- `Exception`: If the host cannot be validated or instance is invalid.

### `run_job(cls, instance, request, schedule_at=None, interval=None, immediate=False, name=None)`

Enqueues a host validation job.

**Parameters:**
- `instance` (Device|VirtualMachine): Target instance.
- `request` (HttpRequest): HTTP request triggering the job.
- `schedule_at` (datetime, optional): Schedule time.
- `interval` (int, optional): Interval for recurring job.
- `immediate` (bool, optional): Run job immediately.
- `name` (str, optional): Job name.

**Returns:**
- `Job`: Enqueued job instance.

### `run_now(cls, instance=None, *args, **kwargs)`

Executes the validation immediately.

**Parameters:**
- `instance` (Device|VirtualMachine, optional): Target instance.

**Returns:**
- `dict`: Validation result.

## Usage Examples

### Running Validation Immediately

```python
from netbox_zabbix.jobs.validate import ValidateHost
from dcim.models import Device

# Get a device to validate
device = Device.objects.get(name="web-server-01")

# Run validation immediately
result = ValidateHost.run_now(instance=device)
print(result)
```

### Scheduling Validation Job

```python
from netbox_zabbix.jobs.validate import ValidateHost
from dcim.models import Device

# Get a device to validate
device = Device.objects.get(name="web-server-01")

# Schedule validation job
job = ValidateHost.run_job(
    instance=device,
    request=request,
    name=f"Validate host {device.name}"
)
```

## Integration with Other Components

1. **AtomicJobRunner**: Inherits transactional execution and error handling capabilities.
2. **Zabbix API**: Uses `get_host` to retrieve Zabbix host information.
3. **Zabbix Validation**: Uses `validate_zabbix_host` to compare configurations.
4. **NetBox Models**: Works with Device and VirtualMachine objects.
5. **Event Logging**: Logs validation events to the EventLog model.

## Description

The ValidateHost job is essential for maintaining synchronization between NetBox and Zabbix configurations. It performs the following operations:

1. Retrieves the target NetBox instance (Device or VirtualMachine)
2. Fetches the corresponding host from Zabbix
3. Compares the Zabbix host configuration with the expected NetBox configuration
4. Reports validation results or raises exceptions on failures

This job helps administrators identify configuration drift and ensures that monitoring configurations remain consistent with infrastructure definitions. It can be run on-demand for specific hosts or scheduled for regular validation of critical infrastructure components.