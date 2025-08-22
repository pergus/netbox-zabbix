# singals.py
#
# Description: Handle signals
#

from django.db.models.signals import post_delete, pre_delete, pre_save, post_save
from django.dispatch import receiver

from netbox_zabbix.models import  (
    DeviceAgentInterface, 
    DeviceSNMPv3Interface, 
    DeviceZabbixConfig, 
    MainChoices
)

from netbox_zabbix.models import Config
from netbox_zabbix.jobs import ImportZabbixSystemJob
from django.db import transaction

from core.models import ObjectChange

from netbox_zabbix.jobs import (
    DeleteZabbixHost,
    DeviceUpdateZabbixHost
)

import logging

logger = logging.getLogger('netbox.plugins.netbox_zabbix')


# ------------------------------------------------------------------------------
# System Jobs
# ------------------------------------------------------------------------------

@receiver(pre_save, sender=Config)
def update_system_job_schedule(sender, instance, **kwargs):
    """
    Reschedule background job.
    Only reschedule if the sync interval has changed.
    """
    if not instance.pk:
        return
    
    prev_config = sender.objects.get( pk=instance.pk )
    if prev_config.zabbix_sync_interval != instance.zabbix_sync_interval:
        transaction.on_commit(lambda: ImportZabbixSystemJob.schedule(instance.zabbix_sync_interval))


# ------------------------------------------------------------------------------
# Device Singals
# ------------------------------------------------------------------------------


#
# Promote Device Agent Interface
#
@receiver(post_delete, sender=DeviceAgentInterface)
def dev_promote_agent_interface_to_main(sender, instance, **kwargs):
    """
    Ensure a device always has a designated main agent interface.
    
    This signal handler is triggered after a `DeviceAgentInterface` instance 
    is deleted. If the deleted interface was marked as the main interface, 
    another available agent interface on the same host will be promoted to 
    become the new main interface.
    
    Behavior:
        - If the deleted interface was NOT the main interface, nothing happens.
        - If it was the main interface:
            - The first remaining agent interface for the host is selected.
            - That interface is promoted to `MainChoices.YES`.
            - A log entry is created documenting the promotion.
    """
    if instance.main == MainChoices.YES:
        remaining = instance.host.agent_interfaces.exclude( pk=instance.pk )
        fallback = remaining.first()
        if fallback:
            fallback.main = MainChoices.YES
            fallback.save()
            logger.info( f"Promoted interface {fallback.name} to main interface for {fallback.host.get_name()}" )

#
# Promote Device SNMPv3 Interface
#
@receiver(post_delete, sender=DeviceSNMPv3Interface)
def dev_promote_snmpv3_interface_to_main(sender, instance, **kwargs):
    """
    Ensure a device always has a designated main snmpv3 interface.
    
    This signal handler is triggered after a `DeviceSNMPv3Interface` instance 
    is deleted. If the deleted interface was marked as the main interface, 
    another available snmpv3 interface on the same host will be promoted to 
    become the new main interface.
    
    Behavior:
        - If the deleted interface was NOT the main interface, nothing happens.
        - If it was the main interface:
            - The first remaining snmpv3 interface for the host is selected.
            - That interface is promoted to `MainChoices.YES`.
            - A log entry is created documenting the promotion.
    
    """
    
    if instance.main == MainChoices.YES:
        remaining = instance.host.snmpv3_interfaces.exclude( pk=instance.pk )
        fallback = remaining.first()
        if fallback:
            fallback.main = MainChoices.YES
            fallback.save()
            logger.info( f"Promoted interface {fallback.name} to main interface for {fallback.host.get_name()}" )

#
# Save Zabbix configuration
#
@receiver(post_save, sender=DeviceZabbixConfig)
def dev_save_zabbix_config(sender, instance, created, **kwargs):
    """
    Update the corresponding host in Zabbix for a device when the Zabbix 
    configuration in NetBox has changed.
    """

    # Don't update upon creation
    if created:
        return
    
    change = ObjectChange.objects.filter( changed_object_id=instance.pk ).order_by( '-time' ).first()
    if change and change.user:
        DeviceUpdateZabbixHost.run_job( device_name=instance.device.name, device_zabbix_config=instance, user=change.user )

#
# Delete Zabbix configuration
#
@receiver(pre_delete, sender=DeviceZabbixConfig)
def dev_delete_zabbix_config(sender, instance, **kwargs):
    """
    Delete the corresponding Zabbix host before removing a device configuration.
    
    This signal handler is triggered before a `DeviceZabbixConfig` instance 
    is deleted. It ensures that the associated host in Zabbix is also 
    deleted to maintain consistency between NetBox and Zabbix.
    
    Behavior:
        - Logs the deletion attempt, including the device name.
        - Calls the background job `DeleteZabbixHost.run_job()` with the 
          host ID from the configuration.
        - If the deletion in Zabbix fails, the exception is raised to 
          prevent inconsistent state.

    Note: The run_job is responsible for logging the current Zabbix host 
          configuration before deleteing the host in Zabbix.
    """
    try:
        logger.info( f"delete zabbix host {instance.device.name}" )
        DeleteZabbixHost.run_job( hostid=instance.hostid )
    except Exception as e:
        raise e

#
# Interface
#
@receiver(post_save, sender=DeviceAgentInterface)
@receiver(post_save, sender=DeviceSNMPv3Interface)
def dev_save_zabbix_interface(sender, instance, created, **kwargs):
    """
    """
    # Don't update upon creation
    if created:
        return

    logger.info( f"Update Interface for {instance.host.device.name}" )    
    change = ObjectChange.objects.filter( changed_object_id=instance.pk ).order_by( '-time' ).first()
    if change and change.user:
        DeviceUpdateZabbixHost.run_job( device_name=instance.host.device.name, device_zabbix_config=instance.host, user=change.user )



# ------------------------------------------------------------------------------
# Virtual Machine Singals
# ------------------------------------------------------------------------------
