# netbox-zabbix

NetBox plugin for Zabbix.


* Free software: MIT
* Documentation: https://pergus.github.io/netbox-zabbix/


## Todo

| Action                                                       | Status        |
| ------------------------------------------------------------ | ------------- |
| Rename the Config model                                      | Todo          |
| Rename Hosts to something else                               | Todo          |
| Rename interfaces to something shorter                       | Todo          |
| Format for exception and logging messages                    | Todo          |
| Replace plugin settings with configuration variables         | Todo          |
| Create Unmanaged Devices                                     | Todo          |
| Create Unmanaged VMs                                         | Todo          |
| Create NetBox only Hosts                                     | Todo          |
| Create Zabbix only Hosts                                     | Done          |
| Create model and form for Agent interfaces                   | Done          |
| Create model and form for SNMPv3 interfaces                  | Done          |
| Create model and form for SNMPv1 interfaces                  | Todo          |
| Create model and form for SNMPv2c interfaces                 | Todo          |
| Create class or function to run background jobs              | Done          |
| Implement signals for create, update and delete              | Todo          |
| Add Host information as a tab for Device and VM              | Todo          |


Convert the code to the naming standard in [new_urls.py](./new_urls.py) and [new_navigation.py](./new_navigation.py).







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
