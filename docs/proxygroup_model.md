# NetBox Zabbix Plugin - ProxyGroup Documentation

## Overview

The ProxyGroup in the NetBox Zabbix plugin represents Zabbix proxy groups, which are collections of proxies that can provide high availability and load distribution for monitoring. This document explains the ProxyGroup's structure, fields, properties, methods, and usage.

## Model Definition

The ProxyGroup synchronizes with Zabbix proxy groups and maintains configuration parameters that define how proxy groups operate in the Zabbix monitoring system. Proxy groups allow for failover and load balancing among multiple proxies.

## Fields

| Field | Type | Description | Default/Notes |
|-------|------|-------------|---------------|
| `name` | CharField (max_length=255) | Name of the proxy group | Human-readable identifier |
| `proxy_groupid` | CharField (max_length=255) | Unique identifier in Zabbix | Blank/null allowed |
| `failover_delay` | CharField (max_length=255) | Failover period | Default: "1m" |
| `min_online` | PositiveSmallIntegerField | Minimum online proxies | Default: 1 |
| `description` | TextField | Description of the proxy group | Blank/null allowed |
| `last_synced` | DateTimeField | Last synchronization timestamp | Blank/null allowed |

### `name`
The human-readable name of the proxy group as it appears in both NetBox and Zabbix.

### `proxy_groupid`
The unique identifier assigned by Zabbix for this proxy group. This field is populated automatically during synchronization.

### `failover_delay`
The period during which a proxy in the proxy group must communicate with the Zabbix server to be considered online. Format follows Zabbix time unit specifications (e.g., "1m", "30s", "2h").

### `min_online`
The minimum number of proxies that must be online for the proxy group to be considered operational.

### `description`
An optional textual description of the proxy group's purpose or configuration.

### `last_synced`
Timestamp indicating when the proxy group was last synchronized with Zabbix.

## Methods

### `__str__()`
Returns the proxy group name as a human-readable string representation.

**Returns:**
- `str`: Proxy group name

### `get_absolute_url()`
Returns the canonical URL for this proxy group within the NetBox plugin UI.

**Returns:**
- `str`: Absolute URL for the proxy group

### `create_new_proxy_group()`
Creates a new proxy group in Zabbix with the current configuration parameters.

### `update_existing_proxy_group()`
Updates an existing proxy group in Zabbix with the current configuration parameters.

### `delete(*args, **kwargs)`
Attempts to delete the proxy group from Zabbix. If successful, also removes it from NetBox. If Zabbix deletion fails, returns a warning but still removes from NetBox.

## Usage Examples

### Creating a ProxyGroup
```python
from netbox_zabbix.models import ProxyGroup

# Create a new proxy group
proxy_group = ProxyGroup.objects.create(
    name="Web Servers Proxy Group",
    failover_delay="30s",
    min_online=2,
    description="Proxy group for monitoring web servers"
)
```

### Configuring Failover Settings
```python
# Configure a proxy group with strict failover requirements
high_availability_group = ProxyGroup.objects.create(
    name="Critical Infrastructure",
    failover_delay="1m",
    min_online=3,
    description="High availability proxy group for critical systems"
)
```

### Synchronizing with Zabbix
```python
# Create the proxy group in Zabbix
proxy_group.create_new_proxy_group()

# Update an existing proxy group in Zabbix
proxy_group.failover_delay = "45s"
proxy_group.update_existing_proxy_group()
```

## Integration with Other Models

ProxyGroup integrates with several other models in the plugin:

1. **Proxy Model**: Proxies can be assigned to proxy groups through the `proxy_group` foreign key relationship.
2. **HostConfig Model**: Host configurations can be assigned to proxy groups for monitoring.
3. **Mapping Models**: DeviceMapping and VMMapping can specify proxy groups for matching hosts.

## Description

The ProxyGroup model provides high availability and load distribution capabilities for Zabbix monitoring by managing groups of proxies. It enables failover mechanisms and ensures continuous monitoring even when individual proxies become unavailable.

Key features include:
- Automatic synchronization with Zabbix proxy groups
- Configurable failover delay settings
- Minimum online proxy requirements
- Integration with Proxy, HostConfig, and Mapping models
- Robust error handling for Zabbix API operations