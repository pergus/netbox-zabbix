# NetBox Zabbix Plugin - Template Documentation

## Overview

The Template in the NetBox Zabbix plugin represents Zabbix templates that can be applied to hosts for monitoring configuration. This document explains the Template's structure, fields, properties, methods, and usage.

## Model Definition

The Template model synchronizes with Zabbix templates and maintains relationships between templates in both NetBox and Zabbix systems. Templates in Zabbix define the monitoring configuration that can be applied to multiple hosts.

## Fields

| Field | Type | Description | Notes |
|-------|------|-------------|-------|
| `name` | CharField (max_length=255) | Name of the Zabbix template | Human-readable identifier |
| `templateid` | CharField (max_length=255) | Unique identifier in Zabbix | Zabbix internal template ID |
| `last_synced` | DateTimeField | Last synchronization timestamp | Nullable, tracks sync status |
| `interface_type` | IntegerField | Required interface type | Default: `Any` (0). Options: `Any` (0), `Agent` (1), `SNMP` (2) |

### `name`
The human-readable name of the Zabbix template as it appears in both NetBox and Zabbix. This field serves as the primary identifier for the template.

### `templateid`
The unique identifier assigned by Zabbix for this template. This field is populated automatically when the template is created or synchronized with Zabbix.

### `last_synced`
Timestamp indicating when the template was last synchronized with Zabbix. This helps track the freshness of the data in NetBox compared to Zabbix.

### `interface_type`
Determines what kind of interface is required for hosts using this template:
- `Any` (0): Template can be applied to hosts with any interface type
- `Agent` (1): Template requires a Zabbix agent interface
- `SNMP` (2): Template requires an SNMP interface

### Template Relationships
Templates can have complex relationships with other templates:

#### `parents`
Many-to-many relationship to other Template objects representing parent templates (linked as children). This is asymmetrical, meaning if Template A is a parent of Template B, Template B is not automatically a parent of Template A.

#### `children`
Related manager for child templates (reverse of parents). This is automatically created by Django and provides access to templates that have this template as their parent.

#### `dependencies`
Many-to-many relationship to other Template objects representing template dependencies. This is asymmetrical, meaning dependencies are directional.

#### `dependents`
Related manager for dependent templates (reverse of dependencies). This is automatically created by Django and provides access to templates that depend on this template.

## Methods

### `__str__()`
Returns the template name as a human-readable string representation.

**Returns:**
- `str`: Template name

### `get_absolute_url()`
Returns the canonical URL for this template within the NetBox plugin UI.

**Returns:**
- `str`: Absolute URL for the template

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

## Description

The Template model provides synchronization capabilities between NetBox and Zabbix template structures. It maintains the relationship between monitoring configurations in both systems, enabling consistent template application and management.

Key features include:
- Automatic synchronization with Zabbix templates
- Support for template hierarchies through parent-child relationships
- Dependency management between templates
- Interface type requirements for proper template-host matching
- Integration with Mapping and HostConfig models
- Preservation of Zabbix identifiers for recovery operations