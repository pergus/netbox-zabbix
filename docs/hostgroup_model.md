# NetBox Zabbix Plugin - HostGroup Documentation

## Overview

The HostGroup in the NetBox Zabbix plugin represents Zabbix host groups, which are logical containers for organizing and managing hosts in the Zabbix monitoring system. This document explains the HostGroup's structure, fields, properties, methods, and usage.

## Model Definition

The HostGroup synchronizes with Zabbix host groups and maintains the relationship between NetBox and Zabbix grouping structures. Host groups in Zabbix provide a way to organize hosts logically for easier management, permission control, and applying configurations.

## Fields

| Field | Type | Description | Notes |
|-------|------|-------------|-------|
| `name` | CharField (max_length=255) | Name of the host group | Human-readable identifier |
| `groupid` | CharField (max_length=255) | Unique identifier in Zabbix | Blank/null allowed, populated during sync |
| `last_synced` | DateTimeField | Last synchronization timestamp | Blank/null allowed |

### `name`
The human-readable name of the host group as it appears in both NetBox and Zabbix. This field is required and serves as the primary identifier for the host group.

### `groupid`
The unique identifier assigned by Zabbix for this host group. This field is populated automatically when the host group is created or synchronized with Zabbix.

### `last_synced`
Timestamp indicating when the host group was last synchronized with Zabbix. This helps track the freshness of the data in NetBox compared to Zabbix.

## Methods

### `__str__()`
Returns the host group name as a human-readable string representation.

**Returns:**
- `str`: Host group name

### `get_absolute_url()`
Returns the canonical URL for this host group within the NetBox plugin UI.

**Returns:**
- `str`: Absolute URL for the host group

### `create_new_host_group()`
Creates a new host group in Zabbix with the current name and updates the `groupid` field with the Zabbix-assigned identifier.

### `update_existing_host_group()`
Updates an existing host group in Zabbix with the current name. Requires that the `groupid` field is already populated.

### `delete(*args, **kwargs)`
Attempts to delete the host group from Zabbix. If successful, also removes it from NetBox. If Zabbix deletion fails, returns a warning but still removes from NetBox.

## Usage Examples

### Creating a HostGroup
```python
from netbox_zabbix.models import HostGroup

# Create a new host group
host_group = HostGroup.objects.create(
    name="Linux Servers"
)
```

### Synchronizing with Zabbix
```python
# Create the host group in Zabbix
host_group.create_new_host_group()

# Verify the groupid was populated
print(f"Zabbix Group ID: {host_group.groupid}")
```

### Updating a HostGroup
```python
# Update the host group name
host_group = HostGroup.objects.get(name="Linux Servers")
host_group.name = "Production Linux Servers"
host_group.update_existing_host_group()
```

### Working with HostGroup Relationships
```python
# Host groups are typically used in HostConfig objects
from netbox_zabbix.models import HostConfig, HostGroup

# Assign host groups to a host configuration
host_config = HostConfig.objects.get(name="web-server-01")
linux_group = HostGroup.objects.get(name="Linux Servers")
database_group = HostGroup.objects.get(name="Database Servers")

# Add host groups to the host configuration
host_config.host_groups.add(linux_group, database_group)
```

## Integration with Other Models

HostGroup integrates with several other models in the plugin:

1. **HostConfig Model**: Host configurations can be assigned to multiple host groups for organizational purposes.
2. **Mapping Models**: DeviceMapping and VMMapping can specify host groups for matching hosts.
3. **Maintenance Model**: Maintenance windows can target specific host groups.

## Description

The HostGroup model provides synchronization capabilities between NetBox and Zabbix host group structures. It maintains the relationship between organizational units in both systems, enabling consistent grouping and management of monitored hosts.

Key features include:
- Automatic synchronization with Zabbix host groups
- Bidirectional management of host group membership
- Robust error handling for Zabbix API operations
- Integration with HostConfig, Mapping, and Maintenance models
- Preservation of Zabbix identifiers for recovery operations