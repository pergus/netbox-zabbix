# HostConfig Model

## Overview

The HostConfig model in the NetBox Zabbix plugin represents the Zabbix host configurations that maintain the relationship between NetBox objects (devices or virtual machines) and their Zabbix monitoring configurations.

## Model Definition

The HostConfig represents a host configuration in Zabbix and maintains the relationship between NetBox objects (devices or virtual machines) and their Zabbix monitoring configurations. It serves as the bridge between NetBox infrastructure objects and their corresponding Zabbix monitoring configurations.

## Fields

| Field | Type | Description | Notes |
|-------|------|-------------|-------|
| `name` | CharField (max_length=200) | Host configuration name | Unique, auto-generated if not provided |
| `hostid` | PositiveIntegerField | Zabbix Host ID | Unique, assigned by Zabbix |
| `status` | IntegerField | Host monitoring status | Default: ENABLED. Options: ENABLED (0), DISABLED (1) |
| `in_sync` | BooleanField | Sync status with Zabbix | True if configuration matches Zabbix |
| `last_sync_update` | DateTimeField | Last sync timestamp | When sync status was last updated |
| `host_groups` | ManyToManyField (HostGroup) | Assigned host groups | Host groups in Zabbix |
| `templates` | ManyToManyField (Template) | Assigned templates | Templates applied to the host |
| `monitored_by` | IntegerField | Monitoring source | Default: ZabbixServer. Options: ZabbixServer (0), Proxy (1), ProxyGroup (2) |
| `proxy` | ForeignKey (Proxy) | Assigned proxy | Proxy for monitoring the host |
| `proxy_group` | ForeignKey (ProxyGroup) | Assigned proxy group | Proxy group for monitoring the host |
| `description` | TextField | Host description | Optional description |
| `content_type` | ForeignKey (ContentType) | Object type | Limited to Device or VirtualMachine |
| `object_id` | PositiveIntegerField | Object ID | ID of the assigned NetBox object |
| `assigned_object` | GenericForeignKey | Assigned object | Generic foreign key to Device or VirtualMachine |

## Properties

### `has_agent_interface`
Returns `True` if this host has at least one AgentInterface assigned.

### `has_snmp_interface`
Returns `True` if this host has at least one SNMPInterface assigned.

### `zabbix_tags`
Returns tags for this host configuration suitable for templates, generated based on the assigned NetBox object and tag mappings.

### `active_maintenances`
Returns all active Maintenance objects that include this HostConfig, either directly or indirectly through sites, host groups, proxy groups, or clusters.

### `in_maintenance`
Returns `True` if this host is currently under any maintenance window.

## Methods

### `__str__()`
Returns the host configuration name as a human-readable string representation.

**Returns:**
- `str`: Host configuration name

### `get_absolute_url()`
Returns the canonical URL for this host configuration within the NetBox plugin UI.

**Returns:**
- `str`: Absolute URL for the host configuration

### `get_in_sync_status()`
Checks if the host is in sync with Zabbix by comparing the NetBox configuration with the actual Zabbix configuration.

**Returns:**
- `bool`: False if host differs from Zabbix configuration, False otherwise

### `get_sync_icon()`
Returns a checkmark or cross to indicate if the Host Config is in Sync with the Zabbix host.

**Returns:**
- HTML-formatted string with checkmark or cross

### `get_sync_diff()`
Gets differences between NetBox host and Zabbix host configuration as a dictionary describing the differences.

**Returns:**
- `dict`: JSON-like dictionary describing differences

### `update_sync_status()`
Checks if the host is in sync with Zabbix and updates the database without triggering any signal handlers.

### `save(*args, **kwargs)`
Saves the HostConfig instance to the database. If no name is provided, automatically generates one using the assigned object's name with a 'z-' prefix.

**Parameters:**
- `*args`: Positional arguments passed to the model save method
- `**kwargs`: Keyword arguments passed to the model save method

### `delete(request=None, *args, **kwargs)`
Custom delete method that checks for active maintenance. If the host is in maintenance, either returns a warning (if request is provided) or raises an exception.

**Parameters:**
- `request`: Optional request object for warning message handling
- `*args`: Positional arguments passed to the model delete method
- `**kwargs`: Keyword arguments passed to the model delete method

**Returns:**
- Warning dictionary if host is in maintenance and request is provided
- Raises exception if host is in maintenance and no request provided

## Usage Examples

### Creating a HostConfig
```python
from netbox_zabbix.models import HostConfig
from dcim.models import Device

# Create a host configuration for a device
device = Device.objects.get(name="web-server-01")
host_config = HostConfig.objects.create(
    assigned_object=device,
    status=0,  # ENABLED
    description="Web server host configuration"
)
```

### Working with Host Groups and Templates
```python
from netbox_zabbix.models import HostGroup, Template

# Add host groups and templates to a host config
linux_group = HostGroup.objects.get(name="Linux Servers")
web_template = Template.objects.get(name="Template App HTTP Service")

host_config.host_groups.add(linux_group)
host_config.templates.add(web_template)
```

### Creating Agent Interface
```python
from netbox_zabbix.models import AgentInterface
from dcim.models import Interface
from ipam.models import IPAddress

# Create an agent interface for a host
device_interface = Interface.objects.get(name="eth0", device__name="web-server-01")
ip_address = IPAddress.objects.get(address="192.168.1.100/24")

agent_interface = AgentInterface.objects.create(
    host_config=host_config,
    interface=device_interface,
    ip_address=ip_address,
    port=10050,
    useip=1,  # Use IP
    main=1    # Main interface
)
```

### Creating SNMP Interface
```python
from netbox_zabbix.models import SNMPInterface

# Create an SNMP interface for a host
snmp_interface = SNMPInterface.objects.create(
    host_config=host_config,
    interface=device_interface,
    ip_address=ip_address,
    port=161,
    version=3,  # SNMPv3
    securitylevel=2,  # authPriv
    authprotocol=1,   # SHA1
    privprotocol=1,   # AES128
    useip=1,  # Use IP
    main=1    # Main interface
)
```

### Checking Sync Status
```python
# Check if host config is in sync with Zabbix
is_in_sync = host_config.get_in_sync_status()
print(f"Host config in sync: {is_in_sync}")

# Get sync differences
differences = host_config.get_sync_diff()
if differences.get("differ"):
    print("Configuration differences found:")
    print(differences)
```

## Integration with Other Models

HostConfig integrates with several other models in the plugin:

1. **Device and VirtualMachine Models**: HostConfig objects are associated with NetBox Device or VirtualMachine objects through a generic foreign key relationship.

2. **HostGroup Model**: Host configurations can be assigned to multiple host groups for organizational purposes.

3. **Template Model**: Host configurations can have multiple templates applied for monitoring configuration.

4. **Proxy and ProxyGroup Models**: Hosts can be monitored directly by the Zabbix server, via a specific proxy, or via a proxy group.

5. **AgentInterface and SNMPInterface Models**: Host configurations can have multiple agent and SNMP interfaces for different monitoring methods.

6. **Maintenance Model**: Host configurations can be included in maintenance windows either directly or indirectly through sites, host groups, proxy groups, or clusters.

## Description

The HostConfig model is a core component of the NetBox Zabbix plugin that represents the synchronization state between NetBox infrastructure objects and their Zabbix monitoring configurations. Each HostConfig object corresponds to a host in Zabbix and maintains the configuration details needed for monitoring.

Key features of the HostConfig model include:

**Object Association:**
- Links to NetBox Device or VirtualMachine objects through generic foreign keys
- Automatically generates host names based on the associated object's name

**Monitoring Configuration:**
- Tracks the Zabbix host ID for synchronization
- Manages host status (enabled/disabled)
- Controls synchronization state with Zabbix
- Records when the last synchronization check occurred

**Organization:**
- Associates with HostGroup objects for logical grouping
- Applies Template objects for monitoring configuration
- Supports different monitoring sources (direct server, proxy, or proxy group)

**Interface Support:**
- Works with both AgentInterface and SNMPInterface objects
- Tracks which interface types are configured for the host

**Maintenance Integration:**
- Automatically detects when a host is in maintenance
- Prevents deletion of hosts that are currently under maintenance

**Sync Management:**
- Provides methods to check synchronization status with Zabbix
- Offers detailed difference reporting between NetBox and Zabbix configurations
- Updates sync status without triggering signal handlers for performance

The model is designed to provide a robust foundation for bidirectional synchronization between NetBox and Zabbix, ensuring that infrastructure changes in NetBox are properly reflected in the monitoring system while also tracking the monitoring state of each host.