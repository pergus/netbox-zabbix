# Setting Model

## Overview

The `Setting` model provides a centralized configuration system for managing the integration between NetBox and Zabbix monitoring systems. This comprehensive configuration framework controls how the plugin interacts with Zabbix servers, manages host configurations, and handles synchronization processes while maintaining security and operational flexibility.

## Model Definition

The Setting model stores global configuration parameters that govern plugin behavior across all operations. This centralized approach ensures consistent configuration management while providing the flexibility needed for diverse operational environments. The model implements robust validation mechanisms to prevent misconfiguration and maintains encrypted storage for sensitive credentials such as API tokens.

Configuration parameters are organized into logical groups that correspond to different aspects of plugin functionality, making it easier for administrators to understand and manage complex integration requirements. The model supports both required and optional configuration elements, allowing organizations to implement monitoring solutions that match their specific operational needs.

## Fields

| Field | Type | Description | Notes |
|-------|------|-------------|-------|
| `name` | CharField (max_length=255) | Name of the setting | Human-readable identifier |
| `ip_assignment_method` | CharField (max_length=16) | Method used to assign IPs to host interfaces | Choices: 'manual', 'primary'. Default: 'primary' |
| `event_log_enabled` | BooleanField | Enable event logging | Default: False |
| `auto_validate_importables` | BooleanField | Automatically validate importable hosts | Default: False |
| `auto_validate_quick_add` | BooleanField | Automatically validate quick-add hosts | Default: False |
| `max_deletions` | IntegerField | Limits deletions of stale entries on Zabbix imports | Default: 3 |
| `max_success_notifications` | IntegerField | Max number of success messages shown per job | Default: 3 |
| `zabbix_import_interval` | PositiveIntegerField | Interval in minutes between each Zabbix import | Choices from SystemJobIntervalChoices |
| `host_config_sync_interval` | PositiveIntegerField | Interval in minutes between each Host Config Sync check | Choices from SystemJobIntervalChoices |
| `cutoff_host_config_sync` | PositiveIntegerField | Minutes to look back when determining which HostConfigs need syncing | Default: 60 |
| `maintenance_cleanup_interval` | PositiveIntegerField | Interval in minutes between maintenance cleanup | Choices from SystemJobIntervalChoices |
| `version` | CharField (max_length=255) | Zabbix server version | Nullable |
| `api_endpoint` | CharField (max_length=255) | URL to the Zabbix API endpoint | Required |
| `web_address` | CharField (max_length=255) | URL to the Zabbix web interface | Required |
| `_encrypted_token` | TextField | Encrypted API token | Stored in encrypted format |
| `connection` | BooleanField | Connection status to Zabbix | Default: False |
| `last_checked_at` | DateTimeField | When connection was last verified | Nullable |
| `delete_setting` | CharField (max_length=10) | Delete settings mode | Choices: 'soft', 'hard'. Default: 'soft' |
| `graveyard` | CharField (max_length=255) | Host Group for soft deletes | Default: "graveyard" |
| `graveyard_suffix` | CharField (max_length=255) | Suffix for deleted hosts | Default: "_archived" |
| `exclude_custom_field_name` | CharField (max_length=255) | Custom field name for exclusion | Default: "Exclude from Zabbix" |
| `exclude_custom_field_enabled` | BooleanField | Enable custom field exclusion | Default: False |
| `useip` | IntegerField | Connect via IP or DNS | Choices from UseIPChoices. Default: IP |
| `inventory_mode` | IntegerField | Mode for populating inventory | Choices from InventoryModeChoices. Default: MANUAL |
| `monitored_by` | IntegerField | Method used to monitor hosts | Choices from MonitoredByChoices. Default: ZabbixServer |
| `tls_connect` | IntegerField | TLS mode for outgoing connections | Choices from TLSConnectChoices. Default: PSK |
| `tls_accept` | IntegerField | TLS mode accepted for incoming connections | Choices from TLSAcceptChoices. Default: PSK |
| `tls_psk_identity` | CharField (max_length=255) | PSK identity | Nullable |
| `tls_psk` | CharField (max_length=255) | Pre-shared key | Nullable |
| `agent_port` | IntegerField | Agent default port | Default: 10050 |
| `snmp_port` | IntegerField | SNMP default port | Default: 161 |
| `snmp_bulk` | IntegerField | Whether to use bulk SNMP requests | Choices from SNMPBulkChoices. Default: YES |
| `snmp_max_repetitions` | IntegerField | Max repetition value for native SNMP bulk requests | Default: 10 |
| `snmp_contextname` | CharField (max_length=255) | SNMP context name | Nullable |
| `snmp_securityname` | CharField (max_length=255) | SNMP security name | Default: "{$SNMPV3_USER}" |
| `snmp_securitylevel` | IntegerField | SNMP security level | Choices from SNMPSecurityLevelChoices. Default: authPriv |
| `snmp_authprotocol` | IntegerField | SNMP authentication protocol | Choices from SNMPAuthProtocolChoices. Default: SHA1 |
| `snmp_authpassphrase` | CharField (max_length=255) | SNMP authentication passphrase | Default: "{$SNMPV3_AUTHPASS}" |
| `snmp_privprotocol` | IntegerField | SNMP privacy protocol | Choices from SNMPPrivProtocolChoices. Default: AES128 |
| `snmp_privpassphrase` | CharField (max_length=255) | SNMP privacy passphrase | Default: "{$SNMPV3_PRIVPASS}" |
| `default_tag` | CharField (max_length=255) | Tag applied to all hosts | Nullable |
| `tag_prefix` | CharField (max_length=255) | Prefix added to all tags | Nullable |
| `tag_name_formatting` | CharField (max_length=10) | Tag name formatting | Choices: 'keep', 'upper', 'lower'. Default: 'keep' |

## Properties

### `token`

Property for getting and setting the encrypted API token.

**Getter Returns:**
- `str` or `None`: Decrypted token or None if decryption fails

**Setter:**
- Encrypts and stores the provided token value

## Methods

### `__str__()`

Return a human-readable string representation of the object.

**Returns:**
- `str`: Human-readable name of the object

### `get_absolute_url()`

Return the canonical URL for this object within the plugin UI.

**Returns:**
- `str`: Absolute URL for the setting

### `get_system_jobs_scheduled()`

Return the system job scheduled status.

**Returns:**
- HTML-formatted string with checkmark or cross indicating job status

### `get_fernet()`

Return a Fernet instance if the key exists.

**Returns:**
- `Fernet` instance or `None`

### `token` (property)

Getter and setter for the encrypted token.

**Returns:**
- Decrypted token (getter) or None if decryption fails
- Sets encrypted token (setter)

### `save(*args, **kwargs)`

Save the Setting instance to the database and schedule system jobs.

**Parameters:**
- `*args`: Positional arguments passed to the model save method
- `**kwargs`: Keyword arguments passed to the model save method

## Usage Examples

### Creating a Basic Setting Configuration
```python
from netbox_zabbix.models import Setting

# Create a basic setting configuration
setting = Setting.objects.create(
    name="Production Zabbix",
    api_endpoint="https://zabbix.example.com/api_jsonrpc.php",
    web_address="https://zabbix.example.com/",
    # Add other required fields as needed
)
```

### Configuring Connection Settings
```python
# Configure Zabbix server connection
setting.api_endpoint = "https://zabbix.example.com/api_jsonrpc.php"
setting.web_address = "https://zabbix.example.com/"
setting.token = "your-api-token-here"  # Will be encrypted automatically
setting.save()
```

### Setting Up TLS Configuration
```python
from netbox_zabbix.models import TLSConnectChoices, TLSAcceptChoices

# Configure PSK encryption
setting.tls_connect = TLSConnectChoices.PSK
setting.tls_accept = TLSAcceptChoices.PSK
setting.tls_psk_identity = "my_plugin_identity"
setting.tls_psk = "a1b2c3d4e5f67890abcdef1234567890"  # Should be at least 32 hex digits
setting.save()
```

### Configuring Host Management Settings
```python
# Configure deletion settings
setting.delete_setting = "soft"  # or "hard"
setting.graveyard = "archived_hosts"
setting.graveyard_suffix = "_deleted"
setting.save()

# Configure exclusion settings
setting.exclude_custom_field_name = "Exclude from Monitoring"
setting.exclude_custom_field_enabled = True
setting.save()
```

### Setting Up SNMP Defaults
```python
from netbox_zabbix.models import SNMPSecurityLevelChoices, SNMPAuthProtocolChoices, SNMPPrivProtocolChoices

# Configure SNMP defaults
setting.snmp_port = 161
setting.snmp_securitylevel = SNMPSecurityLevelChoices.authPriv
setting.snmp_authprotocol = SNMPAuthProtocolChoices.SHA1
setting.snmp_privprotocol = SNMPPrivProtocolChoices.AES128
setting.save()
```

### Configuring System Job Intervals
```python
from netbox_zabbix.models import SystemJobIntervalChoices

# Configure system job intervals
setting.zabbix_import_interval = SystemJobIntervalChoices.INTERVAL_HOURLY
setting.host_config_sync_interval = SystemJobIntervalChoices.INTERVAL_EVERY_2_HOURS
setting.maintenance_cleanup_interval = SystemJobIntervalChoices.INTERVAL_DAILY
setting.save()
```

## Integration with Other Models

Setting integrates with several other components in the plugin:

1. **System Jobs**: Settings control the frequency and behavior of automated system jobs for importing Zabbix data and synchronizing host configurations.

2. **HostConfig Model**: Settings provide default values and configuration parameters that are used when creating and managing HostConfig objects.

3. **Proxy and ProxyGroup Models**: Settings define default TLS and connection parameters that are used for proxy configurations.

4. **Interface Models**: Settings provide default port numbers, TLS configurations, and connection methods for both AgentInterface and SNMPInterface objects.

5. **Zabbix API**: Settings store the connection information and authentication credentials needed to communicate with the Zabbix API.

## Description

The Setting model provides a comprehensive configuration framework that controls all aspects of the NetBox Zabbix plugin's operation. It centralizes configuration management, making it easier to maintain consistent settings across different environments and deployment scenarios.

Key configuration areas managed by the Setting model include:

**Connection Management:**
- Zabbix server API endpoint and web interface URLs
- Authentication token storage with encryption
- Connection status monitoring and verification

**Host Configuration:**
- Default interface settings for agent and SNMP connections
- IP assignment methods and connection preferences
- Inventory mode configurations
- Default monitoring sources (server, proxy, or proxy group)

**Security Configuration:**
- TLS connection settings for encrypted communications
- PSK identity and key management
- Certificate-based authentication parameters

**Operational Parameters:**
- System job scheduling intervals for imports and synchronization
- Deletion policies for soft vs. hard deletion of monitoring objects
- Event logging and notification thresholds
- Automatic validation settings for importable and quick-add hosts

**Exclusion Management:**
- Custom field-based exclusion of NetBox objects from monitoring
- Configuration of exclusion field names and enablement

**Tagging Configuration:**
- Default tags applied to all synchronized hosts
- Tag prefix configurations for namespace organization
- Tag name formatting options (uppercase, lowercase, or preserved)

The model implements robust validation to prevent misconfiguration and ensures that sensitive data like API tokens are properly encrypted. It also provides programmatic access to settings through helper methods and properties, making it easy for other parts of the plugin to retrieve configuration values safely.