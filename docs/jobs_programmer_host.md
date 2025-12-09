# NetBox Zabbix Plugin - Host Management Jobs Documentation

## Overview

Host management jobs handle the lifecycle of Zabbix hosts corresponding to NetBox HostConfig objects. These jobs provide create, update, and delete functionality for individual hosts, ensuring proper synchronization between NetBox and Zabbix.

## Host Management Job Classes

### CreateZabbixHost

This job creates a new Zabbix host from a NetBox HostConfig object.

#### Class Definition
```python
class CreateZabbixHost(AtomicJobRunner)
```

#### Key Methods

##### `run(cls, *args, **kwargs)`
Creates the host in Zabbix and updates the HostConfig with the assigned host ID.

**Required Parameters:**
- `host_config_id` (int): ID of the HostConfig object to create in Zabbix
- `user` (User, optional): The user initiating the creation
- `request_id` (str, optional): Request identifier for logging

**Returns:**
- `dict`: Result containing:
  - `message`: Confirmation message
  - `data`: Zabbix API payload used for creation

**Raises:**
- `ExceptionWithData`: If creation fails but payload data is available
- `Exception`: For other failures

**Implementation Details:**
- Creates the host in Zabbix using the `create_zabbix_host` function
- Updates the HostConfig with the assigned host ID
- Saves the host configuration and logs the creation event
- Associates the instance with the job for tracking
- Automatically attempts to delete the Zabbix host if creation fails after the host ID is assigned

##### `run_job(cls, host_config, request, schedule_at=None, interval=None, immediate=False, name=None, signal_id=None)`
Enqueues a job to create a Zabbix host.

**Parameters:**
- `host_config` (HostConfig): Host configuration to create
- `request` (HttpRequest): Triggering request
- `schedule_at` (datetime, optional): When to schedule the job
- `interval` (int, optional): Interval for recurring jobs
- `immediate` (bool): Whether to run immediately
- `name` (str, optional): Custom job name
- `signal_id` (str, optional): Signal identifier for correlation

**Returns:**
- `Job`: Enqueued job instance

### UpdateZabbixHost

This job updates an existing Zabbix host to match the current NetBox HostConfig.

#### Class Definition
```python
class UpdateZabbixHost(AtomicJobRunner)
```

#### Key Methods

##### `run(cls, *args, **kwargs)`
Updates the host in Zabbix with the current HostConfig.

**Required Parameters:**
- `host_config_id` (int): ID of the HostConfig object to update in Zabbix
- `user` (User, optional): The user initiating the update
- `request_id` (str, optional): Request identifier for logging

**Returns:**
- `dict`: Updated host information from the Zabbix API

**Raises:**
- `Exception`: If update fails

**Implementation Details:**
- Updates the host in Zabbix using the `update_zabbix_host` function
- Passes user and request information for audit logging

##### `run_job(cls, host_config, request, user=None, schedule_at=None, interval=None, immediate=False, name=None, signal_id=None)`
Enqueues an UpdateZabbixHost job.

**Parameters:**
- `host_config` (HostConfig): Host configuration to update
- `request` (HttpRequest): Triggering request
- `user` (User, optional): User initiating the update (used if request is None)
- `schedule_at` (datetime, optional): When to schedule the job
- `interval` (int, optional): Interval for recurring jobs
- `immediate` (bool): Whether to run immediately
- `name` (str, optional): Custom job name
- `signal_id` (str, optional): Signal identifier for correlation

**Returns:**
- `Job`: Enqueued job instance

##### `run_job_now(cls, host_config, request, name=None)`
Immediately updates a Zabbix host synchronously.

**Parameters:**
- `host_config` (HostConfig): Host to update
- `request` (HttpRequest): Triggering request
- `name` (str, optional): Custom job name

**Returns:**
- `dict`: Result of immediate update

### DeleteZabbixHost

This job deletes a Zabbix host, supporting both hard and soft deletion methods.

#### Class Definition
```python
class DeleteZabbixHost(AtomicJobRunner)
```

#### Key Methods

##### `run(cls, *args, **kwargs)`
Executes the deletion of the Zabbix host.

**Required Parameters:**
- `hostid` (str): Zabbix host ID to delete

**Returns:**
- `dict`: Result of deletion operation

**Raises:**
- `Exception`: If deletion fails

**Implementation Details:**
- Determines deletion method based on plugin settings (`HARD` vs `SOFT`)
- Calls either `delete_zabbix_host_hard` or `delete_zabbix_host_soft` function
- Properly handles and logs any errors during deletion

##### `run_job(cls, hostid, user=None, schedule_at=None, interval=None, immediate=False, name=None, signal_id=None)`
Enqueues a job to delete a Zabbix host.

**Parameters:**
- `hostid` (str): Zabbix host ID to delete
- `user` (User, optional): User initiating the deletion
- `schedule_at` (datetime, optional): When to schedule the job
- `interval` (int, optional): Interval for recurring jobs
- `immediate` (bool): Whether to run immediately
- `name` (str, optional): Custom job name
- `signal_id` (str, optional): Signal identifier for correlation

**Returns:**
- `Job`: Enqueued job instance

## Implementation Details

### Atomic Transactions
All host management jobs inherit from `AtomicJobRunner`, ensuring that:
1. Database operations occur within transactions
2. Changes are rolled back on failure
3. Exceptions are properly propagated
4. Event logging is consistent

### Error Handling
Each job implements comprehensive error handling:
- Specific exceptions are raised with meaningful messages
- Failed creations attempt to clean up partially created resources
- Error details are preserved in job metadata for debugging

### Job Enqueuing
Jobs can be enqueued in multiple ways:
- Standard enqueuing for background processing
- Immediate execution for synchronous operations
- Scheduled execution for deferred processing
- Recurring execution for periodic tasks

## Usage Examples

### Creating a Host
```python
# Create a host asynchronously
host_config = HostConfig.objects.get(id=1)
job = CreateZabbixHost.run_job(
    host_config=host_config,
    request=request,
    name="Create web server in Zabbix"
)

# Check job status
if job.status == JobStatusChoices.STATUS_COMPLETED:
    print("Host created successfully")
```

### Updating a Host
```python
# Update a host asynchronously
host_config = HostConfig.objects.get(id=1)
job = UpdateZabbixHost.run_job(
    host_config=host_config,
    request=request
)

# Or update immediately
result = UpdateZabbixHost.run_job_now(
    host_config=host_config,
    request=request
)
```

### Deleting a Host
```python
# Delete a host asynchronously
job = DeleteZabbixHost.run_job(
    hostid="10245",
    user=request.user,
    name="Delete old server from Zabbix"
)
```

## Best Practices

1. **Asynchronous Operations**: Use job enqueuing for long-running operations to maintain UI responsiveness
2. **Error Recovery**: Implement proper cleanup procedures for failed operations
3. **Audit Trail**: Always pass user and request information for proper audit logging
4. **Resource Management**: Consider the impact of concurrent host operations on Zabbix performance
5. **Validation**: Validate HostConfig objects before enqueuing jobs
6. **Naming**: Use descriptive job names to facilitate monitoring and debugging