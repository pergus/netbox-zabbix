# netbox-zabbix

NetBox plugin for Zabbix.


* Free software: MIT
* Documentation: https://pergus.github.io/netbox-zabbix/



### Bugs

Import doesn't include proxy/proxy group.

Not having a name for ZabbixConfig's makes it problematic to script.



### Todo

[DONE] Failsafe delete
1. Disable in Zabbix.
2. Is it possible to add the host in a special host group.





[DONE] DNS name changes

* What if an interface change the ip address?

* What if a device/vm changes or deletes an interface?


[DONE] netbox_zabbix.jobs.ExceptionWithData: ('Error -32602: Invalid params., Cannot link template "AXIS Debian" to host "dk-ece007w", because its parent template "ICMP Ping" would be linked twice.', -32602)


[DONE] Should I add additional information about templates to Zabbix to make
the checks easier.


[DONE] There might a logical error in how Device/VM mapping design.
  
* The interface hostid shoud be set to the Zabbix Hostid.

* Rename 'host' in Interfaces to zconf?

* Add delete button to Agent Interfaces and SNMP Interfaces under the 
  Device Components.


* Update/Delete interfaces should record the changes in the ZC change log
  and update Zabbix.

* If a global default setting changes, should all ZC and Hosts in Z also update?
  Don't think so.


* When the implementation works for Devices, implement the corresponding code
  for Virual Machines.

* Not all interface default settings are used, e.g. snmpv3_contextname.
  So go over the import code in jobs.py and make use of the default settings.


[DONE] The helper function 'quick_add_interface' should take a Zabbix Config
  instance as argument and only add an interface. Now it also creates
  the Zabbix Config which isn't correct if we want separations of concerns.


* The date when scheduling the background job should use
  
  django.utils.timezone.now() to remove the warning:
  
  RuntimeWarning: DateTimeField Job.scheduled received a naive datetime 
  
  (2025-08-21 17:43:35.860721) while time zone support is active.

* Since the background job doesn't use the system job decorator it isn't
  started automatically by NB when the rqworker is started.
  Look into how this can be fixed.

* Go over all models and make sure that the fields doesn't have unnecessary
  null=True and blank=True settings. Many of them were added to prevent having
  to dump the database when running makemigrations.

* Should the system issue a warning when a template is removed while it is still used by a default mapping?
  Should it also block the removal?
  Blocking the removal doesn’t make sense, since if the template has already been removed from Zabbix, it no longer exists anyway.
 
* Implement maintenance mode.

* Add support for IPv6primary interfaces. (Maybe)


#### General

| Action                                                       | Status        |
| ------------------------------------------------------------ | ------------- |
| Document and format the code                                 | Todo          |
| Write a user manual                                          | Todo          |
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
| Add Maintenance                                              | Todo          |
| Add a tab to vm and device that show the Zabbix Configuration. | Todo         |


#### Config

| Action                                                       | Status        |
| ------------------------------------------------------------ | ------------- |
| Add CIDR to the config                                       | Done          |
| Add Automatic Host Validation                                | Done          |
| Add TLS settings                                             | Done          |
| Add Max deletions on import                                  | Done          |
| Add Maximum Success Notifications                            | Done          |
| Add Background Job for Zabbix Config Sync                    | Done          |
| Should Max deletions on import be enabled/disabled?          | Todo          |
| Add defaults for zabbix interfaces                           | Done          |


#### NetBox Only Devices
| Action                                                       | Status        |
| ------------------------------------------------------------ | ------------- |
| Add action button to create new Zabbix config                | Todo          |
| Add action button to quick add Agent                         | Done          |
| Add action button to quick Add SNMPv3                        | Done          |


#### NetBox Only VMs
| Action                                                       | Status        |
| ------------------------------------------------------------ | ------------- |
| Add action button to create new config                       | Todo          |
| Add action button to quick add Agent                         | Todo          |
| Add action button to quick Add SNMPv3                        | Todo          |


#### Mappings
| Action                                                       | Status        |
| ------------------------------------------------------------ | ------------- |
| Tag Mappings                                                 | Done          |
| Inventory Mappings                                           | Done          |
| Device Mappings                                              | Done          |
| VM Mappings                                                  | Todo          |


#### Event Log
| Action                                                       | Status        |
| ------------------------------------------------------------ | ------------- |
| List events                                                  | Done          |
| Add support for pre/post data                                | Todo          |


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

## Notes on date conversion for Zabbix Maintenance

```python

from datetime import datetime

maintenance = {
    'maintenanceid': '1',
    'name': 'Sample',
    'maintenance_type': '0',
    'description': 'Sample Maintenance',
    'active_since': '1751493600',
    'active_till': '1751580000',
    'tags_evaltype': '0'
}

# Convert to datetime
active_since = datetime.fromtimestamp(int(maintenance['active_since']), tz=timezone.utc)
active_till = datetime.fromtimestamp(int(maintenance['active_till']), tz=timezone.utc)

print(f"Active Since: {active_since}")
print(f"Active Till: {active_till}")
```

```python
from datetime import datetime, timezone

# Your datetime object (e.g., in UTC)
dt = datetime(2025, 8, 1, 1, 0, 0, tzinfo=timezone.utc)

# Convert to Unix timestamp
unix_timestamp = int(dt.timestamp())

print(unix_timestamp)  # → 1751493600
````

Converting a Django datetime to a Zabbix-compatible Unix timestamp
```python
from django.utils import timezone

# Get a timezone-aware datetime (UTC or local based on settings)
dt = timezone.now()

# Convert to Unix timestamp
unix_timestamp = int(dt.timestamp())
````

Converting a specific datetime to a timestamp using Django's timezone

```python
from django.utils import timezone
from datetime import datetime

# Define a naive datetime
naive_dt = datetime(2025, 8, 1, 1, 0, 0)

# Make it timezone-aware using Django settings
aware_dt = timezone.make_aware(naive_dt)

# Convert to Unix timestamp
timestamp = int(aware_dt.timestamp())
```




## Credits

Based on the NetBox plugin tutorial:

- [demo repository](https://github.com/netbox-community/netbox-plugin-demo)
- [tutorial](https://github.com/netbox-community/netbox-plugin-tutorial)

This package was created with [Cookiecutter](https://github.com/audreyr/cookiecutter) and the [`netbox-community/cookiecutter-netbox-plugin`](https://github.com/netbox-community/cookiecutter-netbox-plugin) project template.
