
"""
NetBox Zabbix Plugin - Immediate Host Sync Job

This module defines the `SyncHostsNow` job, which can be executed to 
synchronize all NetBox `HostConfig` objects with their corresponding
hosts in Zabbix immediately.

Unlike recurring jobs, this job runs on demand and iterates over all 
host configurations, calling `update_zabbix_host` for each.

Any errors encountered during the sync of individual hosts are logged
and raised to ensure visibility of failures.
"""


# NetBox Zabbix Imports
from netbox_zabbix.jobs.atomicjobrunner import AtomicJobRunner
from netbox_zabbix.models import HostConfig
from netbox_zabbix.zabbix.hosts import update_zabbix_host
from netbox_zabbix.logger import logger


class SyncHostsNow(AtomicJobRunner):
    """
    Job to synchronize all NetBox hosts to Zabbix.
    
    This job loops over all HostConfig objects and updates each one
    in Zabbix. Execution occurs inside a transactional context, so
    any failures will roll back database changes.
    """

    @classmethod
    def run(cls, *args, **kwargs):
        """
        Execute the host synchronization.
        
        Args:
            user (User, optional): The triggering user.
            request_id (str, optional): Request identifier for logging.
        
        Returns:
            dict: Summary of host sync results.
        """
        user = kwargs.get( "user" )
        request_id = kwargs.get( "request_id" )

        total = HostConfig.objects.count()
        updated = 0
        failed = 0

        for idx, host_config in enumerate( HostConfig.objects.all(), start=1 ):
            try:
                update_zabbix_host( host_config, user, request_id )
                host_config.update_sync_status()
                updated += 1
            except Exception as e:
                failed += 1
                msg = f"[{idx}/{total}] Failed to update host {host_config.name} (pk={host_config.pk}): {e}"
                logger.error( msg )

        return {
            "total": total,
            "updated": updated,
            "failed": failed,
            "message": f"Sync complete: {updated}/{total} hosts updated, {failed} failed."
        }

    @classmethod
    def run_job_now(cls, request):
        """
        Immediately execute the job in the current process.

        Args:
            request (HttpRequest): The triggering request.

        Returns:
            dict: Job execution summary.
        """
        # Call `run` directly, bypassing the single-instance expectations of `run_now`
        return cls.run(user=request.user, request_id=request.id)