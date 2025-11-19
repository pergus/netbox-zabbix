from django.core.management.base import BaseCommand
from rich.console import Console
from rich.table import Table
from django_rq import get_queue
from rq.registry import ScheduledJobRegistry
from rq.job import Job

class Command(BaseCommand):
    help = "List, delete, or rerun scheduled jobs"

    def add_arguments(self, parser):
        parser.add_argument(
            "action",
            choices=["list", "delete", "rerun"],
            help="Action to perform: list, delete, or rerun scheduled jobs"
        )
        parser.add_argument(
            "--job-id",
            help="Optional job ID. If provided, action is only applied to this job."
        )

    def handle(self, *args, **options):
        action = options["action"]
        job_id = options.get("job_id")

        if action == "list":
            self.list_scheduled_jobs()
        elif action == "delete":
            self.delete_scheduled_jobs(job_id)
        elif action == "rerun":
            self.rerun_scheduled_jobs(job_id)

    def list_scheduled_jobs(self):
        console = Console()
        queue = get_queue("default")
        scheduled_registry = ScheduledJobRegistry(queue=queue)

        table = Table(title="Scheduled Jobs")
        table.add_column("Job ID")
        for job_id in scheduled_registry.get_job_ids():
            table.add_row(job_id)
        console.print(table)

    def delete_scheduled_jobs(self, job_id=None):
        queue = get_queue("default")
        scheduled_registry = ScheduledJobRegistry(queue=queue)

        if job_id:
            if job_id in scheduled_registry.get_job_ids():
                scheduled_registry.remove(job_id, delete_job=True)
                self.stdout.write(self.style.SUCCESS(f"Deleted job {job_id}"))
            else:
                self.stdout.write(self.style.WARNING(f"Job ID {job_id} not found."))
        else:
            for jid in scheduled_registry.get_job_ids():
                scheduled_registry.remove(jid, delete_job=True)
                self.stdout.write(self.style.SUCCESS(f"Deleted job {jid}"))
            self.stdout.write(self.style.SUCCESS("All scheduled jobs have been deleted."))

    def rerun_scheduled_jobs(self, job_id=None):
        queue = get_queue("default")
        scheduled_registry = ScheduledJobRegistry(queue=queue)

        job_ids = [job_id] if job_id else scheduled_registry.get_job_ids()

        if not job_ids:
            self.stdout.write(self.style.WARNING("No jobs found."))
            return

        for jid in job_ids:
            try:
                job = Job.fetch(jid, connection=queue.connection)
                queue.enqueue_job(job)
                scheduled_registry.remove(jid, delete_job=False)
                self.stdout.write(self.style.SUCCESS(f"Requeued job {jid}"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Failed to requeue job {jid}: {e}"))

        self.stdout.write(self.style.SUCCESS("All specified jobs have been requeued."))
