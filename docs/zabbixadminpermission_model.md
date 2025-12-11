# ZabbixAdminPermission Model

## Overview

The `ZabbixAdminPermission` model is a simple permission model that defines administrative access rights for the NetBox Zabbix plugin.

## Model Definition

```python
class ZabbixAdminPermission(NetBoxModel):
    class Meta:
        verbose_name = "Zabbix Admin Permission"
        permissions = [ ("admin", "NetBox-Zabbix plugin administrator"), ]
    pass
```

## Fields

The ZabbixAdminPermission model is an empty model that exists solely to define custom permissions.

## Meta Options

- `verbose_name`: "Zabbix Admin Permission"
- `permissions`: [("admin", "NetBox-Zabbix plugin administrator")]

## Description

This model exists solely to define a custom permission that can be assigned to users or groups who need administrative access to the NetBox Zabbix plugin functionality. It does not store any data fields but provides a way to grant administrative privileges for plugin operations.

The permission can be assigned through Django's standard permission system, allowing fine-grained control over who can perform administrative tasks within the plugin.