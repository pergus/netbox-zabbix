# netbox-zabbix

NetBox plugin for Zabbix.


* Free software: MIT
* Documentation: https://pergus.github.io/netbox-zabbix/


## Todo and Questions

!!!!!!!!!!!!!!!!!!!!!!!!!!
!!!!  Interface Type  !!!!
!!!!!!!!!!!!!!!!!!!!!!!!!!



rename all hostgroups to host_groups <<<<<=============================  !!!!!!
rename monitoriedby to monitored_by
rename all proxygroup to proxy_group

Reduced the number of SQL-queries 
from 
2083.18 ms (2219 queries including 2205 similar and 2205 duplicates ) 
to 
default 228.66 ms (134 queries including 118 similar and 93 duplicates )

### Questions

Is it possible to let other views inherit field etc like NetBoxOnlyDevicesView does?
Yes!

Greate one view for device and another for vm that show all added fields such
as host_groups, proxies etc.


Remove the null=True in Proxy Mappings and Proxy Group Mappings model.
I added it to makemigrations without having to dump the database.

### General
| Action                                                       | Status        |
| ------------------------------------------------------------ | ------------- |
| Format for exception and logging messages                    | Todo          |
| Replace plugin settings with configuration variables         | Done          |
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
| Add Host information as a tab for Device and VM              | Done          |
| Add filtersets to the views                                  | Todo          |
| Implement GraphQL                                            | Todo          |
| Add template mappings                                        | Done          |
| Add host group mappings                                      | Done          |
| Add models for Proxy and Proxy Groups                        | Done          |
| Add Proxy mappings                                           | Done          |
| Add Proxy Group mappings                                     | Done          |
| Add support for TLS certificates                             | Todo          |

### Config
| Action                                                       | Status        |
| ------------------------------------------------------------ | ------------- |
| Add CIDR to the config                                       | Done          |
| Add Automatic Validation                                     | Done          |
| Add TLS settings                                             | Done          |
| Add Max deletions on import                                  | Done          |
| Add Maximum Success Notifications                            | Done          |
| Add Background Job for Zabbix Config Sync                    | Todo          |
| Should Max deletions on import be enabled/disabled?          | Todo          |


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


### Mappings
| Action                                                       | Status        |
| ------------------------------------------------------------ | ------------- |
| Related objects for Proxy Mappings                           | Done          |
| Related objects for Proxy Group Mappings                     | Done          |




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
