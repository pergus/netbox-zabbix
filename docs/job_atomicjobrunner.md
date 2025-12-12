# AtomicJobRunner Base Class

## Overview

The `AtomicJobRunner` is a base class that extends NetBox's JobRunner to provide transactional execution, proper exception propagation, and enhanced event logging capabilities. All jobs in the NetBox Zabbix plugin inherit from this class to ensure consistency and reliability.

## Class Definition

```python
class AtomicJobRunner(JobRunner)
```

## Methods

### `handle(cls, job, *args, **kwargs)`

Execute the job inside a transactional block and handle exceptions.

**Parameters:**
- `job` (JobRunner): The job instance being executed.
- `*args`: Positional arguments passed to the job's `run` method.
- `**kwargs`: Keyword arguments passed to the job's `run` method.

**Behavior:**
- Calls `job.start()`.
- Executes `cls(job).run(*args, **kwargs)` within a `transaction.atomic()` block.
- Updates `job.data` and terminates the job with success or failure status.
- Logs the event via `_log_event()`.
- Reschedules the job if `job.interval` is set.

**Raises:**
- `Exception`: Any exception raised by `run()` is re-raised after updating job status.

### `run_now(cls, *args, **kwargs)`

Execute the job immediately in a transactional context.

**Parameters:**
- `*args`: Positional arguments for the job's `run` method.
- `**kwargs`: Keyword arguments for the job's `run` method.
  - `name` (str, optional): Name of the job. Defaults to `cls.name`.
  - `eventlog` (bool, optional): Whether to log events. Defaults to True.

**Returns:**
- `str`: The message from the job's result, or the string representation of the result.

**Raises:**
- `Exception`: Any exception raised by `run()` is propagated.

### `_log_event(name, job=None, result=None, exception=None, data=None, pre_data=None, post_data=None, signal_id=None)`

Log a structured job event to the EventLog model.

**Parameters:**
- `name` (str): Name of the job.
- `job` (JobRunner, optional): The job instance associated with the event.
- `result` (dict, optional): The result dictionary returned by the job.
- `exception` (str, optional): Exception message if the job failed.
- `data` (any, optional): Job-specific result data.
- `pre_data` (any, optional): Data captured before job execution.
- `post_data` (any, optional): Data captured after job execution.
- `signal_id` (str, optional): Signal ID for correlating events.

## Usage Examples

### Creating a Custom Job

```python
from netbox_zabbix.jobs.atomicjobrunner import AtomicJobRunner

class MyCustomJob(AtomicJobRunner):
    """
    Example custom job inheriting from AtomicJobRunner.
    """

    @classmethod
    def run(cls, *args, **kwargs):
        """
        Implement the job logic.
        """
        # Job logic here
        return {"message": "Job completed successfully", "data": {"processed": 10}}

    @classmethod
    def run_job(cls, schedule_at=None, interval=None, immediate=False, name=None):
        """
        Schedule the job for execution.
        """
        job_args = {
            "name": name or "My Custom Job",
            "schedule_at": schedule_at,
            "interval": interval,
            "immediate": immediate,
        }

        if interval is None:
            return cls.enqueue(**job_args)
        else:
            return cls.enqueue_once(**job_args)
```

### Running a Job Immediately

```python
from netbox_zabbix.jobs.atomicjobrunner import AtomicJobRunner

# Run any job immediately with transaction safety
result = AtomicJobRunner.run_now()
print(f"Job result: {result}")
```

## Integration with Other Components

1. **NetBox JobRunner**: Extends the base NetBox job framework.
2. **Django Transactions**: Uses `django.db.transaction` for atomic execution.
3. **NetBox Models**: Integrates with Job and EventLog models.
4. **Plugin Settings**: Respects event logging configuration.
5. **Logging**: Uses plugin logger for error and debug logging.

## Description

The AtomicJobRunner class addresses several limitations of NetBox's built-in JobRunner and provides enhanced functionality for reliable job execution in the NetBox Zabbix plugin.

### Problem Solved

NetBox's built-in JobRunner.handle() method swallows all exceptions that occur during job execution. While it updates the job's status and logs the error, it does not re-raise the exception. This makes it impossible to identify the job as failed in GUI and impossible for a user to restart the job.

### Solution Provided

AtomicJobRunner overrides the `handle()` method to re-raise any unhandled exceptions after updating the job status and metadata. This allows external callers using `.enqueue()` or `.handle()` to detect failures, making it suitable for retry mechanisms, task chaining, and tests.

### Key Features

**Transactional Execution:**
- The job execution (`run()`) occurs inside a `transaction.atomic()` block.
- If any part of the job fails, the database changes are rolled back.
- This guarantees consistency between the job's result and its side effects.

**Exception Propagation:**
- Exceptions are properly re-raised after job status updates.
- Enables proper error handling in calling code.
- Allows job restart functionality in NetBox UI.

**Enhanced Event Logging:**
- Stores structured `job.data` on both success and failure.
- Captures pre-execution and post-execution data for debugging.
- Maintains support for periodic (interval-based) jobs via `job.interval`.

**Data Preservation:**
- Preserves job context data for troubleshooting.
- Stores pre-data and post-data snapshots for audit purposes.
- Maintains signal ID correlation for event tracking.

**Rescheduling Support:**
- Automatically reschedules jobs with intervals.
- Handles job continuation for recurring tasks.
- Manages job lifecycle for system jobs.

### Benefits

1. **Consistency**: Database transactions ensure all-or-nothing execution.
2. **Reliability**: Exception propagation enables proper error handling.
3. **Debuggability**: Structured data logging aids troubleshooting.
4. **Maintainability**: Standardized base class reduces code duplication.
5. **Audit Trail**: Comprehensive event logging supports compliance.
6. **Performance**: Efficient execution with minimal overhead.

All jobs in the NetBox Zabbix plugin inherit from AtomicJobRunner to ensure consistent behavior, reliable execution, and proper error handling across the entire job system.