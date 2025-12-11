# NetBox Zabbix Plugin Admin Guide

## Overview

This guide is designed for **Administrators** responsible for configuring and maintaining the NetBox Zabbix plugin. It covers configuration, management of monitoring objects, system jobs, and administrative tasks.

## Plugin Configuration

### Initial Setup Review

After installation, administrators should review several critical configuration areas to ensure proper operation. Connection settings must be verified to confirm that the plugin can successfully communicate with the Zabbix API endpoint. Security configuration requires careful attention to token permissions and key storage practices to protect sensitive credentials. Default device and virtual machine mappings should be reviewed and adjusted to match organizational requirements, ensuring appropriate monitoring policies are applied automatically. System job intervals need to be configured based on environment size and change frequency to balance synchronization needs with system performance.


## Settings Management

Administrators access Settings through the Zabbix plugin menu under **Admin → Settings**. Each setting includes a descriptive name and a default vaule when possible.

| Setting                           | Default Value       | Description                                                            |
| --------------------------------- | ------------------- | ---------------------------------------------------------------------- |
| **Name**                          | N/A (Required)      | Human-readable identifier for this settings configuration              |
| **IP Assignment Method**          | PRIMARY             | Method used to assign IPs to host interfaces                           |
| **Event Log Enabled**             | False               | Enable or disable logging of plugin events                             |
| **Validate Importables**          | False               | Automatically validate hosts eligible for import from Zabbix           |
| **Validate Quick Add**            | False               | Automatically validate hosts eligible for Quick Add                    |
| **Max Deletions On Import**       | 3                   | Limit deletions of stale entries during Zabbix imports                 |
| **Maximum Success Notifications** | 3                   | Max number of success messages shown per job                           |
| **Zabbix Import Interval**        | Daily               | Interval in minutes between each Zabbix import                         |
| **Host Config Sync Interval**     | Daily               | Interval in minutes between Host Config Sync checks                    |
| **Host Config Sync Cutoff**       | 60                  | Minutes to look back when determining which HostConfigs need syncing   |
| **Maintenance Cleanup Interval**  | Daily               | Interval in minutes between maintenance cleanups                       |
| **Version**                       | None                | Zabbix server version (auto-detected)                                  |
| **API Endpoint**                  | N/A (Required)      | URL to the Zabbix API endpoint                                         |
| **Web Address**                   | N/A (Required)      | URL to the Zabbix web interface                                        |
| **Connection**                    | False               | Shows if the plugin can successfully connect to Zabbix                 |
| **Last Checked At**               | None                | Timestamp of last connectivity check                                   |
| **Delete Settings**               | SOFT                | Method for deleting settings (SOFT moves to graveyard, HARD permanent) |
| **Host Group (Graveyard)**        | graveyard           | Host group used for soft-deleted hosts                                 |
| **Deleted Host Suffix**           | _archived           | Suffix appended to soft-deleted hosts                                  |
| **Exclusion Custom Field**        | Exclude from Zabbix | Custom field to exclude objects from synchronization                   |
| **Exclude Custom Field Enabled**  | False               | Enable or disable exclusion based on the custom field                  |
| **Use IP**                        | IP                  | Connect via IP or DNS name                                             |
| **Inventory Mode**                | MANUAL              | Method for populating inventory in Zabbix                              |
| **Monitored By**                  | ZabbixServer        | Method used to monitor hosts (direct, proxy, or proxy group)           |
| **TLS Connect**                   | PSK                 | TLS mode for outgoing connections                                      |
| **TLS Accept**                    | PSK                 | TLS mode accepted for incoming connections                             |
| **PSK Identity**                  | None                | Pre-shared key identity for TLS                                        |
| **TLS PSK**                       | None                | Pre-shared key for TLS encryption                                      |
| **Agent Port**                    | 10050               | Default port for Zabbix agent connections                              |
| **SNMP Port**                     | 161                 | Default port for SNMP connections                                      |
| **SNMP Bulk**                     | YES                 | Whether to use bulk SNMP requests                                      |
| **SNMP Max Repetitions**          | 10                  | Max repetition for SNMP bulk requests                                  |
| **SNMP Context Name**             | None                | SNMP context name                                                      |
| **SNMP Security Name**            | {$SNMPV3_USER}      | SNMP security name                                                     |
| **Security Level**                | authPriv            | SNMP security level                                                    |
| **Authentication Protocol**       | SHA1                | SNMP authentication protocol                                           |
| **Authentication Passphrase**     | {$SNMPV3_AUTHPASS}  | SNMP authentication passphrase                                         |
| **Privacy Protocol**              | AES128              | SNMP privacy protocol                                                  |
| **Privacy Passphrase**            | {$SNMPV3_PRIVPASS}  | SNMP privacy passphrase                                                |
| **Default Tag**                   | None                | Tag applied to all hosts                                               |
| **Tag Prefix**                    | None                | Prefix added to all tags                                               |
| **Tag Name Formatting**           | KEEP                | Formatting method for tag names                                        |



## Mappings Management

Mappings automate assignment of Zabbix monitoring settings to Devices and VMs in NetBox. They allow hosts to be automatically associated with host groups, templates, and proxies based on characteristics.

### How Mappings Work

When creating a new host configuration, the plugin evaluates all non-default mappings for that host type and compares the host's characteristics against mapping rules. The evaluation process considers site membership, role assignments, platform types, and interface configurations to find the most appropriate match. The system applies the most specific mapping available, favoring mappings with more defined filters over broader rules. If no specific mapping matches the host's characteristics, the default mapping is automatically applied to ensure basic monitoring coverage.


### Mapping Types

- **Device Mappings**: For physical devices.
- **VM Mappings**: For virtual machines.

Each mapping defines host groups, templates, proxy or proxy group assignments, interface type restrictions, and optional filters based on sites, roles, or platforms. A default mapping serves as a fallback.

### Creating a Mapping

1. Navigate to the Mappings section in the plugin.
2. Select Device Mapping or VM Mapping and click Add.
3. Complete the form with fields such as Name, Host Groups, Templates, Proxy/Proxy Group, Interface Type, Sites, Roles, Platforms, and Description.

### Viewing Matching Objects

Click on a mapping name and select "Matching Devices" or "Matching VMs" to see which objects currently satisfy the mapping criteria.


## Proxy, Proxy Group, and Host Group Management

### Proxy Group Management

- **Creating**: Navigate to Admin > Proxy Groups → Add, fill out Proxy Group name, Failover period, Minimum proxies, optional Description, and click Create.
- **Editing**: Update fields, changes sync automatically with Zabbix.
- **Importing**: Import existing groups during setup or manually.
- **Deleting**: Removes the group from NetBox; warns if deletion fails in Zabbix.

### Proxy Management

- **Creating**: Admin > Proxies → Add, complete Proxy Name, Proxy Group, Operating Mode, Local/Interface addresses and ports, Allowed Addresses, TLS settings, optional Timeouts, and click Create.
- **Editing**: Update fields; changes sync automatically.
- **Importing**: Existing proxies can be imported.
- **Deleting**: Removes proxy; warns if deletion fails in Zabbix.

### Host Group Management

- **Creating**: Admin > Host Groups → Add, enter Hostgroup Name and optional description, click Create.
- **Editing**: Update names or descriptions; syncs automatically.
- **Importing**: Import existing groups.
- **Deleting**: Removes groups; warns if Zabbix deletion fails.

### Best Practices

- Use descriptive names.
- Ensure at least one proxy online per group.
- Regularly review and update proxies and groups.
- Validate imported objects maintain correct linkage.






## System Job Configuration

Background jobs automate tasks like host creation, synchronization, and maintenance.

- **Job Types**: Zabbix Import, Host Config Sync, Maintenance Cleanup.
- **Intervals**: Adjust frequencies based on environment size and criticality.
- **Monitoring**: View Job History, track performance metrics, and trigger manual execution as needed.

## Monitoring and Maintenance

### Health Checks

- **Connection Status**: Verify Zabbix API connectivity.
- **Job Health**: Ensure scheduled jobs run successfully.
- **Synchronization Status**: Detect out-of-sync hosts.
- **Resource Usage**: Monitor database and system performance.


*For day-to-day user operations, see the User Guide. For technical implementation details, see the Programmer's Guide.*