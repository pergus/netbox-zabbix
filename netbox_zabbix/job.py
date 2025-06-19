# job.py
from datetime import timedelta
from django.db import transaction
from core.choices import JobStatusChoices
from netbox.jobs import JobRunner

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

    # Note: job.data has to be set **before** terminating the job.
    @classmethod
    def handle(cls, job, *args, **kwargs):
        try:
            job.start()
            with transaction.atomic():
                result = cls(job).run(*args, **kwargs)
                job.data = { "status": "success", "result": result }
                job.terminate( status=JobStatusChoices.STATUS_COMPLETED )

        except Exception as e:
            job.data = { "status": "failed", "error": str(e), "message": "Database changes have been reverted automatically." }            
            job.terminate( status=JobStatusChoices.STATUS_ERRORED, error=str(e) )
            logger.error( e )
            raise

        finally:
            if job.interval:
                new_scheduled_time = (job.scheduled or job.started) + timedelta(minutes=job.interval)
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
        with transaction.atomic():
            return cls.run( *args, **kwargs )
    