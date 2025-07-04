# job.py
from datetime import timedelta
from django.db import transaction
from core.choices import JobStatusChoices
from netbox.jobs import JobRunner

from netbox_zabbix.models import EventLog
from netbox_zabbix.config import get_event_log_enabled
from netbox_zabbix.logger import logger

#class AtomicJobRunner(JobRunner):
#    """
#    JobRunner that ensures transactional execution and propagates exceptions.
#    
#    Problem:
#        NetBox's built-in JobRunner.handle() method swallows all exceptions that
#        occur during job execution. While it updates the job's status and logs
#        the error, it does not re-raise the exception. This makes it impossible
#        itentify the job as failed in GUI and impossible for a user to restart
#        the job.
#    
#    Solution:
#        This subclass overrides the `handle()` method to re-raise any unhandled
#        exceptions after updating the job status and metadata. This allows
#        external callers using `.enqueue()` or `.handle()` to detect failures,
#        making it suitable for retry mechanisms, task chaining, and tests.
#    
#    Transaction Behavior:
#        - The job execution (`run()`) occurs inside a `transaction.atomic()` block.
#        - If any part of the job fails, the database changes are rolled back.
#        - This guarantees consistency between the job's result and its side effects.
#    
#    Additional Features:
#        - Stores structured `job.data` on both success and failure to preserve context.
#        - Maintains support for periodic (interval-based) jobs via `job.interval`.
#    
#    Usage:
#        Subclass this instead of JobRunner when external failure visibility and
#        transactional integrity are required.
#    """
#
#    # Note: job.data has to be set **before** terminating the job.
#    @classmethod
#    def handle(cls, job, *args, **kwargs):
#        
#        cls.job = job
#        result = None
#
#        try:
#            job.start()
#            with transaction.atomic():
#                result = cls(job).run(*args, **kwargs)
#                job.data = { "status": "success", "result": result }
#                job.terminate( status=JobStatusChoices.STATUS_COMPLETED )
#            
#            if get_event_log_enabled():
#                EventLog.objects.create( name=job.name, job=job, **result)
#            
#        except Exception as e:
#            job.data = { "status": "failed", "error": str(e), "message": "Database changes have been reverted automatically." }
#            job.terminate( status=JobStatusChoices.STATUS_ERRORED, error=str(e) )
#            logger.error( e )
#
#            if get_event_log_enabled():
#                EventLog.objects.create( name=job.name, job=job, exception=str( e), **result )
#            raise
#
#        finally:
#            if job.interval:
#                new_scheduled_time = (job.scheduled or job.started) + timedelta(minutes=job.interval)
#                cls.enqueue(
#                    instance=job.object,
#                    name=job.name,
#                    user=job.user,
#                    schedule_at=new_scheduled_time,
#                    interval=job.interval,
#                    **kwargs,
#                )
#
#    @classmethod
#    def run_now(cls, *args, **kwargs):
#        name = kwargs.get( "name", cls.name)
#        result = None
#
#        try:
#            with transaction.atomic():
#                result = cls.run( *args, **kwargs )
#
#            if get_event_log_enabled():
#                if isinstance( result, dict ) and "message" in result:
#                    message=result.get("message", "")
#                    EventLog.objects.create( name=name, job=None, **result )
#                    return message
#                else:
#                    message=str( result )
#                    EventLog.objects.create( name=name, job=None, message=message )
#                    return message
#
#        except Exception as e:
#            if get_event_log_enabled():
#                EventLog.objects.create( name=name, job=None, exception=str( e ) )
#            raise Exception( e )


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

        try:
            job.start()
            with transaction.atomic():
                result = cls(job).run( *args, **kwargs ) or {}
                job.data = { "status": "success", "result": result }
                job.terminate( status=JobStatusChoices.STATUS_COMPLETED )

            cls._log_event( name=job.name, job=job, result=result )

        except Exception as e:
            error_msg = str( e )
            job.data = {
                "status": "failed",
                "error": error_msg,
                "message": "Database changes have been reverted automatically.",
            }
            job.terminate( status=JobStatusChoices.STATUS_ERRORED, error=error_msg )
            logger.error(e)
            cls._log_event( name=job.name, job=job, result=result, exception=error_msg )
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
            cls._log_event( name=name, job=None, result=result, exception=exception )

        return result.get( "message", str( result ) )
    
    @staticmethod
    def _log_event(name, job=None, result=None, exception=None):
        if not get_event_log_enabled():
            return
        
        # Ensure result is a dictionary
        result = result or {}

        payload = {
            "name": name,
            "job": job,
            "message": result.get("message", str( result ) if not exception else "" ),
            "data": result.get( "data" ),
        }

        if exception:
            payload["exception"] = exception

        # Only pass allowed keys to EventLog
        allowed_fields = { "name", "job", "message", "data", "exception" }
        safe_payload = { k: v for k, v in payload.items() if k in allowed_fields and v is not None }
        EventLog.objects.create( **safe_payload )