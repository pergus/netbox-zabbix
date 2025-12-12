# BaseInterface Model

## Overview

The `BaseInterface` model is an abstract base class that defines common fields and functionality for both AgentInterface and SNMPInterface models.

## Model Definition

BaseInterface is an abstract Django model that provides shared functionality for both agent and SNMP interfaces. It is an abstract model, meaning no database table is created for it directly. Instead, it serves as a parent class for AgentInterface and SNMPInterface models.

## Fields

| Field | Type | Description | Notes |
|-------|------|-------------|-------|
| `name` | CharField (max_length=255) | Name for the interface in NetBox | Required |
| `hostid` | IntegerField | Zabbix Host ID | Collected from Zabbix, nullable |
| `interfaceid` | IntegerField | Zabbix Interface ID | Collected from Zabbix, nullable |
| `useip` | IntegerField | Whether connection should be made via IP or DNS | Choices from UseIPChoices, default=IP |
| `main` | IntegerField | Whether the interface is used as default on the host | Choices from MainChoices, default=YES |

## Properties

### `resolved_dns_name`

Return DNS name for this interface based on the plugin IP assignment method.

**Returns:**
- `str` or `None`: DNS name if available

### `resolved_ip_address`

Return IP address for this interface based on the plugin IP assignment method.

**Returns:**
- `IPAddress` or `None`: IP address object if available

## Methods

### `clean()`

Validate that the assigned IP address matches the interface.

**Raises:**
- `ValidationError`: If IP does not belong to the selected interface

### `__str__()`

Return a string representation of the interface.

**Returns:**
- `str`: String representation of the interface

## Usage Examples

### Accessing Interface Properties
```python
from netbox_zabbix.models import AgentInterface

# Get an agent interface
agent_interface = AgentInterface.objects.get(name="eth0")

# Access resolved IP address
ip_address = agent_interface.resolved_ip_address
if ip_address:
    print(f"Interface IP: {ip_address}")

# Access resolved DNS name
dns_name = agent_interface.resolved_dns_name
if dns_name:
    print(f"Interface DNS: {dns_name}")
```

### Checking Interface Configuration
```python
# Check if interface uses IP or DNS
if agent_interface.useip == 1:  # Assuming 1 means use IP
    print(f"Connecting via IP: {agent_interface.resolved_ip_address}")
else:
    print(f"Connecting via DNS: {agent_interface.resolved_dns_name}")

# Check if interface is main
if agent_interface.main == 1:  # Assuming 1 means main interface
    print("This is the main interface")
```

## Integration with Other Models

BaseInterface integrates with several other models in the plugin:

1. **HostConfig Model**: BaseInterface instances are associated with specific HostConfig objects through a foreign key relationship.

2. **AgentInterface Model**: Inherits from BaseInterface and adds agent-specific fields.

3. **SNMPInterface Model**: Inherits from BaseInterface and adds SNMP-specific fields.

4. **NetBox Interface Model**: Interfaces are linked to NetBox Interface objects for device/VLAN information.

5. **NetBox IPAddress Model**: IP addresses are linked to NetBox IPAddress objects for IP connectivity.

## Description

BaseInterface provides shared functionality for both agent and SNMP interfaces, including connection settings and IP/DNS resolution logic.

The model handles:
- Interface naming within NetBox
- Storage of Zabbix identifiers (hostid, interfaceid)
- Connection method configuration (IP vs DNS)
- Primary interface designation
- IP address and DNS name resolution based on plugin settings
- Validation of IP address assignments

This abstraction allows both AgentInterface and SNMPInterface to share common functionality while having their own specific fields and behaviors. The abstract nature of this model ensures that only concrete implementations (AgentInterface and SNMPInterface) are stored in the database.