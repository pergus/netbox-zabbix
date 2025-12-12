# NetBox Zabbix Plugin - Interface Jobs Documentation

## Overview

Interface jobs manage Zabbix interfaces for existing HostConfig objects. These jobs ensure that Zabbix hosts have the correct interfaces configured to match their NetBox HostConfig definitions, handling both creation of missing interfaces and updates to existing ones.

## Interface Job Classes

### BaseZabbixInterfaceJob

This is an abstract base class that provides shared enqueue logic for Zabbix interface jobs. It serves as the foundation for both `CreateZabbixInterface` and `UpdateZabbixInterface` jobs.

**Note:** For detailed documentation on this base class including usage examples and integration details, see [BaseZabbixInterfaceJob](job_basezabbixinterfacejob.md).

#### Class Definition
```python
class BaseZabbixInterfaceJob(AtomicJobRunner)
```

#### Key Methods

##### `run_job(cls, host_config, request=None, schedule_at=None, interval=None, immediate=False, name=None, signal_id=None)`
Enqueues a Zabbix interface job for the given HostConfig.

**Parameters:**
- `host_config` (HostConfig): Target HostConfig instance
- `request` (HttpRequest, optional): HTTP request triggering the job
- `schedule_at` (datetime, optional): Schedule time
- `interval` (int, optional): Interval for recurring job
- `immediate` (bool, optional): Run job immediately
- `name` (str, optional): Job name
- `signal_id` (str, optional): Signal identifier for event correlation

**Returns:**
- `Job`: Enqueued job instance

**Raises:**
- `Exception`: If host_config is not a HostConfig instance

### CreateZabbixInterface

This job creates missing Zabbix interfaces for a HostConfig.

**Note:** For detailed documentation on this job including usage examples and integration details, see [CreateZabbixInterface Job](job_createzabbixinterface.md).

#### Class Definition
```python
class CreateZabbixInterface(BaseZabbixInterfaceJob)
```

#### Key Methods

##### `run(cls, *args, **kwargs)`
Creates or updates the Zabbix host/interface and links missing interfaces.

**Required Parameters:**
- `config_id` (int): ID of the HostConfig object

**Returns:**
- `dict`: Result of the interface creation/update

**Raises:**
- `Exception`: If the HostConfig has no associated Zabbix host

### UpdateZabbixInterface

This job updates existing Zabbix interfaces for a HostConfig.

**Note:** For detailed documentation on this job including usage examples and integration details, see [UpdateZabbixInterface Job](job_updatezabbixinterface.md).

#### Class Definition
```python
class UpdateZabbixInterface(BaseZabbixInterfaceJob)
```

#### Key Methods

##### `run(cls, *args, **kwargs)`
Updates the Zabbix host/interface and links missing interfaces.

**Required Parameters:**
- `config_id` (int): ID of the HostConfig object

**Returns:**
- `dict`: Result of the interface update

**Raises:**
- `Exception`: If the HostConfig has no associated Zabbix host

## Implementation Details

### Interface Management Process
Interface jobs perform several operations to ensure interface consistency:
1. Verify that the HostConfig has an associated Zabbix host ID
2. Update the Zabbix host configuration to match NetBox definitions
3. Link any missing Zabbix interfaces to their NetBox counterparts
4. Ensure interface consistency between NetBox and Zabbix

### Linking Mechanism
The interface linking process:
- Associates Zabbix interface IDs with NetBox interface objects
- Ensures proper correlation for future updates
- Handles cases where interfaces exist in one system but not the other
- Maintains consistency between interface configurations

### Error Handling
Interface jobs implement comprehensive error handling:
- Host validation ensures proper target objects
- Zabbix API communication failures are properly handled
- Partial interface operations don't stop the overall process
- Detailed error information is preserved for troubleshooting

## Usage Examples

### Creating Missing Interfaces
```python
# Create missing interfaces for a host
host_config = HostConfig.objects.get(name="web-server-01")
job = CreateZabbixInterface.run_job(
    host_config=host_config,
    request=request,
    name=f"Create interfaces for {host_config.name}"
)

# Run immediately
result = CreateZabbixInterface.run_now(
    config_id=host_config.id,
    user=request.user,
    request_id=request.id
)
print(f"Interface creation result: {result['message']}")
```

### Updating Existing Interfaces
```python
# Update interfaces for a host
host_config = HostConfig.objects.get(name="web-server-01")
job = UpdateZabbixInterface.run_job(
    host_config=host_config,
    request=request,
    name=f"Update interfaces for {host_config.name}"
)

# Run immediately
result = UpdateZabbixInterface.run_now(
    config_id=host_config.id,
    user=request.user,
    request_id=request.id
)
print(f"Interface update result: {result['message']}")
```

## Integration with Other Components

### Relationship to Host Management
Interface jobs complement host management operations by:
- Ensuring proper interface configuration after host creation
- Updating interfaces when host configurations change
- Handling interface-specific operations without full host updates

### Provisioning Integration
Interface jobs work with provisioning by:
- Creating interfaces as part of the provisioning process
- Updating interfaces when provisioning parameters change
- Ensuring interface consistency after initial provisioning

### Event Logging
When event logging is enabled, interface operations generate detailed logs that can be used for:
- Audit trails of interface management activities
- Troubleshooting interface configuration issues
- Performance analysis of interface operations
- Compliance verification