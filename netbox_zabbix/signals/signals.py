# signals.py
#
# Description: Django signal handlers for NetBox Zabbix integration.
#
#

from __future__ import annotations

import logging
from typing import Optional

from django.db import transaction
from django.db.models.signals import pre_delete, post_delete, pre_save, post_save
from django.dispatch import receiver

from core.models import ObjectChange
from dcim.models import Device
from ipam.models import IPAddress
from netbox.context import current_request

from netbox_zabbix.jobs import (
    DeleteZabbixHost,
    CreateZabbixHost,
    UpdateZabbixHost,
    CreateOrUpdateZabbixInterface,
    ImportZabbixSystemJob,
)
from netbox_zabbix.models import (
    Config,
    DeviceAgentInterface,
    DeviceSNMPv3Interface,
    DeviceZabbixConfig,
    MainChoices,
)

logger = logging.getLogger("netbox.plugins.netbox_zabbix")


# ------------------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------------------


def get_request():
    return current_request.get()


def get_request_id():
    """
    Return the current request's id if available, otherwise None.
    """
    req = current_request.get()
    return getattr( req, "id", None ) if req else None


def latest_change_user_forget_request_id(pk: int):
    """
    Return the User associated with the most recent ObjectChange for the given pk.
    """
    change = ObjectChange.objects.filter( changed_object_id=pk ).order_by( "-time" ).first()
    return change.user if change and change.user else None


# ------------------------------------------------------------------------------
# System Signals
# ------------------------------------------------------------------------------

@receiver(pre_save, sender=Config)
def update_system_job_schedule(sender, instance: Config, **kwargs):
    """
    Reschedule the background sync job when the configured Zabbix sync interval changes.
    """
    # Only act on updates (not initial creation)
    if not instance.pk:
        return

    prev = sender.objects.get(pk=instance.pk)
    if prev.zabbix_sync_interval != instance.zabbix_sync_interval:
        logger.info( "Rescheduling Zabbix import system job (interval changed)." )
        transaction.on_commit(
            lambda: ImportZabbixSystemJob.schedule(instance.zabbix_sync_interval)
        )


# ------------------------------------------------------------------------------
# Device Interface Signals
# ------------------------------------------------------------------------------

@receiver(post_delete, sender=DeviceAgentInterface)
def dev_promote_agent_interface_to_main(sender, instance: DeviceAgentInterface, **kwargs):
    """
    Ensure a device always has a designated main Agent interface.

    If the deleted interface was the main one, promote the first remaining
    agent interface on the same host.
    """
    if instance.main == MainChoices.YES:
        logger.info( f"Promoting fallback Agent interface to main (device={instance.host.get_name()})." )
        remaining = instance.host.agent_interfaces.exclude( pk=instance.pk )
        fallback = remaining.first()
        if fallback:
            fallback.main = MainChoices.YES
            fallback.save()
            logger.info(
                "Promoted interface %s to main for %s",
                fallback.name,
                fallback.host.get_name(),
            )


@receiver(post_delete, sender=DeviceSNMPv3Interface)
def dev_promote_snmpv3_interface_to_main(sender, instance: DeviceSNMPv3Interface, **kwargs):
    """
    Ensure a device always has a designated main SNMPv3 interface.

    If the deleted interface was the main one, promote the first remaining
    SNMPv3 interface on the same host.
    """
    if instance.main == MainChoices.YES:
        logger.info( f"Promoting fallback SNMPv3 interface to main (device={instance.host.get_name()})." )
        remaining = instance.host.snmpv3_interfaces.exclude( pk=instance.pk )
        fallback = remaining.first()
        if fallback:
            fallback.main = MainChoices.YES
            fallback.save()
            logger.info(
                "Promoted interface %s to main for %s",
                fallback.name,
                fallback.host.get_name(),
            )


# ------------------------------------------------------------------------------
# Device ZabbixConfig Signals
# ------------------------------------------------------------------------------

@receiver(post_save, sender=DeviceZabbixConfig)
def dev_save_zabbix_config(sender, instance: DeviceZabbixConfig, created: bool, **kwargs):

    user = latest_change_user_forget_request_id( instance.pk )
    if not user:
        logger.info( f"Required user missing, unable to create/update Zabbix Connfigruartion" )
        return
    
    if created:
        logger.info( "***********************************************************" )
        logger.info( f"Created Host in Zabbix for {instance.device.name}" )
        logger.info( "***********************************************************" )

        CreateZabbixHost.run_job(
            host_name=instance.device.name,
            zabbix_config=instance,
            request=get_request(),
            name=f"Create Host in Zabbix for {instance.device.name}"
        )
        
    else:
        logger.info( "***********************************************************" )
        logger.info( f"Updated Host in Zabbix for {instance.device.name}" )
        logger.info( "***********************************************************" )

        UpdateZabbixHost.run_job(
            host_name=instance.device.name,
            zabbix_config=instance,
            request=get_request(),
            name=f"Update Host in Zabbix for {instance.device.name}"
        )
    


@receiver(pre_delete, sender=DeviceZabbixConfig)
def dev_delete_zabbix_config(sender, instance: DeviceZabbixConfig, **kwargs):
    """
    Before deleting a Device Zabbix configuration, delete the corresponding host in Zabbix.
    """
    logger.info( "***********************************************************" )
    logger.info( f"Deleting Zabbix host prior to removing DeviceZabbixConfig (device={instance.device.name})." )
    logger.info( "***********************************************************" )
    
    try:
        if instance and instance.hostid:
            DeleteZabbixHost.run_job( hostid=instance.hostid )
        else:
            logger.info( f"Unable to delete {instance.device.name} in Zabbix, missing required hostid" )

    except Exception:
        # Surface the failure to keep NetBox and Zabbix consistent.
        raise


# ------------------------------------------------------------------------------
# Zabbix Interface (Agent/SNMPv3) Signals
# ------------------------------------------------------------------------------

@receiver(post_save, sender=DeviceAgentInterface)
@receiver(post_save, sender=DeviceSNMPv3Interface)
def dev_save_zabbix_interface(sender, instance, created: bool, **kwargs):
    
    user = latest_change_user_forget_request_id( instance.pk )
    if not user:
        logger.info( f"Required user missing, unable to create/update Device Zabbix Interface" )
        return
    

    if created:
        logger.info( "***********************************************************" )
        logger.info( f"Created Interface for {instance.host.device.name}" )
        logger.info( "***********************************************************" )

        CreateOrUpdateZabbixInterface.run_job(
            host_name=instance.host.device.name,
            zabbix_config=instance.host,
            request=get_request(),
            name=f"Add interface for {instance.host.device.name}"
        )
        
    else:
        logger.info( "***********************************************************" )
        logger.info( f"Updated Interface for {instance.host.device.name}" )
        logger.info( "***********************************************************" )

        CreateOrUpdateZabbixInterface.run_job(
            host_name=instance.host.device.name,
            zabbix_config=instance.host,
            request=get_request(),
            name=f"Update interface for {instance.host.device.name}"
        )

# ------------------------------------------------------------------------------
# IP Address Signals
# ------------------------------------------------------------------------------

@receiver(post_save, sender=IPAddress)
def dev_update_ipaddress(sender, instance: IPAddress, created: bool, **kwargs):
    """
    When an IPAddress changes, schedule a Zabbix host update for the
    owning device (if any) with a DeviceZabbixConfig.
    """
    # Don't act on initial creation
    if created:
        return

    logger.info( f"IPAddress updated; evaluating Zabbix host update (ip={instance.address})." )

    user = latest_change_user_forget_request_id( instance.pk )
    if not user:
        return

    # If no assigned object (e.g., IP not bound to an interface/device), skip
    assigned = getattr( instance, "assigned_object", None )
    if not assigned:
        return

    # Resolve the parent device from the assigned object (interface, etc.)
    device = getattr( assigned, "device", None )
    if not isinstance( device, Device ):
        # Not a Device-backed assignment (e.g., VM interface) or not resolvable
        return

    try:
        device_zcfg = DeviceZabbixConfig.objects.get( device=device )
    except DeviceZabbixConfig.DoesNotExist:
        return
    except DeviceZabbixConfig.MultipleObjectsReturned:
        # Unexpected duplicates; skip to avoid ambiguity
        return

    UpdateZabbixHost.run_job(
         host_name=instance.device.name,
         zabbix_config=instance,
         request=get_request(),
         name=f"Update IP address in Zabbix for {instance.device.name}"
     )

# ------------------------------------------------------------------------------
# Virtual Machine Signals
# ------------------------------------------------------------------------------
# (Add VM-specific signal handlers here as needed.)
