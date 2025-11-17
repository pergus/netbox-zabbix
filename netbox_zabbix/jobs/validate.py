"""
NetBox Zabbix Plugin — Host Validation Jobs

Defines job classes that validate the synchronization status of Zabbix hosts
against corresponding NetBox devices or virtual machines. These jobs ensure
that host configurations in Zabbix match the expected state in NetBox,
helping to detect configuration drift or inconsistencies.

Classes:
    - ValidateHost: Validates a Zabbix host configuration for a given
      NetBox Device or VirtualMachine, raising exceptions on validation
      failures or misconfigured instances.

These jobs can be scheduled, enqueued immediately, or run on-demand
using the NetBox job system.
"""

# Django Imports
from django.contrib.contenttypes.models import ContentType

# NetBox imports
from dcim.models import Device
from virtualization.models import VirtualMachine


# NetBox Zabbix Imports
from netbox_zabbix.jobs.atomicjobrunner import AtomicJobRunner
from netbox_zabbix.jobs.base import require_kwargs
from netbox_zabbix.zabbix.api import get_host
from netbox_zabbix.zabbix.validation import validate_zabbix_host

from netbox_zabbix.helpers import get_instance



class ValidateHost( AtomicJobRunner ):
    """
    Job to validate a Zabbix host configuration against a NetBox device or VM.
    """
    @classmethod
    def run(cls, *args, **kwargs):
        """
        Validates the Zabbix host configuration for a given instance.
        
        Returns:
            bool: True if validation passes.
        
        Raises:
            Exception: If the host cannot be validated or instance is invalid.
        """

        # Require content_type and object id
        content_type = require_kwargs( kwargs, "content_type" )
        obj_id = require_kwargs( kwargs, "id" )

        # Retrieve the actual instance
        instance = get_instance( content_type.id, obj_id )
        
        if not isinstance( instance, (Device, VirtualMachine) ):
            raise Exception( "Missing required device or virtual machine instance" )
        
        try:
            zabbix_host = get_host( instance.name )
        except:
            raise 
        return validate_zabbix_host( zabbix_host, instance )

    @classmethod
    def run_job(cls, instance, request, schedule_at=None, interval=None, immediate=False, name=None):
        """
        Enqueues a host validation job.
        
        Args:
            instance (Device|VirtualMachine): Target instance.
            request (HttpRequest): HTTP request triggering the job.
            schedule_at (datetime, optional): Schedule time.
            interval (int, optional): Interval for recurring job.
            immediate (bool, optional): Run job immediately.
            name (str, optional): Job name.
        
        Returns:
            Job: Enqueued job instance.
        """
        if not isinstance( instance, (Device, VirtualMachine) ):
            raise Exception( "Missing required device or virtual machine instance" )
                
        name = name or f"Validate host {instance.name}"

        job_args = {
            # General Job arguments.
            "name":          name,
            "schedule_at":   schedule_at,
            "interval":      interval,
            "immediate":     immediate,

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


    @classmethod
    def run_now(cls, instance=None, *args, **kwargs):
        """
        Executes the validation immediately.
        
        Args:
            instance (Device|VirtualMachine, optional): Target instance.
        
        Returns:
            dict: Validation result.
        """
        kwargs["eventlog"] = False # Disable logging to the event log
        if instance and "content_type" not in kwargs:
            kwargs["content_type"] = ContentType.objects.get_for_model( instance, for_concrete_model=False )
            kwargs["id"] = instance.id
        return super().run_now( *args, **kwargs )
