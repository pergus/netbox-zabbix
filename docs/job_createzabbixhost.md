# CreateZabbixHost Job

## Overview

The `CreateZabbixHost` job creates a new Zabbix host from a HostConfig. This job registers NetBox HostConfig objects as hosts in Zabbix, enabling monitoring of NetBox-managed infrastructure.

## Class Definition

```python
class CreateZabbixHost(AtomicJobRunner)
```

## Methods

### `run(cls, *args, **kwargs)`

Creates the host in Zabbix and updates HostConfig with host ID.

**Returns:**
- `dict`: Message confirming creation and Zabbix payload.

**Raises:**
- `ExceptionWithData`: If creation fails and payload is available.
- `Exception`: For other failures.

### `run_job(cls, host_config, request, schedule_at=None, interval=None, immediate=False, name=None, signal_id=None)`

Enqueues a job to create a Zabbix host.

**Parameters:**
- `host_config` (HostConfig): Host configuration to create.
- `request` (HttpRequest): Triggering request.
- `schedule_at` (datetime, optional): Schedule time.
- `interval` (int, optional): Interval for recurring job.
- `immediate` (bool, optional): Run job immediately.
- `name` (str, optional): Job name.
- `signal_id` (str, optional): Signal identifier for event correlation.

**Returns:**
- `Job`: Enqueued job instance.

## Usage Examples

### Creating a Zabbix Host

```python
from netbox_zabbix.jobs.host import CreateZabbixHost
from netbox_zabbix.models import HostConfig

# Get a host configuration to create in Zabbix
host_config = HostConfig.objects.get(name="web-server-01")

# Create the host in Zabbix
job = CreateZabbixHost.run_job(
    host_config=host_config,
    request=request,
    name=f"Create host {host_config.name} in Zabbix"
)
```

### Immediate Host Creation

```python
from netbox_zabbix.jobs.host import CreateZabbixHost
from netbox_zabbix.models import HostConfig

# Get a host configuration
host_config = HostConfig.objects.get(name="web-server-01")

# Create host immediately
result = CreateZabbixHost.run_now(
    host_config_id=host_config.id,
    user=request.user,
    request_id=request.id
)
print(f"Host creation result: {result['message']}")
```

## Integration with Other Components

1. **AtomicJobRunner**: Inherits transactional execution and error handling capabilities.
2. **Zabbix Hosts**: Uses `create_zabbix_host` to register hosts in Zabbix.
3. **NetBox Models**: Works with HostConfig objects.
4. **NetBox Changelog**: Uses `log_creation_event` to record host creation.
5. **NetBox Jobs**: Uses `associate_instance_with_job` to link jobs with instances.
6. **Host Configuration**: Uses `save_host_config` to persist host IDs.
7. **Event Logging**: Logs host creation events to the EventLog model.

## Description

The CreateZabbixHost job registers NetBox HostConfig objects as monitored hosts in Zabbix. It performs the following operations:

1. Retrieves the HostConfig object from NetBox
2. Creates a corresponding host in Zabbix with appropriate configuration
3. Updates the HostConfig with the assigned Zabbix host ID
4. Logs the creation event in NetBox's changelog
5. Associates the job with the created host for tracking

This job is typically used when:
- New devices or virtual machines are provisioned for monitoring
- Existing HostConfig objects need to be registered in Zabbix
- Recovering from host creation failures
- Manually adding hosts to Zabbix monitoring

Key features:
- **Transaction Safety**: Executes within a database transaction to ensure consistency
- **Error Recovery**: Attempts to clean up partially created hosts if failures occur
- **Payload Preservation**: Preserves Zabbix API payloads for debugging
- **Changelog Integration**: Records host creation in NetBox's audit trail
- **Job Association**: Links created hosts with their creation jobs for tracking
- **Automatic Cleanup**: Removes partially created Zabbix hosts on failure

The job ensures that all necessary Zabbix host configuration is created, including:
- Host name and description
- Assigned templates based on mapping configurations
- Host groups based on mapping configurations
- Interface configurations (agent, SNMP, etc.)
- Proxy or proxy group assignments
- Custom tags and inventory data