# NetBox Zabbix Plugin

## Overview

The **NetBox Zabbix Plugin** integrates Zabbix with NetBox.
The plugin allows NetBox users to:

* Create/Update and Delete Zabbix hosts from NetBox.
* Configure host interfaces (Agent, SNMP) and host-specific configurations.
* Import hosts from Zabbix to NetBox.

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

### Device & VM Mapping

* Define how Devices or Virtual Machines are transformed into Zabbix hosts.
* Include filters to select specific subsets of Devices/VMs (e.g., by site, role, custom field).
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

## Default Settings

The NetBox Zabbix plugin ships with default tag mappings and inventory mappings. 
These define how NetBox Devices and Virtual Machines are transformed into Zabbix 
hosts, including which attributes are added as tags and which populate the 
Zabbix inventory.

### 1. Tag Mappings

Purpose: Tags in Zabbix are used to categorize hosts and enable filtering in Zabbix dashboards, triggers, and actions.

By default, the plugin maps common NetBox attributes to Zabbix host tags for both Devices and Virtual Machines:


| Object Type	| Zabbix Tag    | NetBox Attribute |
|-------------|---------------|------------------|
| Device	    | Site          | site.name        |
| Device	    | Region	      | site.region      |
| Device	    | Latitude	    | site.latitude    |
| Device	    | Longitude	    | site.longitude   |
| Device	    | Role	        | role.name        |
| Device	    | Platform	    | platform.name    |
| Virtual Machine	| Site	    | site.name        |
| Virtual Machine	| Region	  | site.region      |
| Virtual Machine	| Latitude	| site.latitude    |
| Virtual Machine	| Longitude	| site.longitude   |
| Virtual Machine	| Cluster	  | cluster.name     |
| Virtual Machine	| Role	    | role.name        |
| Virtual Machine	| Platform	| platform.name    |

Explanation:

These tag mappings allow Zabbix to automatically classify hosts based on their location, role, and platform.

For VMs, the Cluster tag is included to distinguish hosts grouped under the same cluster.

### 2. Inventory Mappings

Purpose: Zabbix inventory fields store detailed host metadata that can be used in templates, reports, or automated actions. Inventory mappings define which NetBox fields populate Zabbix inventory keys.

Default mappings for Devices and VMs:

| Object Type      | Inventory Key | Zabbix Field | Source Path(s) in NetBox                     |
|------------------|---------------|--------------|----------------------------------------------|
| Device           | Name          | name         | `["name"]`                                   |
| Device           | Platform      | os           | `["platform.name"]`                          |
| Device           | Location      | location     | `["location.name", "site.name"]`            |
| Device           | Latitude      | location_lat | `["location.site.latitude", "site.latitude"]` |
| Device           | Longitude     | location_lon | `["location.site.longitude", "site.longitude"]` |
| Virtual Machine  | Name          | name         | `["name"]`                                   |
| Virtual Machine  | Platform      | os           | `["platform.name"]`                          |
| Virtual Machine  | Location      | location     | `["location.name", "site.name"]`            |
| Virtual Machine  | Latitude      | location_lat | `["location.site.latitude", "site.latitude"]` |
| Virtual Machine  | Longitude     | location_lon | `["location.site.longitude", "site.longitude"]` |

Explanation:

Each inventory key in Zabbix is filled from one or more NetBox attributes. The plugin attempts the first path in the list that returns a value.

For example, the Location inventory key will first try location.name on the object; if that’s empty, it will fallback to site.name.

Latitude and Longitude provide geolocation for hosts in Zabbix maps.

How These Defaults Are Used:

When importing a Device or VM into Zabbix, the plugin applies these mappings automatically.

Users can override defaults by editing Tag Mappings or Inventory Mappings in NetBox.

These mappings ensure that newly imported Zabbix hosts are consistently categorized and have the relevant metadata.


---

## Contributing

We welcome contributions! Please fork the repository and submit pull requests with enhancements, bug fixes, or new features.

---

## License

Distributed under the MIT License. See `LICENSE` for more information.
