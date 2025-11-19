"""
NetBox Zabbix Plugin — System and Recurring Jobs

Defines system-level and recurring background jobs responsible for periodic
synchronization between Zabbix and NetBox. These jobs ensure that Zabbix
configuration objects (such as templates, proxies, and host groups) remain
up to date in NetBox without manual intervention.

Classes:
    - ImportZabbixSystemJob: Periodically imports Zabbix settings into NetBox
      on a configurable recurring interval.

These jobs are typically scheduled automatically and managed by NetBox’s
background task system using the RQ job queue.
"""

# Standard library imports
from datetime import timedelta

# Django imports
from django.utils import timezone
from django.db import transaction

# NetBox imports
from core.models import Job

# NetBox Zabbix plugin imports
from netbox_zabbix.jobs.atomicjobrunner import AtomicJobRunner
from netbox_zabbix.importing import import_zabbix_settings
from netbox_zabbix.models import HostConfig
from netbox_zabbix import settings
from netbox_zabbix.logger import logger

# registry
SYSTEM_JOB_REGISTRY = {}

def register_system_job(get_interval_func):
    """Class decorator to register a job class with its interval getter."""
    def decorator(cls):
        SYSTEM_JOB_REGISTRY[get_interval_func] = cls
        return cls
    return decorator


@register_system_job(settings.get_zabbix_import_interval)
class SystemJobImportZabbixSettings( AtomicJobRunner ):
    """
    System job to import Zabbix settings on a recurring interval.
    """
    class Meta:
        name = "System Job Import Zabbix Settings"


    @classmethod
    def run(cls, *args, **kwargs):
        """
        Imports Zabbix settings.
        
        Returns:
            dict: Import summary.
        
        Raises:
            Exception: If import fails.
        """
        try:
            return import_zabbix_settings()
        except Exception as e:
            msg = f"Failed to import zabbix settings: { str( e ) }"
            logger.error( msg )
            raise Exception( msg )


    @classmethod
    def schedule(cls, interval=None):
        """
        Schedules the system job at a recurring interval.
        
        Args:
            interval (int): Interval in minutes.
        
        Returns:
            Job: Scheduled job instance.
        
        Notes:
            - Only one instance of the system job is allowed at a time.
        """
        if interval == None:
            logger.error( "Import Zabbix System Job required an interval" )
            return None
        
        name = cls.Meta.name

        jobs = Job.objects.filter( name=name, status__in = [ "scheduled", "pending", "running" ] )

        if len(jobs) > 1:
            logger.error( f"Internal error: there can only be one instance of system job '{name}'" )
            return None
        
        existing_job = jobs[0] if len(jobs) == 1 else None

        if existing_job:
            if existing_job.interval == interval:
                logger.error( f"No need to update interval for system job {name}" )
                return existing_job
            logger.error( f"Deleted old job instance for '{name}'")
            existing_job.delete()
        
        
        job_args = {
            "name":         name,
            "interval":     interval,
            "schedule_at":  timezone.now() + timedelta( minutes=interval ),
        }

        job = cls.enqueue_once( **job_args )
        logger.error( f"Scheduled new system job '{name}' with interval {interval}" )
        return job



@register_system_job(settings.get_host_config_sync_interval)
class SystemJobHostConfigSyncRefresh( AtomicJobRunner ):
    """
    System job to refresh HostConfig sync status on a recurring interval.
    """
    class Meta:
        name = "System Job HostConfig Sync Refresh"

    # Default interval for checking hosts that haven't been synced recently
    CHECK_INTERVAL_MINUTES = 60

    @classmethod
    def run(cls, *args, **kwargs):
        """
        Update HostConfig objects that haven't been checked recently.
        
        Returns:
            dict: Summary of updated hosts.
        
        Raises:
            Exception: If any unexpected error occurs.
        """
        updated = 0
        failed = 0
        total = 0

        cutoff = timezone.now() - timedelta(minutes=cls.CHECK_INTERVAL_MINUTES)
        host_configs = HostConfig.objects.filter(last_synced__lt=cutoff)
        total = host_configs.count()

        for i, host in enumerate(host_configs, start=1):
            try:
                host.update_sync_status()
                host.last_sync_update = timezone.now()
                host.save(update_fields=['last_sync_update'])
                updated += 1
            except Exception as e:
                failed += 1
                logger.warning(f"[{i}/{total}] Failed to update {host.name}: {e}")

        return {
            "total": total,
            "updated": updated,
            "failed": failed,
        }

    @classmethod
    def schedule(cls, interval=None):
        """
        Schedule this system job at a recurring interval.
        
        Args:
            interval (int): Interval in minutes.
        
        Returns:
            Job: Scheduled job instance.
        """
        if interval is None:
            logger.error("UpdateHostConfigSync requires an interval")
            return None

        name = cls.Meta.name
        jobs = Job.objects.filter(name=name, status__in=["scheduled", "pending", "running"])
        existing_job = jobs[0] if jobs.exists() else None

        if existing_job:
            if existing_job.interval == interval:
                logger.error( f"No need to update interval for system job {name}" )
                return existing_job
            logger.error( f"Deleting old job instance for '{name}'" )
            existing_job.delete()

        job_args = {
            "name":        name,
            "interval":    interval,
            "schedule_at": timezone.now() + timedelta(minutes=interval),
        }

        job = cls.enqueue_once(**job_args)
        logger.error( f"Scheduled new system job '{name}' with interval {interval}" )
        return job



def get_current_job_interval(job_cls):
    """
    Retrieve the currently scheduled interval for a given system job.
    
    Args:
        job_cls (type): The system job class (subclass of AtomicJobRunner).
    
    Returns:
        int or None: The interval in minutes at which the job is currently scheduled,
                     or None if the job is not currently scheduled or running.
    
    Example:
        >>> get_current_job_interval(SystemJobImportZabbixSettings)
        60
    """
    name = job_cls.Meta.name
    job = Job.objects.filter( name=name, status__in=["scheduled", "pending", "running"] ).first()
    return job.interval if job else None


def schedule_system_jobs():
    """
    Schedule or reschedule all system jobs in the SYSTEM_JOB_REGISTRY based on their configured intervals.
    
    This function iterates over all registered system jobs, retrieves the desired interval using
    the associated getter function, checks if the currently scheduled interval differs, and if so,
    schedules or reschedules the job using Django's transaction.on_commit to ensure database consistency.
    
    Notes:
        - Uses SYSTEM_JOB_REGISTRY, a mapping of interval getter functions to job classes.
        - If the job is not yet scheduled, it will be scheduled with the new interval.
        - If the job is already scheduled with a different interval, it will be rescheduled.
    
    Example:
        >>> schedule_system_jobs()
    """
    for get_interval, job_cls in SYSTEM_JOB_REGISTRY.items():
        new_interval = get_interval()
        old_interval = get_current_job_interval( job_cls )
        logger.info( f"{job_cls.name} new_interval: {new_interval}" )
        if not old_interval or new_interval != old_interval:
            transaction.on_commit(
                lambda job_cls=job_cls, interval=new_interval: job_cls.schedule( interval )
            )


def system_jobs_scheduled():
    """
    Check if all registered system jobs are currently scheduled or running.
    """

    for job_cls in SYSTEM_JOB_REGISTRY.values():
        name = job_cls.Meta.name
        job_exists = Job.objects.filter( name=name, status__in=["scheduled", "pending", "running"] ).exists()
        if not job_exists:
            return False
    return True


# end