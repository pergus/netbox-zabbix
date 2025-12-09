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
        "FERNET_KEY_PATH": "/opt/netbox-zabbix/data/fernet.key"
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

## Notes



---

## Contributing

We welcome contributions! Please fork the repository and submit pull requests with enhancements, bug fixes, or new features.

---

## License

Distributed under the MIT License. See `LICENSE` for more information.
