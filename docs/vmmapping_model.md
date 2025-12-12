# VMMapping Model

## Overview

The `VMMapping` model defines how NetBox VirtualMachine objects should be mapped to Zabbix host configurations, including templates, host groups, proxies, and filtering criteria.

## Model Definition

VMMapping inherits from the base `Mapping` model and provides specific functionality for mapping NetBox VirtualMachine objects to Zabbix configurations.

## Fields

Inherits all fields from the base `Mapping` model:

| Field | Type | Description | Notes |
|-------|------|-------------|-------|
| `name` | CharField (max_length=255) | Name of the mapping | Human-readable identifier |
| `description` | TextField | Optional description | May be blank |
| `default` | BooleanField | Whether this is the default mapping | Only one default mapping allowed |
| `host_groups` | ManyToManyField (HostGroup) | Assigned Host Groups | Used for matching hosts |
| `templates` | ManyToManyField (Template) | Assigned Templates | Multiple templates can be selected |
| `proxy` | ForeignKey (Proxy) | Assigned Proxy | Optional proxy for matching hosts |
| `proxy_group` | ForeignKey (ProxyGroup) | Assigned Proxy Group | Optional proxy group for matching hosts |
| `interface_type` | IntegerField | Limit mapping to specific interface types | Default: Any. Options: Any (0), Agent (1), SNMP (2) |
| `sites` | ManyToManyField (Site) | Restrict mapping to specific sites | Filter by site |
| `roles` | ManyToManyField (DeviceRole) | Restrict mapping to specific VM roles | Filter by role |
| `platforms` | ManyToManyField (Platform) | Restrict mapping to specific platforms | Filter by platform |

## Methods

### `get_matching_filter(cls, virtual_machine, interface_type=InterfaceTypeChoices.Any)`

Return the most specific VMMapping that matches a virtual machine based on its characteristics.

**Parameters:**
- `virtual_machine` (VirtualMachine): VM instance to match
- `interface_type` (int): Interface type to filter by (default: Any)

**Returns:**
- `VMMapping`: Matching mapping object

### `get_matching_virtual_machines(self)`

Return queryset of VirtualMachines that match this mapping, excluding VMs already covered by more specific mappings.

**Returns:**
- `QuerySet`: Matching VirtualMachine instances

### `get_absolute_url(self)`

Return URL for the VM mapping detail page in the NetBox UI.

**Returns:**
- `str`: Absolute URL for the VM mapping

## Usage Examples

### Creating a Basic VM Mapping
```python
from netbox_zabbix.models import VMMapping, HostGroup, Template

# Create a basic VM mapping
vm_mapping = VMMapping.objects.create(
    name="Linux VMs",
    description="Mapping for Linux-based virtual machines",
    default=False
)

# Add host groups and templates
linux_host_group = HostGroup.objects.get(name="Linux Servers")
generic_template = Template.objects.get(name="Template OS Linux by Zabbix agent")

vm_mapping.host_groups.add(linux_host_group)
vm_mapping.templates.add(generic_template)
```

### Creating a Filtered VM Mapping
```python
from dcim.models import Site
from virtualization.models import ClusterType, Platform

# Create a mapping for specific sites and platforms
filtered_mapping = VMMapping.objects.create(
    name="Production Linux VMs",
    description="Linux VMs in production environment"
)

# Add filters
production_site = Site.objects.get(name="Production DC")
linux_platform = Platform.objects.get(name="Ubuntu 20.04")

filtered_mapping.sites.add(production_site)
filtered_mapping.platforms.add(linux_platform)
```

### Creating a Default Mapping
```python
# Create a default mapping that applies to all VMs not matched by specific mappings
default_vm_mapping = VMMapping.objects.create(
    name="Default VM Mapping",
    description="Default mapping for all unmatched VMs",
    default=True
)
```

### Finding Matching Mappings
```python
from virtualization.models import VirtualMachine
from netbox_zabbix.models import VMMapping

# Find the appropriate mapping for a VM
vm = VirtualMachine.objects.get(name="web-vm-01")
matching_mapping = VMMapping.get_matching_filter(vm)

# Get all VMs that match a specific mapping
vms = matching_mapping.get_matching_virtual_machines()
```

## Integration with Other Models

VMMapping integrates with several other models in the plugin:

1. **HostConfig Model**: VM mappings determine which Zabbix configuration is applied to VirtualMachine objects when they are provisioned for monitoring.

2. **Template Model**: Templates are assigned to VMs through VM mappings.

3. **HostGroup Model**: Host groups are assigned to VMs through VM mappings.

4. **Proxy/ProxyGroup Models**: Proxies or proxy groups can be specified for VMs through VM mappings.

## Description

VMMapping objects allow administrators to define rules for automatically configuring Zabbix monitoring for NetBox virtual machines based on their characteristics. More specific mappings (those with more filter criteria) take precedence over less specific ones.

Mappings can filter virtual machines by:
- Site
- Role
- Platform

And can assign:
- Templates
- Host groups
- Proxy or proxy group
- Interface type restrictions

When a virtual machine matches multiple mappings, the most specific one (with the most restrictive filters) is applied. A default mapping should always exist to catch virtual machines that don't match any specific mapping.