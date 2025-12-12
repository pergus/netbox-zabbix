# EventLog Model

## Overview

The `EventLog` model stores logs of plugin events for auditing and troubleshooting purposes.

## Model Definition

EventLog is a NetBoxModel that records plugin activities, job executions, signal handling, and exceptions. It provides an audit trail of plugin activities, including job executions, signal handling, and any exceptions that occurred during operations.

## Fields

| Field | Type | Description | Notes |
|-------|------|-------------|-------|
| `name` | CharField (max_length=256) | Event name | verbose_name="Name" |
| `job` | ForeignKey (Job) | Reference to the associated job | on_delete=CASCADE, nullable, related_name='logs' |
| `signal_id` | TextField | Signal ID | verbose_name="Signal ID", blank, default="" |
| `message` | TextField | Event message | verbose_name="Message", blank, default="" |
| `exception` | TextField | Exception details | verbose_name="Exception", blank, default="" |
| `data` | JSONField | Event data | verbose_name="Data", nullable, blank, default=dict |
| `pre_data` | JSONField | Pre-change data | verbose_name="Pre-Change Data", nullable, blank, default=dict |
| `post_data` | JSONField | Post-change data | verbose_name="Post-Change Data", nullable, blank, default=dict |
| `created` | DateTimeField | Creation timestamp | verbose_name="Created", auto_now_add=True |

### `name`
A human-readable name for the event that helps identify its purpose or type.

### `job`
Foreign key relationship to the associated Job object. This allows tracking of job execution events and linking logs to specific background operations.

### `signal_id`
Identifier for Django signal handling events. This field tracks which signal was triggered, enabling visibility into the plugin's internal operations.

### `message`
Detailed message about the operation or event. This field provides context about what happened during the logged operation.

### `exception`
Exception information for error tracking. When an exception occurs, this field captures the exception details for troubleshooting purposes.

### `data`
Structured event data stored in JSON format. This field can capture complex Python objects and is useful for storing detailed information about the event.

### `pre_data`
Data snapshot captured before a change occurred. This field is particularly useful for tracking changes to model instances over time and enabling audit trails.

### `post_data`
Data snapshot captured after a change occurred. Together with `pre_data`, this enables comparison of object states before and after operations.

### `created`
Timestamp indicating when the event log entry was created. Entries are ordered chronologically with the newest entries first.

## Methods

### `get_absolute_url()`
Return URL for the event log detail page in the NetBox UI.

**Returns:**
- `str`: Absolute URL for the event log

### `get_job_status_color()`
Return a color representing the status of the associated job.

**Returns:**
- `str`: Hex color or name (e.g., 'red')

### `__str__()`
Return a string representation of the event log.

**Returns:**
- `str`: String representation of the event log

## Usage Examples

### Viewing Event Logs
```python
from netbox_zabbix.models import EventLog

# Get recent event logs
recent_logs = EventLog.objects.all()[:10]

# Get logs for a specific job
job_logs = EventLog.objects.filter(job=some_job)

# Get error logs
error_logs = EventLog.objects.exclude(exception="")

# Get logs with specific signal
signal_logs = EventLog.objects.filter(signal_id="device_post_save")
```

### Analyzing Log Data
```python
# Examine log data
for log in recent_logs:
    print(f"{log.created}: {log.name}")
    if log.message:
        print(f"  Message: {log.message}")
    if log.exception:
        print(f"  Exception: {log.exception}")
    if log.data:
        print(f"  Data: {log.data}")
```

### Filtering by Date Range
```python
from datetime import datetime, timedelta

# Get logs from the last 24 hours
yesterday = datetime.now() - timedelta(days=1)
recent_logs = EventLog.objects.filter(created__gte=yesterday)
```

## Integration with Other Models

EventLog integrates with several other models in the plugin:

1. **Job Model**: EventLog entries are associated with specific Job objects through a foreign key relationship, allowing tracking of job execution events.

2. **All Plugin Models**: Event logs can capture data snapshots before and after changes to any plugin model, enabling change tracking and audit trails.

3. **Django Signal Framework**: Event logs track Django signal handling events, providing visibility into the plugin's internal operations.

## Description

EventLog objects provide an audit trail of plugin activities, including job executions, signal handling, and any exceptions that occurred during operations. This is useful for troubleshooting and monitoring plugin health.

The model captures:
- Event names and descriptions
- Associated job information
- Signal identifiers for tracking Django signal handling
- Detailed messages about operations
- Exception information for error tracking
- Data snapshots before and after changes
- Timestamps for chronological ordering

Event logs are automatically created by the plugin during various operations:
- Job execution (success, failure, progress)
- Signal handling (pre-save, post-save, etc.)
- Configuration changes
- Synchronization operations
- Error conditions

The data fields store structured information about events in JSON format, making it easy to serialize complex Python objects and deserialize them for display or analysis. The pre_data and post_data fields are particularly useful for tracking changes to model instances over time.

Logs are ordered chronologically with the newest entries first, making it easy to see recent activity. The get_job_status_color method provides visual indication of job outcomes in the UI.