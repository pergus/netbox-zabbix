# AgentInterface Model

## Overview

The `AgentInterface` model represents a Zabbix agent interface linked to a HostConfig, defining how a monitored host communicates with Zabbix via the Zabbix agent protocol.

## Model Definition

AgentInterface extends the BaseInterface abstract model and adds fields specific to Zabbix agent monitoring. It defines the configuration for Zabbix agent monitoring, including connection details like IP address, port, and whether this is the primary interface for the host.

## Fields

Inherits all fields from BaseInterface plus:

| Field | Type | Description | Notes |
|-------|------|-------------|-------|
| `host_config` | ForeignKey (HostConfig) | Link to the parent HostConfig | related_name="agent_interfaces" |
| `interface_type` | ForeignKey (ContentType) | Content type of the associated NetBox interface | Limited to Interface or VMInterface models |
| `interface_id` | PositiveIntegerField | ID of the associated NetBox interface |  |
| `interface` | GenericForeignKey | Generic foreign key to the NetBox interface |  |
| `ip_address` | ForeignKey (IPAddress) | Associated IP address from NetBox IPAM | related_name="agent_interface", nullable |
| `type` | IntegerField | Interface type | Choices from TypeChoices, default=AGENT |
| `port` | IntegerField | Port number used by the interface | Default=10050 |

## Methods

### `save(*args, **kwargs)`

Ensure only one main AgentInterface exists per host_config and validate the instance.

**Parameters:**
- `*args`: Positional arguments passed to the parent save method
- `**kwargs`: Keyword arguments passed to the parent save method

**Raises:**
- `ValidationError`: If the model is invalid

### `__str__()`

Return a string representation of the agent interface.

**Returns:**
- `str`: String representation of the agent interface

### `clean()`

Validate that the assigned IP address matches the interface.

**Raises:**
- `ValidationError`: If IP does not belong to the selected interface

### `get_absolute_url()`

Return the canonical URL for this agent interface within the NetBox plugin UI.

**Returns:**
- `str`: Absolute URL for the agent interface

## Usage Examples

### Creating an Agent Interface
```python
from netbox_zabbix.models import AgentInterface, HostConfig
from dcim.models import Interface
from ipam.models import IPAddress

# Get the host configuration
host_config = HostConfig.objects.get(name="z-web-server-01")

# Get the NetBox interface
netbox_interface = Interface.objects.get(name="eth0", device__name="web-server-01")

# Get the IP address
ip_address = IPAddress.objects.get(address="192.168.1.100/24")

# Create an agent interface
agent_interface = AgentInterface.objects.create(
    host_config=host_config,
    interface=netbox_interface,
    ip_address=ip_address,
    port=10050,
    useip=1,  # Use IP
    main=1    # Main interface
)
```

### Working with Agent Interface Properties
```python
# Access resolved IP address
ip_address = agent_interface.resolved_ip_address
if ip_address:
    print(f"Agent connecting on IP: {ip_address}")

# Access resolved DNS name
dns_name = agent_interface.resolved_dns_name
if dns_name:
    print(f"Agent connecting on DNS: {dns_name}")

# Check if this is the main interface
if agent_interface.main == 1:
    print("This is the main agent interface")
```

### Updating Agent Interface Configuration
```python
# Change the port
agent_interface.port = 10051
agent_interface.save()

# Change to DNS connection
agent_interface.useip = 0  # Use DNS
agent_interface.save()

# Change main interface status
agent_interface.main = 0  # Not main
agent_interface.save()
```

## Integration with Other Models

AgentInterface integrates with several other models in the plugin:

1. **HostConfig Model**: AgentInterface instances are associated with specific HostConfig objects through a foreign key relationship.

2. **BaseInterface Model**: AgentInterface inherits from BaseInterface, sharing common interface functionality.

3. **NetBox Interface Model**: AgentInterface links to NetBox Interface objects for device/VLAN information.

4. **NetBox VMInterface Model**: AgentInterface can also link to NetBox VMInterface objects for virtual machine interfaces.

5. **NetBox IPAddress Model**: AgentInterface links to NetBox IPAddress objects for IP connectivity.

## Description

AgentInterface objects define the configuration for Zabbix agent monitoring, including connection details like IP address, port, and whether this is the primary interface for the host.

Key features:
- Links to a specific HostConfig object
- Associates with NetBox Interface or VMInterface objects through generic foreign keys
- Can reference a specific IP address from NetBox IPAM
- Configures agent communication port (default 10050)
- Supports designation as the main interface for the host
- Ensures only one main agent interface exists per host configuration
- Validates that assigned IP addresses belong to the selected interface

The model automatically handles ensuring that only one agent interface is marked as "main" per host configuration, updating other interfaces if needed when changing the main interface designation. This prevents configuration conflicts in Zabbix where multiple main interfaces could cause monitoring issues.