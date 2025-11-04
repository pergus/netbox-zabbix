# NetBox Zabbix Plugin

## Overview

The **NetBox Zabbix Plugin** integrates NetBox with Zabbix, providing a seamless way to monitor devices and virtual machines. The plugin allows NetBox users to:

* Manage Zabbix connection settings.
* Import Zabbix templates, proxies, proxy groups, and host groups into NetBox.
* Map NetBox objects (Devices/VMs) to Zabbix hosts using customizable mappings.
* Configure host interfaces (Agent, SNMP) and host-specific configurations.
* Validate importable hosts and synchronize them with Zabbix.

The plugin **reads data from Zabbix** but does not directly manage templates, proxies, or host groups in Zabbix from NetBox.

---

## Installation

1. **Install the plugin into your NetBox environment**:

```bash
pip install git+https://github.com/pergus/netbox-zabbix.git'
pip install pyzabbix==1.3.1
```

2. **Add the plugin to NetBox configuration** (`configuration.py`):

```python
PLUGINS = [
    'netbox_zabbix',
]

PLUGINS_CONFIG = {
    'netbox_zabbix': {
        # Optional configuration overrides
    }
}
```

3. **Apply database migrations**:

```bash
python manage.py migrate netbox_zabbix
```

4. **Restart NetBox**:

```bash
supervisorctl restart netbox
```

---

## Settings

The plugin provides a single **Zabbix Settings** object in NetBox under the Zabbix menu.

| Field                     | Description                                 | Default       | Notes                                         |
| ------------------------- | ------------------------------------------- | ------------- | --------------------------------------------- |
| Name                      | Friendly name for this Zabbix configuration | -             | Used for identification                       |
| API Endpoint              | Zabbix API URL                              | -             | Required to connect to Zabbix API             |
| Web Address               | Zabbix web interface URL                    | -             | Optional, for links to Zabbix GUI             |
| Token                     | Zabbix API token                            | -             | Must have sufficient API permissions          |
| Connection                | Status of Zabbix connection                 | False         | Updated automatically when testing connection |
| Auto-validate Importables | Validate hosts before import                | True          | Ensures hosts exist and mappings are correct  |
| Max Deletions             | Maximum hosts to delete per run             | 10            | Prevent accidental mass deletions             |
| Event Log Enabled         | Log plugin job events in NetBox             | True          | Records all job execution events              |
| Auto-validate Quick Add   | Validate quick-add hosts                    | True          | Ensures imported hosts comply with mappings   |
| Inventory Mode            | How inventory is pushed to Zabbix           | -             | Device or VM inventory                        |
| Monitored By              | Method to monitor hosts                     | Zabbix Server | Options: Zabbix Server, Proxy, Proxy Group    |
| TLS Connect / TLS Accept  | TLS connection settings                     | -             | Used for agent-based communication            |
| Agent / SNMP Ports        | Default ports for interfaces                | 10050 / 161   | Used for auto-created interfaces              |
| Tagging                   | Default tag and prefix for hosts            | -             | Used to categorize hosts in Zabbix            |
| Last Checked At           | Timestamp of last connection test           | -             | Updated when testing connection               |

> **Note:** Only one Settings object is supported. Attempts to create multiple objects are prevented.

---

## Templates, Proxies, Host Groups

These are **read-only** objects imported from Zabbix:

* **Templates:** Imported Zabbix templates can be viewed in NetBox and linked to hosts.
* **Proxies & Proxy Groups:** Imported for monitoring via proxies.
* **Host Groups:** Imported Zabbix host groups can be used in mappings.

These objects **cannot be modified from NetBox**, only imported and referenced.

---

## Mappings

Mappings define how NetBox objects are translated into Zabbix hosts.

### Tag Mapping

* Maps NetBox tags to Zabbix host tags.
* Allows automated categorization of hosts in Zabbix.

### Inventory Mapping

* Maps device or VM fields (e.g., serial number, model, custom fields) to Zabbix inventory fields.
* Supports multiple paths for each inventory property.
* Ensures accurate reporting of device metadata in Zabbix.

### Device & VM Mapping

* Define how Devices or Virtual Machines are transformed into Zabbix hosts.
* Include filters to select specific subsets of devices/VMs (e.g., by site, role, custom field).
* Filters are based on NetBox’s QuerySet filtering, allowing complex selections.
* Used during host creation and import.

---

## Host Configurations

* Defines host-specific parameters for Zabbix, such as templates, groups, and macros.
* Configurations are applied when creating or updating hosts in Zabbix.
* Allows per-host customization for monitoring.

---

## Interface Types

### Agent Interfaces

* Created for Zabbix agent-based monitoring.
* Configured with port, use of IP, and TLS settings.
* Automatically linked during host creation if “agent” monitoring is selected.

### SNMP Interfaces

* Created for SNMP-based monitoring.
* Supports SNMP v1, v2c, and v3 with full SNMPv3 credentials.
* Can include bulk, max-repetitions, security name, auth/priv credentials.
* Signals are triggered when modifying interfaces to ensure NetBox and Zabbix stay in sync.

---

## Importable Hosts

* **Definition:** Hosts present in NetBox but not yet in Zabbix.
* Hosts can be **validated** before import to check mappings and interface availability.
* **Import Options:**

  * Quick Add: Minimal required fields.
  * Full Import: Apply mappings, templates, host groups, and interfaces.
* Validation ensures host will be correctly created in Zabbix.

---

## NetBox Only Hosts

* Hosts that exist in NetBox but are **not yet managed by Zabbix**.
* Can be queued for import into Zabbix.
* Ensures consistent monitoring setup across all NetBox objects.

---

## Zabbix Only Hosts

* Hosts present in Zabbix but not linked to NetBox objects.
* Displayed for informational purposes and to aid reconciliation.
* Can be manually linked to NetBox objects or ignored.

---

## Event Logs

* Every job or import operation can be logged in NetBox’s **Event Log**.
* Provides detailed information for troubleshooting:

  * Job name
  * Status
  * Error messages
  * Pre/post execution data
* Event logging can be enabled or disabled via Settings.

---

## Contributing

We welcome contributions! Please fork the repository and submit pull requests with enhancements, bug fixes, or new features.

---

## License

Distributed under the MIT License. See `LICENSE` for more information.
