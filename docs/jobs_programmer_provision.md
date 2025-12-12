# NetBox Zabbix Plugin - Provisioning Jobs Documentation

## Overview

Provisioning jobs create new Zabbix monitoring configurations for NetBox devices and virtual machines. These jobs enable Zabbix agent-based and SNMP-based monitoring by establishing the necessary host configurations and interfaces in Zabbix.

## Provisioning Job Classes

### ProvisionAgent

This job provisions a Zabbix host using an Agent interface. It creates a Host Configuration using the Agent interface model and registers it in Zabbix.

**Note:** For detailed documentation on this job including usage examples and integration details, see [ProvisionAgent Job](job_provisionagent.md).

#### Class Definition
```python
class ProvisionAgent(AtomicJobRunner)
```

#### Key Methods

##### `run(cls, *args, **kwargs)`
Provisions an Agent interface in Zabbix for the given instance.

**Required Parameters:**
- `content_type` (ContentType): Content type of the target object
- `id` (int): ID of the target object

**Returns:**
- `dict`: Result of provisioning

**Raises:**
- `Exception`: If instance is invalid or provisioning fails

##### `run_job(cls, instance, request, schedule_at=None, interval=None, immediate=False, name=None)`
Enqueues a ProvisionAgent job.

**Parameters:**
- `instance` (Device|VirtualMachine): Target instance
- `request` (HttpRequest): Triggering request
- `schedule_at` (datetime, optional): Schedule time
- `interval` (int, optional): Interval for recurring job
- `immediate` (bool, optional): Run immediately
- `name` (str, optional): Job name

**Returns:**
- `Job`: Enqueued job instance

##### `run_now(cls, instance=None, *args, **kwargs)`
Immediately provisions an Agent interface.

**Parameters:**
- `instance` (Device|VirtualMachine, optional): Target instance

**Returns:**
- `dict`: Result of immediate provisioning

### ProvisionSNMP

This job provisions a Zabbix host using an SNMP interface. It creates a Host configuration using the SNMP interface model and registers it in Zabbix.

**Note:** For detailed documentation on this job including usage examples and integration details, see [ProvisionSNMP Job](job_provisionsnmp.md).

#### Class Definition
```python
class ProvisionSNMP(AtomicJobRunner)
```

#### Key Methods

##### `run(cls, *args, **kwargs)`
Provisions an SNMP interface in Zabbix for the given instance.

**Required Parameters:**
- `content_type` (ContentType): Content type of the target object
- `id` (int): ID of the target object

**Returns:**
- `dict`: Result of provisioning

**Raises:**
- `Exception`: If instance is invalid or provisioning fails

##### `run_job(cls, instance, request, schedule_at=None, interval=None, immediate=False, name=None)`
Enqueues a ProvisionSNMP job.

**Parameters:**
- `instance` (Device|VirtualMachine): Target instance
- `request` (HttpRequest): Triggering request
- `schedule_at` (datetime, optional): Schedule time
- `interval` (int, optional): Interval for recurring job
- `immediate` (bool, optional): Run immediately
- `name` (str, optional): Job name

**Returns:**
- `Job`: Enqueued job instance

##### `run_now(cls, instance=None, *args, **kwargs)`
Immediately provisions an SNMP interface.

**Parameters:**
- `instance` (Device|VirtualMachine, optional): Target instance

**Returns:**
- `dict`: Result of immediate provisioning

## Implementation Details

### Provisioning Process
Provisioning jobs perform several operations to establish monitoring:
1. Retrieve the target NetBox instance (Device or VirtualMachine)
2. Create a HostConfig object in NetBox
3. Create appropriate interface objects (AgentInterface or SNMPInterface)
4. Register the new host in Zabbix with proper configuration
5. Apply templates and host groups based on mapping configurations

### Interface Configuration
Different interface types require specific configuration:
- **Agent Interfaces**: Configure port, connection method, and main interface status
- **SNMP Interfaces**: Configure version, security settings, authentication, and privacy parameters

### Mapping Integration
Provisioning jobs leverage mapping configurations to:
- Automatically apply appropriate templates based on device characteristics
- Assign host groups for organizational purposes
- Select proxies or proxy groups for monitoring
- Configure interface types and settings

### Error Handling
Provisioning jobs implement comprehensive error handling:
- Instance validation ensures proper target objects
- Zabbix API communication failures are properly handled
- Partial provisioning failures trigger cleanup operations
- Detailed error information is preserved for troubleshooting

## Usage Examples

### Agent Provisioning
```python
# Provision agent interface for a device
device = Device.objects.get(name="web-server-01")
job = ProvisionAgent.run_job(
    instance=device,
    request=request,
    name=f"Provision Agent for {device.name}"
)

# Provision immediately
result = ProvisionAgent.run_now(instance=device)
print(f"Provisioning result: {result['message']}")
```

### SNMP Provisioning
```python
# Provision SNMP interface for a network device
device = Device.objects.get(name="network-switch-01")
job = ProvisionSNMP.run_job(
    instance=device,
    request=request,
    name=f"Provision SNMP for {device.name}"
)

# Provision immediately
result = ProvisionSNMP.run_now(instance=device)
print(f"Provisioning result: {result['message']}")
```

## Integration with Other Components

### Relationship to Mapping System
Provisioning jobs work closely with the mapping system by:
- Applying templates based on device/site/role/platform mappings
- Assigning host groups according to mapping configurations
- Selecting appropriate proxies or proxy groups
- Configuring interface types based on template requirements

### Interface Management
Provisioning creates the foundation for interface management:
- Initial interface creation establishes baseline configuration
- Subsequent interface jobs can modify existing configurations
- Interface linking ensures proper Zabbix-NetBox correlation

### Event Logging
When event logging is enabled, provisioning operations generate detailed logs that can be used for:
- Audit trails of provisioning activities
- Troubleshooting provisioning issues
- Compliance verification
- Capacity planning