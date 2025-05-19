from netbox.jobs import JobRunner
from core.choices import JobStatusChoices
from datetime import timedelta
from core.models import Job

import logging
logger = logging.getLogger( 'netbox.plugins.netbox_zabbix' )

class RaisingJobRunner(JobRunner):
    """
    Custom JobRunner that fixes a limitation in NetBox's default JobRunner.
    
    Problem:
        NetBox's built-in JobRunner.handle() method swallows all exceptions that
        occur during job execution. While it updates the job's status and logs
        the error, it does not re-raise the exception. This makes it impossible
        for external systems (e.g., background task runners or API callers) to
        detect that the job has failed unless they explicitly poll the job
        status or inspect `job.data`.

    Solution:
        This subclass overrides the `handle()` method to re-raise any unhandled
        exceptions after updating the job status and metadata. This ensures that
        external callers using `.enqueue()` or `.handle()` will receive the
        exception, making it suitable for cases where you want failure
        visibility, such as chaining tasks, retry mechanisms, or test
        environments.
    
    Additionally:
        - Stores structured `job.data` on both success and failure to preserve context.
        - Maintains support for periodic jobs via `job.interval`.
    
    Usage:
        Subclass this instead of JobRunner for any job that needs external failure visibility.
    """

    
    @classmethod
    def handle(cls, job, *args, **kwargs):
        try:
            job.start()
            result = cls(job).run(*args, **kwargs)
            job.data = { "status": "success", "result": result }
            job.terminate( status=JobStatusChoices.STATUS_COMPLETED )

        except Exception as e:
            job.terminate(status=JobStatusChoices.STATUS_ERRORED, error=str(e))
            job.data = { "status": "failed", "error": str(e) }
            logging.error(e)
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

