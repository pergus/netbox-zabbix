# SNMPInterface Model

## Overview

The `SNMPInterface` model represents an SNMP interface linked to a HostConfig, defining how a monitored host communicates with Zabbix via the SNMP protocol.

## Model Definition

SNMPInterface extends the BaseInterface abstract model and adds fields specific to SNMP monitoring.

## Fields

Inherits all fields from BaseInterface plus:

- `host_config` (ForeignKey): Link to the parent HostConfig (related_name="snmp_interfaces")
- `interface_type` (ForeignKey): Content type of the associated NetBox interface (limited to Interface or VMInterface models)
- `interface_id` (PositiveIntegerField): ID of the associated NetBox interface
- `interface` (GenericForeignKey): Generic foreign key to the NetBox interface
- `ip_address` (ForeignKey): Associated IP address from NetBox IPAM (related_name="snmp_interface", nullable)
- `type` (IntegerField): Interface type (choices from TypeChoices, default=SNMP)
- `port` (IntegerField): Port number used by the interface (default=161)
- `version` (IntegerField): SNMP version (choices from SNMPVersionChoices, default=SNMPv3, nullable)
- `bulk` (IntegerField): Whether to use bulk SNMP requests (choices from SNMPBulkChoices, default=1, nullable)
- `max_repetitions` (IntegerField): Max repetition value for native SNMP bulk requests (default=10, nullable)
- `contextname` (CharField): SNMP context name (max_length=255, nullable)
- `securityname` (CharField): SNMP security name (max_length=255, default="{$SNMPV3_USER}", nullable)
- `securitylevel` (IntegerField): SNMP security level (choices from SNMPSecurityLevelChoices, default=SNMPSecurityLevelChoices.authPriv, nullable)
- `authprotocol` (IntegerField): SNMP authentication protocol (choices from SNMPAuthProtocolChoices, default=SNMPAuthProtocolChoices.SHA1, nullable)
- `authpassphrase` (CharField): SNMP authentication passphrase (max_length=255, default="{$SNMPV3_AUTHPASS}", nullable)
- `privprotocol` (IntegerField): SNMP privacy protocol (choices from SNMPPrivProtocolChoices, default=SNMPPrivProtocolChoices.AES128, nullable)
- `privpassphrase` (CharField): SNMP privacy passphrase (max_length=255, default="{$SNMPV3_PRIVPASS}", nullable)

## Methods

### save(\*args, \*\*kwargs)

Ensure only one main SNMPInterface exists per host_config and validate the instance.

**Parameters:**
- `*args`: Positional arguments passed to the parent save method
- `**kwargs`: Keyword arguments passed to the parent save method

**Raises:**
- `ValidationError`: If the model is invalid

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

The model automatically handles ensuring that only one SNMP interface is marked as "main" per host configuration, updating other interfaces if needed when changing the main interface designation.