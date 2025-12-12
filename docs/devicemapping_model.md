# DeviceMapping Model

## Overview

The `DeviceMapping` model defines how NetBox Device objects should be mapped to Zabbix host configurations, including templates, host groups, proxies, and filtering criteria.

## Model Definition

DeviceMapping inherits from the base `Mapping` model and provides specific functionality for mapping NetBox Device objects to Zabbix configurations.

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
| `roles` | ManyToManyField (DeviceRole) | Restrict mapping to specific device roles | Filter by role |
| `platforms` | ManyToManyField (Platform) | Restrict mapping to specific platforms | Filter by platform |

## Methods

### `get_matching_filter(cls, device, interface_type=InterfaceTypeChoices.Any)`

Return the most specific DeviceMapping that matches a device based on its characteristics.

**Parameters:**
- `device` (Device): Device instance to match
- `interface_type` (int): Interface type to filter by (default: Any)

**Returns:**
- `DeviceMapping`: Matching mapping object

### `get_matching_devices(self)`

Return queryset of Devices that match this mapping, excluding devices already covered by more specific mappings.

**Returns:**
- `QuerySet`: Matching Device instances

### `get_absolute_url(self)`

Return URL for the device mapping detail page in the NetBox UI.

**Returns:**
- `str`: Absolute URL for the device mapping

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
# Create a default mapping that applies to all devices not matched by specific mappings
default_device_mapping = DeviceMapping.objects.create(
    name="Default Device Mapping",
    description="Default mapping for all unmatched devices",
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

DeviceMapping integrates with several other models in the plugin:

1. **HostConfig Model**: Device mappings determine which Zabbix configuration is applied to Device objects when they are provisioned for monitoring.

2. **Template Model**: Templates are assigned to devices through device mappings.

3. **HostGroup Model**: Host groups are assigned to devices through device mappings.

4. **Proxy/ProxyGroup Models**: Proxies or proxy groups can be specified for devices through device mappings.

## Description

DeviceMapping objects allow administrators to define rules for automatically configuring Zabbix monitoring for NetBox devices based on their characteristics. More specific mappings (those with more filter criteria) take precedence over less specific ones.

Mappings can filter devices by:
- Site
- Role
- Platform

And can assign:
- Templates
- Host groups
- Proxy or proxy group
- Interface type restrictions

When a device matches multiple mappings, the most specific one (with the most restrictive filters) is applied. A default mapping should always exist to catch devices that don't match any specific mapping.