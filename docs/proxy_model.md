# NetBox Zabbix Plugin - Proxy Documentation

The Proxy  in the NetBox Zabbix plugin represents Zabbix proxies, which are intermediary components that can collect monitoring data from agents and send it to the Zabbix server. This document explains the Proxy's structure, fields, methods, and usage.

## Overview

The Proxy synchronizes with Zabbix proxies and maintains comprehensive configuration parameters including networking, encryption, and timeout settings. Proxies can operate in active or passive modes and can be organized into proxy groups for high availability.

## Fields

### Basic Fields

| Field | Type | Description | Default/Notes |
|-------|------|-------------|---------------|
| `name` | CharField (max_length=255) | Name of the proxy | Human-readable identifier |
| `proxyid` | CharField (max_length=255) | Unique identifier in Zabbix | Blank/null allowed |
| `proxy_groupid` | CharField (max_length=255) | Proxy group identifier | Blank/null allowed |
| `proxy_group` | ForeignKey (ProxyGroup) | Associated proxy group | Null/blank allowed, related_name='proxies' |
| `last_synced` | DateTimeField | Last synchronization timestamp | Blank/null allowed |
| `description` | TextField | Description of the proxy | Blank/null allowed |

### Operating Mode

| Field | Type | Description | Default/Notes |
|-------|------|-------------|---------------|
| `operating_mode` | PositiveSmallIntegerField | Proxy operating mode | Default: ACTIVE (0). Options: ACTIVE (0), PASSIVE (1) |

### Networking Fields

#### Active Mode Fields
| Field | Type | Description | Default/Notes |
|-------|------|-------------|---------------|
| `local_address` | GenericIPAddressField | Address for active agents | Default: "", blank/null allowed |
| `local_port` | PositiveIntegerField | Proxy port for active mode | Default: 10051, blank/null allowed |
| `allowed_addresses` | CharField | Allowed addresses for active proxy | Blank/null allowed |

#### Passive Mode Fields
| Field | Type | Description | Default/Notes |
|-------|------|-------------|---------------|
| `address` | GenericIPAddressField | Interface address | Default: "127.0.0.1", blank/null allowed |
| `port` | PositiveIntegerField | Port for passive mode | Default: 10051, blank/null allowed |

### Encryption Fields

| Field | Type | Description | Default/Notes |
|-------|------|-------------|---------------|
| `tls_connect` | PositiveSmallIntegerField | TLS mode for outgoing connections | Default: NoEncryption (1). Options: NoEncryption (1), PSK (2), Certificate (4) |
| `tls_accept` | PositiveSmallIntegerField | TLS mode for incoming connections | Default: NoEncryption (1). Options: NoEncryption (1), PSK (2), Certificate (4) |
| `tls_issuer` | CharField (max_length=255) | Certificate issuer DN | Blank/null allowed |
| `tls_subject` | CharField (max_length=255) | Certificate subject DN | Blank/null allowed |
| `tls_psk_identity` | CharField (max_length=255) | PSK identity | Blank/null allowed |
| `tls_psk` | CharField (max_length=255) | Pre-shared key | Blank/null allowed |

### Timeout Fields

| Field | Type | Description | Default/Notes |
|-------|------|-------------|---------------|
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

## Methods

### `__str__()`
Returns the proxy name as a human-readable string representation.

### `get_absolute_url()`
Returns the canonical URL for this proxy within the NetBox plugin UI:
```
/plugins/netbox_zabbix/proxies/{pk}/
```

### `_build_params()`
Constructs the parameters dictionary for Zabbix API create/update proxy calls. This method handles the conditional inclusion of parameters based on operating mode, encryption settings, and timeout configurations.

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

## Operating Modes

### Active Mode
In active mode, the proxy actively connects to agents to collect data. Configuration fields:
- `local_address` and `local_port`: Where agents connect to the proxy
- `allowed_addresses`: Which addresses are allowed to connect

### Passive Mode
In passive mode, the proxy waits for the Zabbix server to connect and request data. Configuration fields:
- `address` and `port`: Where the Zabbix server connects to the proxy

## Best Practices

1. **Network Configuration**: Ensure proper network connectivity between proxies, agents, and the Zabbix server based on the operating mode.

2. **Encryption Security**: When using PSK encryption, use strong pre-shared keys with at least 32 hexadecimal digits.

3. **Timeout Tuning**: Adjust timeout values based on network latency and the complexity of checks being performed.

4. **Proxy Group Assignment**: Use proxy groups for critical monitoring infrastructure to ensure high availability.

5. **Resource Planning**: Monitor proxy resource usage (CPU, memory, disk I/O) and plan capacity accordingly.

6. **Descriptive Naming**: Use clear, descriptive names for proxies to facilitate management and troubleshooting.

7. **Regular Synchronization**: Keep proxies synchronized with Zabbix to ensure accurate monitoring configurations.

## Error Handling

The Proxy model includes robust error handling for Zabbix operations:

- If a proxy cannot be deleted from Zabbix, it will still be removed from NetBox but will return a warning message.
- All Zabbix API operations are wrapped in try-except blocks to handle connection issues gracefully.
- The `_build_params()` method handles conditional parameter inclusion to ensure valid API requests.