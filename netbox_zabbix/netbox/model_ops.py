"""
NetBox Zabbix Plugin — Model Utilities and Integration

This module provides utility functions for managing NetBox model objects
in the context of the Zabbix plugin, including creation, validation,
and persistence of HostConfig and associated interface objects.

Key functionality:

- `create_custom_field(name, defaults)`: Ensures a custom field exists
  for Device and VirtualMachine objects.
- `can_delete_interface(interface)`: Checks if a Zabbix interface can be safely deleted.
- `is_interface_available(interface)`: Checks if a Zabbix interface is currently available.
- `create_host_config(obj)`: Creates a HostConfig object for a Device or VirtualMachine.
- `create_zabbix_interface(...)`: Creates and persists a Zabbix interface for a host.
- `save_host_config(host_config)`: Validates and saves a HostConfig object to NetBox.

These utilities handle integration between NetBox objects and Zabbix,
including proper changelog tracking, signal management, and error handling.
"""

# Django imports
from django.contrib.contenttypes.models import ContentType

# NetBox imports
from extras.models import CustomField
from dcim.models import Device
from virtualization.models import VirtualMachine

# NetBox Zabbix plugin imports
import netbox_zabbix.zabbix.api as zapi
from netbox_zabbix import models
from netbox_zabbix.netbox.changelog import changelog_create
from netbox_zabbix.logger import logger


def create_custom_field(name, defaults):
    """
    Create a custom field for Device and VirtualMachine if it doesn't exist.
    
    Args:
        name (str): Custom field name.
        defaults (dict): Field attributes such as type, label, etc.
    """
    device_ct = ContentType.objects.get_for_model( Device )
    vm_ct     = ContentType.objects.get_for_model( VirtualMachine )
    
    # Create or get the custom field
    cf, created = CustomField.objects.get_or_create( name=name, defaults=defaults )
    if created:
        cf.object_types.set( [ device_ct.id, vm_ct.id ] )
        cf.save()


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


def create_host_config( obj ):
    """
    Create a HostConfig object for a Device or VirtualMachine.
    
    Args:
        obj (Device | VirtualMachine): Object for which to create the config.
    
    Returns:
        HostConfig: Newly created configuration object.
    
    Raises:
        Exception: If creation or validation fails.
    """
    try:
        content_type = ContentType.objects.get_for_model( obj )
        host_config = models.HostConfig( name=f"z-{obj.name}", content_type=content_type, object_id=obj.id )
        host_config.full_clean()

        # Mark this instance to bypass signals for this save operation only
        host_config._skip_signal = True
        host_config.save()

        return host_config
    
    except Exception as e:
        raise Exception( f"Failed to create Zabbix configuration: {e}" )


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
        
        changelog_create( iface, user, request_id )

        return iface
    except Exception as e:
        msg = f"Failed to create {interface_name_suffix} interface for {obj.name}: {e}"
        logger.error( msg )
        raise Exception( msg )


def save_host_config( host_config ):
    """
    Validate and save a HostConfig object to NetBox.
    
    Args:
        host_config (HostConfig): The configuration to save.
    """
    host_config.full_clean()
    host_config._skip_signal = True
    host_config.save()

