# NetBox Zabbix Plugin

NetBox plugin for Zabbix. DEMO DEMO DEMO


* Free software: Apache-2.0
* Documentation: https://.github.io/netbox-zabbix/


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
pip install git+https://github.com//netbox-zabbix
```

or by adding to your `local_requirements.txt` or `plugin_requirements.txt` (netbox-docker):

```bash
git+https://github.com//netbox-zabbix
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


## Todo


Clean up the code!!!


### Zabbix Configuration

Only allow one configuration.
Add a test connection button.
Retrieve the Zabbix version.


### Templates

When a template is deleted it should be removed from all hosts as well.
This means that a host with the template should have its templeate removed.
This should not be synced to Z, since removing a template in Z removes it from
all hosts.


### Hosts

Add tab view?

Agent

SNMP

Additional Fields:
 - last_synced (date)
 - synced_status - Failed or Succeded

Multi Model so that VMs and Devices can be display in the same table.

What should be synced from NB to Z?

List all hosts that are synced with Z.

List all hosts that are NOT synced with Z.

### Signals

Research how signals work when syncing from Z to NB.
Prevent loops!!


### Jobs

Rewrite the jobs and move the code for the jobs to a separate file.

Document what is required to write a job.


### Zabbix

Can we embedd Z pages in NB?
