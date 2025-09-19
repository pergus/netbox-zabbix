# signals.py
#
# Description: Django signal handlers for NetBox Zabbix integration.
# These helpers and signal receivers keep Zabbix host/interface
# configuration synchronized with NetBox objects.
#

from email import message
from django.db import transaction
from django.db.models.signals import pre_delete, post_delete, pre_save, post_save
from django.dispatch import receiver
from django.contrib import messages
from django.core.exceptions import ValidationError
from core.models import ObjectChange
from dcim.models import Device, Interface
from virtualization.models  import VirtualMachine, VMInterface
from ipam.models import IPAddress
from netbox.context import current_request
from netbox_zabbix.jobs import (
    DeleteZabbixHost,
    CreateZabbixHost,
    UpdateZabbixHost,
    CreateZabbixInterface,
    UpdateZabbixInterface,
    ImportZabbixSystemJob,
)
from netbox_zabbix.models import (
    Config,
    DeviceAgentInterface,
    DeviceSNMPv3Interface,
    DeviceZabbixConfig,
    MainChoices,
    InterfaceTypeChoices
)
import logging

logger = logging.getLogger("netbox.plugins.netbox_zabbix")


# ------------------------------------------------------------------------------
# Helpers Functions
# ------------------------------------------------------------------------------


def get_current_request():
    """
    Return the current NetBox HTTP request stored in thread-local context.
    """
    return current_request.get()


def get_current_request_id():
    """
    Return the current request's id if available, otherwise None.
    """
    req = current_request.get()
    return getattr( req, "id", None ) if req else None


def get_latest_change_user(pk: int):
    """
    Return the User associated with the most recent ObjectChange for the given pk.
    """
    change = ObjectChange.objects.filter( changed_object_id=pk ).order_by( "-time" ).first()
    return change.user if change and change.user else None


def schedule_zabbix_host_update(instance, message):
    """
    Trigger a Zabbix host update job for the Device related to the given instance.
    Supports Device, Interface, VMInterface, and IPAddress instances.
    """
    logger.debug( "Scheduling Zabbix host update for instance %r with message %r", instance.name, message )

    # Determine which PK to use for latest-change user lookup
    pk_for_user = getattr( instance, "pk", None )
    if not pk_for_user:
        logger.error( "Cannot schedule Zabbix update: instance %r has no primary key.", instance )
        return

    user = get_latest_change_user( pk_for_user )
    if not user:
        logger.warning( "Skipping Zabbix update: no user found for latest change on pk=%s.", pk_for_user )
        return

    # Try to resolve a Device regardless of model type
    if isinstance( instance, Device ):
        device = instance
    else:
        device = getattr( instance, "device", None )

    if not isinstance( device, Device ):
        logger.error( "Cannot schedule Zabbix update: instance %r is not or does not resolve to a Device.", instance )
        return

    try:
        device_zcfg = DeviceZabbixConfig.objects.get( device=device )
    except DeviceZabbixConfig.DoesNotExist:
        logger.warning( "Skipping Zabbix update: no DeviceZabbixConfig found for device '%s'.", device.name )
        return
    except DeviceZabbixConfig.MultipleObjectsReturned:
          logger.error( "Multiple DeviceZabbixConfig objects found for device '%s'. Manual cleanup required.", device.name )
          return
    
    logger.info( "Queuing Zabbix host update job for device '%s'.", device.name )
    UpdateZabbixHost.run_job( zabbix_config=device_zcfg, request=get_current_request(), name= f"{message}" if message else f"Update {device_zcfg.device.name} in Zabbix: {message}" )
    logger.info( "Successfully scheduled  Zabbix host update job for device '%s'", device.name )


def needs_zabbix_ip_reassignment(interface: Interface | VMInterface):
    """
    Determine if a Zabbix interface should be reassigned to the device/VM's primary IP.
    
    Reassignment is needed when:
        * No IP is assigned, OR
        * The current IP differs from the device/VM's primary IPv4, OR
        * The primary IP lacks a DNS name.
    
    Returns True if reassignment is required, False otherwise.
    """

    # Determine parent device/VM
    devm = getattr(interface, "device", None) or getattr(interface, "virtual_machine", None)
    if not devm:
        logger.warning( "Skipping Zabbix IP reassignment: no parent Device/VM found for interface id=%s", interface.id )
        return False

    # Ensure the interface has a Zabbix config interface
    zabbix_iface = getattr(interface, "agent_interface", None) or \
                   getattr(interface, "snmpv3_interface", None)
    if not zabbix_iface:
        logger.warning( "Skipping Zabbix IP reassignment: interface id=%s has no Zabbix config interface", interface.id )
        return False

    # Check candidate primary IP
    primary_ip = devm.primary_ip4
    if not primary_ip:
        logger.info( "Device/VM '%s' has no primary IPv4; cannot reassign Zabbix IP for interface id=%s", devm.name, interface.id )
        return False

    # Already correctly assigned?
    if zabbix_iface.ip_address_id == primary_ip.id and primary_ip.dns_name:
        logger.debug( "Zabbix interface id=%s already assigned to correct primary IP %s", zabbix_iface.id, primary_ip.address )
        return False

    # Otherwise, reassignment is needed
    logger.info( "Zabbix interface id=%s requires reassignment to primary IP %s (dns_name=%s)", zabbix_iface.id, primary_ip.address, primary_ip.dns_name )
    return True


def assign_primary_ip_to_zabbix_interface(interface: Interface | VMInterface) -> bool:
    """
    Attempt to reassign the Zabbix interface IP to the parent device/VM's primary IPv4.

    The reassignment is performed only if:
      * The primary IPv4 exists,
      * It belongs to the same interface,
      * It has a DNS name.
    
    Returns True if an IP was successfully re-associated, False otherwise.
    """
    logger.debug( "Starting primary IP reassignment check for interface id=%s", interface.id )

    # Determine parent device/VM
    devm = getattr( interface, "device", None ) or getattr( interface, "virtual_machine", None )
    if not devm:
        logger.warning( "Cannot reassign Zabbix IP: no parent Device/VM for interface id=%s", interface.id )
        return False

    # Ensure the interface has a Zabbix config interface
    zabbix_iface = getattr( interface, "agent_interface", None ) or \
                   getattr( interface, "snmpv3_interface", None )
    if not zabbix_iface:
        logger.warning( "Cannot reassign Zabbix IP: interface id=%s has no Zabbix config interface", interface.id )
        return False

    # Candidate IP must be:
    # 1) primary IPv4 of the device/VM
    # 2) bound to THIS interface
    # 3) have a DNS name
    primary_ip = devm.primary_ip4
    if not primary_ip:
        logger.info( "Device/VM %s has no primary IPv4; skipping Zabbix IP reassignment for interface id=%s", devm, interface.id )
        return False

    if primary_ip.assigned_object_id != interface.id:
        logger.info( "Primary IP %s is not assigned to interface id=%s (belongs to object id=%s)", primary_ip.address, interface.id, primary_ip.assigned_object_id )
        return False

    if not primary_ip.dns_name:
        logger.info( "Primary IP %s has no DNS name; skipping Zabbix IP reassignment for interface id=%s", primary_ip.address, interface.id )
        return False

    # Associate with Zabbix interface
    zabbix_iface.ip_address = primary_ip
    zabbix_iface.save()

    logger.info( "Re-associated Zabbix interface id=%s with primary IP %s (dns_name=%s)", zabbix_iface.id, primary_ip.address, primary_ip.dns_name )
    return True


def has_primary_ipv4_changed(device):
    """
    Check whether a Device's primary IPv4 address has changed in the database.
    """

    if not device.pk:
        logger.debug( "Skipping primary IPv4 change check: device '%s' has no primary key.", getattr(device, "name", "<unnamed>") )
        return False
    
    old_primary = ( Device.objects.filter( pk=device.pk ).values_list( "primary_ip4_id", flat=True ).first() )

    changed = old_primary != device.primary_ip4_id

    logger.debug( "Primary IPv4 change check for device '%s': old=%s, new=%s, changed=%s", device.name, old_primary, device.primary_ip4_id, changed )
    return changed


def has_device_name_changed(device):
    """
    Check whether a Device's name has changed in the database.
    """

    if not device.pk:
        logger.debug( "Skipping device name change check: device has no primary key." )
        return False
    
    old_name = ( Device.objects.filter( pk=device.pk ).values_list( "name", flat=True ).first() )

    changed = old_name != device.name

    logger.debug( "Device name change check for device '%s': old='%s', new='%s', changed=%s", device.pk, old_name, device.name, changed )
    
    return changed

# ------------------------------------------------------------------------------
# System Job
# ------------------------------------------------------------------------------


@receiver(pre_save, sender=Config)
def reschedule_zabbix_sync_job(sender, instance: Config, **kwargs):
    """
    Reschedule the Zabbix import system job when the sync interval changes.
    
    Triggered before saving a Config object to detect interval modifications.
    """

    logger.debug( "Re-Scheduling Zabbix sync job" )

    # Only act on updates (not initial creation)
    if not instance.pk:
        logger.debug( "Config is new; no sync job interval comparison performed." )
        return

    try:
        prev = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        logger.warning( "Previous Config(pk=%s) not found; cannot compare sync interval.", instance.pk )
        return
    
    logger.debug( "Previous interval=%s, New interval=%s", prev.zabbix_sync_interval, instance.zabbix_sync_interval )

    if prev.zabbix_sync_interval != instance.zabbix_sync_interval:
        logger.info( "Zabbix sync interval changed from %s to %s. Rescheduling system job.", prev.zabbix_sync_interval, instance.zabbix_sync_interval )
        transaction.on_commit(
            lambda: ImportZabbixSystemJob.schedule(instance.zabbix_sync_interval)
        )


# ------------------------------------------------------------------------------
# Device Promote Zabbix Interface to main
# ------------------------------------------------------------------------------


#@receiver(post_delete, sender=DeviceAgentInterface)
#def dev_promote_agent_interface_to_main(sender, instance: DeviceAgentInterface, **kwargs):
#    """
#    Ensure a device always has a designated main Agent interface.
#
#    If the deleted interface was the main one, promote the first remaining
#    agent interface on the same host.
#    """
#
#    logger.debug( "Post-delete signal received for DeviceAgentInterface(pk=%s, device=%s)", instance.pk, instance.host.get_name() if instance.host else "UNKNOWN" )
#
#    if instance.main != MainChoices.YES:
#        logger.debug( "Deleted interface was not main; no promotion needed." )
#        return
#    
#    remaining = instance.host.agent_interfaces.exclude( pk=instance.pk )
#    fallback = remaining.first()
#    
#    if not fallback:
#        logger.warning( "No fallback Agent interface available to promote for device '%s'", instance.host.get_name() )
#        return
#    
#    fallback.main = MainChoices.YES
#    fallback.save()
#    
#    logger.info( "Promoted fallback Agent interface %s (pk=%s) to main for device '%s'", fallback.name, fallback.pk, fallback.host.get_name() )
#
#
#
#@receiver(post_delete, sender=DeviceSNMPv3Interface)
#def dev_promote_snmpv3_interface_to_main(sender, instance: DeviceSNMPv3Interface, **kwargs):
#    """
#    Ensure a device always has a designated main SNMPv3 interface.
#
#    If the deleted interface was the main one, promote the first remaining
#    SNMPv3 interface on the same host.
#    """
#
#    logger.debug( "Post-delete signal received for DeviceSNMPv3Interface(pk=%s, device=%s)", instance.pk, instance.host.get_name() if instance.host else "UNKNOWN" )
#    
#    if instance.main != MainChoices.YES:
#        logger.debug( "Deleted interface was not main; no promotion needed." )
#        return
#    
#    remaining = instance.host.snmpv3_interfaces.exclude( pk=instance.pk )
#    fallback = remaining.first()
#    
#    if not fallback:
#        logger.warning( "No fallback SNMPv3 interface available to promote for device %s", instance.host.get_name() )
#        return
#    
#    fallback.main = MainChoices.YES
#    fallback.save()
#    
#    logger.info( "Promoted fallback SNMPv3 interface %s (pk=%s) to main for device %s", fallback.name, fallback.pk, fallback.host.get_name() )


# ------------------------------------------------------------------------------
# Device Create/Update ZabbixConfig
# ------------------------------------------------------------------------------


@receiver(post_save, sender=DeviceZabbixConfig)
def dev_create_or_update_zabbix_config(sender, instance: DeviceZabbixConfig, created: bool, **kwargs):
    """
    Create or update a Zabbix host when a DeviceZabbixConfig is saved.
    """

    logger.debug( "DeviceZabbixConfig signal: pk=%s created=%s", instance.pk, created )

    user = get_latest_change_user( instance.pk )
    if not user:
        logger.error( "No user found for DeviceZabbixConfig %s. Cannot create/update Zabbix host.", instance.pk )
        return
    
    if created:
        logger.info( "Queuing create Zabbix host for device '%s' job", instance.device.name )
        CreateZabbixHost.run_job( zabbix_config=instance, request=get_current_request(), name=f"Create Host in Zabbix for {instance.device.name}" )
        logger.info( "Successfully scheduled create Zabbix host for device '%s' job", instance.device.name )
    else:
        logger.info( "Queuing update Zabbix host for device '%s' job", instance.device.name )        
        UpdateZabbixHost.run_job( zabbix_config=instance, request=get_current_request(), name=f"Update Host in Zabbix for {instance.device.name}" )
        logger.info( "Successfully scheduled update Zabbix host for device '%s' job", instance.device.name )

# ------------------------------------------------------------------------------
# Device Delete ZabbixConfig
# ------------------------------------------------------------------------------


@receiver(pre_delete, sender=DeviceZabbixConfig)
def dev_delete_zabbix_config(sender, instance: DeviceZabbixConfig, **kwargs):
    """
    Delete the associated Zabbix host before removing a DeviceZabbixConfig.
    """

    logger.debug( "DeviceZabbixConfig pre-delete signal received: pk=%s, device=%s", instance.pk, getattr( instance.device, "name", "unknown" ) )

    if not instance.hostid:
        logger.error( "Cannot delete Zabbix host for device '%s': missing hostid (DeviceZabbixConfig pk=%s)", getattr( instance.device, "name", "unknown" ), instance.pk )
        return
    
    logger.info( "Deleting Zabbix host for device '%s' (DeviceZabbixConfig pk=%s) prior to removing config", instance.device.name, instance.pk )
    
    try:
        logger.info( "Queuing delete Zabbix host for device '%s' job", instance.device.name )
        DeleteZabbixHost.run_job(hostid=instance.hostid)
        logger.info( "Successfully scheduled deletion of Zabbix host for device '%s'", instance.device.name )
    except Exception as e:
        logger.error( "Failed to delete Zabbix host for device '%s': %s", instance.device.name, str( e ), exc_info=True )
        raise


# ------------------------------------------------------------------------------
# Create/Update Zabbix Interface (Agent/SNMPv3)
# ------------------------------------------------------------------------------


@receiver(post_save, sender=DeviceAgentInterface)
@receiver(post_save, sender=DeviceSNMPv3Interface)
def dev_create_or_update_zabbix_interface(sender, instance, created: bool, **kwargs):
    """
    Create or update a Zabbix interface (Agent or SNMPv3) when saved.
    """

    logger.debug( "Device interface post-save signal received: pk=%s, created=%s, device=%s", instance.pk, created, getattr(instance.host.device, "name", "unknown") )

    user = get_latest_change_user( instance.pk )
    if not user:
        logger.error( "Cannot create/update Zabbix interface for instance pk=%s: missing latest change user", instance.pk )
        return

    action = "Created" if created else "Updated"
    logger.info( "%s Zabbix interface for device '%s' (interface pk=%s)", action, instance.host.device.name, instance.pk )

    job_func = CreateZabbixInterface.run_job if created else UpdateZabbixInterface.run_job

    try:        
        logger.info( "Queuing %s Zabbix interface job for device '%s'", action.lower(), instance.host.device.name )
        job_func( zabbix_config=instance.host, request=get_current_request(), name=f"{action} interface for {instance.host.device.name}" )
        logger.info( "Successfully scheduled %s Zabbix interface job for device '%s'", action.lower(), instance.host.device.name )
    except Exception as e:
        logger.error( "Failed to schedule %s Zabbix interface job for device '%s': %s", action.lower(), instance.host.device.name, str( e ), exc_info=True )
        raise

# ------------------------------------------------------------------------------
# Delete Zabbix Interface (Agent/SNMPv3)
# ------------------------------------------------------------------------------


#@receiver(post_delete, sender=DeviceAgentInterface)
#@receiver(post_delete, sender=DeviceSNMPv3Interface)
#def dev_delete_interface(sender, instance, **kwargs):
#    """
#    Delete a Zabbix interface (Agent or SNMPv3).
#    """
#
#    logger.debug( "Device Zabbix interface post-delete signal received: pk=%s,  device=%s", instance.pk, getattr( instance.host.device, "name", "unknown" ) )
#    
#    user = get_latest_change_user( instance.pk )
#    if not user:
#        logger.error( "Cannot delete Zabbix interface for instance pk=%s: missing latest change user", instance.pk )
#        return
#    
#    logger.info( "Queuing delete Zabbix interface for device '%s' (interface pk=%s) job ", instance.host.device.name, instance.pk )
#    UpdateZabbixHost.run_job( zabbix_config=instance.host, request=get_current_request(), name=f"Update Host in Zabbix for {instance.host.device.name}" )
#    logger.info( "Successfully scheduled deletion of Zabbix interface for device '%s' (interface pk=%s) job ", instance.host.device.name, instance.pk )

#@receiver(pre_delete, sender=DeviceAgentInterface)
#@receiver(pre_delete, sender=DeviceSNMPv3Interface)
#def prevent_deleting_last_required_interface(sender, instance, **kwargs):
#    """
#    Prevent deletion of the last interface of a type (Agent/SNMPv3)
#    if templates exist that require this interface type.
#    """
#
#    interface_type = ( InterfaceTypeChoices.Agent if isinstance( instance, DeviceAgentInterface ) else InterfaceTypeChoices.SNMP )
#
#    logger.debug( "Pre-delete signal received for interface pk=%s, type=%s, device=%s", instance.pk, interface_type.label, instance.host.get_name() if instance.host else "UNKNOWN" )
#
#    # Count remaining interfaces of this type for the device
#    if interface_type == InterfaceTypeChoices.Agent:
#        remaining_count = instance.host.agent_interfaces.exclude( pk=instance.pk ).count()
#    else:
#        remaining_count = instance.host.snmpv3_interfaces.exclude( pk=instance.pk ).count()
#
#    logger.debug( "Remaining interfaces of type %s for device '%s': %d", interface_type.label, instance.host.get_name() if instance.host else "UNKNOWN", remaining_count )
#
#    if remaining_count == 0:
#        logger.info( "Interface pk=%s is the last %s interface for device '%s'", instance.pk, interface_type.label, instance.host.get_name() if instance.host else "UNKNOWN" )
#
#        # Check if any assigned templates require this interface type
#        zbx_config = getattr( instance, "host", None )
#        if zbx_config:
#            templates_requiring_type = zbx_config.templates.filter( interface_type=interface_type, marked_for_deletion=False ).exists()
#
#            if templates_requiring_type:
#                logger.warning( "Cannot delete last %s interface for device '%s': templates still require it", interface_type.label, instance.host.get_name() if instance.host else "UNKNOWN" )
#                messages.error( get_current_request(), f"Cannot delete the last {interface_type.label} interface for device '{instance.host.device.name}' because templates are still assigned that require it." )
#            else:
#                logger.info( "No templates require this interface type; deletion allowed for interface pk=%s", instance.pk )
#        else:
#            logger.info( "No Zabbix configuration found for device '%s'; deletion allowed", instance.host.get_name() if instance.host else "UNKNOWN" )
#    else:
#        logger.debug( "More than one interface of type %s exists; deletion allowed for pk=%s", interface_type.label, instance.pk )
#
#    # Otherwise deletion is allowed



@receiver(post_delete, sender=DeviceAgentInterface)
@receiver(post_delete, sender=DeviceSNMPv3Interface)
def handle_interface_post_delete(sender, instance, **kwargs):
    """
    Handle post-delete actions for Agent/SNMPv3 interfaces:
      1. Promote a fallback interface to main if the deleted one was main.
      2. Schedule Zabbix host update to reflect interface deletion.
    """
    
    device_name = getattr(instance.host, "get_name", lambda: "UNKNOWN")()
    interface_type = "Agent" if isinstance(instance, DeviceAgentInterface) else "SNMPv3"

    logger.debug( "Post-delete signal received for %s interface (pk=%s, device='%s')", interface_type, instance.pk, device_name )

    # ------------------------------
    # Step 1: Promote fallback to main
    # ------------------------------
    if instance.main == MainChoices.YES:
        remaining_interfaces = (
            instance.host.agent_interfaces.exclude( pk=instance.pk )
            if isinstance( instance, DeviceAgentInterface )
            else instance.host.snmpv3_interfaces.exclude( pk=instance.pk )
        )
        fallback = remaining_interfaces.first()
        if fallback:
            fallback.main = MainChoices.YES
            fallback.save()
            logger.info( "Promoted fallback %s interface %s (pk=%s) to main for device '%s'", interface_type, fallback.name, fallback.pk, device_name )
        else:
            logger.warning( "No fallback %s interface available to promote for device '%s'", interface_type, device_name )
    else:
        logger.debug("Deleted interface was not main; no promotion needed.")

    # ------------------------------
    # Step 2: Schedule Zabbix host update
    # ------------------------------
    user = get_latest_change_user(instance.pk)
    if not user:
        logger.error( "Cannot delete Zabbix interface for instance pk=%s: missing latest change user", instance.pk )
        return

    try:
        device_zcfg = DeviceZabbixConfig.objects.get( device=instance.host.device )
    except DeviceZabbixConfig.DoesNotExist:
        logger.warning( "Device '%s' has no Zabbix configuration. Skipping Zabbix job.", device_name )
        return

    logger.info( "Queuing update Zabbix host for device '%s' due to %s interface deletion (interface pk=%s)", device_name, interface_type, instance.pk )
    UpdateZabbixHost.run_job( zabbix_config=device_zcfg, request=get_current_request(), name=f"Update Host in Zabbix for {device_name}" )
    logger.info( "Successfully scheduled update of Zabbix host for device '%s' due to %s interface deletion (interface pk=%s)", device_name, interface_type, instance.pk )




# ------------------------------------------------------------------------------
# Create/Update IP Address
# ------------------------------------------------------------------------------


@receiver(post_save, sender=IPAddress)
def create_or_update_ip_address(sender, instance, created, **kwargs):
    """
    Handle creation or update of an IPAddress.
    """

    ip = instance
    iface = ip.assigned_object

    action = "Created" if created else "Updated"
    logger.debug( "IPAddress post-save signal received: pk=%s, action=%s, ip=%s", ip.pk, action, ip.address )

    if not isinstance(iface, (Interface, VMInterface)):
        logger.info( "Assigned object for IP %s (pk=%s) is not Interface/VMInterface. Skipping Zabbix update.", ip.address, ip.pk )
        return
    
    devm = getattr( iface, "device", None ) or getattr( iface, "virtual_machine", None )
    if devm and needs_zabbix_ip_reassignment( iface ):
        if assign_primary_ip_to_zabbix_interface( iface ):
            logger.info( "Reassigned primary IP %s to Zabbix interface (pk=%s) for device/VM '%s'.", ip.address, iface.pk, devm.name )
        else:
            logger.warning( "Failed to reassign primary IP %s to Zabbix interface (pk=%s) for device/VM '%s'.", ip.address, iface.pk, devm.name )
    
    try:
        schedule_zabbix_host_update( iface, f"{action} IP Address {ip.address}" )
        logger.info( "Scheduled Zabbix host update for IP %s (interface pk=%s).", ip.address, iface.pk )
    except Exception as e:
        logger.error( "Failed to schedule Zabbix host update for IP %s (interface pk=%s): %s", ip.address, iface.pk, str( e ), exc_info=True )
        raise


# ------------------------------------------------------------------------------
# Delete IP Address
# ------------------------------------------------------------------------------


@receiver(pre_delete, sender=IPAddress)
def delete_ip_address(sender, instance: IPAddress,  **kwargs):
    """
    Handle deletion of an IPAddress.
    """

    ip = instance

    logger.debug( "IPAddress pre-delete signal received: pk=%s, ip=%s", ip.pk, ip.address )

    # Get the assigned interface
    interface = getattr( ip, "assigned_object", None )
    if not interface:
        logger.info( "IP %s (pk=%s) has no assigned object. Skipping Zabbix update.", ip.address, ip.pk )
        return
    
    # TODO: Handle VMs

    # Get the device assigned to the interface
    device = getattr( interface, "device", None )
    if not isinstance( device, Device ):
        logger.info( "Assigned object for IP %s (interface pk=%s) is not a Device. Skipping Zabbix update.", ip.address, interface.pk )
        return
    
    # Get the Zabbix Configuration for the device
    try:
        device_zcfg = DeviceZabbixConfig.objects.get( device=device )
        logger.warning( "Zabbix configuration for device '%s' may be out of sync due to IP %s deletion.", device.name, ip.address )
        messages.error( get_current_request(), f"Zabbix configuration for device '{device_zcfg.device.name}' may be out of sync." )
        
    except DeviceZabbixConfig.DoesNotExist:
        logger.debug( "No DeviceZabbixConfig found for device '%s'. Nothing to update in Zabbix.", device.name )


# ------------------------------------------------------------------------------
# Update Device
# ------------------------------------------------------------------------------


@receiver(pre_save, sender=Device)
def update_device(sender, instance, **kwargs):
    """
    Trigger Zabbix host updates when a Device's name or primary IPv4 changes.
    """

    logger.debug( "Pre-save signal for Device: pk=%s, name=%s", instance.pk, instance.name )
    

    # Device name changed
    if has_device_name_changed( instance ):
        logger.info( "Device name changed: pk=%s, old_name=?, new_name=%s. Scheduling Zabbix host update.", instance.pk, instance.name )        
        schedule_zabbix_host_update( instance, f"Update Zabbix host for device '{instance.name}' device name changed" )
        return


    # Check if primary IP changed
    if not has_primary_ipv4_changed( instance ):
        logger.debug( "No primary IPv4 change detected for Device pk=%s, name=%s. Skipping Zabbix update.", instance.pk, instance.name )
        return

    if not instance.primary_ip4:
        logger.info( "Primary IP cleared for Device pk=%s, name=%s. Skipping Zabbix update.", instance.pk, instance.name )
        return

    # Update Zabbix host for the new primary IP
    iface = instance.primary_ip4.assigned_object
    if isinstance( iface, (Interface, VMInterface)):
        logger.info( "Primary IPv4 changed for Device pk=%s, name=%s, new IP=%s. Scheduling Zabbix update.", instance.pk, instance.name, instance.primary_ip4.address )

        if needs_zabbix_ip_reassignment(iface):
            assign_primary_ip_to_zabbix_interface(iface)

        schedule_zabbix_host_update( instance.primary_ip4, f"Update Zabbix host for device '{instance.name}' primary IP {instance.primary_ip4.address} changed" )

    else:
        logger.warning( "Primary IP assigned_object for Device pk=%s, name=%s is not an Interface or VMInterface. Skipping Zabbix update.", instance.pk, instance.name )

# end