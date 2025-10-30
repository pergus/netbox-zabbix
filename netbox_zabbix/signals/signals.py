# signals.py
#
# Description: Django signal handlers for NetBox Zabbix integration.
# These helpers and signal receivers keep Zabbix host/interface
# configuration synchronized with NetBox objects.
#

from django.db import transaction
from django.db.models.signals import pre_delete, post_delete, pre_save, post_save
from django.dispatch import receiver
from django.contrib import messages
from django.http import HttpRequest
from core.models import ObjectChange
from dcim.models import Device, Interface
from virtualization.models  import VirtualMachine, VMInterface
from ipam.models import IPAddress
from netbox.context import current_request
from netbox_zabbix.jobs import (
    DeleteZabbixHost,
    CreateZabbixHost,
    UpdateZabbixHost,
    ImportZabbixSystemJob,
    CreateZabbixInterface,
    UpdateZabbixInterface
)
from netbox_zabbix.models import (
    Setting,
    HostConfig,
    AgentInterface,
    SNMPInterface,
    MainChoices,
)

import threading
import os
import logging

logger = logging.getLogger("netbox.plugins.netbox_zabbix")


# Thread-local storage to track deletion state per thread

_deletion_context = threading.local()

# ------------------------------------------------------------------------------
# Short identifiers for models
# ------------------------------------------------------------------------------

SIGNAL_CODES = {
    Setting:         "SET",
    Device:          "DEV",
    VirtualMachine:  "VM",
    HostConfig:      "HC",
    AgentInterface:  "AI",
    SNMPInterface:   "SI",
    IPAddress:       "IP",
}

# ------------------------------------------------------------------------------
# Short identifiers for signal types
# ------------------------------------------------------------------------------

SIGNAL_TYPE_CODES = {
    "post_save":   "PS",
    "pre_save":    "PrS",
    "post_delete": "PD",
    "pre_delete":  "PrD",
}


# ------------------------------------------------------------------------------
# Helpers Functions
# ------------------------------------------------------------------------------


def get_signal_id(sender, signal_name: str) -> str:
    """
    Build a short identifier for a signal, e.g. [DZC-PS].
    """
    model_code = SIGNAL_CODES.get(sender, sender.__name__[:3].upper())
    signal_code = SIGNAL_TYPE_CODES.get(signal_name, signal_name.upper())
    return f"{model_code}-{signal_code}"


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


def needs_zabbix_ip_reassignment(interface: Interface | VMInterface):
    """
    Determine if a Zabbix interface should be reassigned to the Device/VM's primary IP.
    
    Reassignment is needed when:
        * No IP is assigned, OR
        * The current IP differs from the Device/VM's primary IPv4, OR
        * The primary IP lacks a DNS name.
    
    Returns True if reassignment is required, False otherwise.
    """

    # Determine parent Device/VM
    dev_or_vm = getattr(interface, "device", None) or getattr(interface, "virtual_machine", None)
    if not dev_or_vm:
        logger.warning( "Skipping Zabbix IP reassignment: no parent Device/VM found for interface id=%s", interface.id )
        return False


    # Ensure the interface has a Zabbix config interface
    snmp_iface   = SNMPInterface.objects.filter( interface_id=interface.id ).first()
    agent_iface  = AgentInterface.objects.filter( interface_id=interface.id ).first()
    
    zabbix_iface = agent_iface or snmp_iface
    
    if not zabbix_iface:
        logger.warning( "Skipping Zabbix IP reassignment: interface id=%s is not associated with a Zabbix interface", interface.id )
        return False

    # Check candidate primary IP
    primary_ip = dev_or_vm.primary_ip4
    if not primary_ip:
        logger.info( "Device/VM '%s' has no primary IPv4; cannot reassign Zabbix IP for interface id=%s", dev_or_vm.name, interface.id )
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
    Attempt to reassign the Zabbix interface IP to the parent Device/VM's primary IPv4.

    The reassignment is performed only if:
      * The primary IPv4 exists,
      * It belongs to the same interface,
      * It has a DNS name.
    
    Returns True if an IP was successfully re-associated, False otherwise.
    """
    logger.debug( "Starting primary IP reassignment check for interface id=%s", interface.id )

    # Determine parent Device/VM
    dev_or_vm = getattr( interface, "device", None ) or getattr( interface, "virtual_machine", None )
    if not dev_or_vm:
        logger.warning( "Cannot reassign Zabbix IP: no parent Device/VM for interface id=%s", interface.id )
        return False

    # Ensure the interface has a Zabbix config interface
    snmp_iface   = SNMPInterface.objects.filter( interface_id=interface.id ).first()
    agent_iface  = AgentInterface.objects.filter( interface_id=interface.id ).first()
    
    zabbix_iface = agent_iface or snmp_iface
    
    
    if not zabbix_iface:
        logger.warning( "Cannot reassign Zabbix IP: interface id=%s has no Zabbix config interface", interface.id )
        return False

    # Candidate IP must be:
    # 1) primary IPv4 of the Device/VM
    # 2) bound to THIS interface
    # 3) have a DNS name
    primary_ip = dev_or_vm.primary_ip4
    if not primary_ip:
        logger.info( "Device/VM %s has no primary IPv4; skipping Zabbix IP reassignment for interface id=%s", dev_or_vm, interface.id )
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


def has_object_name_changed(obj):
    """
    Check whether a Device or VirtualMachine's name has changed in the database.
    """

    if not obj.pk:
        logger.debug( "Skipping name change check: object has no primary key." )
        return False

    model = obj.__class__  # Works for both Device and VirtualMachine
    old_name = model.objects.filter( pk=obj.pk ).values_list( "name", flat=True ).first()

    changed = old_name != obj.name

    logger.debug( "Name change check for %s (pk=%s): old='%s', new='%s', changed=%s", model.__name__, obj.pk, old_name, obj.name, changed )

    return changed, old_name


def is_config_being_deleted(config_pk: int) -> bool:
    return ( hasattr(_deletion_context, "configs_being_deleted") and config_pk in _deletion_context.configs_being_deleted )

# ------------------------------------------------------------------------------
# System Job
# ------------------------------------------------------------------------------


@receiver(pre_save, sender=Setting)
def reschedule_zabbix_sync_job(sender, instance: Setting, **kwargs):
    """
    Reschedule the Zabbix import system job when the sync interval changes.
    
    Triggered before saving a Setting object to detect interval modifications.
    """
    
    if os.environ.get("DISABLE_NETBOX_ZABBIX_SIGNALS") == "1":
        return  # skip logic silently
    
    logger.debug( "re-Scheduling Zabbix sync job" )

    # Only act on updates (not initial creation)
    if not instance.pk:
        logger.debug( "Setting is new; no sync job interval comparison performed." )
        return

    try:
        prev = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        logger.warning( "previous Setting(pk=%s) not found; cannot compare sync interval.", instance.pk )
        return
    
    logger.debug( "previous interval=%s, new interval=%s", prev.zabbix_sync_interval, instance.zabbix_sync_interval )

    if prev.zabbix_sync_interval != instance.zabbix_sync_interval:
        logger.info( "zabbix sync interval changed from %s to %s, rescheduling system job.", prev.zabbix_sync_interval, instance.zabbix_sync_interval )
        transaction.on_commit(
            lambda: ImportZabbixSystemJob.schedule( instance.zabbix_sync_interval )
        )


# ------------------------------------------------------------------------------
# Create/Update Host Config
# ------------------------------------------------------------------------------


@receiver(post_save, sender=HostConfig)
def create_or_update_host_config(sender, instance, created: bool, **kwargs):
    """
    Create or update a Zabbix host when the Host Config is saved.
    """
    if os.environ.get("DISABLE_NETBOX_ZABBIX_SIGNALS") == "1":
        return  # skip logic silently

    signal_id = get_signal_id( sender, "post_save" )
    
    logger.debug( "[%s] received: pk=%s created=%s", signal_id, instance.pk, created )

    if getattr( instance, "_skip_signal", False ):
        logger.debug( "[%s] signal skipped for pk=%s (created=%s) because _skip_signal flag is set", signal_id, instance.pk, created )
        return

    
    # Find user who triggered change
    user = get_latest_change_user( instance.pk )
    if not user:
        logger.error( "[%s] no user found for Host Config %s. Cannot create/update Zabbix host.", signal_id, instance.pk )
        return

    action = "create" if created else "update"

    job_func = CreateZabbixHost.run_job if created else UpdateZabbixHost.run_job
    
    try:
        logger.info( "[%s] queuing %s Zabbix host for '%s'", action, signal_id, instance.name )
        
        name=f"{action.capitalize()} host in Zabbix for {instance.name}"
        request=get_current_request()
        job_func( host_config=instance, request=request, name=name, signal_id=signal_id )

        logger.info( "[%s] successfully scheduled %s Zabbix host for '%s'", action, signal_id, instance.name )
    
    except Exception as e:
        logger.error( "[%s] failed to schedule %s Zabbix host for '%s': %s", signal_id, action, instance.name, str(e), exc_info=True )


# ------------------------------------------------------------------------------
# Delete Host Config
# ------------------------------------------------------------------------------


@receiver(pre_delete, sender=HostConfig)
def delete_host_config(sender, instance, **kwargs):
    """
    Delete the associated Zabbix host before removing a host configuration in NetBox.
    """
    if os.environ.get("DISABLE_NETBOX_ZABBIX_SIGNALS") == "1":
        return  # skip logic silently
    
    signal_id = get_signal_id( sender, "pre_delete" )
    
    logger.debug( "[%s] received: pk=%s, name=%s", signal_id, instance.pk, instance.name )

    if not instance.hostid:
        logger.error( "[%s] cannot delete Zabbix host for '%s': missing hostid (HostConfig pk='%s')", signal_id, instance.name, instance.pk )
        return

    logger.info( "[%s] deleting Zabbix host for '%s' (HostConfig pk=%s) prior to removing config", signal_id, instance.name, instance.pk )

    # Flag this configuration as "being deleted" so that any related objects
    # being deleted via CASCADE can detect the deletion and skip their own post-delete actions.
    # See handle_interface_post_delete()
    if not hasattr( _deletion_context, "configs_being_deleted" ):
        _deletion_context.configs_being_deleted = set()
    _deletion_context.configs_being_deleted.add( instance.pk )
    logger.debug("[%s] marked HostConfig %s as being deleted", signal_id, instance.pk)

    try:
        logger.info( "[%s] queuing delete Zabbix host for '%s'", signal_id, instance.name )
        DeleteZabbixHost.run_job( hostid=instance.hostid, signal_id=signal_id )
        logger.info( "[%s] successfully scheduled delete Zabbix host for '%s'", signal_id, instance.name )
    except Exception as e:
        logger.error( "[%s] failed to schedule delete Zabbix host for '%s': %s", signal_id, instance.name, str(e), exc_info=True )


@receiver(post_delete, sender=HostConfig)
def unmark_config(sender, instance, **kwargs):
    """
    Signal receiver that unmarks a HostConfig object after it has been deleted.
    
    This function listens for the Django `post_delete` signal on the `HostConfig` model.
    When triggered, it removes the deleted object's primary key from the thread-local
    `_deletion_context.configs_being_deleted` set to ensure cleanup of any temporary
    deletion tracking state.
    
    Environment Variable:
        DISABLE_NETBOX_ZABBIX_SIGNALS (str): 
            If set to "1", the function exits early and no cleanup occurs.
    
    Args:
        sender (Model): The model class (`HostConfig`) that sent the signal.
        instance (HostConfig): The specific instance of `HostConfig` that was deleted.
        **kwargs: Additional keyword arguments provided by the signal.
    """
    if os.environ.get("DISABLE_NETBOX_ZABBIX_SIGNALS") == "1":
        return  # skip logic silently
    
    signal_id = get_signal_id( sender, "post_delete" )
    logger.debug( "[%s] received: pk=%s", signal_id, instance.pk )
    getattr( _deletion_context, "configs_being_deleted", set() ).discard( instance.pk )


# ------------------------------------------------------------------------------
# Create/Update Zabbix Interface (Agent/SNMP)
# ------------------------------------------------------------------------------

@receiver(post_save, sender=AgentInterface)
@receiver(post_save, sender=SNMPInterface)
def create_or_update_zabbix_interface(sender, instance, created: bool, **kwargs):

    if os.environ.get("DISABLE_NETBOX_ZABBIX_SIGNALS") == "1":
        return  # skip logic silently
    
    signal_id = get_signal_id( sender, "post_save" )

    logger.debug( "[%s] received: sender=%s, pk=%s, created=%s, host_config=%s", 
                 signal_id, sender.__name__, instance.pk, created, 
                 getattr( instance.host_config, "pk", "unknown" ) )
    
    # Skip if flagged
    if getattr( instance, "_skip_signal", False ):
        logger.debug( "[%s] signal skipped for pk=%s (created=%s) because _skip_signal flag is set", signal_id, instance.pk, created )
        return
    
    # Find user who triggered change
    user = get_latest_change_user(instance.pk)
    if not user:
        logger.error( "[%s] cannot create/update Zabbix interface for pk=%s: missing latest change user", signal_id, instance.pk )
        return

    # Determine action
    action = "create" if created else "update"    
    logger.info( "[%s] %s Zabbix interface for '%s' (interface pk=%s)", signal_id, action, instance.name, instance.pk )

    # Pick the job
    job_func = CreateZabbixInterface.run_job if created else UpdateZabbixInterface.run_job
    
    try:
        logger.info( "[%s] queuing %s Zabbix host for '%s'", signal_id, action, instance.name )

        request=get_current_request()
        name=f"{action.capitalize()} interface for {instance.name}"
        
        job_func( host_config=instance.host_config, request=request, name=name, signal_id=signal_id )
        
        logger.info( "[%s] successfully scheduled %s Zabbix host for '%s'", signal_id, action, instance.name )

    except Exception as e:
        logger.error( "[%s] failed to schedule %s Zabbix host for '%s': %s", signal_id, action, instance.name, str(e), exc_info=True )



# ------------------------------------------------------------------------------
# Delete Zabbix Interface (Agent/SNMP)
# ------------------------------------------------------------------------------


@receiver(post_delete, sender=AgentInterface)
@receiver(post_delete, sender=SNMPInterface)
def handle_interface_post_delete(sender, instance, **kwargs):
   """
   Handle post-delete actions for Agent/SNMP interfaces:
     1. Promote a fallback interface to main if the deleted one was main.
     2. Schedule Zabbix host update to reflect interface deletion.
   """
   if os.environ.get("DISABLE_NETBOX_ZABBIX_SIGNALS") == "1":
       return  # skip logic silently
   
   signal_id = get_signal_id( sender, "post_delete" )

   logger.debug( "[%s] received: pk=%s", signal_id, instance.pk )
   

   host_config = getattr( instance, "host_config", None)
   if host_config is None:
       logger.error( "[%s] interface pk=%s has no Zabbix configuration associated with it", signal_id, instance.pk )
       return
   
   if host_config.has_agent_interface:
       interface_type = "Agent"
   elif host_config.has_snmp_interface:
       interface_type = "SNMP"
   else:
       logger.error( "[%s] interface with pk=%s has an unsupported or missing type. Expected 'Agent' or 'SNMP'.", signal_id, host_config.pk )
       return
   
   # Don't do anything if the Zabbix configuration is being deleted and 
   # handle_interface_post_delete() has been called due to CASCADE.
   if is_config_being_deleted( host_config.id ):
       logger.debug( "[%s] skipping Zabbix update for interface '%s' (pk=%s): parent config '%s' pk=%s) is being deleted", signal_id, instance.name, instance.pk, host_config.name, host_config.id )
       return
   
   # ------------------------------
   # Step 1: Promote fallback to main
   # ------------------------------
   if instance.main == MainChoices.YES:
       remaining_interfaces = (
           host_config.agent_interfaces.exclude( pk=instance.pk )
           if host_config.has_agent_interface
           else host_config.snmp_interfaces.exclude( pk=instance.pk )
       )
       fallback = remaining_interfaces.first()
       if fallback:
           fallback.main = MainChoices.YES
           fallback.save()
           logger.info( "[%s] promoted fallback %s interface %s (pk=%s) to main for '%s'", signal_id, interface_type, fallback.name, fallback.pk, host_config.name )
       else:
           logger.warning( "[%s] no fallback %s interface available to promote for '%s'", signal_id, interface_type, host_config.name )
           if host_config:
               msg = f"Zabbix configuration for '{host_config.name}' may be out of sync due to interface {instance.name} deletion."
               logger.warning("[%s] %s", signal_id, msg)
               request = get_current_request()
               if isinstance(request, HttpRequest):
                   messages.error(request, msg)
   else:
       logger.debug( "[%s] deleted interface was not main; no promotion needed.", signal_id )

   # ------------------------------
   # Step 2: Schedule Zabbix host update
   # ------------------------------
   user = get_latest_change_user( instance.pk )
   if not user:
       logger.error( "[%s] cannot update Zabbix interface for instance pk=%s: missing latest change user", signal_id, instance.pk )
       return

   try:
       logger.info( "[%s] queuing Zabbix host update for '%s' due to interface deletion (interface pk=%s)", signal_id, host_config.name, instance.pk )
       
       request=get_current_request()
       name=f"Update Host in Zabbix for {host_config.name}"

       UpdateZabbixHost.run_job( host_config=host_config, request=request, name=name, signal_id=signal_id )

       logger.info( "[%s] successfully scheduled Zabbix host update for '%s' due to %s interface deletion (interface pk=%s)", signal_id, host_config.name, instance.pk )

   except Exception as e:
       logger.error( "[%s] failed to schedule Zabbix host update for '%s': %s", signal_id, host_config.name, str( e ), exc_info=True )


# ------------------------------------------------------------------------------
# Create/Update IP Address
# ------------------------------------------------------------------------------


@receiver(post_save, sender=IPAddress)
def create_or_update_ip_address(sender, instance, created, **kwargs):
   """
   Handle creation or update of an IPAddress.
   """

   if os.environ.get("DISABLE_NETBOX_ZABBIX_SIGNALS") == "1":
       return  # skip logic silently
   
   ip = instance
   action = "create" if created else "update"
   signal_id = get_signal_id( sender, "post_save" )

   logger.debug( "[%s] received: pk=%s, action=%s ip=%s", signal_id, instance.pk, action, ip.address )
   
   # Get the assigned interface
   iface = getattr( ip, "assigned_object", None )
   if not iface:
       logger.info( "[%s] IP %s (pk=%s) has no assigned interface, skipping Zabbix update.", signal_id, ip.address, ip.pk )
       return
   
   if not isinstance( iface, (Interface, VMInterface) ):
       logger.info( "[%s] assigned interface for IP %s (pk=%s) is not an Interface/VMInterface, skipping Zabbix update.", signal_id, ip.address, ip.pk )
       return

   dev_or_vm = getattr( iface, "device", None ) or getattr( iface, "virtual_machine", None )
   host_config = getattr( dev_or_vm, "host_config", None )

   if host_config:
       
       # Get the user
       user = get_latest_change_user( instance.pk )
       if not user:
           logger.warning( "[%s] skipping Zabbix update: no user found for latest change on pk=%s.", signal_id, instance.pk )
           return
       
       if dev_or_vm and host_config and needs_zabbix_ip_reassignment( iface ):
           if assign_primary_ip_to_zabbix_interface( iface ):
               logger.info( "[%s] reassigned primary IP %s to Zabbix interface (pk=%s) for Device/VM '%s'.", signal_id, ip.address, iface.pk, dev_or_vm.name )
           else:
               logger.warning( "[%s] failed to reassign primary IP %s to Zabbix interface (pk=%s) for Device/VM '%s'.", signal_id, ip.address, iface.pk, dev_or_vm.name )

       try:
           logger.info( "[%s] queuing %s IPAddress in Zabbix for Host Config'%s'", signal_id, action, host_config.name )
           
           request = get_current_request()
           name=f"{action.capitalize()} IPAddress in Zabbix for Host Config {host_config.name}"

           UpdateZabbixHost.run_job( host_config=host_config, request=request, name=name, user=user, signal_id=signal_id )

           logger.info( "[%s] successfully scheduled %s IPAddress in Zabbix for Host Config '%s'", signal_id, action, host_config.name )

       except Exception as e:
           logger.error( "[%s] Failed to schedule %s of IP address '%s' in Zabbix for Host Config '%s' (interface pk=%s): %s", signal_id, action, ip.address, host_config.name, iface.pk, e, exc_info=True )

   else:
       logger.error( "[%s] no Zabbix update required since '%s' has no Zabbix Configuration." , signal_id, dev_or_vm.name )



# ------------------------------------------------------------------------------
# Delete IP Address
# ------------------------------------------------------------------------------


@receiver(pre_delete, sender=IPAddress)
def delete_ip_address(sender, instance: IPAddress,  **kwargs):
   """
   Handle deletion of an IPAddress.
   This function only present a warning in the UI that the host configuration
   in NetBox may be out of sync with Zabbix.
   """
   if os.environ.get("DISABLE_NETBOX_ZABBIX_SIGNALS") == "1":
       return  # skip logic silently
   
   ip = instance
   signal_id = get_signal_id( sender, "pre_delete" )

   logger.debug( "[%s] received: pk=%s, ip=%s", signal_id, instance.pk, ip.address )

   # Get the assigned interface
   iface = getattr( ip, "assigned_object", None )
   if not iface:
       logger.info( "[%s] ip %s (pk=%s) has no assigned object, skipping further processing.", signal_id, ip.address, ip.pk )
       return

   if not isinstance( iface, (Interface, VMInterface) ):
       logger.info( "[%s] assigned object for IP %s (pk=%s) is not an Agent or SNMP Interface, skipping further processing.", signal_id, ip.address, ip.pk )
       return
   
   dev_or_vm = getattr( iface, "device", None ) or getattr( iface, "virtual_machine", None )
   host_config = getattr( dev_or_vm, "host_config", None )

   if host_config:
       msg = f"Zabbix configuration for '{host_config.name}' may be out of sync due to IP {ip.address} deletion."
       logger.warning("[%s] %s", signal_id, msg)
       request = get_current_request()
       if isinstance(request, HttpRequest):
           messages.error(request, msg)


# ------------------------------------------------------------------------------
# Update Device or VirtualMachine
# ------------------------------------------------------------------------------

@receiver(pre_save, sender=Device)
@receiver(pre_save, sender=VirtualMachine)
def update_device_or_vm(sender, instance, **kwargs):
   """
   Trigger Zabbix host updates when the name or primary IPv4 changes for
   a Device or VirtualMachine changes.
   """

   if os.environ.get("DISABLE_NETBOX_ZABBIX_SIGNALS") == "1":
       return  # skip logic silently
   
   signal_id = get_signal_id( sender, "pre_save" )
   logger.debug( "[%s] received: pk=%s, name=%s", signal_id, instance.pk, instance.name )

   config = getattr( instance, "host_config", None)

   if not config:
       logger.warning( "[%s] %s has not Zabbix Config. Skipping futher processing", signal_id, instance.name )
       return

   # Get the user
   user = get_latest_change_user( instance.pk )
   if not user:
       logger.warning( "[%s] failed to schedule Zabbix update, no user found for latest change on pk=%s.", signal_id, instance.pk )
       return


   # Name has changed
   changed, old_name = has_object_name_changed( instance )

   if changed:
       logger.info( "[%s] name changed from %s to %s. Scheduling Zabbix update.", signal_id, old_name, instance.name )
       
       try:
           logger.info( "[%s] queuing Zabbix host update for '%s' due to name change from %s to %s", signal_id, instance.name, old_name, instance.name )

           request=get_current_request()
           name=f"Update Host in Zabbix, name changed from {old_name} to {instance.name}"
           UpdateZabbixHost.run_job( host_config=config, request=request, name=name, signal_id=signal_id )
           logger.info( "[%s] successfully scheduled Zabbix host update for '%s' due to name change from %s to %s", signal_id, instance.name, old_name, instance.name )

       except Exception as e:
           logger.error( "[%s] failed to schedule Zabbix host update for '%s': %s", signal_id, instance.name, str(e), exc_info=True )

   # Check if primary IP changed
   if not has_primary_ipv4_changed( instance ):
       logger.debug( "[%s] No primary IPv4 change detected for %s. Skipping Zabbix update.", signal_id, instance.name )
       return

   if not instance.primary_ip4:
       logger.info( "[%s] %s has no primary ip. Skipping Zabbix update.", signal_id, instance.name )
       return

   # Update Zabbix host for the new primary IP
   iface = instance.primary_ip4.assigned_object
   if isinstance( iface, (Interface, VMInterface)):
       logger.info( "[%s] Primary IPv4 changed for name=%s, new IP=%s. Scheduling Zabbix update.", signal_id, instance.name, instance.primary_ip4.address )

       if needs_zabbix_ip_reassignment(iface):
           assign_primary_ip_to_zabbix_interface(iface)

       try:
           logger.info( "[%s] queuing Zabbix host update for '%s' due to primary ip change to %s", signal_id, instance.name, instance.primary_ip4.address )

           request=get_current_request()
           name=f"Update Host in Zabbix, name changed from {old_name} to {instance.name}"
           UpdateZabbixHost.run_job( host_config=config, request=request, name=name, signal_id=signal_id )

           logger.info( "[%s] successfully scheduled Zabbix host update for '%s' due to primary ip change to %s", signal_id, instance.name, instance.primary_ip4.address )
           
       except Exception as e:
           logger.info( "[%s] failed to schedule Zabbix host update for '%s' due to primary ip change to '%s': %s ", signal_id, instance.name, instance.primary_ip4.address, str( e ), exc_info=True )

   else:
       logger.warning( "[%s] primary IP assigned_object for name=%s is not an Interface or VMInterface, skipping Zabbix update.", signal_id, instance.name )


# end