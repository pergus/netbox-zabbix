# NetBox Zabbix Plugin - Template Documentation

The Template in the NetBox Zabbix plugin represents Zabbix templates that can be applied to hosts for monitoring configuration. This document explains the Template's structure, fields, relationships, and usage.

## Overview

The Template model synchronizes with Zabbix templates and maintains relationships between templates in both NetBox and Zabbix systems. Templates in Zabbix define the monitoring configuration that can be applied to multiple hosts.

## Fields

| Field | Type | Description | Notes |
|-------|------|-------------|-------|
| `name` | CharField (max_length=255) | Name of the Zabbix template | Human-readable identifier |
| `templateid` | CharField (max_length=255) | Unique identifier in Zabbix | Zabbix internal template ID |
| `last_synced` | DateTimeField | Last synchronization timestamp | Nullable, tracks sync status |
| `interface_type` | IntegerField | Required interface type | Default: `Any` (0). Options: `Any` (0), `Agent` (1), `SNMP` (2) |

## Relationships

| Relationship | Type | Description | Notes |
|--------------|------|-------------|-------|
| `parents` | ManyToManyField (self) | Parent templates (linked as children) | Asymmetrical, blank allowed |
| `children` | RelatedManager | Child templates (reverse of parents) | Automatically created |
| `dependencies` | ManyToManyField (self) | Template dependencies | Asymmetrical, blank allowed |
| `dependents` | RelatedManager | Dependent templates (reverse of dependencies) | Automatically created |

## Interface Type Choices

The `interface_type` field determines what kind of interface is required for hosts using this template:

- `Any` (0): Template can be applied to hosts with any interface type
- `Agent` (1): Template requires a Zabbix agent interface
- `SNMP` (2): Template requires an SNMP interface

## Methods

### `__str__()`
Returns the template name as a human-readable string representation.

### `get_absolute_url()`
Returns the canonical URL for this template within the NetBox plugin UI:
```
/plugins/netbox_zabbix/templates/{pk}/
```

## Usage Examples

### Creating a Template Entry
```python
from netbox_zabbix.models import Template

# Create a new template entry
template = Template.objects.create(
    name="Template OS Linux by Zabbix agent",
    templateid="10001",
    interface_type=1  # Agent interface required
)
```

### Working with Template Relationships
```python
# Create parent-child relationship
parent_template = Template.objects.get(name="Template App HTTP")
child_template = Template.objects.get(name="Template App HTTP Service")

# Add child relationship
parent_template.children.add(child_template)

# Create dependency relationship
dependent_template = Template.objects.get(name="Template App Database")
source_template = Template.objects.get(name="Template OS Linux")

# Add dependency
dependent_template.dependencies.add(source_template)
```

### Filtering Templates by Interface Type
```python
from netbox_zabbix.models import Template, InterfaceTypeChoices

# Get all templates that require Agent interface
agent_templates = Template.objects.filter(
    interface_type=InterfaceTypeChoices.Agent
)

# Get all templates that work with any interface
any_templates = Template.objects.filter(
    interface_type=InterfaceTypeChoices.Any
)
```

## Integration with Other Models

Templates are integrated with several other models in the plugin:

1. **Mapping Models**: Templates are referenced in DeviceMapping and VMMapping objects to determine which templates should be applied to specific hosts.

2. **HostConfig Model**: Templates are assigned to HostConfig objects to define the monitoring configuration for individual hosts.

3. **Synchronization**: Templates are synchronized with Zabbix to ensure that template information is consistent between both systems.

