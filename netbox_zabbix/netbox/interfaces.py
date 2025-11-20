"""
NetBox Zabbix Plugin — Interface Management Utilities

This module provides helper functions for creating, validating, and
managing Zabbix interfaces associated with NetBox Device and VirtualMachine
objects.

Key functionality:

- `create_zabbix_interface(...)`: Creates and persists a Zabbix interface
  (e.g., agent or SNMP) for a NetBox object, including validation,
  signal bypass handling, and changelog tracking.

- `can_delete_interface(interface)`: Determines whether a Zabbix interface
  can be safely deleted by checking template dependencies via the Zabbix API.

- `is_interface_available(interface)`: Checks whether a Zabbix interface
  is currently available and responsive according to Zabbix.

"""

# NetBox Zabbix plugin imports
import netbox_zabbix.zabbix.api as zapi
from netbox_zabbix import models
from netbox_zabbix.netbox.changelog import log_creation_event
from netbox_zabbix.logger import logger

def create_zabbix_interface( obj, host_config, interface_model, interface_name_suffix, interface_kwargs_fn, user, request_id ):
    """
    Create and persist a Zabbix interface for a host in NetBox.
    
    Args:
        obj (Device | VirtualMachine): Object for which the interface is created.
        host_config (HostConfig): Associated Zabbix configuration.
        interface_model (Type): Interface class (AgentInterface or SNMPInterface).
        interface_name_suffix (str): Suffix for interface name (e.g., 'agent', 'snmp').
        interface_kwargs_fn (Callable): Function returning extra kwargs for the interface.
        user (User): NetBox user performing the action.
        request_id (str): Request ID for changelog tracking.
    
    Returns:
        interface_model instance: Newly created interface.
    
    Raises:
        Exception: If creation or validation fails.
    """
    ip = getattr( obj, "primary_ip4", None )
    if not ip:
        raise Exception( f"{obj.name} does not have a primary IPv4 address" )

    useip = models.UseIPChoices.DNS if getattr( ip, "dns_name", None ) else models.UseIPChoices.IP

    try:
        interface_fields = dict(
            name=f"{obj.name}-{interface_name_suffix}",
            host_config=host_config,
            interface=ip.assigned_object,
            ip_address=ip,
            useip=useip,
        )
        interface_fields.update( interface_kwargs_fn() )
        iface = interface_model( **interface_fields )
        iface.full_clean()

        # Mark this instance to bypass signals for this save operation only
        iface._skip_signal = True
        iface.save()
        
        log_creation_event( iface, user, request_id )

        return iface
    except Exception as e:
        msg = f"Failed to create {interface_name_suffix} interface for {obj.name}: {e}"
        logger.error( msg )
        raise Exception( msg )


def can_delete_interface(interface):
    """
    Check if a Zabbix interface can be deleted.
    
    Args:
        interface: Host interface instance.
    
    Returns:
        bool: True if deletion is allowed, False otherwise.
    """
    try:
        hostid      = int( interface.host_config.hostid )
        interfaceid = int( interface.interfaceid )

        # Check if there are templates that need to be deleted before we can delete the interface.
        if not zapi.can_remove_interface( hostid, interfaceid ):
            return False

    except:
        # Default to False if Zabbix isn't responding.
        return False
    return True


def is_interface_available(interface):
    """
    Check if a Zabbix interface is available.
    
    Args:
        interface: Host interface instance.
    
    Returns:
        bool: True if available, False otherwise.
    """
    try:
        hostid      = int( interface.host_config.hostid )
        interfaceid = int( interface.interfaceid )
    
        # Check if there are templates that need to be deleted before we can delete the interface.
        if not zapi.interface_availability( hostid, interfaceid ):
            return False
    
    except:
        # Default to False if Zabbix isn't responding.
        return False
    return True

