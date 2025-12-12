# UpdateZabbixInterface Job

## Overview

The `UpdateZabbixInterface` job updates existing Zabbix interfaces for a HostConfig. This job synchronizes interface configurations between NetBox and Zabbix, ensuring that changes made in NetBox are reflected in the corresponding Zabbix interfaces.

## Class Definition

```python
class UpdateZabbixInterface(BaseZabbixInterfaceJob)
```

## Methods

### `run(cls, *args, **kwargs)`

Updates the Zabbix host/interface and links missing interfaces.

**Returns:**
- `dict`: Result of the interface update.

**Raises:**
- `Exception`: If the HostConfig has no associated Zabbix host.

## Usage Examples

### Updating Interfaces

```python
from netbox_zabbix.jobs.interface import UpdateZabbixInterface
from netbox_zabbix.models import HostConfig

# Get a host configuration that needs interface updates
host_config = HostConfig.objects.get(name="web-server-01")

# Update interfaces
job = UpdateZabbixInterface.run_job(
    host_config=host_config,
    request=request,
    name=f"Update interfaces for {host_config.name}"
)
```

### Immediate Interface Update

```python
from netbox_zabbix.jobs.interface import UpdateZabbixInterface
from netbox_zabbix.models import HostConfig

# Get a host configuration
host_config = HostConfig.objects.get(name="web-server-01")

# Update interfaces immediately
result = UpdateZabbixInterface.run_now(
    host_config_id=host_config.id,
    user=request.user,
    request_id=request.id
)
print(f"Interface update result: {result['message']}")
```

## Integration with Other Components

1. **BaseZabbixInterfaceJob**: Inherits common interface job functionality.
2. **AtomicJobRunner**: Inherits transactional execution and error handling capabilities.
3. **Zabbix Hosts**: Uses `update_zabbix_host` to synchronize host configuration.
4. **Zabbix Interfaces**: Uses `link_missing_zabbix_interface` to associate interfaces.
5. **NetBox Models**: Works with HostConfig objects.
6. **Event Logging**: Logs interface update events to the EventLog model.

## Description

The UpdateZabbixInterface job ensures that Zabbix interface configurations match their corresponding NetBox HostConfig definitions. It performs the following operations:

1. Verifies that the HostConfig has an associated Zabbix host ID
2. Links any missing Zabbix interfaces to their NetBox counterparts
3. Updates the Zabbix host configuration to match NetBox definitions
4. Ensures interface consistency between NetBox and Zabbix

This job is typically used when:
- Interface configurations have been modified in NetBox
- Network settings such as IP addresses or ports have changed
- SNMP or agent parameters need to be updated
- Interface types or settings have been modified
- Recovering from interface synchronization issues

The job provides a targeted approach to interface management, allowing administrators to ensure interface consistency without performing full host updates. It's particularly useful in scenarios where only interface configuration has changed while other host settings remain valid.

Key features:
- **Validation**: Ensures the HostConfig has a valid Zabbix host ID before proceeding
- **Linking**: Automatically associates Zabbix interfaces with NetBox interface objects
- **Synchronization**: Updates Zabbix interface parameters to match NetBox definitions
- **Transaction Safety**: Executes within a database transaction to ensure consistency
- **Error Handling**: Provides clear error messages when interface updates fail

The job complements the CreateZabbixInterface job by focusing on updating existing interfaces rather than creating new ones, providing a complete interface management solution.