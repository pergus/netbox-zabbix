# BaseInterface Model

## Overview

The `BaseInterface` model is an abstract base class that defines common fields and functionality for both AgentInterface and SNMPInterface models.

## Model Definition

BaseInterface is an abstract Django model that provides shared functionality for both agent and SNMP interfaces.

## Fields

- `name` (CharField): Name for the interface in NetBox (max_length=255, required)
- `hostid` (IntegerField): Zabbix Host ID (collected from Zabbix, nullable)
- `interfaceid` (IntegerField): Zabbix Interface ID (collected from Zabbix, nullable)
- `useip` (IntegerField): Whether connection should be made via IP or DNS (choices from UseIPChoices, default=IP)
- `main` (IntegerField): Whether the interface is used as default on the host (choices from MainChoices, default=YES)

## Properties

### resolved_dns_name

Return DNS name for this interface based on the plugin IP assignment method.

**Returns:**
- `str` or `None`: DNS name if available

### resolved_ip_address

Return IP address for this interface based on the plugin IP assignment method.

**Returns:**
- `IPAddress` or `None`: IP address object if available

## Methods

### clean()

Validate that the assigned IP address matches the interface.

**Raises:**
- `ValidationError`: If IP does not belong to the selected interface

## Description

BaseInterface provides shared functionality for both agent and SNMP interfaces, including connection settings and IP/DNS resolution logic. It is an abstract model, meaning no database table is created for it directly. Instead, it serves as a parent class for AgentInterface and SNMPInterface models.

The model handles:
- Interface naming within NetBox
- Storage of Zabbix identifiers (hostid, interfaceid)
- Connection method configuration (IP vs DNS)
- Primary interface designation
- IP address and DNS name resolution based on plugin settings
- Validation of IP address assignments

This abstraction allows both AgentInterface and SNMPInterface to share common functionality while having their own specific fields and behaviors.