# netbox-zabbix

NetBox plugin for Zabbix.


* Free software: MIT
* Documentation: https://pergus.github.io/netbox-zabbix/





from django.db.models import Q

def resolve_hostgroup_for_host(host):
    """
    Given a NetBox host object (device or VM), find a matching ZabbixHostGroup
    based on mappings by role, platform, or tags.
    """

    # Device case
    if hasattr(host, 'device') and host.device:
        device = host.device
        mappings = ZabbixHostGroupMapping.objects.filter(
            Q(device_role=device.role) |
            Q(platform=device.platform) |
            Q(tag__in=device.tags.all())
        ).select_related('hostgroup').distinct()

    # Virtual Machine case
    elif hasattr(host, 'virtual_machine') and host.virtual_machine:
        vm = host.virtual_machine
        mappings = ZabbixHostGroupMapping.objects.filter(
            Q(vm_role=vm.role) |
            Q(platform=vm.platform) |
            Q(tag__in=vm.tags.all())
        ).select_related('hostgroup').distinct()

    else:
        return None

    # Return first matching hostgroup or None
    return mappings.first().hostgroup if mappings.exists() else None


## Todo

Is it possible to let other views inherit field etc like NetBoxOnlyDevicesView does?


In "Host Group Mapping" add tabs for matching Devices and matching VMs.
Should I replace the Tabs for matching Devices and VMs with a "related
objects" similar to a Device Role??



### General
| Action                                                       | Status        |
| ------------------------------------------------------------ | ------------- |
| Format for exception and logging messages                    | Todo          |
| Replace plugin settings with configuration variables         | Todo          |
| Create Importable Devices/VMs                                | Done          |
| Create Devices/VM Zabbix configurations                      | Done          |
| Create Devices/VM components                                 | Done          |
| Create ALL Zabbix Configurations                             | Done          |
| Create NetBox only Devices/VMs                               | Done          |
| Create Zabbix only Hosts                                     | Done          |
| Create model and form for Agent interfaces                   | Done          |
| Create model and form for SNMPv3 interfaces                  | Done          |
| Create model and form for SNMPv1 interfaces                  | Todo          |
| Create model and form for SNMPv2c interfaces                 | Todo          |
| Create class or function to run background jobs              | Done          |
| Implement signals for create, update and delete              | Todo          |
| Auto hide validate button depending on if automatic validation is enabled or not | Done |
| Add Host information as a tab for Device and VM              | Todo          |
| Add filtersets to the views                                  | Todo          |
| Implement GraphQL                                            | Todo          |



### Config
| Action                                                       | Status        |
| ------------------------------------------------------------ | ------------- |
| Add CIDR to the config                                       | Done          |
| Add Automatic Validation                                     | Done          |
| Add Automatic Validation                                     | Done          |
| Add Background Job for Zabbix Config Sync                    | Done          |
| Add a limit to how many messages to show when importing multiple Devices/VMs | Todo |


### NetBox Only Devices
| Action                                                       | Status        |
| ------------------------------------------------------------ | ------------- |
| Add action button to create new config                       | Todo          |
| Add action button to quick add Agent                         | Todo          |
| Add action button to quick Add SNMPv3                        | Todo          |

### NetBox Only VMs
| Action                                                       | Status        |
| ------------------------------------------------------------ | ------------- |
| Add action button to create new config                       | Todo          |
| Add action button to quick add Agent                         | Todo          |
| Add action button to quick Add SNMPv3                        | Todo          |






## Features

The features the plugin provides should be listed here.

## Compatibility

| NetBox Version | Plugin Version |
|----------------|----------------|
|     4.0        |      0.1.0     |

## Installing

For adding to a NetBox Docker setup see
[the general instructions for using netbox-docker with plugins](https://github.com/netbox-community/netbox-docker/wiki/Using-Netbox-Plugins).

While this is still in development and not yet on pypi you can install with pip:

```bash
pip install git+https://github.com/pergus/netbox-zabbix
```

or by adding to your `local_requirements.txt` or `plugin_requirements.txt` (netbox-docker):

```bash
git+https://github.com/pergus/netbox-zabbix
```

Enable the plugin in `/opt/netbox/netbox/netbox/configuration.py`,
 or if you use netbox-docker, your `/configuration/plugins.py` file :

```python
PLUGINS = [
    'netbox-zabbix'
]

PLUGINS_CONFIG = {
    "netbox-zabbix": {},
}
```

## Credits

Based on the NetBox plugin tutorial:

- [demo repository](https://github.com/netbox-community/netbox-plugin-demo)
- [tutorial](https://github.com/netbox-community/netbox-plugin-tutorial)

This package was created with [Cookiecutter](https://github.com/audreyr/cookiecutter) and the [`netbox-community/cookiecutter-netbox-plugin`](https://github.com/netbox-community/cookiecutter-netbox-plugin) project template.
