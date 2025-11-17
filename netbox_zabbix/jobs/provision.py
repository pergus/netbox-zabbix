"""
NetBox Zabbix Plugin — Host Provisioning Jobs

Defines RQ job classes responsible for provisioning Zabbix hosts via Agent or 
SNMP interfaces. These jobs handle the creation of HostConfig objects, 
association of Zabbix interfaces, and registration of new hosts in Zabbix.

Classes:
    - ProvisionAgent: Provisions a Zabbix host using an Agent interface.
    - ProvisionSNMP:  Provisions a Zabbix host using an SNMP interface.

Both jobs use the ProvisionContext to encapsulate provisioning logic and support 
asynchronous execution, scheduling, and immediate runs.
"""


# Django imports
from django.contrib.contenttypes.models import ContentType

# NetBox imports
from dcim.models import Device
from virtualization.models import VirtualMachine


# NetBox Zabbix Imports
from netbox_zabbix.jobs.atomicjobrunner import AtomicJobRunner
from netbox_zabbix.jobs.base import require_kwargs
from netbox_zabbix.helpers import get_instance

from netbox_zabbix import settings, models
from netbox_zabbix.provisioning import ProvisionContext, provision_zabbix_host


class ProvisionAgent(AtomicJobRunner):
    """
    Job to provision an Agent interface in Zabbix for a device or VM
    This job creates a Host Configuration using the Agent interface model and 
    registers it in Zabbix.
    """
    @classmethod
    def run(cls, *args, **kwargs):
        """
        Provisions an Agent interface in Zabbix for the given instance.
        
        Returns:
            dict: Result of provisioning.
        
        Raises:
            Exception: If instance is invalid or provisioning fails.
        """
        # Require content_type and object id
        content_type = require_kwargs( kwargs, "content_type" )
        obj_id = require_kwargs( kwargs, "id" )
        
        # Retrieve the actual instance
        instance = get_instance( content_type.id, obj_id )
        
        if not isinstance( instance, (Device, VirtualMachine) ):
            raise Exception( "Missing required device or virtual machine instance" )

        job_args = {
            "object":                instance,
            "interface_model":       models.AgentInterface,
            "interface_name_suffix": "agent",
            "job":                   cls.job,
            "user":                  cls.job.user,
            "request_id":            kwargs.get( "request_id" ),
            "interface_kwargs_fn":   lambda: {},
        }

        return provision_zabbix_host( ProvisionContext( **job_args ) )

    @classmethod
    def run_job(cls, instance, request, schedule_at=None, interval=None, immediate=False, name=None):
        """
        Enqueues a ProvisionAgent job.
        
        Returns:
            Job: Enqueued job instance.
        """
        if not isinstance( instance, (Device, VirtualMachine) ):
            raise Exception( "Missing required device or virtual machine instance" )
        
        name = name or f"Provision Agent configuration for {instance.name}"

        job_args = {
            # General Job arguments.
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

    @classmethod
    def run_now(cls, instance=None, *args, **kwargs):
        """
        Immediately provisions an Agent interface.
        
        Args:
            instance (Device|VirtualMachine, optional): Target instance.
        """
        if instance and "content_type" not in kwargs:
            kwargs["content_type"] = ContentType.objects.get_for_model( instance, for_concrete_model=False )
            kwargs["id"] = instance.id
        return super().run_now( *args, **kwargs )


class ProvisionSNMP( AtomicJobRunner ):
    """
    Job to provision an SNMP interface in Zabbix for a device or VM.    
    This job creates a Host configuration using the SNMP interface model and 
    registers it in Zabbix.
    """
    @classmethod
    def run(cls, *args, **kwargs):
        """
        Provisions an SNMP interface in Zabbix for the given instance.
        
        Returns:
            dict: Result of provisioning.
        
        Raises:
            Exception: If instance is invalid or provisioning fails.
        """
        # Require content_type and object id
        content_type = require_kwargs( kwargs, "content_type" )
        obj_id = require_kwargs( kwargs, "id" )
        
        # Retrieve the actual instance
        instance = get_instance( content_type.id, obj_id )
        
        if not isinstance( instance, (Device, VirtualMachine) ):
            raise Exception( "Missing required device or virtual machine instance" )
        
        
        snmp_defaults = {
            "securityname":   settings.get_snmp_securityname(),
            "authprotocol":   settings.get_snmp_authprotocol(),
            "authpassphrase": settings.get_snmp_authpassphrase(),
            "privprotocol":   settings.get_snmp_privprotocol(),
            "privpassphrase": settings.get_snmp_privpassphrase()
        }
        
        job_args = {
            "object":                 instance,
            "interface_model":        models.SNMPInterface,
            "interface_name_suffix":  "snmp",
            "job":                    cls.job,
            "user":                   cls.job.user,
            "request_id":             kwargs.get( "request_id" ),
            "interface_kwargs_fn":    lambda: snmp_defaults,
        }
        
        try:
            return provision_zabbix_host( ProvisionContext( **job_args ) )
        except Exception as e:
            raise e


    @classmethod
    def run_job(cls, instance, request, schedule_at=None, interval=None, immediate=False, name=None):
        """
        Enqueues a ProvisionSNMP job.
        
        Returns:
            Job: Enqueued job instance.
        """
        if not isinstance( instance, (Device, VirtualMachine) ):
            raise Exception( "Missing required device or virtual machine instance" )
        
        name = name or f"Provision SNMP configuration for {instance.name}"

        job_args = {
            # General Job arguments.
            "name":         name,
            "schedule_at":  schedule_at,
            "interval":     interval,
            "immediate":    immediate,
            "object":       instance,

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
        Immediately provisions an SNMP interface.
        
        Args:
            instance (Device|VirtualMachine, optional): Target instance.
        """
        if instance and "content_type" not in kwargs:
            kwargs["content_type"] = ContentType.objects.get_for_model( instance, for_concrete_model=False )
            kwargs["id"] = instance.id
        return super().run_now( *args, **kwargs )

