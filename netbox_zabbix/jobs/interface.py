"""
NetBox Zabbix Plugin — Interface Management Jobs

Defines background RQ job classes for creating and updating Zabbix interfaces 
linked to NetBox HostConfig objects. These jobs ensure that host interfaces in 
Zabbix remain synchronized with their corresponding Device or VirtualMachine 
interfaces in NetBox.

Classes:
    - BaseZabbixInterfaceJob: Abstract base providing shared enqueue logic.
    - CreateZabbixInterface: Job for creating missing interfaces in Zabbix.
    - UpdateZabbixInterface: Job for synchronizing existing interfaces.

Each job handles asynchronous execution, validation, and automatic linking 
of missing interfaces between Zabbix and NetBox.
"""

# NetBox Zabbix Imports
from netbox_zabbix.jobs.atomicjobrunner import AtomicJobRunner
from netbox_zabbix.jobs.base import require_kwargs
from netbox_zabbix.zabbix.hosts import update_host_in_zabbix
from netbox_zabbix.zabbix.interfaces import link_missing_interface
from netbox_zabbix import models


class BaseZabbixInterfaceJob(AtomicJobRunner):
    """
    Base class for jobs that create or update Zabbix interfaces.
    
    Provides common utilities to load HostConfig and enqueue interface operations.
    """

    @classmethod
    def run_job(cls, host_config, request=None, schedule_at=None, interval=None, immediate=False, name=None, signal_id=None):
        """
        Enqueues a Zabbix interface job for the given HostConfig.
        
        Returns:
            Job: Enqueued job instance.
        """
        if not isinstance( host_config, models.HostConfig ):
            raise Exception( "host_config must be an instance of HostConfig" )

        name = name or f"{cls.__name__} for {host_config.assigned_object.name}"

        job_args = {
            # General Job arguments.
            "name":         name,
            "instance":     host_config,
            "schedule_at":  schedule_at,
            "interval":     interval,
            "immediate":    immediate,

            # Specific Job arguments
            "signal_id":    signal_id,
            "config_id":    host_config.id,
        }

        if request:
            job_args["user"]       = request.user
            job_args["request_id"] = getattr( request, "id", None )

        if interval is None:
            return cls.enqueue( **job_args )
        else:
            return cls.enqueue_once( **job_args )


class CreateZabbixInterface(BaseZabbixInterfaceJob):
    """
    Job to create a Zabbix interface for a HostConfig.
    
    Raises:
        Exception: If the HostConfig has no associated Zabbix host.
    """

    @classmethod
    def run(cls, *args, **kwargs):
        """
        Creates or updates the Zabbix host/interface and links missing interfaces.
        
        Returns:
            dict: Result of the interface creation/update.
        """
        config_id =require_kwargs( kwargs, "config_id" )
        host_config = models.HostConfig.objects.get( id=config_id )

        if not host_config.hostid:
            raise Exception(
                f"Cannot create interface for '{host_config.assigned_object.name}': "
                f"Host Config '{host_config.name}' has no associated Zabbix host id."
            )

        retval = update_host_in_zabbix( host_config, kwargs.get( "user" ), kwargs.get( "request_id" ) )
        link_missing_interface( host_config, host_config.hostid )
        return retval


class UpdateZabbixInterface(BaseZabbixInterfaceJob):
    """
    Job to update an existing Zabbix interface for a HostConfig.
    
    Raises:
        Exception: If the HostConfig has no associated Zabbix host.
    """

    @classmethod
    def run(cls, *args, **kwargs):
        """
        Updates the Zabbix host/interface and links missing interfaces.
        
        Returns:
            dict: Result of the interface update.
        """
        config_id   =require_kwargs( kwargs, "config_id" )
        host_config = models.HostConfig.objects.get( id=config_id )
        
        if not host_config.hostid:
            raise Exception(
                f"Cannot update interface for '{host_config.assigned_object.name}': "
                f"Host Config '{host_config.name}' has no associated Zabbix host id."
            )

        # Assoicate the interface with the interfaceid
        link_missing_interface( host_config, host_config.hostid )
        return update_host_in_zabbix( host_config, kwargs.get( "user" ), kwargs.get( "request_id" ) )

