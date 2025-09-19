
def delete_failed_jobs():
    from django_rq import get_queue
    from rq.registry import FailedJobRegistry
    
    queue = get_queue( "default" )  # or "high"/"low" if you use multiple queues
    failed_registry = FailedJobRegistry( queue=queue )

    # Remove all failed jobs
    for job_id in failed_registry.get_job_ids():
        failed_registry.remove( job_id, delete_job=True )