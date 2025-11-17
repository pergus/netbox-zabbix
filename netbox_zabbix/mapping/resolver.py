"""
NetBox Zabbix Plugin — Mapping Resolvers

Provides utilities to resolve and apply configuration mappings for
NetBox Devices and VirtualMachines when provisioning or synchronizing
Zabbix hosts.

This module includes functions to:

- Resolve the appropriate mapping for a Device or VM based on interface type.
- Apply the mapping's templates, host groups, proxies, and monitored_by
  settings to a HostConfig.
- Handle default mappings and fallback logic when no specific match exists.

These resolvers ensure that Zabbix hosts created or updated via NetBox
adhere to pre-defined configuration standards.
"""

# NetBox Zabbix Imports
from netbox_zabbix import models
from netbox_zabbix.logger import logger


def resolve_mapping(obj, interface_model, mapping_model, mapping_name: str):
    """
    Resolve the appropriate mapping for a Device or VM based on interface type.
    
    Tries to find a mapping matching the host's properties; if none found,
    falls back to the default mapping.
    
    Args:
        obj (Device | VirtualMachine): Object to map.
        interface_model (Type): Interface class (AgentInterface or SNMPInterface).
        mapping_model (Type): Mapping model class (DeviceMapping or VMMapping).
        mapping_name (str): Human-readable mapping type name (for logging).
    
    Returns:
        mapping_model instance: The resolved mapping.
    
    Raises:
        Exception: If no default mapping exists or multiple defaults are found.
    """
    
    interface_model_to_interface_type = {
        models.AgentInterface: models.InterfaceTypeChoices.Agent,
        models.SNMPInterface:  models.InterfaceTypeChoices.SNMP
    }

    # Load mapping
    try:
        default_mapping = mapping_model.objects.get( default=True )
    except mapping_model.DoesNotExist:
        msg = f"No default {mapping_name} mapping defined. Unable to add interface to {obj.name}"
        logger.error( msg )
        raise Exception( msg )
    except mapping_model.MultipleObjectsReturned:
        msg = f"Multiple default {mapping_name} mappings found. Unable to add interface to {obj.name}"
        logger.error( msg )
        raise Exception( msg )

    # Get interface type - use Any as fallback.
    interface_type = interface_model_to_interface_type.get( interface_model, models.InterfaceTypeChoices.Any )

    # Match mapping
    try:
        mapping = mapping_model.get_matching_filter( obj, interface_type )
    except Exception as e:
        logger.error( f"Using default {mapping_name} mapping for {obj.name}: {e}" )
        mapping = default_mapping

    return mapping


def resolve_device_mapping(obj, interface_model):
    """
    Resolve the mapping for a NetBox Device instance.
    
    Args:
        obj (Device): Device instance.
        interface_model (Type): Interface class (AgentInterface or SNMPInterface).
    
    Returns:
        DeviceMapping: The resolved mapping.
    """
    return resolve_mapping( obj, interface_model, models.DeviceMapping, "Device" )


def resolve_vm_mapping(obj, interface_model):
    """
    Resolve the mapping for a NetBox VirtualMachine instance.
    
    Args:
        obj (VirtualMachine): VM instance.
        interface_model (Type): Interface class (AgentInterface or SNMPInterface).
    
    Returns:
        VMMapping: The resolved mapping.
    """
    return resolve_mapping( obj, interface_model, models.VMMapping, "VM" )


def apply_mapping_to_config( host_config, mapping, monitored_by ):
    """
    Apply a mapping's templates, host groups, proxies, and monitored_by setting to a HostConfig.
    
    Args:
        host_config (HostConfig): Zabbix configuration object.
        mapping (DeviceMapping | VMMapping): Mapping to apply.
        monitored_by (MonitoredByChoices): Monitored by setting.
    
    Raises:
        Exception: If templates, host groups, or proxies cannot be applied.
    """
    # Templates
    for template in mapping.templates.all():
        try:
            host_config.templates.add( models.Template.objects.get( name=template.name ) )
        except Exception as e:
            msg = f"Failed to add template {template.name}: {e}"
            logger.error( msg )
            raise Exception( msg )

    # Host Groups
    for hostgroup in mapping.host_groups.all():
        try:
            host_config.host_groups.add( models.HostGroup.objects.get( name=hostgroup.name ) )
        except Exception as e:
            msg = f"Failed to add host group {hostgroup.name}: {e}"
            logger.error( msg )
            raise Exception( msg )

    # Monitored by
    host_config.monitored_by = monitored_by

    # Proxy
    if monitored_by == models.MonitoredByChoices.Proxy:
        try:
            host_config.proxy = models.Proxy.objects.get( name=mapping.proxy.name )
        except Exception as e:
            msg = f"Failed to add proxy {mapping.proxy.name}: {e}"
            logger.error( msg )
            raise Exception( msg )

    # Proxy Group
    if monitored_by == models.MonitoredByChoices.ProxyGroup:
        try:
            host_config.proxy_group = models.ProxyGroup.objects.get( name=mapping.proxy_group.name )
        except Exception as e:
            msg = f"Failed to add proxy group {mapping.proxy_group.name}: {e}"
            logger.error( msg )
            raise Exception( msg )

