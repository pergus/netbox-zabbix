# job.py
#
# Description:
#


from django.db import transaction

from datetime import timedelta
from core.choices import JobStatusChoices
from netbox.jobs import JobRunner

from netbox_zabbix.settings import get_event_log_enabled
from netbox_zabbix.logger import logger

class AtomicJobRunner(JobRunner):
    """
    JobRunner that ensures transactional execution and propagates exceptions.
    
    Problem:
        NetBox's built-in JobRunner.handle() method swallows all exceptions that
        occur during job execution. While it updates the job's status and logs
        the error, it does not re-raise the exception. This makes it impossible
        itentify the job as failed in GUI and impossible for a user to restart
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
                    "signal_id":  str( kwargs.get( "signal_id" ) ),
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
                    signal_id=job.signal_id,
                    **kwargs,
                )


    @classmethod
    def run_now(cls, *args, **kwargs):
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
        from netbox_zabbix.models import EventLog # Here to prevent circular imports
        if not get_event_log_enabled():
            return
        
        # Ensure result is a dictionary
        result = result or {}
        payload = {
            "name":      name,
            "job":       job,
            "signal_id": signal_id,
            "message":   result.get( "message", str( result ) if not exception else "" ),
            "data":      data      if data      else result.get( "data" ),
            "pre_data":  pre_data  if pre_data  else result.get( "pre_data" ),
            "post_data": post_data if post_data else result.get( "post_data" ),
        }

        if exception:
            payload["exception"] = exception

        # Only pass allowed keys to EventLog
        allowed_fields = { "name", "job", "message", "data", "pre_data", "post_data", "exception", "signal_id" }
        safe_payload = { k: v for k, v in payload.items() if k in allowed_fields and v is not None }
        EventLog.objects.create( **safe_payload )