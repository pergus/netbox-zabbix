# NetBox Zabbix Plugin - Model Reference

This document provides detailed reference information for all models used in the NetBox Zabbix plugin. These models define the data structures that store configuration, mappings, interfaces, and other entities used for integrating NetBox with Zabbix monitoring.

## ZabbixAdminPermission

The `ZabbixAdminPermission` model is a simple permission model that defines administrative access rights for the NetBox Zabbix plugin.

### Fields

None (empty model with only permission definition)

### Meta

- `verbose_name`: "Zabbix Admin Permission"
- `permissions`: [("admin", "NetBox-Zabbix plugin administrator")]

### Description

This model exists solely to define a custom permission that can be assigned to users or groups who need administrative access to the NetBox Zabbix plugin functionality.

## DeviceMapping

The `DeviceMapping` model defines how NetBox Device objects should be mapped to Zabbix host configurations, including templates, host groups, proxies, and filtering criteria.

### Fields

Inherits all fields from the base `Mapping` model:

- `name` (CharField): Name of the mapping
- `description` (TextField): Optional description
- `default` (BooleanField): Whether this is the default mapping
- `host_groups` (ManyToManyField): Assigned Host Groups
- `templates` (ManyToManyField): Assigned Templates
- `proxy` (ForeignKey): Assigned Proxy
- `proxy_group` (ForeignKey): Assigned Proxy Group
- `interface_type` (IntegerField): Limit mapping to specific interface types
- `sites` (ManyToManyField): Restrict mapping to specific sites
- `roles` (ManyToManyField): Restrict mapping to specific device roles
- `platforms` (ManyToManyField): Restrict mapping to specific platforms

### Methods

- `get_matching_filter(device, interface_type)`: Return the most specific DeviceMapping that matches a device
- `get_matching_devices()`: Return queryset of Devices that match this mapping
- `get_absolute_url()`: Return URL for the device mapping detail page

### Description

DeviceMapping objects allow administrators to define rules for automatically configuring Zabbix monitoring for NetBox devices based on their characteristics. More specific mappings (those with more filter criteria) take precedence over less specific ones.

## VMMapping

The `VMMapping` model defines how NetBox VirtualMachine objects should be mapped to Zabbix host configurations, including templates, host groups, proxies, and filtering criteria.

### Fields

Inherits all fields from the base `Mapping` model:

- `name` (CharField): Name of the mapping
- `description` (TextField): Optional description
- `default` (BooleanField): Whether this is the default mapping
- `host_groups` (ManyToManyField): Assigned Host Groups
- `templates` (ManyToManyField): Assigned Templates
- `proxy` (ForeignKey): Assigned Proxy
- `proxy_group` (ForeignKey): Assigned Proxy Group
- `interface_type` (IntegerField): Limit mapping to specific interface types
- `sites` (ManyToManyField): Restrict mapping to specific sites
- `roles` (ManyToManyField): Restrict mapping to specific VM roles
- `platforms` (ManyToManyField): Restrict mapping to specific platforms

### Methods

- `get_matching_filter(virtual_machine, interface_type)`: Return the most specific VMMapping that matches a virtual machine
- `get_matching_virtual_machines()`: Return queryset of VirtualMachines that match this mapping
- `get_absolute_url()`: Return URL for the VM mapping detail page

### Description

VMMapping objects allow administrators to define rules for automatically configuring Zabbix monitoring for NetBox virtual machines based on their characteristics. More specific mappings (those with more filter criteria) take precedence over less specific ones.

## BaseInterface

The `BaseInterface` model is an abstract base class that defines common fields and functionality for both AgentInterface and SNMPInterface models.

### Fields

- `name` (CharField): Name for the interface in NetBox
- `hostid` (IntegerField): Zabbix Host ID (collected from Zabbix)
- `interfaceid` (IntegerField): Zabbix Interface ID (collected from Zabbix)
- `useip` (IntegerField): Whether connection should be made via IP or DNS
- `main` (IntegerField): Whether the interface is used as default on the host

### Properties

- `resolved_dns_name`: Return DNS name for this interface based on plugin IP assignment method
- `resolved_ip_address`: Return IP address for this interface based on plugin IP assignment method

### Methods

- `clean()`: Validate that the assigned IP address matches the interface

### Description

BaseInterface provides shared functionality for both agent and SNMP interfaces, including connection settings and IP/DNS resolution logic.

## AgentInterface

The `AgentInterface` model represents a Zabbix agent interface linked to a HostConfig, defining how a monitored host communicates with Zabbix via the Zabbix agent protocol.

### Fields

Inherits all fields from BaseInterface plus:

- `host_config` (ForeignKey): Link to the parent HostConfig
- `interface_type` (ForeignKey): Content type of the associated NetBox interface
- `interface_id` (PositiveIntegerField): ID of the associated NetBox interface
- `interface` (GenericForeignKey): Generic foreign key to the NetBox interface
- `ip_address` (ForeignKey): Associated IP address from NetBox IPAM
- `type` (IntegerField): Interface type (defaults to AGENT)
- `port` (IntegerField): Port number used by the interface (defaults to 10050)

### Methods

- `save()`: Ensure only one main AgentInterface exists per host_config

### Description

AgentInterface objects define the configuration for Zabbix agent monitoring, including connection details like IP address, port, and whether this is the primary interface for the host.

## SNMPInterface

The `SNMPInterface` model represents an SNMP interface linked to a HostConfig, defining how a monitored host communicates with Zabbix via the SNMP protocol.

### Fields

Inherits all fields from BaseInterface plus:

- `host_config` (ForeignKey): Link to the parent HostConfig
- `interface_type` (ForeignKey): Content type of the associated NetBox interface
- `interface_id` (PositiveIntegerField): ID of the associated NetBox interface
- `interface` (GenericForeignKey): Generic foreign key to the NetBox interface
- `ip_address` (ForeignKey): Associated IP address from NetBox IPAM
- `type` (IntegerField): Interface type (defaults to SNMP)
- `port` (IntegerField): Port number used by the interface (defaults to 161)
- `version` (IntegerField): SNMP version (defaults to SNMPv3)
- `bulk` (IntegerField): Whether to use bulk SNMP requests
- `max_repetitions` (IntegerField): Max repetition value for native SNMP bulk requests
- `contextname` (CharField): SNMP context name
- `securityname` (CharField): SNMP security name
- `securitylevel` (IntegerField): SNMP security level
- `authprotocol` (IntegerField): SNMP authentication protocol
- `authpassphrase` (CharField): SNMP authentication passphrase
- `privprotocol` (IntegerField): SNMP privacy protocol
- `privpassphrase` (CharField): SNMP privacy passphrase

### Methods

- `save()`: Ensure only one main SNMPInterface exists per host_config

### Description

SNMPInterface objects define the configuration for SNMP-based monitoring, including all necessary SNMP parameters like version, authentication, and privacy settings.

## EventLog

The `EventLog` model stores logs of plugin events for auditing and troubleshooting purposes.

### Fields

- `name` (CharField): Event name
- `job` (ForeignKey): Reference to the associated job
- `signal_id` (TextField): Signal ID
- `message` (TextField): Event message
- `exception` (TextField): Exception details (if any)
- `data` (JSONField): Event data
- `pre_data` (JSONField): Pre-change data
- `post_data` (JSONField): Post-change data
- `created` (DateTimeField): Creation timestamp

### Methods

- `get_absolute_url()`: Return URL for the event log detail page
- `get_job_status_color()`: Return a color representing the status of the associated job

### Description

EventLog objects provide an audit trail of plugin activities, including job executions, signal handling, and any exceptions that occurred during operations. This is useful for troubleshooting and monitoring plugin health.