# NetBox Zabbix Plugin - TagMapping Documentation

The TagMapping in the NetBox Zabbix plugin defines how NetBox object fields are mapped to Zabbix tags for devices and virtual machines. This document explains the TagMapping's structure, fields, and usage.

## Overview

The TagMapping provides a flexible way to configure which NetBox object fields should be exported as tags in Zabbix. Separate mappings can be defined for devices and virtual machines, allowing different tagging strategies for each object type.

## Fields

| Field | Type | Description | Notes |
|-------|------|-------------|-------|
| `object_type` | CharField (max_length=20) | Type of NetBox object | Choices: 'device', 'virtualmachine'. Must be unique. |
| `selection` | JSONField | Field paths for Zabbix tags | List of field paths to use as tags |

## Field Details

### `object_type`
Specifies which type of NetBox object this mapping applies to. Valid choices are:
- `device`: Applies to NetBox Device objects
- `virtualmachine`: Applies to NetBox VirtualMachine objects

This field must be unique, meaning only one TagMapping can exist for each object type.

### `selection`
A JSON array containing field paths that specify which NetBox object attributes should be exported as Zabbix tags. Each field path is a dot-notation string that references attributes of the NetBox object.

For example:
```json
[
    "site.name",
    "role.name",
    "platform.name"
]
```

This would create Zabbix tags for the site name, role name, and platform name of each device or virtual machine.

## Methods

### `__str__()`
Returns a human-readable string representation in the format "Tag Mapping {object_type}".

### `get_absolute_url()`
Returns the canonical URL for this tag mapping within the NetBox plugin UI:
```
/plugins/netbox_zabbix/tagmappings/{pk}/
```

## Usage Examples

### Creating a Device Tag Mapping
```python
from netbox_zabbix.models import TagMapping
import json

# Create a tag mapping for devices
device_tag_mapping = TagMapping.objects.create(
    object_type='device',
    selection=[
        'site.name',
        'site.region.name',
        'role.name',
        'platform.name',
        'location.name'
    ]
)
```

### Creating a Virtual Machine Tag Mapping
```python
# Create a tag mapping for virtual machines
vm_tag_mapping = TagMapping.objects.create(
    object_type='virtualmachine',
    selection=[
        'site.name',
        'cluster.name',
        'role.name',
        'platform.name'
    ]
)
```

### Modifying an Existing Tag Mapping
```python
# Update an existing tag mapping
tag_mapping = TagMapping.objects.get(object_type='device')
tag_mapping.selection.append('tenant.name')
tag_mapping.save()
```

### Working with Tag Mappings in Code
```python
# Retrieve and use tag mappings
from netbox_zabbix.models import TagMapping

def get_device_tags(device):
    """Get Zabbix tags for a device based on its tag mapping."""
    try:
        tag_mapping = TagMapping.objects.get(object_type='device')
        tags = {}
        for field_path in tag_mapping.selection:
            # Navigate the field path to get the value
            obj = device
            for attr in field_path.split('.'):
                if obj is None:
                    break
                obj = getattr(obj, attr, None)
            if obj is not None:
                # Use the last part of the path as the tag name
                tag_name = field_path.split('.')[-1].title()
                tags[tag_name] = str(obj)
        return tags
    except TagMapping.DoesNotExist:
        return {}
```

## Integration with Other Models

TagMapping integrates with the core NetBox models:
1. **Device Model**: Device tag mappings determine which device attributes become Zabbix tags
2. **VirtualMachine Model**: Virtual machine tag mappings determine which VM attributes become Zabbix tags
3. **HostConfig Model**: Tag mappings are used when creating Zabbix host configurations

## Best Practices

1. **Selective Tagging**: Only map fields that are useful for filtering and organizing hosts in Zabbix to avoid cluttering the tag space.

2. **Consistent Naming**: Use consistent field paths across similar object types to maintain uniformity in your Zabbix environment.

3. **Hierarchical Information**: Consider including hierarchical information like region/site/tenant to enable layered filtering in Zabbix.

4. **Performance Considerations**: Be mindful of the number of tags per host, as excessive tags can impact Zabbix performance.

5. **Regular Review**: Periodically review and update tag mappings to ensure they meet evolving organizational needs.