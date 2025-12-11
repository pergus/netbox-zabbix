# NetBox Zabbix Plugin - Sync Jobs Documentation

## Overview

Sync jobs handle bulk synchronization operations between NetBox and Zabbix. These jobs are designed for scenarios where multiple host configurations need to be updated simultaneously, such as after major configuration changes or when bringing a new NetBox instance online with existing Zabbix data.

## Sync Job Classes

### SyncHostsNow

This job synchronizes all NetBox HostConfig objects with their corresponding hosts in Zabbix immediately.

#### Class Definition
```python
class SyncHostsNow(AtomicJobRunner)
```

#### Key Methods

##### `run(cls, *args, **kwargs)`
Execute the host synchronization for all HostConfig objects.

**Parameters:**
- `user` (User, optional): The triggering user for audit logging
- `request_id` (str, optional): Request identifier for correlation

**Returns:**
- `dict`: Summary of sync results containing:
  - `total`: Total number of HostConfig objects processed
  - `updated`: Number of hosts successfully updated
  - `failed`: Number of hosts that failed to update
  - `message`: Human-readable summary message

**Implementation Details:**
- Iterates through all HostConfig objects in the database
- Calls `update_zabbix_host` for each host configuration
- Updates sync status for each host after successful update
- Logs errors for individual hosts that fail to update
- Continues processing remaining hosts even if some fail
- Executes within a transactional context for consistency

##### `run_job_now(cls, request)`
Immediately execute the job in the current process.

**Parameters:**
- `request` (HttpRequest): The triggering request

**Returns:**
- `dict`: Job execution summary

**Implementation Details:**
- Bypasses the single-instance expectations of the standard `run_now` method
- Directly calls the `run` method with user and request information
- Provides immediate feedback without job queuing overhead

## Implementation Details

### Transactional Execution
The `SyncHostsNow` job executes within a database transaction to ensure consistency:
- All database changes are committed only if the entire operation succeeds
- Partial failures result in automatic rollback of all changes
- This prevents inconsistent states between NetBox and Zabbix metadata

### Error Handling and Resilience
The sync job is designed to be resilient to individual failures:
- Individual host failures do not stop the overall sync process
- Detailed error messages are logged for each failed host
- Progress counters track successful and failed operations
- The job completes even if some hosts cannot be synchronized

### Performance Considerations
- The job processes hosts sequentially to avoid overwhelming the Zabbix API
- Progress tracking provides visibility into long-running operations
- Resource usage is bounded by the transactional context

## Usage Examples

### Running a Full Sync
```python
# Run a full sync immediately
request = HttpRequest()  # Your request object
result = SyncHostsNow.run_job_now(request)

print(f"Sync complete: {result['updated']}/{result['total']} hosts updated")

# Handle failures
if result['failed'] > 0:
    print(f"{result['failed']} hosts failed to sync")
```

### Manual Sync Execution
```python
# Execute sync with specific user context
result = SyncHostsNow.run(
    user=some_user,
    request_id="sync-request-123"
)

# Process results
print(result['message'])
```

## Integration with Other Components

### Relationship to Host Management Jobs
The sync job leverages the same underlying `update_zabbix_host` function used by individual host management jobs, ensuring consistency in update behavior.

### Complementary to System Jobs
While system jobs like `SystemJobHostConfigSyncRefresh` periodically check sync status for individual hosts, the `SyncHostsNow` job provides a way to force immediate synchronization of all hosts.

### Event Logging
When event logging is enabled, sync operations generate detailed logs that can be used for:
- Audit trails of bulk operations
- Performance analysis
- Troubleshooting sync issues


## Common Use Cases

1. **Initial Setup**: Synchronize all hosts when first connecting NetBox to an existing Zabbix instance
2. **Configuration Changes**: Apply widespread configuration changes that affect multiple hosts
3. **Recovery Operations**: Recover from sync issues affecting multiple hosts
4. **Migration Scenarios**: Migrate hosts between Zabbix servers or proxy configurations
5. **Template Updates**: Apply template changes across all matching hosts

## Limitations and Considerations

1. **Execution Time**: Full syncs can take significant time in large environments
2. **API Load**: The job generates substantial API traffic to Zabbix
3. **Transaction Size**: Large transactions may impact database performance
4. **Error Isolation**: Individual host failures don't stop the overall process but should be investigated