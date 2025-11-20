"""
NetBox Zabbix Plugin — Host Management Jobs

This module defines job classes for creating, updating, and deleting 
Zabbix hosts based on NetBox HostConfig objects. Each job class inherits 
from AtomicJobRunner and provides both synchronous execution (`run`) 
and enqueuing for asynchronous execution (`run_job`, `run_job_now`).

Responsibilities:
- CreateZabbixHost: Add a new Zabbix host from a HostConfig, persist the host ID, 
  and log changes in NetBox.
- UpdateZabbixHost: Update an existing Zabbix host to reflect the current HostConfig.
- DeleteZabbixHost: Remove a Zabbix host, supporting both soft and hard deletion.

These jobs handle payload preparation, host validation, and error handling, 
ensuring safe interaction between NetBox and Zabbix.
"""


# NetBox Zabbix Imports
from netbox_zabbix.jobs.atomicjobrunner import AtomicJobRunner
from netbox_zabbix.jobs.base import require_kwargs
from netbox_zabbix import settings, models
from netbox_zabbix.netbox.changelog import (
    log_creation_event
)
from netbox_zabbix.netbox.jobs import associate_instance_with_job
from netbox_zabbix.zabbix.hosts import (
    create_zabbix_host,
    update_zabbix_host,
    delete_zabbix_host_hard,
    delete_zabbix_host_soft,
    
)
from netbox_zabbix.netbox.host_config import (
    save_host_config
)
from netbox_zabbix.zabbix.api import (
    delete_host
)
from netbox_zabbix.exceptions import ExceptionWithData
from netbox_zabbix.logger import logger


class CreateZabbixHost( AtomicJobRunner ):
    """
    Job to create a new Zabbix host from a HostConfig.
    """

    @classmethod
    def run(cls, *args, **kwargs):
        """
        Creates the host in Zabbix and updates HostConfig with host ID.
        
        Returns:
            dict: Message confirming creation and Zabbix payload.
        
        Raises:
            ExceptionWithData: If creation fails and payload is available.
            Exception: For other failures.
        """
        host_config_id = require_kwargs( kwargs, "host_config_id" )
        user           = kwargs.get( "user" )
        request_id     = kwargs.get( "request_id" )

        host_config = models.HostConfig.objects.get( id=host_config_id )

        try:
            hostid, payload = create_zabbix_host( host_config )
            host_config.hostid = hostid

            save_host_config( host_config )
            log_creation_event( host_config, user, request_id )
            associate_instance_with_job( cls.job, host_config )

            return {"message": f"Host {host_config.assigned_object.name} added to Zabbix.", "data": payload}
        except Exception as e:
            if 'hostid' in locals():
                try:
                    delete_host( hostid )
                except:
                    pass # Don't fail the job if the host cannot be deleted
            if isinstance( e, ExceptionWithData ):
                raise  # don’t wrap twice
            raise ExceptionWithData( e, data=locals().get( "payload" ) )


    @classmethod
    def run_job(cls, host_config, request, schedule_at=None, interval=None, immediate=False, name=None, signal_id=None):
        """
        Enqueues a job to create a Zabbix host.
        
        Args:
            host_config (HostConfig): Host configuration to create.
            request (HttpRequest): Triggering request.
        
        Returns:
            Job: Enqueued job instance.
        """
        if not isinstance( host_config, models.HostConfig ):
            raise Exception( "Missing required host configuration instance" )
        
        name = name or f"Create Host in Zabbix for {host_config.devm_name}"
        
        job_args = {
            # General Job arguments.
            "name":           name,
            "schedule_at":    schedule_at,
            "interval":       interval,
            "immediate":      immediate,
            "instance":       host_config,

            # Specific Job arguments
            "signal_id":      signal_id,
            "host_config_id": host_config.id,
        }
    
        if request:
            job_args["user"]       = request.user
            job_args["request_id"] = request.id
    
        if interval is None:
            netbox_job = cls.enqueue( **job_args )
        else:
            netbox_job = cls.enqueue_once( **job_args )
    
        return netbox_job


class UpdateZabbixHost( AtomicJobRunner ):
    """
    Job to update an existing Zabbix host using HostConfig.
    """

    @classmethod
    def run(cls, *args, **kwargs):
        """
        Updates the host in Zabbix with the current HostConfig.
        
        Returns:
            dict: Updated host information.
        
        Raises:
            Exception: If update fails.
        """
        host_config_id    = require_kwargs( kwargs, "host_config_id" )
        user              = kwargs.get( "user" )
        request_id        = kwargs.get( "request_id" )
        
        host_config = models.HostConfig.objects.get( id=host_config_id )
        return update_zabbix_host( host_config, user, request_id )


    @classmethod
    def run_job(cls, host_config, request, user=None, schedule_at=None, interval=None, immediate=False, name=None, signal_id=None):
        """
        Enqueues an UpdateZabbixHost job.
        
        Returns:
            Job: Enqueued job instance.
        """
        if not isinstance( host_config, models.HostConfig ):
            raise ValueError( "host_config must be an instance of HostConfig" )

        name = name or f"Update Host in Zabbix for {host_config.name}"

        job_args = {
            # General Job arguments.
            "name":            name,
            "schedule_at":     schedule_at,
            "interval":        interval,
            "immediate":       immediate,
            "instance":        host_config,

            # Specific Job arguments
            "signal_id":       signal_id,
            "host_config_id":  host_config.id,
        }
        
        if request:
            job_args["user"]       = request.user
            job_args["request_id"] = request.id
        else:
            if user:
                job_args["user"] = user

        if interval is None:
            netbox_job = cls.enqueue( **job_args )
        else:
            netbox_job = cls.enqueue_once( **job_args )
        
        return netbox_job


    @classmethod
    def run_job_now(cls, host_config, request, name=None):
        """
        Immediately updates a Zabbix host.
        
        Args:
            host_config (HostConfig): Host to update.
            request (HttpRequest): Triggering request.
        
        Returns:
            dict: Result of immediate update.
        """
        if not isinstance( host_config, models.HostConfig ):
            raise ValueError( "host_config must be an instance of HostConfig" )
        
        if name is None:
            name = f"Update Host in Zabbix for {host_config.name}"
    
        return cls.run_now(
            host_config_id=host_config.id,
            user=request.user,
            request_id=request.id,
            name=name
        )


class DeleteZabbixHost( AtomicJobRunner ):
    """
    Job to delete a Zabbix host.
    
    Supports both hard and soft deletion.
    """

    @classmethod
    def run(cls, *args, **kwargs):
        """
        Executes the deletion of the Zabbix host.
        
        Returns:
            dict: Result of deletion.
        
        Raises:
            Exception: If deletion fails.
        """
        hostid = require_kwargs( kwargs, "hostid" )

        try:

            if settings.get_delete_setting() == models.DeleteSettingChoices.HARD:
                return delete_zabbix_host_hard( hostid )
            else:
                return delete_zabbix_host_soft( hostid )

        except Exception as e:
            msg = f"{ str( e ) }"
            logger.error( msg )
            raise Exception( msg )


    @classmethod
    def run_job(cls, hostid, user=None, schedule_at=None, interval=None, immediate=False, name=None, signal_id=None):
        """
        Enqueues a job to delete a Zabbix host.
        
        Returns:
            Job: Enqueued job instance.
        """
        name = name or f"Delete Zabbix host '{hostid}'"
        
        job_args = {
            "name":        name,
            "schedule_at": schedule_at,
            "interval":    interval,
            "immediate":   immediate,
            "signal_id":   signal_id,
            "user":        user,
            "hostid":      hostid,
        }
        
        if interval is None:
            netbox_job = cls.enqueue( **job_args )
        else:
            netbox_job = cls.enqueue_once( **job_args )
        
        return netbox_job

