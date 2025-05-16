from core.choices import JobStatusChoices
from core.models import Job


import logging
logger = logging.getLogger('netbox.plugins.netbox_zabbix')


class TaskExecutionError(Exception):
    """Raised when the task logic encounters a known failure."""
    pass


def run_task(task_func, *args, job=None, **kwargs):
    """
    Run a task function either as an RQ job or regular function call.

    Args:
        task_func (callable): Core logic function.
        job (Job, optional): Job instance if run as a background job.
        **kwargs: Arguments passed to the task_func.

    Returns:
        str: Success message from the task function.

    Raises:
        TaskExecutionError: For controlled failures.
        Exception: For unexpected exceptions.
    """
    task_name = task_func.__name__
    job_id = getattr(job, 'job_id', 'N/A')
    logger.info(f"[{task_name}] Starting (Job ID: {job_id})")

    try:
        message = task_func( *args, **kwargs )
        logger.info( f"[{task_name}] Success: {message}" )

        if job:
            job.data = {"status": "ok", "message": message}
            job.terminate( status=JobStatusChoices.STATUS_COMPLETED )

        return message

    except TaskExecutionError as e:
        logger.error( f"[{task_name}] Failed: {e}" )
        if job:
            job.data = {"status": "failed", "error": str(e)}
            job.terminate( status=JobStatusChoices.STATUS_ERRORED, error=str(e) )
        raise

    except Exception as e:
        logger.exception( f"[{task_name}] Unexpected error: {e}" )
        if job:
            job.data = {"status": "failed", "error": "Unexpected error"}
            job.terminate( status=JobStatusChoices.STATUS_ERRORED, error=str(e) )
        raise


def job_wrapper(task_func, **kwargs):
    from netbox_zabbix.jobb import run_task
    return run_task(task_func, **kwargs)


def run(func, *args, **kwargs):
    """
    Run a task
    """
    return run_task(func, *args, **kwargs)

def run_as_job(task_func, name, user, **kwargs):
    return Job.enqueue( job_wrapper, name=name, user=user, task_func=task_func, **kwargs )
