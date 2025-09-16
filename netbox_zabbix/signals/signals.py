# signals.py
#
# Description: Django signal handlers for NetBox Zabbix integration.
#
#

from __future__ import annotations


from django.db import transaction
from django.db.models.signals import pre_delete, post_delete, pre_save, post_save
from django.dispatch import receiver
from django.contrib import messages


from core.models import ObjectChange
from dcim.models import Device, Interface
from virtualization.models  import VirtualMachine, VMInterface

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

import logging

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


#def is_primary_ip(ip):
#
#    if not ip.assigned_object:
#        return False
#    
#    devm = getattr( ip.assigned_object, "device", getattr( ip.assigned_object, "virtual_machine", None ) )
#    if devm is None:
#        return False
#
#    return devm.primary_ip4_id == ip.id


#def associate_primary_ip(ip: IPAddress):
#    """
#    Associate the given primary IP with its Zabbix interface.
#    """
#    devm = ip.assigned_object
#    if isinstance(devm, Interface):
#        interface = Interface.objects.filter(id=devm.id).first()
#    elif isinstance(devm, VMInterface):
#        interface = VMInterface.objects.filter(id=devm.id).first()
#    else:
#        return
#
#    if not interface:
#        return
#
#    if hasattr( interface, "agent_interface" ):
#        zabbix_iface = interface.agent_interface
#    elif hasattr( interface, "snmpv3_interface" ):
#        zabbix_iface = interface.snmpv3_interface
#    else:
#        return
#
#    zabbix_iface.ip_address = ip
#    zabbix_iface.save()


#def primary_ip_changed(model, instance) -> bool: 
#    """ Check the database to see if primary_ip4 changed since last save. """ 
#    if not instance.pk: return False 
#    
#    old_primary_ip4_id = ( model.objects.filter( pk=instance.pk ).values_list("primary_ip4_id", flat=True).first() )
#
#    logger.info( f"old_primary {old_primary_ip4_id} instance.primary_ip4_id {instance.primary_ip4_id}" ) 
#    
#    return old_primary_ip4_id != instance.primary_ip4_id




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
        logger.info( f"Required user missing, unable to create/update Zabbix Connfiguration" )
        return
    
    if created:
        logger.info( "***********************************************************" )
        logger.info( f"Created Host in Zabbix for {instance.device.name}" )
        logger.info( "***********************************************************" )

        CreateZabbixHost.run_job(
            zabbix_config=instance,
            request=get_request(),
            name=f"Create Host in Zabbix for {instance.device.name}"
        )
        
    else:
        logger.info( "***********************************************************" )
        logger.info( f"Updated Host in Zabbix for {instance.device.name}" )
        logger.info( "***********************************************************" )

        UpdateZabbixHost.run_job(
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
            zabbix_config=instance.host,
            request=get_request(),
            name=f"Add interface for {instance.host.device.name}"
        )
        
    else:
        logger.info( "***********************************************************" )
        logger.info( f"Updated Interface for {instance.host.device.name}" )
        logger.info( "***********************************************************" )

        CreateOrUpdateZabbixInterface.run_job(
            zabbix_config=instance.host,
            request=get_request(),
            name=f"Update interface for {instance.host.device.name}"
        )


# ------------------------------------------------------------------------------
# Device Interface Signals
# ------------------------------------------------------------------------------


@receiver(post_save, sender=Interface)
def dev_interface(sender, instance, created:bool, **kwargs):

    if created:
        logger.info( "***********************************************************" )
        logger.info( f"Created a new interface for device {instance.device.name}" )
        logger.info( "***********************************************************" )
        return
    
    logger.info( "***********************************************************" )
    logger.info( f"Interface updated for device {instance.device.name}" )
    logger.info( "***********************************************************" )
    return


# ------------------------------------------------------------------------------
# IP Address Signals
# ------------------------------------------------------------------------------


#@receiver(pre_delete, sender=IPAddress)
#def dev_delete_ipaddress(sender, instance: IPAddress,  **kwargs):
#
#    
#    logger.info( "***********************************************************" )
#    logger.info( f"Delete IPAddress ({instance.address})" )
#    logger.info( "***********************************************************" )
#
#    user = latest_change_user_forget_request_id( instance.pk )
#    if not user:
#        return
#    
#    # If no assigned object (e.g., IP not bound to an interface/device), skip
#    assigned = getattr( instance, "assigned_object", None )
#    if not assigned:
#        return
#    
#    # Resolve the parent device from the assigned object (interface, etc.)
#    device = getattr( assigned, "device", None )
#    if not isinstance( device, Device ):
#        # Not a Device-backed assignment (e.g., VM interface) or not resolvable
#        return
#    
#    try:
#        device_zcfg = DeviceZabbixConfig.objects.get( device=device )
#    except DeviceZabbixConfig.DoesNotExist:
#        return
#    
#    from django.contrib import messages
#    messages.error( get_request(), f"{device_zcfg.get_name()} is inconsistent with host configuration in Zabbix." )
#    
#    return
#
#
#def associate_ip_with_zabbix_interface(ip: IPAddress) -> bool:
#    """
#    Attempt to associate the given IPAddress with its Zabbix interface.
#
#    Requirements:
#      • IP must be the primary IP of its parent Device/VM
#      • IP must have a DNS name
#      • Interface must have a Zabbix agent or SNMPv3 interface
#
#    Returns:
#        True if the association was successfully made, False otherwise.
#    """
#    if not is_primary_ip(ip):
#        logger.info( "IP %s is not a primary IP", ip.address )
#        return False
#
#    if not ip.dns_name:
#        logger.info( "IP %s has no DNS name", ip.address )
#        return False
#
#    devm = ip.assigned_object
#    if isinstance( devm, Interface ):
#        interface = Interface.objects.filter( id=devm.id ).first()
#    elif isinstance( devm, VMInterface ):
#        interface = VMInterface.objects.filter( id=devm.id ).first()
#    else:
#        logger.info( "IP %s not bound to a valid interface", ip.address )
#        return False
#
#    if not interface:
#        return False
#
#    # Find Zabbix interface
#    zabbix_iface = getattr( interface, "agent_interface", None ) or \
#                   getattr( interface, "snmpv3_interface", None )
#
#    if not zabbix_iface:
#        logger.info( "No Zabbix interface found for interface %s", interface.id )
#        return False
#
#    # Perform the association
#    zabbix_iface.ip_address = ip
#    zabbix_iface.save()
#    logger.info( "Associated IP %s with Zabbix interface %s", ip.address, zabbix_iface.id )
#
#    return True


#@receiver(post_save, sender=IPAddress)
#def dev_update_ipaddress(sender, instance: IPAddress, created: bool, **kwargs):
#    """
#    When an IPAddress changes, schedule a Zabbix host update for the
#    owning device (if any) with a DeviceZabbixConfig.
#    """
#
#    ip = instance
#    devm = ip.assigned_object
#
#    action = "Created" if created else "Updated"
#
#    logger.info("*" * 60)
#    logger.info(f"{action} IP Address ({ip.address})")
#    logger.info("*" * 60)
#    
#
#    if created:
#        if not associate_ip_with_zabbix_interface( ip ):
#            return
#
#    # Update the host in Zabbix
#    update_zabbix_host_for_instance( ip , f"{action} IP Address {ip.address}" ) 


# ------------------------------------------------------------------------------
# Device Signals
# ------------------------------------------------------------------------------

#@receiver(pre_save, sender=Device)
#def device_primary_ip_changed(sender, instance: Device,  **kwargs):
#
#
#    # HERE BE DRAGONS!  
#    if primary_ip_changed( Device, instance ):
#        logger.info("*" * 60)
#        logger.info(f"Primary IP changed for {instance.name} to {instance.primary_ip4}")
#        logger.info("*" * 60)
#        associate_primary_ip( instance.primary_ip4 )
#
#    if instance.primary_ip4 and instance.primary_ip4.dns_name:
#        update_zabbix_host_for_instance( instance, f"Primary IP Address updated" ) 


# ------------------------------------------------------------------------------
# Virtual Machine Signals
# ------------------------------------------------------------------------------
# (Add VM-specific signal handlers here as needed.)


# ------------------------------------------------------------------------------
# Test
# ------------------------------------------------------------------------------


def update_zabbix_host_for_instance(instance, message) -> None:
    """
    Resolve a Device from the given instance and trigger an UpdateZabbixHost job.
    Works for IPAddress, Device, Interface, etc.
    """
    # Determine which PK to use for latest-change user lookup
    pk_for_user = getattr( instance, "pk", None )
    if not pk_for_user:
        logger.info( f"update_zabbix_host_for_instance: No primary key found for instance {instance}. Skipping update." )
        return

    user = latest_change_user_forget_request_id( pk_for_user )
    if not user:
        logger.info( f"update_zabbix_host_for_instance: No user found for latest change on PK {pk_for_user}. Skipping update." )
        return

    # Try to resolve a Device regardless of model type
    if isinstance( instance, Device ):
        device = instance
    else:
        device = getattr( instance, "device", None )

    if not isinstance( device, Device ):
        logger.info( f"update_zabbix_host_for_instance: Could not resolve a Device from instance {instance}. Skipping update." )
        return

    try:
        device_zcfg = DeviceZabbixConfig.objects.get( device=device )
    except (DeviceZabbixConfig.DoesNotExist, DeviceZabbixConfig.MultipleObjectsReturned):

        logger.info( f"update_zabbix_host_for_instance: No DeviceZabbixConfig found for device {device.name}. Skipping update." )
        return

    UpdateZabbixHost.run_job(
        zabbix_config=device_zcfg,
        request=get_request(),
        name= f"{message}" if message else f"Update {device_zcfg.device.name} in Zabbix: {message}"
    )


def should_reassign_zabbix_ip(interface: Interface | VMInterface) -> bool:
    """
    Returns True if the interface's Zabbix config interface either:
      a) has no IP assigned, or
      b) is assigned an IP that is not the current primary IPv4 of the parent device/VM
         or has no dns_name
    """

    # Determine parent device/VM
    devm = getattr(interface, "device", None) or getattr(interface, "virtual_machine", None)
    if not devm:
        logger.info(f"should_reassign_zabbix_ip: No parent device/VM for interface {interface.id}")
        return False

    # Ensure the interface has a Zabbix config interface
    zabbix_iface = getattr(interface, "agent_interface", None) or \
                   getattr(interface, "snmpv3_interface", None)
    if not zabbix_iface:
        logger.info(f"should_reassign_zabbix_ip: Interface {interface.id} has no Zabbix config interface")
        return False

    # Check candidate primary IP
    primary_ip = devm.primary_ip4
    if not primary_ip:
        logger.info(f"should_reassign_zabbix_ip: Device/VM {devm} has no primary IPv4")
        return False

    # Already correctly assigned?
    if zabbix_iface.ip_address_id == primary_ip.id and primary_ip.dns_name:
        logger.info(f"should_reassign_zabbix_ip: Zabbix interface {zabbix_iface.id} already assigned to correct primary IP {primary_ip.address}")
        return False

    # Otherwise, reassignment is needed
    logger.info( f"should_reassign_zabbix_ip return True" )
    return True


def reassign_zabbix_ip_for_interface(interface: Interface | VMInterface) -> bool:
    """
    If the interface's Zabbix config interface lost its IP, attempt to
    associate a new one that meets the required conditions:
      a) New IP is the primary IPv4 of the parent device/VM
      b) IP has a dns_name
      c) IP belongs to the same interface

    Returns True if an IP was successfully re-associated.
    """
    logger.info( "reassign_zabbix_ip_for_interface..." )

    # Determine parent device/VM
    devm = getattr( interface, "device", None ) or getattr( interface, "virtual_machine", None )
    if not devm:
        return False

    # Ensure the interface has a Zabbix config interface
    zabbix_iface = getattr( interface, "agent_interface", None ) or \
                   getattr( interface, "snmpv3_interface", None )
    if not zabbix_iface:
        return False

    # Candidate IP must be:
    # 1) primary IPv4 of the device/VM
    # 2) bound to THIS interface
    # 3) have a DNS name
    primary_ip = devm.primary_ip4
    if not primary_ip:
        return False

    if primary_ip.assigned_object_id != interface.id:
        logger.info( f"Primary IP {primary_ip} is not on interface {interface.id}" )
        return False

    if not primary_ip.dns_name:
        logger.info( f"Primary IP {primary_ip} has no dns_name" )
        return False

    # Associate with Zabbix interface
    zabbix_iface.ip_address = primary_ip
    zabbix_iface.save()

    logger.info( f"Re-associated Zabbix interface {zabbix_iface.id} with IP {primary_ip.address}" )
    return True



#
# Delete IP Address
#
@receiver(pre_delete, sender=IPAddress)
def dev_delete_ipaddress(sender, instance: IPAddress,  **kwargs):

    
    logger.info( "***********************************************************" )
    logger.info( f"Delete IPAddress ({instance.address})" )
    logger.info( "***********************************************************" )

    ip = instance

    # Get the assigned interface
    interface = getattr( ip, "assigned_object", None )
    if not interface:
        return
    
    # Get the device assigned to the interface
    device = getattr( interface, "device", None )
    if not isinstance( device, Device ):
        return
    
    # Get the Zabbix Configuration for the device
    try:
        device_zcfg = DeviceZabbixConfig.objects.get( device=device )
        
        messages.error( get_request(), f"Zabbix configuration for device '{device_zcfg.device.name}' may be out of sync." )
        
    except DeviceZabbixConfig.DoesNotExist:
        pass

    return


#
# Save IP Address
#
@receiver(post_save, sender=IPAddress)
def zabbix_ip_post_save(sender, instance, created, **kwargs):

    ip = instance
    iface = ip.assigned_object

    action = "Created" if created else "Updated"
    logger.info( "*" * 60 )
    logger.info( f"{action} IP Address ({ip.address})" )
    logger.info( "*" * 60 )

    if ip.assigned_object:
        parent = getattr( ip.assigned_object, 'parent_object', None )
        logger.info( f"ip {ip}" )
        logger.info( f"parent {parent}" )
        logger.info( f"ip.family {ip.family}" )
        logger.info( f"hasattr( parent, 'primary_ip4' ) {hasattr( parent, 'primary_ip4' )}" )
        logger.info( f"primary_ip4 {parent.primary_ip4}" )
        logger.info( f"parent.primary_ip4_id ({parent.primary_ip4_id})  == ip.pk ({ip.pk}) => {parent.primary_ip4_id == ip.pk} " )

        if ip.family == 4 and hasattr( parent, 'primary_ip4' ) and parent.primary_ip4_id == ip.pk:
            logger.info( f"IP IS PRIMARY" )
        else:
            logger.info( f"IP IS NOT A PRIMARY" )
    else:
        logger.info( f"IP IS NOT ASSIGNED TO AN OBJECT" )

    if isinstance(iface, (Interface, VMInterface)):
        devm = getattr( iface, "device", None ) or getattr( iface, "virtual_machine", None )
        if devm and should_reassign_zabbix_ip( iface ):
            reassign_zabbix_ip_for_interface( iface)
    else:
        logger.info( f"Object is not an instance of Interface or VMInterface. Skipping Zabbix update." )
        return
    
    logger.info( f"update_zabbix_host_for_instance()" )
    update_zabbix_host_for_instance( iface, f"{action} IP Address {ip.address}")


def primary_ip4_changed(device: Device) -> bool:
    if not device.pk:
        return False
    old_primary = ( Device.objects.filter( pk=device.pk ).values_list( "primary_ip4_id", flat=True ).first() )
    return old_primary != device.primary_ip4_id


#
# Pre Save Device - Primary IP
#
@receiver(pre_save, sender=Device)
def zabbix_primary_ip_changed(sender, instance, **kwargs):

    logger.info("*" * 60)
    logger.info(f"Pre Save Device")
    logger.info("*" * 60)

    if not primary_ip4_changed(instance):
        logger.info(f"No Primary IPv4 change detected for device '{instance}'. Skipping Zabbix update.")
        return

    if not instance.primary_ip4:
        logger.info(f"Primary IP cleared for device '{instance}'. Skipping Zabbix update.")
        return

    iface = instance.primary_ip4.assigned_object
    if isinstance(iface, (Interface, VMInterface)):

        logger.info("*" * 60)
        logger.info(f"Updated Primary IP Address ({instance.primary_ip4.address})")
        logger.info("*" * 60)
        if should_reassign_zabbix_ip(iface):
            reassign_zabbix_ip_for_interface(iface)

        update_zabbix_host_for_instance(
            instance.primary_ip4,
            f"Update Zabbix host for device '{instance.name}' primary IP {instance.primary_ip4.address} changed"
        )

#    if instance.primary_ip4 and instance.primary_ip4.dns_name:
#        iface = instance.primary_ip4.assigned_object
#        if isinstance( iface, (Interface, VMInterface) ):
#
#            logger.info("*" * 60)
#            logger.info(f"Updated Primary IP Address ({instance.primary_ip4.address})")
#            logger.info("*" * 60)
#            if should_reassign_zabbix_ip( iface):
#                reassign_zabbix_ip_for_interface( iface )
#            update_zabbix_host_for_instance( instance.primary_ip4 , f"Update Zabbix host for device '{instance.name}' primary IP {instance.primary_ip4.address} changed" )
#    else:
#        logger.info( f"No Primary IPv4 or dns_name for device '{instance.name}'. Skipping Zabbix update.")