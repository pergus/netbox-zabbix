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
from datetime import timedelta, datetime

# NetBox imports
from core.models import Job

# NetBox Zabbix Imports
from netbox_zabbix.jobs.atomicjobrunner import AtomicJobRunner
from netbox_zabbix.importing import import_zabbix_settings
from netbox_zabbix.logger import logger


class ImportZabbixSystemJob( AtomicJobRunner ):
    """
    System job to import Zabbix settings on a recurring interval.
    """
    class Meta:
        name = "Import Zabbix System Job"


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
            "schedule_at":  datetime.now() + timedelta(minutes=interval),
        }

        job = cls.enqueue_once( **job_args )
        logger.error( f"Scheduled new system job '{name}' with interval {interval}" )
        return job

