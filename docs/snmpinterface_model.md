# SNMPInterface Model

## Overview

The `SNMPInterface` model represents an SNMP interface linked to a HostConfig, defining how a monitored host communicates with Zabbix via the SNMP protocol.

## Model Definition

SNMPInterface extends the BaseInterface abstract model and adds fields specific to SNMP monitoring. It defines the configuration for SNMP-based monitoring, including all necessary SNMP parameters like version, authentication, and privacy settings.

## Fields

Inherits all fields from BaseInterface plus:

| Field | Type | Description | Notes |
|-------|------|-------------|-------|
| `host_config` | ForeignKey (HostConfig) | Link to the parent HostConfig | related_name="snmp_interfaces" |
| `interface_type` | ForeignKey (ContentType) | Content type of the associated NetBox interface | Limited to Interface or VMInterface models |
| `interface_id` | PositiveIntegerField | ID of the associated NetBox interface |  |
| `interface` | GenericForeignKey | Generic foreign key to the NetBox interface |  |
| `ip_address` | ForeignKey (IPAddress) | Associated IP address from NetBox IPAM | related_name="snmp_interface", nullable |
| `type` | IntegerField | Interface type | Choices from TypeChoices, default=SNMP |
| `port` | IntegerField | Port number used by the interface | Default=161 |
| `version` | IntegerField | SNMP version | Choices from SNMPVersionChoices, default=SNMPv3, nullable |
| `bulk` | IntegerField | Whether to use bulk SNMP requests | Choices from SNMPBulkChoices, default=1, nullable |
| `max_repetitions` | IntegerField | Max repetition value for native SNMP bulk requests | Default=10, nullable |
| `contextname` | CharField (max_length=255) | SNMP context name | Nullable |
| `securityname` | CharField (max_length=255) | SNMP security name | Default="{$SNMPV3_USER}", nullable |
| `securitylevel` | IntegerField | SNMP security level | Choices from SNMPSecurityLevelChoices, default=SNMPSecurityLevelChoices.authPriv, nullable |
| `authprotocol` | IntegerField | SNMP authentication protocol | Choices from SNMPAuthProtocolChoices, default=SNMPAuthProtocolChoices.SHA1, nullable |
| `authpassphrase` | CharField (max_length=255) | SNMP authentication passphrase | Default="{$SNMPV3_AUTHPASS}", nullable |
| `privprotocol` | IntegerField | SNMP privacy protocol | Choices from SNMPPrivProtocolChoices, default=SNMPPrivProtocolChoices.AES128, nullable |
| `privpassphrase` | CharField (max_length=255) | SNMP privacy passphrase | Default="{$SNMPV3_PRIVPASS}", nullable |

## Methods

### `save(*args, **kwargs)`

Ensure only one main SNMPInterface exists per host_config and validate the instance.

**Parameters:**
- `*args`: Positional arguments passed to the parent save method
- `**kwargs`: Keyword arguments passed to the parent save method

**Raises:**
- `ValidationError`: If the model is invalid

### `__str__()`

Return a string representation of the SNMP interface.

**Returns:**
- `str`: String representation of the SNMP interface

### `clean()`

Validate that the assigned IP address matches the interface.

**Raises:**
- `ValidationError`: If IP does not belong to the selected interface

### `get_absolute_url()`

Return the canonical URL for this SNMP interface within the NetBox plugin UI.

**Returns:**
- `str`: Absolute URL for the SNMP interface

## Usage Examples

### Creating an SNMP Interface
```python
from netbox_zabbix.models import SNMPInterface, HostConfig
from dcim.models import Interface
from ipam.models import IPAddress

# Get the host configuration
host_config = HostConfig.objects.get(name="z-router-01")

# Get the NetBox interface
netbox_interface = Interface.objects.get(name="GigabitEthernet0/1", device__name="router-01")

# Get the IP address
ip_address = IPAddress.objects.get(address="192.168.1.1/24")

# Create an SNMP interface
snmp_interface = SNMPInterface.objects.create(
    host_config=host_config,
    interface=netbox_interface,
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

### Configuring SNMPv2 Interface
```python
# Create an SNMPv2 interface
snmp_v2_interface = SNMPInterface.objects.create(
    host_config=host_config,
    interface=netbox_interface,
    ip_address=ip_address,
    port=161,
    version=2,  # SNMPv2c
    useip=1,    # Use IP
    main=1      # Main interface
)
```

### Working with SNMP Interface Properties
```python
# Access resolved IP address
ip_address = snmp_interface.resolved_ip_address
if ip_address:
    print(f"SNMP connecting on IP: {ip_address}")

# Access resolved DNS name
dns_name = snmp_interface.resolved_dns_name
if dns_name:
    print(f"SNMP connecting on DNS: {dns_name}")

# Check if this is the main interface
if snmp_interface.main == 1:
    print("This is the main SNMP interface")

# Check SNMP version
if snmp_interface.version == 3:
    print(f"Using SNMPv3 with security level: {snmp_interface.securitylevel}")
```

### Updating SNMP Configuration
```python
# Change SNMP version
snmp_interface.version = 2  # SNMPv2c
snmp_interface.save()

# Update SNMPv3 security settings
snmp_interface.securitylevel = 1  # authNoPriv
snmp_interface.authprotocol = 2   # SHA256
snmp_interface.privprotocol = 0   # No privacy
snmp_interface.save()

# Disable bulk operations
snmp_interface.bulk = 0
snmp_interface.save()
```

## Integration with Other Models

SNMPInterface integrates with several other models in the plugin:

1. **HostConfig Model**: SNMPInterface instances are associated with specific HostConfig objects through a foreign key relationship.

2. **BaseInterface Model**: SNMPInterface inherits from BaseInterface, sharing common interface functionality.

3. **NetBox Interface Model**: SNMPInterface links to NetBox Interface objects for device/VLAN information.

4. **NetBox VMInterface Model**: SNMPInterface can also link to NetBox VMInterface objects for virtual machine interfaces.

5. **NetBox IPAddress Model**: SNMPInterface links to NetBox IPAddress objects for IP connectivity.

## Description

SNMPInterface objects define the configuration for SNMP-based monitoring, including all necessary SNMP parameters like version, authentication, and privacy settings.

Key features:
- Links to a specific HostConfig object
- Associates with NetBox Interface or VMInterface objects through generic foreign keys
- Can reference a specific IP address from NetBox IPAM
- Configures SNMP communication port (default 161)
- Supports SNMP versions 1, 2c, and 3
- Configures authentication and privacy settings for SNMPv3
- Supports bulk SNMP operations
- Supports designation as the main interface for the host
- Ensures only one main SNMP interface exists per host configuration
- Validates that assigned IP addresses belong to the selected interface

The model provides comprehensive SNMP configuration options:
- SNMP version selection (v1, v2c, v3)
- Security level configuration (noAuthNoPriv, authNoPriv, authPriv)
- Authentication protocol selection (MD5, SHA1, SHA224, SHA256, SHA384, SHA512)
- Privacy protocol selection (DES, AES128, AES192, AES256)
- Context name support for SNMPv3
- Bulk operation settings for improved performance

The model automatically handles ensuring that only one SNMP interface is marked as "main" per host configuration, updating other interfaces if needed when changing the main interface designation. This prevents configuration conflicts in Zabbix where multiple main interfaces could cause monitoring issues.