# Mapping Models

## Overview

The Mapping models in the NetBox Zabbix plugin define how NetBox objects (devices and virtual machines) are mapped to Zabbix monitoring configurations. This document explains the Mapping, DeviceMapping, and VMMapping models' structure, fields, properties, methods, and usage.

## Model Definition

The Mapping models provide a flexible system for defining how NetBox objects should be configured in Zabbix. The base `Mapping` model defines common configuration elements, while `DeviceMapping` and `VMMapping` inherit from it to provide object-specific functionality.

Mappings allow administrators to automatically configure Zabbix monitoring for NetBox devices and virtual machines based on their characteristics. More specific mappings (those with more filter criteria) take precedence over less specific ones.

## Fields

| Field | Type | Description | Notes |
|-------|------|-------------|-------|
| `name` | CharField (max_length=255) | Name of the mapping | Human-readable identifier |
| `description` | TextField | Description of the mapping | Optional |
| `default` | BooleanField | Default mapping flag | Only one default mapping per type allowed |
| `host_groups` | ManyToManyField (HostGroup) | Assigned host groups | Used for matching hosts |
| `templates` | ManyToManyField (Template) | Assigned templates | Multiple templates can be selected |
| `proxy` | ForeignKey (Proxy) | Assigned proxy | Optional proxy for matching hosts |
| `proxy_group` | ForeignKey (ProxyGroup) | Assigned proxy group | Optional proxy group for matching hosts |
| `interface_type` | IntegerField | Interface type limitation | Default: Any. Options: Any (0), Agent (1), SNMP (2) |
| `sites` | ManyToManyField (Site) | Site filters | Restrict to specific sites |
| `roles` | ManyToManyField (DeviceRole) | Role filters | Restrict to specific roles |
| `platforms` | ManyToManyField (Platform) | Platform filters | Restrict to specific platforms |

### `name`
Human-readable identifier for the mapping. Should be descriptive and unique within the mapping type.

### `description`
Optional text field providing additional context about the mapping's purpose or configuration.

### `default`
Boolean flag indicating whether this is the default mapping. Only one mapping of each type (DeviceMapping, VMMapping) can be marked as default. The default mapping is used when no other mappings match a device or VM.

### `host_groups`
Many-to-many relationship to HostGroup objects. When a device or VM matches this mapping, it will be assigned to these host groups in Zabbix.

### `templates`
Many-to-many relationship to Template objects. When a device or VM matches this mapping, these templates will be applied in Zabbix.

### `proxy`
Foreign key to a Proxy object. When a device or VM matches this mapping, it will be monitored by this proxy.

### `proxy_group`
Foreign key to a ProxyGroup object. When a device or VM matches this mapping, it will be monitored by this proxy group.

### `interface_type`
Integer field limiting the mapping to specific interface types:
- `Any` (0): Matches devices/VMs with any interface type
- `Agent` (1): Matches devices/VMs with Zabbix agent interfaces
- `SNMP` (2): Matches devices/VMs with SNMP interfaces

### Filter Fields (`sites`, `roles`, `platforms`)
Many-to-many relationships that restrict which devices or VMs this mapping applies to:
- `sites`: Restricts to devices/VMs at specific sites
- `roles`: Restricts to devices/VMs with specific roles
- `platforms`: Restricts to devices/VMs running specific platforms

If any filter field is left empty, that filter is ignored (matches all values for that field).

## Properties

The base Mapping model does not define any computed properties. However, the DeviceMapping and VMMapping subclasses inherit and extend the functionality.

## Methods

### `delete(*args, **kwargs)`
Delete this mapping instance from the database.

**Raises:**
- `ValidationError`: If the mapping is marked as default, it cannot be deleted.

**Parameters:**
- `*args`: Positional arguments passed to the model delete method
- `**kwargs`: Keyword arguments passed to the model delete method

### `__str__()`
Return a human-readable string representation of the object.

**Returns:**
- `str`: Human-readable name of the object

### `get_absolute_url()`
Return the canonical URL for this object within the plugin UI.

**Returns:**
- `str`: Absolute URL as a string. Can be None if not applicable.

## DeviceMapping

The DeviceMapping inherits from the base Mapping model and provides device-specific functionality for matching NetBox Device objects to Zabbix configurations.

### Methods

#### `get_matching_filter(cls, device, interface_type=InterfaceTypeChoices.Any)`
Class method that returns the most specific DeviceMapping that matches a given device based on site, role, and platform filters.

**Parameters:**
- `device` (Device): Device instance to match
- `interface_type` (int): Interface type to filter by (default: Any)

**Returns:**
- `DeviceMapping`: Matching mapping object

#### `get_matching_devices(self)`
Returns a queryset of Device objects that match this mapping, excluding devices already covered by more specific mappings.

**Returns:**
- `QuerySet`: Matching Device instances

#### `get_absolute_url(self)`
Returns the canonical URL for this device mapping within the NetBox plugin UI.

**Returns:**
- `str`: Absolute URL for the device mapping

## VMMapping

The VMMapping inherits from the base Mapping model and provides virtual machine-specific functionality for matching NetBox VirtualMachine objects to Zabbix configurations.

### Methods

#### `get_matching_filter(cls, virtual_machine, interface_type=InterfaceTypeChoices.Any)`
Class method that returns the most specific VMMapping that matches a given virtual machine based on site, role, and platform filters.

**Parameters:**
- `virtual_machine` (VirtualMachine): VM instance to match
- `interface_type` (int): Interface type to filter by (default: Any)

**Returns:**
- `VMMapping`: Matching mapping object

#### `get_matching_virtual_machines(self)`
Returns a queryset of VirtualMachine objects that match this mapping, excluding VMs already covered by more specific mappings.

**Returns:**
- `QuerySet`: Matching VirtualMachine instances

#### `get_absolute_url(self)`
Returns the canonical URL for this VM mapping within the NetBox plugin UI.

**Returns:**
- `str`: Absolute URL for the VM mapping

## Usage Examples

### Creating a Basic Device Mapping
```python
from netbox_zabbix.models import DeviceMapping, HostGroup, Template

# Create a basic device mapping
device_mapping = DeviceMapping.objects.create(
    name="Linux Servers",
    description="Mapping for Linux-based servers",
    default=False
)

# Add host groups and templates
linux_host_group = HostGroup.objects.get(name="Linux Servers")
generic_template = Template.objects.get(name="Template OS Linux by Zabbix agent")

device_mapping.host_groups.add(linux_host_group)
device_mapping.templates.add(generic_template)
```

### Creating a Filtered Device Mapping
```python
from dcim.models import Site, DeviceRole, Platform

# Create a mapping for specific sites and roles
filtered_mapping = DeviceMapping.objects.create(
    name="Production Web Servers",
    description="Web servers in production environment"
)

# Add filters
production_site = Site.objects.get(name="Production DC")
web_role = DeviceRole.objects.get(name="Web Server")
linux_platform = Platform.objects.get(name="Ubuntu 20.04")

filtered_mapping.sites.add(production_site)
filtered_mapping.roles.add(web_role)
filtered_mapping.platforms.add(linux_platform)
```

### Creating a Default Mapping
```python
# Create a default mapping that applies to all devices/VMs not matched by specific mappings
default_device_mapping = DeviceMapping.objects.create(
    name="Default Device Mapping",
    description="Default mapping for all unmatched devices",
    default=True
)

default_vm_mapping = VMMapping.objects.create(
    name="Default VM Mapping",
    description="Default mapping for all unmatched VMs",
    default=True
)
```

### Finding Matching Mappings
```python
from dcim.models import Device
from netbox_zabbix.models import DeviceMapping

# Find the appropriate mapping for a device
device = Device.objects.get(name="web-server-01")
matching_mapping = DeviceMapping.get_matching_filter(device)

# Get all devices that match a specific mapping
devices = matching_mapping.get_matching_devices()
```

## Integration with Other Models

Mapping models integrate with several other models in the plugin:

1. **HostConfig Model**: Mappings determine which Zabbix configuration is applied to Device and VirtualMachine objects when they are provisioned for monitoring.

2. **HostGroup Model**: Mappings can assign HostGroup objects to devices/VMs for organizational purposes.

3. **Template Model**: Mappings can assign Template objects to devices/VMs for monitoring configuration.

4. **Proxy and ProxyGroup Models**: Mappings can specify which Proxy or ProxyGroup should monitor matching devices/VMs.

5. **Device and VirtualMachine Models**: Mappings filter and match against these core NetBox models based on their characteristics.

6. **Site, DeviceRole, and Platform Models**: Mappings use these models as filter criteria to determine which devices/VMs they apply to.

## Description

The Mapping models provide a powerful and flexible system for automatically configuring Zabbix monitoring based on NetBox object characteristics. This allows administrators to define rules that automatically apply appropriate monitoring configurations to devices and virtual machines without manual intervention.

Key features of the Mapping system include:

**Flexible Filtering:**
- Filter devices/VMs by site, role, and platform
- Support for multiple filter criteria combinations
- Empty filters match all values for that field
- More specific mappings take precedence over less specific ones

**Configuration Assignment:**
- Assign multiple host groups to matching objects
- Apply multiple templates for comprehensive monitoring
- Specify monitoring via proxy or proxy group
- Limit mappings to specific interface types (Agent, SNMP, or Any)

**Hierarchical Organization:**
- Base Mapping model provides common functionality
- DeviceMapping for device-specific features
- VMMapping for virtual machine-specific features
- Default mappings serve as fallback for unmatched objects

**Smart Matching Logic:**
- Automatic selection of most specific matching mapping
- Exclusion of objects covered by more specific mappings
- Support for interface type restrictions
- Efficient queryset-based matching

The system is designed to scale from simple blanket mappings to complex, highly specific configurations. Default mappings ensure that all objects receive some monitoring configuration, while specific mappings allow for granular control over monitoring setups for different types of infrastructure components.