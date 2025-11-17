"""
NetBox Zabbix Plugin — Import Jobs

This module defines background job classes for importing data from Zabbix 
into NetBox using RQ (Redis Queue). It handles both Zabbix config imports 
and Zabbix host imports:

- ImportZabbixSettings: Synchronizes global Zabbix entities such as templates, 
  proxies, proxy groups, and host groups into NetBox models.

- ImportHost: Imports a single Zabbix host into NetBox, creating or updating 
  a corresponding HostConfig for a Device or VirtualMachine.

These jobs provide asynchronous execution, error handling, and logging 
to ensure consistent synchronization between Zabbix and NetBox.
"""

# Django imports
from django.contrib.contenttypes.models import ContentType


# NetBox imports

from dcim.models import Device
from virtualization.models import VirtualMachine

# NetBox Zabbix Imports
from netbox_zabbix.jobs.atomicjobrunner import AtomicJobRunner
from netbox_zabbix.jobs.base import require_kwargs
from netbox_zabbix.zabbix.api import get_host
from netbox_zabbix.helpers import get_instance
from netbox_zabbix.importing  import ImportHostContext, import_zabbix_host, import_zabbix_settings
from netbox_zabbix.logger import logger


class ImportZabbixSettings( AtomicJobRunner ):
    """
    Job to import Zabbix settings into NetBox.
    
    This job imports templates, proxies, proxy groups, and host groups from Zabbix.
    """
    @classmethod
    def run(cls, *args, **kwargs):
        """
        Executes the import of Zabbix settings.
        
        Returns:
            dict: Imported configuration summary.
        
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
    def run_job(cls, user=None, schedule_at=None, interval=None, immediate=False, name=None):
        """
        Schedules or enqueues the ImportZabbixSettings job.
        
        Args:
            user (User, optional): User triggering the job.
            schedule_at (datetime, optional): Schedule time.
            interval (int, optional): Interval in minutes for recurring job.
            immediate (bool, optional): Run job immediately.
            name (str, optional): Job name.
        
        Returns:
            Job: The enqueued job instance.
        """
        name = name or "Import Zabbix Settings"

        job_args = {
            "name":        name,
            "schedule_at": schedule_at,
            "interval":    interval,
            "immediate":   immediate,
            "user":        user,
        }

        if interval is None:
            netbox_job = cls.enqueue( **job_args )
        else:
            netbox_job = cls.enqueue_once( **job_args )

        return netbox_job


class ImportHost( AtomicJobRunner ):
    """
    Job to import a Zabbix host into NetBox as a HostConfig.
    """
    @classmethod
    def run(cls, *args, **kwargs):
        """
        Imports a Zabbix host into NetBox using ImportHostContext.
        
        Returns:
            dict: Message confirming import and imported Zabbix host data.
        
        Raises:
            Exception: If instance is invalid or import fails.
        """
        # Require content_type and object id
        content_type = require_kwargs( kwargs, "content_type" )
        obj_id = require_kwargs( kwargs, "id" )

        # Retrieve the actual instance
        instance = get_instance( content_type.id, obj_id )

        if not isinstance( instance, (Device, VirtualMachine) ):
            raise Exception( "Missing required device or virtual machine instance" )

        job_args = {
            "obj_instance": instance,
            "content_type": content_type,
            "user":         cls.job.user,
            "request_id":   kwargs.get( "request_id" ),
            "job":          cls.job
        }
        
        try:
            job_args["zabbix_host"] = get_host( instance.name )
        except:
            raise

        return import_zabbix_host( ImportHostContext( **job_args ) )

    @classmethod
    def run_job(cls, instance, request, schedule_at=None, interval=None, immediate=False, name=None):
        """
        Schedules an ImportHost job.
        
        Args:
            instance (Device|VirtualMachine): Target instance.
            request (HttpRequest): Triggering request.
            schedule_at (datetime, optional): Schedule time.
            interval (int, optional): Interval for recurring job.
            immediate (bool, optional): Run immediately.
            name (str, optional): Job name.
        
        Returns:
            Job: Enqueued job instance.
        """
        if not isinstance( instance, (Device, VirtualMachine) ):
            raise Exception( "Missing required device or virtual machine instance" )

        name = name or f"Import {instance.name}"
        
        job_args = {
            # General Job arguments - 'instance' cannot be used on Devices or VMs.
            "name":         name,
            "schedule_at":  schedule_at,
            "interval":     interval,
            "immediate":    immediate,

            # Specific Job arguments
            "content_type": ContentType.objects.get_for_model( instance, for_concrete_model=False ),
            "id":           instance.id
        }
        
        if request:
            job_args["user"]       = request.user
            job_args["request_id"] = request.id

        if interval is None:
            netbox_job = cls.enqueue( **job_args )
        else:
            netbox_job = cls.enqueue_once( **job_args )

        return netbox_job
