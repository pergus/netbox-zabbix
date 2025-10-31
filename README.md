# netbox-zabbix

NetBox plugin for Zabbix.


* Free software: MIT
* Documentation: https://pergus.github.io/netbox-zabbix/



## Logging

Use logger.error() when something is wrong and action may be required (exceptions, inconsistent state, missing required data).

Use logger.info() only for high-level events that operators care about (host created, host updated, config deleted). Keep these concise.

Use logger.debug() for internal decisions and state checks (branching logic, computed values). Wrap in f-strings only if cheap to evaluate, or use lazy logging (%s) to avoid overhead when debug is off. 


Examples

| When                              | Level | Why                                 |
| --------------------------------- | ------|------------------------------------ |
| Function entry + decision details | debug | Only useful during troubleshooting. |
| “No DeviceZabbixConfig found … Skipping update.” | warning | Likely a configuration issue. |
| Job queued successfully           | info  | Operational event worth recording in production. |


### Bugs



### Todo/Bugs


[DONE] Implement filtering where applicable.

[DONE] Add user to the event log.

* Add Tags

* Access control.

* Add options in Setting to control how the diff between NetBox and Zabbix should
  behave. strict/lenient?

[DONE] Should the zabbix host pre-data be normalized before it is displayed or 
  when it is saved to the event/job logs? I could just normalize it
  when displaying the data just in case we need the full data...dunno.

* Should the system issue a warning when a template is removed while it is 
  still used by a default mapping? - Yes!
  Should it also block the removal? - No

  Blocking the removal doesn’t make sense, since if the template has already 
  been removed from Zabbix, it no longer exists anyway.
  Also, it is ok for a host in Zabbix not have any templates.

* Should NetBox be the source for proxies, proxy group and groups?
  And Zabbix should only be the source for Templates?

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

* Make sure the API works as expected.

* Implement maintenance mode.


[DONE] Rename 'zabbix_config_model' in jobs to 'config_model'.


[DONE] When the implementation works for Devices, implement the corresponding code
  for Virual Machines.

[DONE] Replace checks for interfaces in forms? with calls to has_agent_interface & has_snmpv3_interface.


[DONE] It should not be possible to assign an ip address to a zabbix interface
  for an ip that isn't associated with the underlyin device or vm.
  Let's say we have two devices A and B. It should not be possible to
  create a zabbix interface for A and assign it an IP that belongs to B.

[DONE] Edit zabbix configuration - when chaning monitored by to say proxy, then
  the form should force the user to add a proxy. The same goes for proxy group.


[DONE] Added has_agent_interface/has_snmpv3_interface methods to ZConfig.

[DONE] Rename 'host' in Interfaces to zabbix_config or zcfg?

[DONE] Not having a proper name for ZabbixConfig's makes it problematic for scripting and searching.


[DONE] CF that excludes a machine from appearing in NetBox only.

[DONE] Bug - Users can delete the Configuration.

[DONE] Should deleting a host in zabbix that doesn't exist cause an exception?
  Exception: Failed to soft delete zabbix host 11537: No host with host id '11537' found in Zabbix
  No the jobs should not cause an exception. But a warning as result.


[DONE] Handle delete of an ip addres and/or interface on a device.

[DONE] Handle delete of an Z-interface.

[DONE] Failsafe delete - implemented Hard/Soft delete.

[DONE] DNS name changes

[DONE] netbox_zabbix.jobs.ExceptionWithData: ('Error -32602: Invalid params., 
       Cannot link template "AXIS Debian" to host "dk-ece007w", because its 
       parent template "ICMP Ping" would be linked twice.', -32602)

[DONE] Should I add additional information about templates to Zabbix to make
       the checks easier.

[DONE] There might a logical error in how Device/VM mapping design.

[DONE] The interface hostid shoud be set to the Zabbix Hostid.

[DONE] Add delete button to Agent Interfaces and SNMP Interfaces.
This took longer than expected beacuse I couldn't get it to work.
The solution was to implement bulk delete.

[DONE] Update/Delete interfaces should record the changes in the ZC change log
       and update Zabbix.

[DONE] Import doesn't include proxy/proxy group.

[DNE] Mapping ins't updated when the user change page for Devices Exclusive To NetBox.
        To update the mapping the user has to reload the page....

[DONE] The helper function 'quick_add_interface' should take a Zabbix Config
  instance as argument and only add an interface. Now it also creates
  the Zabbix Config which isn't correct if we want separations of concerns.

[WAIT] If a global default setting changes, should all ZC and Hosts in Z also update?
  Don't think so.



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
| Add a tab to vm and device that show the Zabbix Configuration. | Done         |


#### Settings

| Action                                                       | Status        |
| ------------------------------------------------------------ | ------------- |
| Add Automatic Host Validation                                | Done          |
| Add TLS settings                                             | Done          |
| Add Max deletions on import                                  | Done          |
| Add Maximum Success Notifications                            | Done          |
| Add Background Job for Zabbix Config Sync                    | Done          |
| Should Max deletions on import be enabled/disabled?          | Done          |
| Add defaults for zabbix interfaces                           | Done          |


#### NetBox Only Hosts
| Action                                                       | Status        |
| ------------------------------------------------------------ | ------------- |
| Add action button to quick add Agent                         | Done          |
| Add action button to quick Add SNMP                          | Done          |


#### Mappings
| Action                                                       | Status        |
| ------------------------------------------------------------ | ------------- |
| Tag Mappings                                                 | Done          |
| Inventory Mappings                                           | Done          |
| Device Mappings                                              | Done          |
| VM Mappings                                                  | Done          |


#### Event Log
| Action                                                       | Status        |
| ------------------------------------------------------------ | ------------- |
| List events                                                  | Done          |
| Add support for pre/post data                                | Done          |


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
