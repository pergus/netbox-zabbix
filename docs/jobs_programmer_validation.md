# NetBox Zabbix Plugin - Validation Jobs Documentation

## Overview

Validation jobs verify the synchronization status between NetBox HostConfig objects and their corresponding Zabbix hosts. These jobs ensure that monitoring configurations remain consistent and help identify configuration drift that might impact monitoring effectiveness.

## Validation Job Classes

### ValidateHost

This job validates a Zabbix host configuration against a NetBox device or virtual machine.

**Note:** For detailed documentation on this job including usage examples and integration details, see [ValidateHost Job](job_validatehost.md).

#### Class Definition
```python
class ValidateHost(AtomicJobRunner)
```

#### Key Methods

##### `run(cls, *args, **kwargs)`
Validates the Zabbix host configuration for a given instance.

**Required Parameters:**
- `content_type` (ContentType): Content type of the target object
- `id` (int): ID of the target object

**Returns:**
- `bool`: True if validation passes

**Raises:**
- `Exception`: If the host cannot be validated or instance is invalid

##### `run_job(cls, instance, request, schedule_at=None, interval=None, immediate=False, name=None)`
Enqueues a host validation job.

**Parameters:**
- `instance` (Device|VirtualMachine): Target instance
- `request` (HttpRequest): HTTP request triggering the job
- `schedule_at` (datetime, optional): Schedule time
- `interval` (int, optional): Interval for recurring job
- `immediate` (bool, optional): Run job immediately
- `name` (str, optional): Job name

**Returns:**
- `Job`: Enqueued job instance

##### `run_now(cls, instance=None, *args, **kwargs)`
Executes the validation immediately.

**Parameters:**
- `instance` (Device|VirtualMachine, optional): Target instance

**Returns:**
- `dict`: Validation result

## Implementation Details

### Validation Process
The validation job performs several checks to ensure consistency:
1. Retrieves the target NetBox instance (Device or VirtualMachine)
2. Fetches the corresponding host from Zabbix
3. Compares Zabbix host configuration with NetBox definitions
4. Reports validation results or raises exceptions on failures

### Error Handling
Validation jobs implement comprehensive error handling:
- Invalid instances are detected and reported
- Zabbix API communication failures are properly handled
- Detailed error information is preserved for troubleshooting
- Validation failures don't stop the overall job execution

## Usage Examples

### Running Validation
```python
# Validate a specific host
device = Device.objects.get(name="web-server-01")
job = ValidateHost.run_job(
    instance=device,
    request=request,
    name=f"Validate {device.name}"
)

# Run validation immediately
result = ValidateHost.run_now(instance=device)
if result:
    print("Validation passed")
else:
    print("Validation failed")
```

## Integration with Other Components

### Relationship to Host Management
Validation jobs complement host management operations by:
- Verifying that created hosts match NetBox configurations
- Confirming that updated hosts reflect recent changes
- Detecting configuration drift that might require updates

### Event Logging
When event logging is enabled, validation operations generate detailed logs that can be used for:
- Audit trails of validation activities
- Compliance verification
- Troubleshooting validation issues