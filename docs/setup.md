# The Setup Zabbix Management Command

The setup zabbix management command initializes required defaults, mappings, and cryptographic keys.
Below are a description of each individual step in the setup process.
The setup script is divided into two parts. The first part prompts the user to configure the connection to Zabbix and stores this information securely in the NetBox database. The second part allows the user to configure default Device and VM mappings.


**Part 1 — Configure Zabbix Connection**

Step 1. Enter a name for this configuration

```bash
Enter the name of the setting instance [config]:
```
This becomes the instance name of the Setting object.


Step 2. Enter the Zabbix host and URLs
The script auto-detects the machine hostname and proposes defaults:

```bash
Enter the Zabbix host [myserver.example.com]:
Enter the Zabbix API URL [https://myserver.example.com/api_jsonrpc.php]:
Enter the Zabbix Web URL [https://myserver.example.com]:
```
The user can accept defaults or enter custom values.

Step 3. Enter the Zabbix API Token
The token cannot be empty. The command will repeat the prompt until a non-empty value is provided:

```bash
Enter the Zabbix API token:
```

Step 4. Provide or confirm the path to the fernet.key file
The plugin uses Fernet encryption for secure token storage.

```bash
Path to Fernet key file [/opt/netbox/netbox_zabbix/fernet.key]:
```

The user may:
Accept the default path, or
Provide a custom path.

If the file does not exist, the script creates the file and the fernet key automatically and prints the location.

Step 5. The script imports data from Zabbix

The plugin now contacts Zabbix and loads:

* Templates
* Host groups
* Proxies
* Proxy groups



**Part 2 — Configure Device and VM Mappings**

The script next asks the user to define default mappings for devices and virtual machines.
These values will be used when automatically assigning Zabbix templates and groups to NetBox objects.

> Important: A new Zabbix installation defines a number of Templates and Host Groups. The default template selected should be compatible with both Zabbix Agent and SNMPv3 interfaces. For broad compatibility, ICMP Ping is recommended.


Step 7. Select the default Template (required)

```bash
Enter Default Template
 1. ICMP Ping
 2. Linux by Zabbix agent
 3. SNMP Device
Select a number [1–3]:
```

> Recommendation: Choose ICMP Ping for maximum compatibility across Agents and SNMPv3 devices.


Step 8. Select the default Host Group (required)
Similar numbered list:

```bash
Enter Default Host Group
 1. Linux Servers
 2. Network Devices
Select a number [1–2]:
```

Step 9. Select the Default Proxy (optional — may skip with Enter)

```bash
Enter Default Proxy
 1. zbx-proxy-eu
 2. zbx-proxy-us
Select a number [1–2] (Enter to skip):
```

Step 10. Select the Default Proxy Group (optional — may skip with Enter)

```bash
Enter Default Proxy Group
 1. EU Datacenter
 2. US Datacenter
Select a number [1–2] (Enter to skip):
```

Step 11. The script stores the mappings in the database
Both DeviceMapping and VMMapping are created or updated.

Step 12. Final Step — Add FERNET_KEY_PATH to NetBox configuration
At the end of the setup, the script prints instructions:

```bash
Next Required Step

You must add the path to your fernet.key file in PLUGINS_CONFIG:

PLUGINS_CONFIG = {
    'netbox_zabbix': {
        "FERNET_KEY_PATH": "/opt/netbox/netbox_zabbix/fernet.key"
    }
}
```