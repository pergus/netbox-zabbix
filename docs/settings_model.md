# NetBox Zabbix Plugin - Settings Documentation

The Settings in the NetBox Zabbix plugin provides a centralized configuration system for managing the integration between NetBox and Zabbix. This document explains each configuration option, its purpose, and default values.

## Overview

The Settings stores global configuration parameters that control how the plugin interacts with Zabbix servers, manages host configurations, and handles synchronization processes.

## General Settings

| Setting | Description | Default Value | Notes |
|---------|-------------|---------------|-------|
| `name` | Configuration name | N/A (Required) | Human-readable identifier for this settings configuration |
| `ip_assignment_method` | Method for assigning IPs to host interfaces | `PRIMARY` | Options: `MANUAL` or `PRIMARY` (uses host's primary IPv4 address) |
| `event_log_enabled` | Enable event logging | `False` | When enabled, logs plugin events for troubleshooting |
| `auto_validate_importables` | Auto-validate importable hosts | `False` | Automatically validates hosts eligible for import from Zabbix |
| `auto_validate_quick_add` | Auto-validate quick add hosts | `False` | Automatically validates hosts eligible for quick addition |

## Background Job Settings

| Setting | Description | Default Value | Notes |
|---------|-------------|---------------|-------|
| `max_deletions` | Limits deletions of stale entries on Zabbix imports | `3` | Prevents accidental mass deletions during import operations |
| `max_success_notifications` | Maximum success messages per job | `3` | Controls verbosity of job completion notifications |

## System Job Settings

| Setting | Description | Default Value | Notes |
|---------|-------------|---------------|-------|
| `zabbix_import_interval` | Interval between Zabbix imports | `Daily` | Frequency for importing data from Zabbix |
| `host_config_sync_interval` | Host configuration sync frequency | `Daily` | How often to check host configuration synchronization |
| `cutoff_host_config_sync` | Sync lookback period (minutes) | `60` | Time window for determining which hosts need sync |
| `maintenance_cleanup_interval` | Maintenance cleanup frequency | `Daily` | How often to clean up expired maintenance windows |

## Zabbix Server Connection Settings

| Setting | Description | Default Value | Notes |
|---------|-------------|---------------|-------|
| `api_endpoint` | Zabbix API URL | N/A (Required) | Full URL to the Zabbix API endpoint (e.g., https://zabbix.example.com/api_jsonrpc.php) |
| `web_address` | Zabbix web interface URL | N/A (Required) | URL to the Zabbix web interface for linking |
| `token` | API authentication token | N/A | Encrypted API token for authenticating with Zabbix (stored securely) |
| `version` | Zabbix version | N/A | Automatically detected Zabbix version |
| `connection` | Connection status | `False` | Indicates if connection to Zabbix is currently successful |
| `last_checked_at` | Last connection check timestamp | N/A | Timestamp of the last connection verification |

## Deletion Settings

| Setting | Description | Default Value | Notes |
|---------|-------------|---------------|-------|
| `delete_setting` | Deletion mode | `SOFT` | Options: `SOFT` (move to graveyard) or `HARD` (permanent deletion) |
| `graveyard` | Host group for soft-deleted hosts | `"graveyard"` | Name of the Zabbix host group where soft-deleted hosts are moved |
| `graveyard_suffix` | Suffix for deleted hosts | `"_archived"` | Suffix appended to hostnames when moved to graveyard |

## Exclusion Settings

| Setting | Description | Default Value | Notes |
|---------|-------------|---------------|-------|
| `exclude_custom_field_name` | Custom field for exclusion | `"Exclude from Zabbix"` | Name of the custom field used to exclude devices/VMs from Zabbix sync |
| `exclude_custom_field_enabled` | Enable exclusion field | `False` | When enabled, objects with the exclusion field set will be skipped |

## Common Protocol Defaults

| Setting | Description | Default Value | Notes |
|---------|-------------|---------------|-------|
| `useip` | Connection method | `IP` | Options: `IP` (use IP address) or `DNS` (use DNS name) |
| `inventory_mode` | Inventory population mode | `MANUAL` | Options: `DISABLED`, `MANUAL`, or `AUTOMATIC` |
| `monitored_by` | Monitoring source | `ZabbixServer` | Options: `ZabbixServer`, `Proxy`, or `ProxyGroup` |
| `tls_connect` | TLS connection mode | `PSK` | Options: `NoEncryption`, `PSK`, or `CERTIFICATE` |
| `tls_accept` | TLS acceptance mode | `PSK` | Options: `NoEncryption`, `PSK`, or `CERTIFICATE` |
| `tls_psk_identity` | PSK identity | N/A | Identity string for PSK authentication |
| `tls_psk` | Pre-shared key | N/A | PSK value for secure connections (minimum 32 hex digits) |

## Agent Interface Defaults

| Setting | Description | Default Value | Notes |
|---------|-------------|---------------|-------|
| `agent_port` | Default agent port | `10050` | Port number for Zabbix agent connections |

## SNMP Interface Defaults

| Setting | Description | Default Value | Notes |
|---------|-------------|---------------|-------|
| `snmp_port` | Default SNMP port | `161` | Port number for SNMP connections |
| `snmp_bulk` | Use bulk requests | `YES` | Options: `NO` or `YES` |
| `snmp_max_repetitions` | Max repetitions | `10` | Maximum repetition value for SNMP bulk requests |
| `snmp_contextname` | SNMP context name | N/A | Context name for SNMP operations |
| `snmp_securityname` | Security name | `"{$SNMPV3_USER}"` | SNMPv3 security name |
| `snmp_securitylevel` | Security level | `authPriv` | Options: `noAuthNoPriv`, `authNoPriv`, or `authPriv` |
| `snmp_authprotocol` | Authentication protocol | `SHA1` | Options: `MD5`, `SHA1`, `SHA224`, `SHA256`, `SHA384`, `SHA512` |
| `snmp_authpassphrase` | Authentication passphrase | `"{$SNMPV3_AUTHPASS}"` | Passphrase for SNMP authentication |
| `snmp_privprotocol` | Privacy protocol | `AES128` | Options: `DES`, `AES128`, `AES192`, `AES256`, `AES192C`, `AES256C` |
| `snmp_privpassphrase` | Privacy passphrase | `"{$SNMPV3_PRIVPASS}"` | Passphrase for SNMP privacy |

## Tag Settings

| Setting | Description | Default Value | Notes |
|---------|-------------|---------------|-------|
| `default_tag` | Tag applied to all hosts | N/A | Global tag that will be added to all synchronized hosts |
| `tag_prefix` | Prefix for all tags | N/A | String prefix added to all tag names |
| `tag_name_formatting` | Tag name formatting | `KEEP` | Options: `KEEP` (as entered), `UPPER` (uppercase), or `LOWER` (lowercase) |

## Validation and Constraints

The Settings model implements several validation mechanisms to ensure data integrity:

1. **Choice Fields**: Many settings use predefined choice sets to restrict values to valid options:
   - `IPAssignmentChoices`: `MANUAL`, `PRIMARY`
   - `MonitoredByChoices`: `ZabbixServer`, `Proxy`, `ProxyGroup`
   - `TLSConnectChoices`/`TLSAcceptChoices`: `NoEncryption`, `PSK`, `CERTIFICATE`
   - `InventoryModeChoices`: `DISABLED`, `MANUAL`, `AUTOMATIC`
   - `TagNameFormattingChoices`: `KEEP`, `UPPER`, `LOWER`
   - `DeleteSettingChoices`: `SOFT`, `HARD`
   - `UseIPChoices`: `DNS`, `IP`

2. **Encrypted Token Storage**: The API token is encrypted using Fernet encryption before storage, ensuring sensitive credentials are protected.

3. **Data Type Constraints**: Integer fields enforce numeric values, and required fields prevent incomplete configurations.

4. **Custom Validation**: The model includes custom validation in the `clean()` method for interface/IP matching and ensures only one main interface exists per host configuration.

## Accessing Settings

Settings can be accessed programmatically through helper functions in `settings.py`:

```python
from netbox_zabbix.settings import get_settings

# Get the settings object
settings = get_settings()

# Or use specific getter functions
from netbox_zabbix.settings import (
    get_zabbix_api_endpoint,
    get_useip,
    get_agent_port,
    # ... many more getters
)

api_endpoint = get_zabbix_api_endpoint()
agent_port = get_agent_port()
```

These helper functions provide safe access to settings with appropriate default values when settings are not configured.