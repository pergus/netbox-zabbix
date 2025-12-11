# NetBox Zabbix Plugin - HostConfig and Interface Documentation

The HostConfig and interface in the NetBox Zabbix plugin represent the Zabbix host configurations and their network interfaces. This document explains the structure, fields, properties, methods, and usage.

## HostConfig Model

The HostConfig represents a host configuration in Zabbix and maintains the relationship between NetBox objects (devices or virtual machines) and their Zabbix monitoring configurations.

### Model Fields

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

### Properties

#### `has_agent_interface`
Returns `True` if this host has at least one AgentInterface assigned.

#### `has_snmp_interface`
Returns `True` if this host has at least one SNMPInterface assigned.

#### `zabbix_tags`
Returns tags for this host configuration suitable for templates, generated based on the assigned NetBox object and tag mappings.

#### `active_maintenances`
Returns all active Maintenance objects that include this HostConfig, either directly or indirectly through sites, host groups, proxy groups, or clusters.

#### `in_maintenance`
Returns `True` if this host is currently under any maintenance window.

### Methods

#### `__str__()`
Returns the host configuration name as a human-readable string representation.

#### `get_absolute_url()`
Returns the canonical URL for this host configuration within the NetBox plugin UI:
```
/plugins/netbox_zabbix/hostconfigs/{pk}/
```

#### `get_in_sync_status()`
Checks if the host is in sync with Zabbix by comparing the NetBox configuration with the actual Zabbix configuration.

#### `get_sync_icon()`
Returns a checkmark or cross to indicate if the Host Config is in Sync with the Zabbix host.

#### `get_sync_diff()`
Gets differences between NetBox host and Zabbix host configuration as a dictionary describing the differences.

#### `update_sync_status()`
Checks if the host is in sync with Zabbix and updates the database without triggering any signal handlers.

#### `save(*args, **kwargs)`
Saves the HostConfig instance to the database. If no name is provided, automatically generates one using the assigned object's name with a 'z-' prefix.

#### `delete(request=None, *args, **kwargs)`
Custom delete method that checks for active maintenance. If the host is in maintenance, either returns a warning (if request is provided) or raises an exception.

## BaseInterface Model

The BaseInterface model (`netbox_zabbix.models.BaseInterface`) is an abstract base class for Zabbix host interfaces (Agent or SNMP).

### Model Fields

| Field | Type | Description | Notes |
|-------|------|-------------|-------|
| `name` | CharField (max_length=255) | Interface name in NetBox | Required |
| `hostid` | IntegerField | Zabbix Host ID | Collected from Zabbix |
| `interfaceid` | IntegerField | Zabbix Interface ID | Collected from Zabbix |
| `useip` | IntegerField | Connection method | Default: IP. Options: DNS (0), IP (1) |
| `main` | IntegerField | Main interface flag | Default: YES. Options: NO (0), YES (1) |

### Properties

#### `resolved_dns_name`
Returns DNS name for this interface based on the plugin IP assignment method.

#### `resolved_ip_address`
Returns IP address for this interface based on the plugin IP assignment method.

### Methods

#### `__str__()`
Returns the interface name as a human-readable string representation.

#### `clean()`
Validates that the assigned IP address matches the interface, raising a ValidationError if the IP does not belong to the selected interface.

## AgentInterface Model

The AgentInterface model (`netbox_zabbix.models.AgentInterface`) represents a Zabbix agent interface linked to a HostConfig.

### Model Fields

| Field | Type | Description | Notes |
|-------|------|-------------|-------|
| `host_config` | ForeignKey (HostConfig) | Parent host config | Related name: agent_interfaces |
| `interface_type` | ForeignKey (ContentType) | Interface type | Limited to Interface or VMInterface |
| `interface_id` | PositiveIntegerField | Interface ID | ID of the NetBox interface |
| `interface` | GenericForeignKey | Assigned interface | Generic foreign key to Interface or VMInterface |
| `ip_address` | ForeignKey (IPAddress) | Assigned IP | Related name: agent_interface |
| `type` | IntegerField | Interface type | Default: AGENT (1). Options: AGENT (1), SNMP (2) |
| `port` | IntegerField | Agent port | Default: 10050 |

### Methods

#### `save(*args, **kwargs)`
Ensures only one main AgentInterface exists per host_config and validates the instance. Enforces that only one agent interface can be marked as main per host configuration.

## SNMPInterface Model

The SNMPInterface model (`netbox_zabbix.models.SNMPInterface`) represents an SNMP interface linked to a HostConfig.

### Model Fields

| Field | Type | Description | Notes |
|-------|------|-------------|-------|
| `host_config` | ForeignKey (HostConfig) | Parent host config | Related name: snmp_interfaces |
| `interface_type` | ForeignKey (ContentType) | Interface type | Limited to Interface or VMInterface |
| `interface_id` | PositiveIntegerField | Interface ID | ID of the NetBox interface |
| `interface` | GenericForeignKey | Assigned interface | Generic foreign key to Interface or VMInterface |
| `ip_address` | ForeignKey (IPAddress) | Assigned IP | Related name: snmp_interface |
| `type` | IntegerField | Interface type | Default: SNMP (2). Options: AGENT (1), SNMP (2) |
| `port` | IntegerField | SNMP port | Default: 161 |
| `version` | IntegerField | SNMP version | Default: SNMPv3 (3). Options: SNMPv1 (1), SNMPv2c (2), SNMPv3 (3) |
| `bulk` | IntegerField | Bulk requests | Default: YES (1). Options: NO (0), YES (1) |
| `max_repetitions` | IntegerField | Max repetitions | Default: 10 |
| `contextname` | CharField (max_length=255) | Context name | Optional |
| `securityname` | CharField (max_length=255) | Security name | Default: "{$SNMPV3_USER}" |
| `securitylevel` | IntegerField | Security level | Default: authPriv (2). Options: noAuthNoPriv (0), authNoPriv (1), authPriv (2) |
| `authprotocol` | IntegerField | Auth protocol | Default: SHA1 (1). Options: MD5 (0), SHA1 (1), SHA224 (2), SHA256 (3), SHA384 (4), SHA512 (5) |
| `authpassphrase` | CharField (max_length=255) | Auth passphrase | Default: "{$SNMPV3_AUTHPASS}" |
| `privprotocol` | IntegerField | Privacy protocol | Default: AES128 (1). Options: DES (0), AES128 (1), AES192 (2), AES256 (3), AES192C (4), AES256C (5) |
| `privpassphrase` | CharField (max_length=255) | Privacy passphrase | Default: "{$SNMPV3_PRIVPASS}" |

### Methods

#### `save(*args, **kwargs)`
Ensures only one main SNMPInterface exists per host_config and validates the instance. Enforces that only one SNMP interface can be marked as main per host configuration.

## Field Details

### HostConfig Fields

#### `name`
The name of the host configuration in Zabbix. If not provided, it's automatically generated using the assigned object's name with a 'z-' prefix.

#### `hostid`
The unique identifier assigned by Zabbix for this host. This field is populated when the host is created in Zabbix.

#### `status`
The monitoring status of the host:
- `ENABLED` (0): Host is enabled for monitoring
- `DISABLED` (1): Host is disabled for monitoring

#### `in_sync`
Boolean flag indicating whether the NetBox host configuration matches the actual Zabbix configuration.

#### `last_sync_update`
Timestamp indicating when the sync status was last checked or updated.

#### `monitored_by`
Specifies how the host is monitored:
- `ZabbixServer` (0): Monitored directly by the Zabbix server
- `Proxy` (1): Monitored via a Zabbix proxy
- `ProxyGroup` (2): Monitored via a Zabbix proxy group

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