# NetBox Zabbix Plugin - Proxy Documentation

## Overview

The Proxy in the NetBox Zabbix plugin represents Zabbix proxies, which are intermediary components that can collect monitoring data from agents and send it to the Zabbix server. This document explains the Proxy's structure, fields, properties, methods, and usage.

## Model Definition

The Proxy synchronizes with Zabbix proxies and maintains comprehensive configuration parameters including networking, encryption, and timeout settings. Proxies can operate in active or passive modes and can be organized into proxy groups for high availability.

## Fields

| Field | Type | Description | Default/Notes |
|-------|------|-------------|---------------|
| `name` | CharField (max_length=255) | Name of the proxy | Human-readable identifier |
| `proxyid` | CharField (max_length=255) | Unique identifier in Zabbix | Blank/null allowed |
| `proxy_groupid` | CharField (max_length=255) | Proxy group identifier | Blank/null allowed |
| `proxy_group` | ForeignKey (ProxyGroup) | Associated proxy group | Null/blank allowed, related_name='proxies' |
| `last_synced` | DateTimeField | Last synchronization timestamp | Blank/null allowed |
| `description` | TextField | Description of the proxy | Blank/null allowed |
| `operating_mode` | PositiveSmallIntegerField | Proxy operating mode | Default: ACTIVE (0). Options: ACTIVE (0), PASSIVE (1) |
| `local_address` | GenericIPAddressField | Address for active agents | Default: "", blank/null allowed |
| `local_port` | PositiveIntegerField | Proxy port for active mode | Default: 10051, blank/null allowed |
| `allowed_addresses` | CharField | Allowed addresses for active proxy | Blank/null allowed |
| `address` | GenericIPAddressField | Interface address | Default: "127.0.0.1", blank/null allowed |
| `port` | PositiveIntegerField | Port for passive mode | Default: 10051, blank/null allowed |
| `tls_connect` | PositiveSmallIntegerField | TLS mode for outgoing connections | Default: NoEncryption (1). Options: NoEncryption (1), PSK (2), Certificate (4) |
| `tls_accept` | PositiveSmallIntegerField | TLS mode for incoming connections | Default: NoEncryption (1). Options: NoEncryption (1), PSK (2), Certificate (4) |
| `tls_issuer` | CharField (max_length=255) | Certificate issuer DN | Blank/null allowed |
| `tls_subject` | CharField (max_length=255) | Certificate subject DN | Blank/null allowed |
| `tls_psk_identity` | CharField (max_length=255) | PSK identity | Blank/null allowed |
| `tls_psk` | CharField (max_length=255) | Pre-shared key | Blank/null allowed |
| `custom_timeouts` | BooleanField | Enable custom timeout settings | Default: False |
| `timeout_zabbix_agent` | CharField (max_length=255) | Zabbix agent check timeout | Default: "4s", blank/null allowed |
| `timeout_simple_check` | CharField (max_length=255) | Simple check timeout | Default: "4s", blank/null allowed |
| `timeout_snmp_agent` | CharField (max_length=255) | SNMP agent check timeout | Default: "4s", blank/null allowed |
| `timeout_external_check` | CharField (max_length=255) | External check timeout | Default: "4s", blank/null allowed |
| `timeout_db_monitor` | CharField (max_length=255) | Database monitor timeout | Default: "4s", blank/null allowed |
| `timeout_http_agent` | CharField (max_length=255) | HTTP agent check timeout | Default: "4s", blank/null allowed |
| `timeout_ssh_agent` | CharField (max_length=255) | SSH agent check timeout | Default: "4s", blank/null allowed |
| `timeout_telnet_agent` | CharField (max_length=255) | Telnet agent check timeout | Default: "4s", blank/null allowed |
| `timeout_script` | CharField (max_length=255) | Custom script timeout | Default: "4s", blank/null allowed |
| `timeout_browser` | CharField (max_length=255) | Browser-based check timeout | Default: "60s", blank/null allowed |

### `name`
The human-readable name of the proxy as it appears in both NetBox and Zabbix. This field serves as the primary identifier for the proxy.

### `proxyid`
The unique identifier assigned by Zabbix for this proxy. This field is populated automatically when the proxy is created or synchronized with Zabbix.

### `proxy_groupid`
Identifier for the proxy group that this proxy belongs to in Zabbix. This field is populated automatically when the proxy is synchronized with Zabbix.

### `proxy_group`
Foreign key relationship to the ProxyGroup object that this proxy belongs to. This allows for high availability configurations through proxy groups.

### `last_synced`
Timestamp indicating when the proxy was last synchronized with Zabbix. This helps track the freshness of the data in NetBox compared to Zabbix.

### `description`
An optional textual description of the proxy's purpose or configuration.

### `operating_mode`
Determines how the proxy operates:
- `ACTIVE` (0): The proxy actively connects to agents to collect data
- `PASSIVE` (1): The proxy waits for the Zabbix server to connect and request data

### Network Configuration Fields

#### Active Mode Fields
- `local_address`: IP address or DNS name where agents connect to the proxy in active mode
- `local_port`: Port number where agents connect to the proxy in active mode
- `allowed_addresses`: Comma-delimited list of IP addresses or DNS names allowed to connect to the active proxy

#### Passive Mode Fields
- `address`: IP address or DNS name where the Zabbix server connects to the proxy in passive mode
- `port`: Port number where the Zabbix server connects to the proxy in passive mode

### Encryption Fields
- `tls_connect`: TLS mode for outgoing connections to agents and Zabbix server
- `tls_accept`: TLS mode for incoming connections from agents and Zabbix server
- `tls_issuer`: Certificate issuer distinguished name for certificate-based TLS
- `tls_subject`: Certificate subject distinguished name for certificate-based TLS
- `tls_psk_identity`: Pre-shared key identity for PSK-based TLS
- `tls_psk`: Pre-shared key string for PSK-based TLS

### Timeout Fields
- `custom_timeouts`: Flag to enable custom timeout settings
- `timeout_zabbix_agent`: Timeout for Zabbix agent checks (1-600 seconds)
- `timeout_simple_check`: Timeout for simple checks (1-600 seconds)
- `timeout_snmp_agent`: Timeout for SNMP agent checks (1-600 seconds)
- `timeout_external_check`: Timeout for external checks (1-600 seconds)
- `timeout_db_monitor`: Timeout for database monitoring checks (1-600 seconds)
- `timeout_http_agent`: Timeout for HTTP agent checks (1-600 seconds)
- `timeout_ssh_agent`: Timeout for SSH agent checks (1-600 seconds)
- `timeout_telnet_agent`: Timeout for Telnet agent checks (1-600 seconds)
- `timeout_script`: Timeout for custom scripts (1-600 seconds)
- `timeout_browser`: Timeout for browser-based checks (1-600 seconds)

## Methods

### `__str__()`
Returns the proxy name as a human-readable string representation.

**Returns:**
- `str`: Proxy name

### `get_absolute_url()`
Returns the canonical URL for this proxy within the NetBox plugin UI.

**Returns:**
- `str`: Absolute URL for the proxy

### `_build_params()`
Constructs the parameters dictionary for Zabbix API create/update proxy calls. This method handles the conditional inclusion of parameters based on operating mode, encryption settings, and timeout configurations.

**Returns:**
- `dict`: Parameters dictionary for Zabbix API calls

### `create_new_proxy()`
Creates a new proxy in Zabbix with the current configuration parameters.

### `update_existing_proxy()`
Updates an existing proxy in Zabbix with the current configuration parameters.

### `delete(*args, **kwargs)`
Attempts to delete the proxy from Zabbix. If successful, also removes it from NetBox. If Zabbix deletion fails, returns a warning but still removes from NetBox.

### `save(*args, **kwargs)`
Overrides the default save method to synchronize the `proxy_groupid` with the associated `proxy_group` foreign key relationship.

## Usage Examples

### Creating an Active Proxy
```python
from netbox_zabbix.models import Proxy, ProxyModeChoices

# Create an active proxy
active_proxy = Proxy.objects.create(
    name="Active Proxy 1",
    operating_mode=ProxyModeChoices.ACTIVE,
    local_address="192.168.1.100",
    local_port=10051,
    allowed_addresses="192.168.1.0/24"
)
```

### Creating a Passive Proxy
```python
from netbox_zabbix.models import Proxy, ProxyModeChoices

# Create a passive proxy
passive_proxy = Proxy.objects.create(
    name="Passive Proxy 1",
    operating_mode=ProxyModeChoices.PASSIVE,
    address="192.168.1.101",
    port=10051
)
```

### Configuring Encryption
```python
from netbox_zabbix.models import Proxy, TLSConnectChoices, TLSAcceptChoices

# Configure PSK encryption
proxy = Proxy.objects.get(name="My Proxy")
proxy.tls_connect = TLSConnectChoices.PSK
proxy.tls_accept = TLSAcceptChoices.PSK
proxy.tls_psk_identity = "my_proxy_identity"
proxy.tls_psk = "a1b2c3d4e5f67890"  # Should be at least 32 hex digits
proxy.save()
```

### Setting Custom Timeouts
```python
# Enable custom timeouts and configure specific values
proxy = Proxy.objects.get(name="My Proxy")
proxy.custom_timeouts = True
proxy.timeout_zabbix_agent = "10s"
proxy.timeout_http_agent = "30s"
proxy.timeout_browser = "120s"
proxy.save()
```

### Assigning to a Proxy Group
```python
from netbox_zabbix.models import Proxy, ProxyGroup

# Assign proxy to a proxy group
proxy_group = ProxyGroup.objects.get(name="Web Servers Proxy Group")
proxy = Proxy.objects.get(name="My Proxy")
proxy.proxy_group = proxy_group
proxy.save()
```

## Integration with Other Models

Proxy integrates with several other models in the plugin:

1. **ProxyGroup Model**: Proxies can be assigned to proxy groups for high availability.
2. **HostConfig Model**: Host configurations can be assigned to specific proxies for monitoring.
3. **Mapping Models**: DeviceMapping and VMMapping can specify proxies for matching hosts.

## Description

The Proxy model provides comprehensive configuration and synchronization capabilities for Zabbix proxies. It supports both active and passive proxy modes, extensive encryption options, and detailed timeout configurations.

Key features include:
- Support for both active and passive proxy operating modes
- Comprehensive TLS encryption configuration options
- Detailed timeout settings for various check types
- Integration with ProxyGroup for high availability configurations
- Automatic synchronization with Zabbix proxy configurations
- Robust error handling for Zabbix API operations
- Flexible network configuration for different deployment scenarios