# EventLog Model

## Overview

The `EventLog` model stores logs of plugin events for auditing and troubleshooting purposes.

## Model Definition

EventLog is a NetBoxModel that records plugin activities, job executions, signal handling, and exceptions.

## Fields

- `name` (CharField): Event name (verbose_name="Name", max_length=256)
- `job` (ForeignKey): Reference to the associated job (on_delete=CASCADE, nullable, related_name='logs')
- `signal_id` (TextField): Signal ID (verbose_name="Signal ID", blank, default="")
- `message` (TextField): Event message (verbose_name="Message", blank, default="")
- `exception` (TextField): Exception details (verbose_name="Exception", blank, default="")
- `data` (JSONField): Event data (verbose_name="Data", nullable, blank, default=dict)
- `pre_data` (JSONField): Pre-change data (verbose_name="Pre-Change Data", nullable, blank, default=dict)
- `post_data` (JSONField): Post-change data (verbose_name="Post-Change Data", nullable, blank, default=dict)
- `created` (DateTimeField): Creation timestamp (verbose_name="Created", auto_now_add=True)

## Methods

### get_absolute_url()

Return URL for the event log detail page in the NetBox UI.

**Returns:**
- `str`: Absolute URL for the event log

### get_job_status_color()

Return a color representing the status of the associated job.

**Returns:**
- `str`: Hex color or name (e.g., 'red')

## Meta Options

- `ordering`: ['-created'] (orders by creation timestamp, newest first)

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