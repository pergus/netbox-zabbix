
from django.core.management.base import BaseCommand
from rich.console import Console
from rich.table import Table
from django_rq import get_queue
from rq.registry import FailedJobRegistry
from rq.job import Job

class Command(BaseCommand):
    help = "Delete or list failed jobs"

    def add_arguments(self, parser):
        # Add a positional argument 'action' that can be 'list' or 'delete'
        parser.add_argument(
            "action",
            choices=["list", "delete", "rerun" ],
            help="Action to perform: list, delete or rerun failed jobs"
        )

    def handle(self, *args, **options):
        action = options["action"]

        if action == "list":
            self.list_failed_jobs()
        elif action == "delete":
            self.delete_failed_jobs()
        elif action == "rerun":
            self.rerun_failed_jobs()


    def list_failed_jobs(self):
        console = Console()
        queue = get_queue( "default" )
        failed_registry = FailedJobRegistry( queue=queue )

        table = Table( title="Failed Jobs" )
        table.add_column( "Job ID" )
        for job_id in failed_registry.get_job_ids():
            table.add_row( job_id )
        console.print( table )

    def delete_failed_jobs(self):
        queue = get_queue( "default" )
        failed_registry = FailedJobRegistry( queue=queue )
        
        for job_id in failed_registry.get_job_ids():
            failed_registry.remove( job_id, delete_job=True )
            self.stdout.write( self.style.SUCCESS( f"Deleted job {job_id}" ) )
        self.stdout.write( self.style.SUCCESS( "All failed jobs have been deleted." ) )


    def rerun_failed_jobs(self):
         queue = get_queue("default")
         failed_registry = FailedJobRegistry(queue=queue)
    
         job_ids = failed_registry.get_job_ids()
    
         if not job_ids:
             self.stdout.write(self.style.WARNING("No failed jobs found."))
             return
    
         for job_id in job_ids:
             job = Job.fetch(job_id, connection=queue.connection)
    
             # Requeue the job
             queue.enqueue_job(job)
    
             # Remove from failed registry
             # Set delete_job=False so the original job object remains
             failed_registry.remove(job_id, delete_job=False)
    
             self.stdout.write(
                 self.style.SUCCESS(f"Requeued job {job_id}")
             )
    
         self.stdout.write(
             self.style.SUCCESS("All failed jobs have been requeued.")
         )