# DeviceMapping Model

## Overview

The `DeviceMapping` model defines how NetBox Device objects should be mapped to Zabbix host configurations, including templates, host groups, proxies, and filtering criteria.

## Model Definition

DeviceMapping inherits from the base `Mapping` model and provides specific functionality for mapping NetBox Device objects to Zabbix configurations.

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
- `roles` (ManyToManyField): Restrict mapping to specific device roles
- `platforms` (ManyToManyField): Restrict mapping to specific platforms

## Methods

### get_matching_filter(device, interface_type)

Return the most specific DeviceMapping that matches a device based on its characteristics.

**Parameters:**
- `device` (Device): Device instance to match
- `interface_type` (int): Interface type to filter by

**Returns:**
- `DeviceMapping`: Matching mapping object

### get_matching_devices()

Return queryset of Devices that match this mapping, excluding devices already covered by more specific mappings.

**Returns:**
- `QuerySet`: Matching Device instances

### get_absolute_url()

Return URL for the device mapping detail page in the NetBox UI.

**Returns:**
- `str`: Absolute URL for the device mapping

## Description

DeviceMapping objects allow administrators to define rules for automatically configuring Zabbix monitoring for NetBox devices based on their characteristics. More specific mappings (those with more filter criteria) take precedence over less specific ones.

Mappings can filter devices by:
- Site
- Role
- Platform

And can assign:
- Templates
- Host groups
- Proxy or proxy group
- Interface type restrictions

When a device matches multiple mappings, the most specific one (with the most restrictive filters) is applied. A default mapping should always exist to catch devices that don't match any specific mapping.