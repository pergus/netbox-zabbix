# VMMapping Model

## Overview

The `VMMapping` model defines how NetBox VirtualMachine objects should be mapped to Zabbix host configurations, including templates, host groups, proxies, and filtering criteria.

## Model Definition

VMMapping inherits from the base `Mapping` model and provides specific functionality for mapping NetBox VirtualMachine objects to Zabbix configurations.

## Fields

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

## Methods

### get_matching_filter(virtual_machine, interface_type)

Return the most specific VMMapping that matches a virtual machine based on its characteristics.

**Parameters:**
- `virtual_machine` (VirtualMachine): VM instance to match
- `interface_type` (int): Interface type to filter by

**Returns:**
- `VMMapping`: Matching mapping object

### get_matching_virtual_machines()

Return queryset of VirtualMachines that match this mapping, excluding VMs already covered by more specific mappings.

**Returns:**
- `QuerySet`: Matching VirtualMachine instances

### get_absolute_url()

Return URL for the VM mapping detail page in the NetBox UI.

**Returns:**
- `str`: Absolute URL for the VM mapping

## Description

VMMapping objects allow administrators to define rules for automatically configuring Zabbix monitoring for NetBox virtual machines based on their characteristics. More specific mappings (those with more filter criteria) take precedence over less specific ones.

Mappings can filter virtual machines by:
- Site
- Role
- Platform

And can assign:
- Templates
- Host groups
- Proxy or proxy group
- Interface type restrictions

When a virtual machine matches multiple mappings, the most specific one (with the most restrictive filters) is applied. A default mapping should always exist to catch virtual machines that don't match any specific mapping.