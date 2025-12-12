# ProvisionAgent Job

## Overview

The `ProvisionAgent` job provisions a Zabbix host using an Agent interface. This job creates a Host Configuration using the Agent interface model and registers it in Zabbix, enabling Zabbix agent-based monitoring for NetBox devices and virtual machines.

## Class Definition

```python
class ProvisionAgent(AtomicJobRunner)
```

## Methods

### `run(cls, *args, **kwargs)`

Provisions an Agent interface in Zabbix for the given instance.

**Returns:**
- `dict`: Result of provisioning.

**Raises:**
- `Exception`: If instance is invalid or provisioning fails.

### `run_job(cls, instance, request, schedule_at=None, interval=None, immediate=False, name=None)`

Enqueues a ProvisionAgent job.

**Returns:**
- `Job`: Enqueued job instance.

### `run_now(cls, instance=None, *args, **kwargs)`

Immediately provisions an Agent interface.

**Parameters:**
- `instance` (Device|VirtualMachine, optional): Target instance.

## Usage Examples

### Provisioning an Agent Interface

```python
from netbox_zabbix.jobs.provision import ProvisionAgent
from dcim.models import Device

# Get a device to provision
device = Device.objects.get(name="web-server-01")

# Provision agent interface
job = ProvisionAgent.run_job(
    instance=device,
    request=request,
    name=f"Provision Agent for {device.name}"
)
```

### Immediate Provisioning

```python
from netbox_zabbix.jobs.provision import ProvisionAgent
from dcim.models import Device

# Get a device to provision
device = Device.objects.get(name="web-server-01")

# Provision immediately
result = ProvisionAgent.run_now(instance=device)
print(f"Provisioning result: {result['message']}")
```

## Integration with Other Components

1. **AtomicJobRunner**: Inherits transactional execution and error handling capabilities.
2. **Provisioning Functions**: Uses `provision_zabbix_host` and `ProvisionContext` for provisioning logic.
3. **NetBox Models**: Works with Device, VirtualMachine, HostConfig, and AgentInterface objects.
4. **Plugin Settings**: Uses global settings for default agent configuration.
5. **Event Logging**: Logs provisioning events to the EventLog model.

## Description

The ProvisionAgent job enables Zabbix agent-based monitoring for NetBox infrastructure. It performs the following operations:

1. Retrieves the target NetBox instance (Device or VirtualMachine)
2. Creates a HostConfig object in NetBox
3. Creates an AgentInterface object with appropriate configuration
4. Registers the new host in Zabbix with agent interface
5. Applies templates and host groups based on mapping configurations

This job is typically used when:
- Onboarding new devices that will be monitored via Zabbix agent
- Converting existing devices to agent-based monitoring
- Setting up monitoring for virtual machines with agent support
- Implementing standardized agent monitoring configurations

The job leverages mapping configurations to automatically apply appropriate templates, host groups, proxies, and other settings based on device characteristics. It ensures that all necessary Zabbix configuration is created consistently and in accordance with organizational policies.