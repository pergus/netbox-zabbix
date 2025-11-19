"""
NetBox Zabbix Plugin — Atomic Job Runner

This module provides a subclass of NetBox's JobRunner that executes jobs 
within a database transaction and ensures that any exceptions are properly 
propagated. Jobs executed using AtomicJobRunner will have their changes 
rolled back automatically if an error occurs, and structured event data 
will be logged to the EventLog model if event logging is enabled. 

It also supports rescheduling for periodic jobs and captures pre- and post-
execution data for debugging or auditing purposes. This class is intended 
for Zabbix-related jobs that require both database consistency and clear 
failure visibility.
"""

# Standard library imports
from datetime import timedelta

# Django imports
from django.db import transaction

# NetBox imports
from core.choices import JobStatusChoices
from netbox.jobs import JobRunner

# NetBox Zabbix plugin imports
from netbox_zabbix.settings import get_event_log_enabled
from netbox_zabbix.logger import logger



class AtomicJobRunner(JobRunner):
    """
    JobRunner that ensures transactional execution and propagates exceptions.
    
    Problem:
        NetBox's built-in JobRunner.handle() method swallows all exceptions that
        occur during job execution. While it updates the job's status and logs
        the error, it does not re-raise the exception. This makes it impossible
        to itentify the job as failed in GUI and impossible for a user to restart
        the job.
    
    Solution:
        This subclass overrides the `handle()` method to re-raise any unhandled
        exceptions after updating the job status and metadata. This allows
        external callers using `.enqueue()` or `.handle()` to detect failures,
        making it suitable for retry mechanisms, task chaining, and tests.
    
    Transaction Behavior:
        - The job execution (`run()`) occurs inside a `transaction.atomic()` block.
        - If any part of the job fails, the database changes are rolled back.
        - This guarantees consistency between the job's result and its side effects.
    
    Additional Features:
        - Stores structured `job.data` on both success and failure to preserve context.
        - Maintains support for periodic (interval-based) jobs via `job.interval`.
    
    Usage:
        Subclass this instead of JobRunner when external failure visibility and
        transactional integrity are required.
    """

    @classmethod
    def handle(cls, job, *args, **kwargs):
        """
        Execute the job inside a transactional block and handle exceptions.
        
        Args:
            job (JobRunner): The job instance being executed.
            *args: Positional arguments passed to the job's `run` method.
            **kwargs: Keyword arguments passed to the job's `run` method.
        
        Behavior:
            - Calls `job.start()`.
            - Executes `cls(job).run(*args, **kwargs)` within a `transaction.atomic()` block.
            - Updates `job.data` and terminates the job with success or failure status.
            - Logs the event via `_log_event()`.
            - Reschedules the job if `job.interval` is set.
        
        Raises:
            Exception: Any exception raised by `run()` is re-raised after updating job status.
        """
        cls.job = job
        result = {}
        signal_id  = str( kwargs.get( "signal_id", None ) )
        
        try:
            job.start()
            with transaction.atomic():
                result = cls(job).run( *args, **kwargs ) or {}
                job.data = { 
                    "status":     "success", 
                    "result":     result, 
                    "signal_id":  signal_id,
                    "data":       result.get( "data" ),
                    "pre_data":   result.get( "pre_data" ),
                    "post_data":  result.get( "post_data" ),
                }
                job.terminate( status=JobStatusChoices.STATUS_COMPLETED )
            cls._log_event( name=job.name, job=job, result=result, signal_id=signal_id )

        except Exception as e:
            error_msg = str( e )
            data      = getattr( e, "data", None )
            pre_data  = getattr( e, "pre_data", None )
            post_data = getattr( e, "post_data", None )
            
            job.data = {
                "status":     "failed",
                "error":      error_msg,
                "message":    "Database changes have been reverted automatically.",
                "signal_id":  signal_id,
                "data":       data,
                "pre_data":   pre_data,
                "post_data":  post_data,
            }

            job.terminate( status=JobStatusChoices.STATUS_ERRORED, error=error_msg )
            
            logger.error( e )
            
            cls._log_event( name=job.name, job=job, result=result, exception=error_msg, data=data, pre_data=pre_data, post_data=post_data, signal_id=signal_id )
            raise

        finally:
            if job.interval:
                new_scheduled_time = ( job.scheduled or job.started ) + timedelta( minutes=job.interval )
                cls.enqueue(
                    instance=job.object,
                    name=job.name,
                    user=job.user,
                    schedule_at=new_scheduled_time,
                    interval=job.interval,
                    **kwargs,
                )


    @classmethod
    def run_now(cls, *args, **kwargs):
        """
        Execute the job immediately in a transactional context.
        
        Args:
            *args: Positional arguments for the job's `run` method.
            **kwargs: Keyword arguments for the job's `run` method.
                - name (str, optional): Name of the job. Defaults to `cls.name`.
                - eventlog (bool, optional): Whether to log events. Defaults to True.
        
        Returns:
            str: The message from the job's result, or the string representation of the result.
        
        Raises:
            Exception: Any exception raised by `run()` is propagated.
        
        Notes:
            - This method ensures that database changes are rolled back if an exception occurs.
            - Logs the job result to EventLog if `eventlog=True`.
        """
        name = kwargs.get( "name", cls.name )
        result = None
        exception = None

        try:
            with transaction.atomic():
                result = cls.run( *args, **kwargs ) or {}
        except Exception as e:
            exception = str( e )
            raise
        finally:
            if kwargs.get("eventlog", True):
                cls._log_event(name=name, job=None, result=result, exception=exception)

        return result.get( "message", str( result ) )
    
    @staticmethod
    def _log_event(name, job=None, result=None, exception=None, data=None, pre_data=None, post_data=None, signal_id=None ):
        """
        Log a structured job event to the EventLog model.
        
        Args:
            name (str): Name of the job.
            job (JobRunner, optional): The job instance associated with the event.
            result (dict, optional): The result dictionary returned by the job.
            exception (str, optional): Exception message if the job failed.
            data (any, optional): Job-specific result data.
            pre_data (any, optional): Data captured before job execution.
            post_data (any, optional): Data captured after job execution.
            signal_id (str, optional): Signal ID for correlating events.
        
        Behavior:
            - Skips logging if event logging is disabled via `get_event_log_enabled()`.
            - Ensures only allowed keys are passed to EventLog (`name`, `job`, `message`, `data`, `pre_data`, `post_data`, `exception`, `signal_id`).
            - Creates an EventLog record with the structured payload.
        """
        from netbox_zabbix.models import EventLog # Here to prevent circular imports
        if not get_event_log_enabled():
            return
        
        # Ensure result is a dictionary
        result = result or {}
        payload = {
            "name":       name,
            "job":        job,
            "signal_id":  signal_id,
            "message":    result.get( "message", str( result ) if not exception else "" ),
            "data":       data      if data      else result.get( "data" ),
            "pre_data":   pre_data  if pre_data  else result.get( "pre_data" ),
            "post_data":  post_data if post_data else result.get( "post_data" ),
        }

        if exception:
            payload["exception"] = exception

        # Only pass allowed keys to EventLog
        allowed_fields = { "name", "job", "message", "data", "pre_data", "post_data", "exception", "signal_id" }
        safe_payload = { k: v for k, v in payload.items() if k in allowed_fields and v is not None }
        EventLog.objects.create( **safe_payload )


# end