# NetBox Zabbix Plugin - InventoryMapping Documentation

The InventoryMapping in the NetBox Zabbix plugin defines how NetBox object fields are mapped to Zabbix inventory items for devices and virtual machines. This document explains the InventoryMapping's structure, fields, and usage.

## Overview

The InventoryMapping provides a flexible way to configure which NetBox object fields should be exported as inventory items in Zabbix. Separate mappings can be defined for devices and virtual machines, allowing different inventory strategies for each object type.

## Fields

| Field | Type | Description | Notes |
|-------|------|-------------|-------|
| `object_type` | CharField (max_length=20) | Type of NetBox object | Choices: 'device', 'virtualmachine'. Must be unique. |
| `selection` | JSONField | Field paths for Zabbix inventory | Structured array defining inventory mappings |

## Field Details

### `object_type`
Specifies which type of NetBox object this mapping applies to. Valid choices are:
- `device`: Applies to NetBox Device objects
- `virtualmachine`: Applies to NetBox VirtualMachine objects

This field must be unique, meaning only one InventoryMapping can exist for each object type.

### `selection`
A JSON array with a structured format containing arrays with three elements:
1. **Display Name**: Human-readable name for the inventory field
2. **Zabbix Property**: The Zabbix inventory property name
3. **Field Paths**: Array of NetBox field paths (in order of preference)

## Methods

### `__str__()`
Returns a human-readable string representation in the format "Inventory Mapping {object_type}".

### `get_absolute_url()`
Returns the canonical URL for this inventory mapping within the NetBox plugin UI:
```
/plugins/netbox_zabbix/inventorymappings/{pk}/
```

## Usage Examples

### Creating a Device Inventory Mapping
```python
from netbox_zabbix.models import InventoryMapping

# Create an inventory mapping for devices
device_inventory_mapping = InventoryMapping.objects.create(
    object_type='device',
    selection=[
        ["Name", "name", ["name"]],
        ["Platform", "os", ["platform.name"]],
        ["Location", "location", ["location.name", "site.name"]],
        ["Latitude", "location_lat", ["location.site.latitude", "site.latitude"]],
        ["Longitude", "location_lon", ["location.site.longitude", "site.longitude"]]
    ]
)
```

### Creating a Virtual Machine Inventory Mapping
```python
# Create an inventory mapping for virtual machines
vm_inventory_mapping = InventoryMapping.objects.create(
    object_type='virtualmachine',
    selection=[
        ["Name", "name", ["name"]],
        ["Platform", "os", ["platform.name"]],
        ["Location", "location", ["location.name", "site.name"]],
        ["Latitude", "location_lat", ["location.site.latitude", "site.latitude"]],
        ["Longitude", "location_lon", ["location.site.longitude", "site.longitude"]]
    ]
)
```

### Understanding Selection Structure
The `selection` field contains arrays with three elements:
1. **Display Name**: Human-readable name for the inventory field
2. **Zabbix Property**: The Zabbix inventory property name
3. **Field Paths**: Array of NetBox field paths (in order of preference)

For example:
```json
["Name", "name", ["device.name", "vm.name"]]
```
This maps either `device.name` or `vm.name` to the Zabbix inventory `name` property, displayed as "Name".

## Integration with Other Models

InventoryMapping integrates with the core NetBox models:
1. **Device Model**: Device inventory mappings determine which device attributes become Zabbix inventory items
2. **VirtualMachine Model**: Virtual machine inventory mappings determine which VM attributes become Zabbix inventory items
3. **HostConfig Model**: Inventory mappings are used when creating Zabbix host configurations

## Best Practices

1. **Relevant Inventory Items**: Only map fields that are meaningful as inventory items in Zabbix, such as hardware specifications, location data, or asset information.

2. **Fallback Fields**: Use multiple field paths in the selection to provide fallback values when primary fields are empty.

3. **Standard Properties**: Map to standard Zabbix inventory properties when possible to leverage built-in functionality.

4. **Data Consistency**: Ensure that mapped fields contain appropriate data types for Zabbix inventory properties.

5. **Regular Updates**: Keep inventory mappings current with changes in NetBox data models or organizational requirements.