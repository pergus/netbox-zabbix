# ProvisionSNMP Job

## Overview

The `ProvisionSNMP` job provisions a Zabbix host using an SNMP interface. This job creates a Host configuration using the SNMP interface model and registers it in Zabbix, enabling SNMP-based monitoring for NetBox devices and virtual machines.

## Class Definition

```python
class ProvisionSNMP(AtomicJobRunner)
```

## Methods

### `run(cls, *args, **kwargs)`

Provisions an SNMP interface in Zabbix for the given instance.

**Returns:**
- `dict`: Result of provisioning.

**Raises:**
- `Exception`: If instance is invalid or provisioning fails.

### `run_job(cls, instance, request, schedule_at=None, interval=None, immediate=False, name=None)`

Enqueues a ProvisionSNMP job.

**Returns:**
- `Job`: Enqueued job instance.

### `run_now(cls, instance=None, *args, **kwargs)`

Immediately provisions an SNMP interface.

**Parameters:**
- `instance` (Device|VirtualMachine, optional): Target instance.

## Usage Examples

### Provisioning an SNMP Interface

```python
from netbox_zabbix.jobs.provision import ProvisionSNMP
from dcim.models import Device

# Get a device to provision
device = Device.objects.get(name="network-switch-01")

# Provision SNMP interface
job = ProvisionSNMP.run_job(
    instance=device,
    request=request,
    name=f"Provision SNMP for {device.name}"
)
```

### Immediate Provisioning with Custom Settings

```python
from netbox_zabbix.jobs.provision import ProvisionSNMP
from dcim.models import Device

# Get a device to provision
device = Device.objects.get(name="network-switch-01")

# Provision immediately with custom SNMP settings
result = ProvisionSNMP.run_now(instance=device)
print(f"Provisioning result: {result['message']}")
```

## Integration with Other Components

1. **AtomicJobRunner**: Inherits transactional execution and error handling capabilities.
2. **Provisioning Functions**: Uses `provision_zabbix_host` and `ProvisionContext` for provisioning logic.
3. **NetBox Models**: Works with Device, VirtualMachine, HostConfig, and SNMPInterface objects.
4. **Plugin Settings**: Uses global settings for default SNMP configuration.
5. **Event Logging**: Logs provisioning events to the EventLog model.

## Description

The ProvisionSNMP job enables SNMP-based monitoring for NetBox infrastructure. It performs the following operations:

1. Retrieves the target NetBox instance (Device or VirtualMachine)
2. Creates a HostConfig object in NetBox
3. Creates an SNMPInterface object with appropriate configuration
4. Registers the new host in Zabbix with SNMP interface
5. Applies templates and host groups based on mapping configurations

This job is typically used when:
- Onboarding network devices that will be monitored via SNMP
- Converting existing devices to SNMP-based monitoring
- Setting up monitoring for infrastructure without agent support
- Implementing standardized SNMP monitoring configurations

The job leverages mapping configurations to automatically apply appropriate templates, host groups, proxies, and other settings based on device characteristics. It uses global plugin settings to configure default SNMP parameters such as security names, authentication protocols, and privacy settings.

Key SNMP configuration parameters supported:
- SNMP version (v1, v2c, v3)
- Security levels (noAuthNoPriv, authNoPriv, authPriv)
- Authentication protocols (MD5, SHA1, SHA224, SHA256, SHA384, SHA512)
- Privacy protocols (DES, AES128, AES192, AES256)
- Context names for SNMPv3
- Bulk operation settings for improved performance