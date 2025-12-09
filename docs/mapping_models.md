# NetBox Zabbix Plugin - Mapping Documentation

The Mapping in the NetBox Zabbix plugin define how NetBox objects (devices and virtual machines) are mapped to Zabbix monitoring configurations. This document explains the Mapping, DeviceMapping, and VMMapping's structure, fields, and usage.

## Overview

The Mapping provide a flexible system for defining how NetBox objects should be configured in Zabbix. The base `Mapping`  defines common configuration elements, while `DeviceMapping` and `VMMapping` inherit from it to provide object-specific functionality.

## Base Mapping Fields

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

## DeviceMapping

The DeviceMapping inherits from the base Mapping  and provides device-specific functionality for matching NetBox Device objects to Zabbix configurations.

### Methods

#### `get_matching_filter(cls, device, interface_type=InterfaceTypeChoices.Any)`
Class method that returns the most specific DeviceMapping that matches a given device based on site, role, and platform filters.

#### `get_matching_devices(self)`
Returns a queryset of Device objects that match this mapping, excluding devices already covered by more specific mappings.

#### `get_absolute_url(self)`
Returns the canonical URL for this device mapping within the NetBox plugin UI:
```
/plugins/netbox_zabbix/devicemappings/{pk}/
```

## VMMapping

The VMMapping inherits from the base Mapping model and provides virtual machine-specific functionality for matching NetBox VirtualMachine objects to Zabbix configurations.

### Methods

#### `get_matching_filter(cls, virtual_machine, interface_type=InterfaceTypeChoices.Any)`
Class method that returns the most specific VMMapping that matches a given virtual machine based on site, role, and platform filters.

#### `get_matching_virtual_machines(self)`
Returns a queryset of VirtualMachine objects that match this mapping, excluding VMs already covered by more specific mappings.

#### `get_absolute_url(self)`
Returns the canonical URL for this VM mapping within the NetBox plugin UI:
```
/plugins/netbox_zabbix/vmmappings/{pk}/
```

## Field Details

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

## Best Practices

1. **Specificity Ordering**: Create more specific mappings before general ones, as the system selects the most specific match.

2. **Default Mappings**: Always ensure you have default mappings configured to handle devices/VMs that don't match any specific mappings.

3. **Descriptive Names**: Use clear, descriptive names for mappings to facilitate management and troubleshooting.

4. **Filter Strategy**: Use filters judiciously to avoid overly complex matching logic that's hard to maintain.

5. **Regular Review**: Periodically review mappings to ensure they align with current infrastructure organization.