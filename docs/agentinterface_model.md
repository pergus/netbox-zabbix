# AgentInterface Model

## Overview

The `AgentInterface` model represents a Zabbix agent interface linked to a HostConfig, defining how a monitored host communicates with Zabbix via the Zabbix agent protocol.

## Model Definition

AgentInterface extends the BaseInterface abstract model and adds fields specific to Zabbix agent monitoring.

## Fields

Inherits all fields from BaseInterface plus:

- `host_config` (ForeignKey): Link to the parent HostConfig (related_name="agent_interfaces")
- `interface_type` (ForeignKey): Content type of the associated NetBox interface (limited to Interface or VMInterface models)
- `interface_id` (PositiveIntegerField): ID of the associated NetBox interface
- `interface` (GenericForeignKey): Generic foreign key to the NetBox interface
- `ip_address` (ForeignKey): Associated IP address from NetBox IPAM (related_name="agent_interface", nullable)
- `type` (IntegerField): Interface type (choices from TypeChoices, default=AGENT)
- `port` (IntegerField): Port number used by the interface (default=10050)

## Methods

### save(\*args, \*\*kwargs)

Ensure only one main AgentInterface exists per host_config and validate the instance.

**Parameters:**
- `*args`: Positional arguments passed to the parent save method
- `**kwargs`: Keyword arguments passed to the parent save method

**Raises:**
- `ValidationError`: If the model is invalid

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

The model automatically handles ensuring that only one agent interface is marked as "main" per host configuration, updating other interfaces if needed when changing the main interface designation.