"""
NetBox Zabbix Plugin — Jobs Utilities

This module defines helper classes and functions for jobs that synchronize 
NetBox objects with Zabbix. It includes exception classes, interface normalization, 
and common routines used by Zabbix job runners.

N.B: 
Background jobs in NetBox are executed via RQ, which serializes
(possibly "pickles") only the arguments passed to the job. Model instances
cannot safely be passed directly, because their state may become stale
or they may fail to serialize correctly.

To work around this, we pass the model's primary key (`id`) as job arguments. 
The actual model instance is re-fetched from the database inside the job using
`Model.objects.get( id=config_id )`. 

This ensures that the job always operates on a fresh, fully hydrated
instance, and avoids any issues with pickling complex Django objects.

A temporary, in-memory flag (_skip_signal) is attached to some model instances
to signal that all connected Django signals should be ignored for a specific
save operation. The flag is never written to the database and exists only for
the lifetime of the Python object. Other requests, threads, and future saves
are unaffected, so normal signal processing resumes immediately after this
save completes.
"""

# Standard library imports
from dataclasses import dataclass, field
from typing import Callable, Any, Type, Union
from datetime import timedelta, datetime

# Third-party imports
import netaddr

# Django imports
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType

# NetBox imports
from core.models import Job
from core.choices import ObjectChangeActionChoices
from ipam.models import IPAddress
from dcim.models import Device, Interface as DeviceInterface
from virtualization.models import VirtualMachine, VMInterface

# NetBox Zabbix Imports
from netbox_zabbix.job import AtomicJobRunner
from netbox_zabbix.models import (
    UseIPChoices,
    StatusChoices,
    MonitoredByChoices,
    InventoryModeChoices,
    TLSConnectChoices,
    TagNameFormattingChoices,
    DeleteSettingChoices,
    InterfaceTypeChoices,

    Template,
    HostGroup,
    Proxy,
    ProxyGroup,
    DeviceMapping,
    VMMapping,
    HostConfig,
    AgentInterface,
    SNMPInterface
)
from netbox_zabbix.settings import (
    get_inventory_mode,
    get_delete_setting,
    get_graveyard,
    get_graveyard_suffix,
    get_monitored_by, 
    get_tls_accept, 
    get_tls_connect, 
    get_tls_psk, 
    get_tls_psk_identity,
    get_snmp_securityname,
    get_snmp_authprotocol,
    get_snmp_authpassphrase,
    get_snmp_privprotocol,
    get_snmp_privpassphrase,
    get_tag_name_formatting,
)
from netbox_zabbix.utils import ( 
    get_zabbix_tags_for_object,
    get_zabbix_inventory_for_object,
    find_ip_address
)
from netbox_zabbix.zabbix import (
    import_templates,
    import_proxies,
    import_proxy_groups,
    import_host_groups,
    get_host,
    get_host_by_id,
    create_host,
    update_host,
    delete_host,
    get_host_interfaces,
    get_host_group,
    create_host_group,
    ZabbixHostNotFound
)
from netbox_zabbix.logger import logger


# ------------------------------------------------------------------------------
# Helper Classes and Functions 
# ------------------------------------------------------------------------------


class ExceptionWithData(Exception):
    """
    A custom exception class that carries additional structured data alongside 
    the error message.
    
    This is useful in scenarios where simply raising an exception with a string 
    is not enough, and additional context (such as a failed API payload, 
    validation results, or debug metadata) needs to be passed along with the 
    error.  
    
    The additional data can be consumed by higher-level handlers (e.g. job 
    runners or UI code) to provide richer error reporting, troubleshooting 
    output, or rollback logic.
    
    Attributes:
        data (Any): Arbitrary structured data associated with the exception.
    
    Example:
        >>> payload = {"host": "router1", "status": "failed"}
        >>> raise ExceptionWithData("Failed to create host in Zabbix", payload)
    
        try:
            ...
        except ExceptionWithData as e:
            print(e)        # Output: Failed to create host in Zabbix
            print(e.data)   # Output: {'host': 'router1', 'status': 'failed'}
    """
    def __init__(self, message, data=None, pre_data=None, post_data=None):
        """
        Intialize ExceptionWithData
        """
        super().__init__( message )
        self.data = data
        self.pre_data = pre_data
        self.post_data = post_data


def normalize_interface(iface: dict) -> dict:
    """
    Normalize a Zabbix interface dictionary to ensure correct types and structure.
    
    Converts string representations of integers and nested SNMP fields into
    proper Python types. Supports Agent and SNMPv3 interfaces.
    
    Args:
        iface (dict): Zabbix interface dictionary as returned by the API.
    
    Returns:
        dict: Normalized interface dictionary with integer fields and proper SNMP details.
    
    Notes:
        - Unrecognized SNMP versions are ignored.
        - Does not modify the original input dictionary.
    """

    details = iface.get( "details" )
    if not isinstance( details, dict ):
        details = {}

    base = {
            **iface,
            "type":        int( iface["type"] ),
            "useip":       int( iface["useip"] ),
            "main":        int( iface["main"] ),
            "port":        int( iface["port"] ),
            "interfaceid": int( iface["interfaceid"] ),
    }
    
    version = details.get("version")
    if version is not None:
        try:
            version = int(version)
        except ValueError:
            version = None

    if version == 3:
        base.update({
            # SNMP
            "version":         int( details.get( "version", "0") ),
            "bulk":            int( details.get( "bulk", "1") ),
            "max_repetitions": int( details.get( "max_repetitions", "10") ),
            "securityname":    details.get( "securityname", "" ),
            "securitylevel":   int( details.get( "securitylevel", "0") ),
            "authpassphrase":  details.get( "authpassphrase", "" ),
            "privpassphrase":  details.get( "privpassphrase", "" ),
            "authprotocol":    int( details.get( "authprotocol", "") ),
            "privprotocol":    int( details.get( "privprotocol", "") ),
            "contextname":     details.get( "contextname", "" ),
        })

    # These are not implemented!
    elif version == 2:
        base.update({
            # SNMPv2c
            "version":         int( details.get( "version", "0") ),
            "bulk":            int( details.get( "bulk", "0") ),
            "max_repetitions": int( details.get( "max_repetitions", "0") ),
            "community":       details.get( "snmp_community", "" ),
        })
    
    elif version == 1:
        base.update({
            # SNMPv1
            "version":   int( details.get( "version", "0") ),
            "bulk":      int( details.get( "bulk", "0") ),
            "community": details.get( "snmp_community", "" ),
        })
    else:
        pass

    return base


# ------------------------------------------------------------------------------
# Validate Zabbix Hosts
# ------------------------------------------------------------------------------


def validate_zabbix_host(zabbix_host: dict, host: Union[Device, VirtualMachine]) -> bool:
    """
    Validate a Zabbix host definition against the corresponding NetBox host.
    
    Checks include:
        - Hostname consistency
        - Zabbix config does not already exist in NetBox
        - All templates exist in NetBox
        - Interface types are valid (Agent=1, SNMP=2)
        - IP/DNS addresses map to NetBox interfaces
        - No duplicate IP+port combinations across interfaces
        - No multiple Agent/SNMP interfaces mapped to the same NetBox interface
    
    Args:
        zabbix_host (dict): Zabbix host data from API.
        host (Device | VirtualMachine): Corresponding NetBox object.
    
    Returns:
        dict: Validation result message and optional data.
    
    Raises:
        Exception: If any validation rule is violated.
    """
    # Validate hostname
    zabbix_name = zabbix_host.get( "host", "" )
    if host.name != zabbix_name: # This should never happen, but...
        raise Exception( f"NetBox host name '{host.name}' does not match Zabbix host name '{zabbix_name}'" )

    # Check for existing Zabbix config objects
    if isinstance( host, Device ):
        if hasattr( host, 'host_config' ) and host.host_config is not None:
            raise Exception(f"Device '{host.name}' already has a Host Config associated")
    else:  # VirtualMachine
        if hasattr( host, 'host_config' ) and host.host_config is not None:
            raise Exception( f"VM '{host.name}' already has a Host Config associated" )
    
    # Validate Zabbix templates exists in NetBox
    zabbix_templates = zabbix_host.get( "parentTemplates", [] )
    
    if len( zabbix_templates ) == 0:
        raise Exception( "The Zabbix host has no assigned templates" )
    
    for tmpl in zabbix_templates:
        template_id = tmpl.get( "templateid" )
        template_name = tmpl.get( "name" )
        if not Template.objects.filter( templateid=template_id ).exists():
            raise Exception( f"Template '{template_name}' (ID {template_id}) not found in NetBox" )

    # Validate interfaces
    valid_interface_types = {1, 2}  # 1 = Agent, 2 = SNMP

    # Determine the correct IPAddress foreign key field based on host type
    ip_field = "interface" if isinstance( host, Device ) else "vminterface"
    

    netbox_ips = {
        str( netaddr.IPAddress( ip.address.ip ) ): ip
        for iface in host.interfaces.all()
        for ip in IPAddress.objects.filter( **{ip_field: iface} )
        if ip.address
    }
    netbox_dns = {
        ip.dns_name.lower(): ip
        for iface in host.interfaces.all()
        for ip in IPAddress.objects.filter( **{ip_field: iface} )
        if ip.dns_name
    }

    interfaces = zabbix_host.get( "interfaces", [] )

    if not interfaces:
        raise Exception( "The Zabbix host has no interfaces defined" )


    # Track used (ip, port) tuples per interface type for duplicate detection
    used_ip_ports = {
        1: set(),  # Agent
        2: set(),  # SNMP
    }
    used_nb_interfaces = { 
        1: set(), # Agent
        2: set()  #SNMP
    }
    

    for iface in zabbix_host.get( "interfaces", [] ):
        try:
            interfaceid = int(iface.get("interfaceid"))
        except (TypeError, ValueError):
            raise Exception( "Invalid Zabbix interface id" )
        
        try:
            iface_type = int( iface.get( "type" ) )
            useip = int( iface.get("useip") )
            port = int(iface.get("port"))
        except (TypeError, ValueError):
            raise Exception( f"Invalid 'type', 'useip' or 'port' in Zabbix interface '{interfaceid}" )

        if iface_type not in valid_interface_types:
            raise Exception( f"Unsupported interface type '{iface_type}' in Zabbix interface '{interfaceid}'" )

        if useip == 1:
            ip = iface.get( "ip" )
            if not ip:
                raise Exception( f"The Zabbix interface is configured to use IP address but is missing an IP address" )
            if ip not in netbox_ips:
                raise Exception( f"The IP address {ip} is not associated with '{host.name}' in NetBox" )
            # Also confirm the related NetBox Interface exists
            if not netbox_ips[ip].assigned_object_id:
                raise Exception( f"The IP address {ip} is not associated with an interface in NetBox" )
            nb_ip_obj = netbox_ips[ip]

        elif useip == 0:
            dns = iface.get( "dns", "" ).lower()
            if not dns:
                raise Exception( f"The Zabbix interface is configured to use DNS but is missing DNS" )
            if dns not in netbox_dns:
                raise Exception( f"The DNS name '{dns}' is not associated with '{host.name}' in NetBox" )
            if not netbox_dns[dns].assigned_object_id:
                raise Exception( f"The DNS name '{dns}' is not associated with an interface in NetBox" )
            nb_ip_obj = netbox_dns[dns]
            ip = str(nb_ip_obj.address.ip)
        else:
            raise Exception( f"Unsupported 'useip' value {useip} in interface '{interfaceid}'" )


        # Check duplicate IP+port for same interface type
        ip_port_tuple = (ip, port)
        if ip_port_tuple in used_ip_ports[iface_type]:
            iface_type_str = "Agent" if iface_type == 1 else "SNMP"
            raise Exception(f"Duplicate {iface_type_str} interface with IP+port {ip}:{port} detected")
        
        # Check cross-type IP+port conflicts
        other_type = 2 if iface_type == 1 else 1
        if ip_port_tuple in used_ip_ports[other_type]:
            iface_type_str = "Agent" if iface_type == 1 else "SNMP"
            other_type_str = "SNMP" if iface_type == 1 else "Agent"
            raise Exception(f"{iface_type_str} interface uses IP+port {ip}:{port} already used by {other_type_str} interface")
        
        used_ip_ports[iface_type].add(ip_port_tuple)
        
        # Now check for duplicate NetBox interface usage
        nb_interface_id = nb_ip_obj.assigned_object_id
        if nb_interface_id in used_nb_interfaces[iface_type]:
            iface_type_str = "Agent" if iface_type == 1 else "SNMP"
            raise Exception(f"Duplicate {iface_type_str} interface for NetBox interface ID {nb_interface_id}")
        used_nb_interfaces[iface_type].add(nb_interface_id)

    return { "message": f"'{host.name}' is valid", "data": {} }


# ------------------------------------------------------------------------------
# Payload Support Functions
# ------------------------------------------------------------------------------


def get_tags(obj, existing_tags=None):
    """
    Generate Zabbix-compatible tags for a NetBox object.
    
    Combines dynamic tags derived from the object with any existing tags,
    applies configured formatting (upper/lower), and deduplicates tags.
    
    Args:
        obj (Device | VirtualMachine): NetBox object for which to generate tags.
        existing_tags (list, optional): Pre-existing tag dictionaries to include.
    
    Returns:
        list[dict]: List of tag dictionaries with keys 'tag' and 'value'.
    """
    if existing_tags is None:
        existing_tags = []

    tag_name_formatting = get_tag_name_formatting()
    tag_seen = set()
    result = []

    # Combine existing and dynamic tags, format and deduplicate in one loop
    for tag in existing_tags + get_zabbix_tags_for_object( obj ):
        name = tag['tag']

        if tag_name_formatting == TagNameFormattingChoices.LOWER:
            name = name.lower()
        elif tag_name_formatting == TagNameFormattingChoices.UPPER:
            name = name.upper()

        key = (name, tag['value'])
        if key not in tag_seen:
            tag_seen.add( key )
            result.append( {'tag': name, 'value': tag['value']} )

    return result


# ------------------------------------------------------------------------------
#  Payload
# ------------------------------------------------------------------------------


def build_payload(host_config, for_update=False, pre_data=None) -> dict:
    """
    Construct a Zabbix host payload from a HostConfig instance.
    
    Includes:
        - Host details (name, status, monitored_by)
        - Host groups and templates
        - Inventory data if enabled
        - TLS credentials if required
        - Interfaces (Agent and SNMP) with proper IDs for updates
    
    Args:
        host_config (HostConfig): NetBox Zabbix configuration instance.
        for_update (bool, optional): Whether payload is for host.update() vs. host.create().
        pre_data (dict, optional): Existing Zabbix data to recover interface IDs.
    
    Returns:
        dict: Dictionary suitable for Zabbix API calls (host.create() or host.update()).
    
    Raises:
        Exception: If configuration is invalid or required proxies are missing.
    """

    payload = {
        "host":           host_config.assigned_object.name,
        "status":         str( host_config.status ),
        "monitored_by":   str( host_config.monitored_by ),
        "proxyid":        "0",
        "proxy_groupid":  "0",
        "description":    str( host_config.description ) if host_config.description else "",
        "tags":           get_tags( host_config.assigned_object ),
        "groups":         [ {"groupid": g.groupid} for g in host_config.host_groups.all() ],
        "templates":      [ {"templateid": t.templateid} for t in host_config.templates.all() ],
        "inventory_mode": str( get_inventory_mode() ),
    }

    if host_config.hostid:
        payload["hostid"] = str( host_config.hostid )

    # Monitoring proxy/proxy group
    if host_config.monitored_by == MonitoredByChoices.Proxy:
        if not host_config.proxy:
            raise Exception( f"Host '{payload['host']}' is set to use a proxy, but none is configured." )
        payload["proxyid"] = host_config.proxy.proxyid

    if host_config.monitored_by == MonitoredByChoices.ProxyGroup:
        if not host_config.proxy_group:
            raise Exception( f"Host '{payload['host']}' is set to use a proxy group, but none is configured." )
        payload["proxy_groupid"] = host_config.proxy_group.proxy_groupid

    # Inventory
    if payload["inventory_mode"] == str( InventoryModeChoices.MANUAL ):
        payload["inventory"] = get_zabbix_inventory_for_object( host_config.assigned_object )

    # TLS
    if get_tls_connect() == TLSConnectChoices.PSK or get_tls_accept() == TLSConnectChoices.PSK:
        payload["tls_psk_identity"] = get_tls_psk_identity()
        payload["tls_psk"] = get_tls_psk()

    # Build a map of existing Zabbix interfaces (only for updates)
    existing_ifaces = {}
    if for_update and pre_data and "interfaces" in pre_data:
        for iface in pre_data["interfaces"]:
            key = ( iface.get("ip"), iface.get( "dns" ), iface.get( "type" ), iface.get( "port" ) )
            existing_ifaces[key] = iface.get( "interfaceid" )

    # Interfaces handling
    interfaces = []
    for iface in host_config.agent_interfaces.all():
        entry = {
            "type":  "1",
            "main":  str( iface.main ),
            "useip": str( iface.useip ),
            "ip":    str( iface.resolved_ip_address.address.ip ) if iface.resolved_ip_address else "",
            "dns":   iface.resolved_dns_name or "",
            "port":  str( iface.port ),
        }

        if for_update:
            if iface.interfaceid:
                entry["interfaceid"] = str( iface.interfaceid )

        interfaces.append( entry )

    for iface in host_config.snmp_interfaces.all():
        entry = {
            "type":  "2",
            "main":  str( iface.main ),
            "useip": str( iface.useip),
            "ip":    str( iface.resolved_ip_address.address.ip ) if iface.resolved_ip_address else "",
            "dns":   iface.resolved_dns_name or "",
            "port":  str( iface.port ),
            "details": {
                "version":         str( iface.version ),
                "bulk":            str( iface.bulk ),
                "max_repetitions": str( iface.max_repetitions ),
                "contextname":     str( iface.contextname ),
                "securityname":    str( iface.securityname ),
                "securitylevel":   str( iface.securitylevel ),
                "authprotocol":    str( iface.authprotocol ),
                "authpassphrase":  str( iface.authpassphrase ),
                "privprotocol":    str( iface.privprotocol ),
                "privpassphrase":  str( iface.privpassphrase ),
            },
        }

        if for_update:
            if iface.interfaceid:
                entry["interfaceid"] = str( iface.interfaceid )
            else:
                key = ( entry["ip"], entry["dns"], entry["type"], entry["port"] )
                if key in existing_ifaces:
                    entry["interfaceid"] = existing_ifaces[key]

        interfaces.append( entry )

    payload["interfaces"] = interfaces

    return payload


# ------------------------------------------------------------------------------
#  Mapping
# ------------------------------------------------------------------------------


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
        AgentInterface: InterfaceTypeChoices.Agent,
        SNMPInterface:  InterfaceTypeChoices.SNMP
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
    interface_type = interface_model_to_interface_type.get( interface_model, InterfaceTypeChoices.Any )

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
    return resolve_mapping( obj, interface_model, DeviceMapping, "Device" )


def resolve_vm_mapping(obj, interface_model):
    """
    Resolve the mapping for a NetBox VirtualMachine instance.
    
    Args:
        obj (VirtualMachine): VM instance.
        interface_model (Type): Interface class (AgentInterface or SNMPInterface).
    
    Returns:
        VMMapping: The resolved mapping.
    """
    return resolve_mapping( obj, interface_model, VMMapping, "VM" )


# ------------------------------------------------------------------------------
#  NetBox
# ------------------------------------------------------------------------------


def changelog_create( obj, user, request_id ):
    """
    Manually log an ObjectChange entry for an object creation in a background job.

    Normally, when objects are created via the NetBox UI, the change log
    (ObjectChange) is automatically created by signals that have access to
    the current HTTP request. However, this code runs in a background job,
    which does not have a live request object, so the signals will not fire.
    To ensure the creation is logged, we manually create an ObjectChange.

    Args:
        obj (models.Model): Object that was created.
        user (User): NetBox user performing the operation.
        request_id (str): Request ID for tracking.
    """

    if user and request_id:
        obj_change = obj.to_objectchange( action=ObjectChangeActionChoices.ACTION_CREATE )
        obj_change.user = user
        obj_change.request_id = request_id
        obj_change.save()


def changelog_update( obj, user, request_id ):
    """
    Manually log an ObjectChange entry for an object update in a background job.

    Normally, when objects are created via the NetBox UI, the change log
    (ObjectChange) is automatically created by signals that have access to
    the current HTTP request. However, this code runs in a background job,
    which does not have a live request object, so the signals will not fire.
    To ensure the creation is logged, we manually create an ObjectChange.

    Args:
        obj (models.Model): Object that was updated.
        user (User): NetBox user performing the operation.
        request_id (str): Request ID for tracking.
    """

    if user and request_id:
        obj_change = obj.to_objectchange( action=ObjectChangeActionChoices.ACTION_UPDATE )
        obj_change.user = user
        obj_change.request_id = request_id
        obj_change.save()


def associate_instance_with_job(job, instance):
    """
    Link a Django model instance to a NetBox Job record.
    This sets the job's ``object_type_id`` and ``object_id`` fields to
    reference the given model instance, effectively linking the job to the
    instance in a way compatible with NetBox's changelog and object tracking.
    
    Args:
        job (JobResult): Job record to associate.
        instance (models.Model): Django model instance to link.
    
    Notes:
        - Useful for background jobs creating or updating objects.
    """
    job.object_type_id = ContentType.objects.get_for_model( instance ).pk
    job.object_id = instance.pk


def create_zabbix_config( obj ):
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
        host_config = HostConfig( name=f"z-{obj.name}", content_type=content_type, object_id=obj.id )
        host_config.full_clean()

        # Mark this instance to bypass signals for this save operation only
        host_config._skip_signal = True
        host_config.save()

        return host_config
    
    except Exception as e:
        raise Exception( f"Failed to create Zabbix configuration: {e}" )


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
            host_config.templates.add( Template.objects.get( name=template.name ) )
        except Exception as e:
            msg = f"Failed to add template {template.name}: {e}"
            logger.error( msg )
            raise Exception( msg )

    # Host Groups
    for hostgroup in mapping.host_groups.all():
        try:
            host_config.host_groups.add( HostGroup.objects.get( name=hostgroup.name ) )
        except Exception as e:
            msg = f"Failed to add host group {hostgroup.name}: {e}"
            logger.error( msg )
            raise Exception( msg )

    # Monitored by
    host_config.monitored_by = monitored_by

    # Proxy
    if monitored_by == MonitoredByChoices.Proxy:
        try:
            host_config.proxy = Proxy.objects.get( name=mapping.proxy.name )
        except Exception as e:
            msg = f"Failed to add proxy {mapping.proxy.name}: {e}"
            logger.error( msg )
            raise Exception( msg )

    # Proxy Group
    if monitored_by == MonitoredByChoices.ProxyGroup:
        try:
            host_config.proxy_group = ProxyGroup.objects.get( name=mapping.proxy_group.name )
        except Exception as e:
            msg = f"Failed to add proxy group {mapping.proxy_group.name}: {e}"
            logger.error( msg )
            raise Exception( msg )


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

    useip = UseIPChoices.DNS if getattr( ip, "dns_name", None ) else UseIPChoices.IP

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


def save_zabbix_config( host_config ):
    """
    Validate and save a HostConfig object to NetBox.
    
    Args:
        host_config (HostConfig): The configuration to save.
    """
    host_config.full_clean()
    host_config._skip_signal = True
    host_config.save()


# ------------------------------------------------------------------------------
#  Zabbix
# ------------------------------------------------------------------------------


def create_host_in_zabbix( host_config ):
    """
    Create a host in Zabbix via the API using a HostConfig.
    
    Args:
        host_config (HostConfig): Configuration object representing the host.
    
    Returns:
        tuple[int, dict]: Zabbix host ID and the payload sent to the API.
    
    Raises:
        ExceptionWithData: If the creation fails or hostid is not returned.
    """
    payload = build_payload( host_config, for_update=False )
        
    try:
        result = create_host( **payload )
    except Exception as e:
        raise ExceptionWithData( f"Failed to create host in Zabbix {str( e) }", payload )
    
    hostid = result.get( "hostids", [None] )[0]
    if not hostid:
        raise ExceptionWithData( f"Zabbix failed to return hostid for {host_config.devm_name()}", payload )
    return int( hostid ), payload


def link_interface_in_zabbix( hostid, iface, name ):
    """
    Link a NetBox interface to its Zabbix interface ID after creation.
    
    Args:
        hostid (int): Zabbix host ID.
        iface (AgentInterface | SNMPInterface): Interface object.
        name (str): Human-readable name for logging.
    
    Raises:
        Exception: If linking fails or interfaces cannot be fetched.
    """
    try:
        result = get_host_interfaces( hostid )
        if len( result ) != 1:
            raise ExceptionWithData( f"Unexpected number of interfaces returned for {name}", result )
    except Exception as e:
        raise Exception( f"Failed to link interface for {name}: {str( e )}" )

    iface.interfaceid = result[0].get( "interfaceid", None )
    iface.hostid = hostid
    iface.full_clean()

    # Disable signals
    iface._skip_signal = True
    iface.save()


def link_missing_interface(host_config, hostid):
    """
    Ensure that any NetBox interface missing a Zabbix interface ID is linked.
   
    Args:
        host_config (HostConfig): Device or VM Zabbix configuration.
        hostid (int): Zabbix host ID.
   
    Raises:
        ExceptionWithData: If no matching Zabbix interface can be found.
    """
    # Fetch all Zabbix interfaces for this host
    try:
        zbx_interfaces = get_host_interfaces( hostid )
    except Exception as e:
        raise Exception( f"Failed to link missing interface for hostid {hostid}: {str( e )}" )

    # Find the unlinked interface (Agent or SNMP)
    unlinked_iface = None
    for iface in list( host_config.agent_interfaces.all() ) + list( host_config.snmp_interfaces.all() ):
        if iface.interfaceid is None:
            unlinked_iface = iface
            break

    if not unlinked_iface:  
        logger.info( f"All interfaces for {host_config.name} are already linked")
        return

    if not zbx_interfaces:
        logger.info( f"No interfaces found in Zabbix for host {host_config.name} hostid ({host_config.hostid})" )
        return

    # Normalize unlinked IP (remove /prefix) for comparison
    unlinked_ip_obj = unlinked_iface.resolved_ip_address
    unlinked_ip = str( unlinked_ip_obj.address ) if unlinked_ip_obj else ""
    unlinked_dns = str( unlinked_iface.resolved_dns_name ) if unlinked_iface.resolved_dns_name else ""
    iface_type = unlinked_iface.type

    # Find the matching Zabbix interface
    target_iface = None
    for z in zbx_interfaces:
        z_ip = z.get( "ip", "" )
        z_dns = z.get( "dns", "" )
        z_type = int( z.get( "type", 0 ) )

        if z_type != iface_type:
            continue

        # Found a match
        if z_ip == unlinked_ip or z_dns == unlinked_dns:
            target_iface = z
            break


    # Fallback: if no match but only one interface exists, use it
    if not target_iface and len(zbx_interfaces) == 1:
        logger.info( f"No exact match found; only one Zabbix interface exists, linking it anyway." )
        target_iface = zbx_interfaces[0]


    if not target_iface:
        raise ExceptionWithData( f"Could not find a matching Zabbix interface for {unlinked_iface}", 
                                data={  "zbx_interfaces": [ str( iface ) for iface in zbx_interfaces ],
                                        "unlinked_iface": str( unlinked_iface ) } )

    # Update the interface
    unlinked_iface.interfaceid = target_iface["interfaceid"]
    unlinked_iface.hostid = hostid
    unlinked_iface.full_clean()

    # Mark this instance to bypass signals for this save operation only
    unlinked_iface._skip_signal = True
    unlinked_iface.save( update_fields=["interfaceid", "hostid"] )


 
# ------------------------------------------------------------------------------
#  Provision an new Zabbix Configuration in NetBox and a Host in Zabbix
# ------------------------------------------------------------------------------

@dataclass
class ProvisionContext:
    """
    Context object for provisioning a Zabbix host.
    
    Attributes:
        object (Device | VirtualMachine): Host being provisioned.
        interface_model (Type): Interface class (AgentInterface or SNMPInterface).
        interface_name_suffix (str): Suffix for interface names.
        job (JobResult): Background job performing the import.
        user (User): NetBox user performing the action.
        request_id (str): Request ID for changelog tracking.
        interface_kwargs_fn (Callable): Function returning extra kwargs for interface creation.
    """
    object: Any
    # The Device or VM being provisioned

    interface_model: Type  
    # The interface model (Agent or SNMP)

    interface_name_suffix: str  
    # Name suffix to append to the interface name (e.g., "agent", "snmp")

    job: Any
    # The NetBox JobResult instance representing the background job that is
    # performing the import. Used to log messages and associate the imported
    # configuration with the job.

    user: Any  
    # NetBox user performing the action

    request_id: str 
    # Request ID for changelog tracking

    interface_kwargs_fn: Callable[[], dict] = field(default_factory=dict)  
    # Function that returns extra kwargs for interface creation

def provision_zabbix_host(ctx: ProvisionContext):
    """
    Provision a new Zabbix host and create its NetBox configuration.
    
    Handles:
        - Checking for existing configs
        - Creating HostConfig and interfaces
        - Applying mappings
        - Creating or updating host in Zabbix
        - Linking interfaces
        - Logging changelogs and job associations
    
    Args:
        ctx (ProvisionContext): Context object containing all relevant data.
    
    Returns:
        dict: Message and payload data describing the result.
    
    Raises:
        Exception: If provisioning fails; partial creations are cleaned up.
    """
    try:
        monitored_by = get_monitored_by()

        mapping = ( resolve_device_mapping if isinstance( ctx.object, Device ) else resolve_vm_mapping )( ctx.object, ctx.interface_model )

        # Check if a Zabbix config already exists
        host_config = HostConfig.objects.filter( content_type=ContentType.objects.get_for_model( ctx.object ), object_id=ctx.object.id ).first()

        if host_config:
            # Existing config - only add interface and update host in Zabbix
            iface = create_zabbix_interface(
                ctx.object,
                host_config,
                ctx.interface_model,
                ctx.interface_name_suffix,
                ctx.interface_kwargs_fn,
                ctx.user,
                ctx.request_id
            )

            # Update existing host in Zabbix
            update_host_in_zabbix( host_config, ctx.user, ctx.request_id )

            link_interface_in_zabbix (host_config.hostid, iface, ctx.object.name )
            save_zabbix_config( host_config )
            changelog_create( host_config, ctx.user, ctx.request_id )
            associate_instance_with_job( ctx.job, host_config )

            return {
                "message": f"Updated {ctx.object.name} with new interface {iface.name} in Zabbix",
                "data": {"hostid": host_config.hostid}
            }

        # No existing config exists so we do a full provisioning
        host_config = create_zabbix_config( ctx.object )
        apply_mapping_to_config( host_config, mapping, monitored_by )

        iface = create_zabbix_interface(
            ctx.object,
            host_config,
            ctx.interface_model,
            ctx.interface_name_suffix,
            ctx.interface_kwargs_fn,
            ctx.user,
            ctx.request_id
        )

        hostid, payload = create_host_in_zabbix( host_config )
        host_config.hostid = hostid
        link_interface_in_zabbix( hostid, iface, ctx.object.name )
        save_zabbix_config( host_config )
        changelog_create( host_config, ctx.user, ctx.request_id )
        associate_instance_with_job( ctx.job, host_config )

        return {
            "message": f"Created {ctx.object.name} with {mapping.name} mapping",
            "data": payload
        }

    except Exception as e:
        # Rollback if it failed mid-process
        if 'hostid' in locals():
            try:
                delete_host(hostid)
            except:
                pass # Don't fail the job if the host cannot be deleted
        if 'zabbix_config' in locals():
            associate_instance_with_job( ctx.job, host_config )
        raise


#-------------------------------------------------------------------------------
# Update Zabbix Host
# ------------------------------------------------------------------------------


def update_host_in_zabbix(host_config, user, request_id):
    """
    Update an existing Zabbix host based on its HostConfig.
    
    Performs:
        - Fetching current host state from Zabbix
        - Determining templates to remove/add
        - Sending host.update() payload to Zabbix
        - Logging changelog entry in NetBox
    
    Args:
        host_config (HostConfig): Configuration object representing the host.
        user (User): NetBox user performing the update.
        request_id (str): Request ID for changelog tracking.
    
    Returns:
        dict: Message and pre/post payload data.
    
    Raises:
        ExceptionWithData: If update fails.
    """
    if not isinstance( host_config, HostConfig ):
        raise ValueError( "host_config must be an instance of HostConfig" )
    
    # Fetch current state of the host in Zabbix
    try:
        pre_data = get_host_by_id( host_config.hostid )
    except Exception as e:
        raise Exception( f"Failed to get host by id Zabbix: {str( e )}" )

    # Current template IDs in Zabbix (directly assigned to host)
    current_template_ids = set( t["templateid"] for t in pre_data.get( "templates", [] ) )

    # Templates currently assigned in NetBox
    new_template_ids = set( str( tid ) for tid in host_config.templates.values_list( "templateid", flat=True ) )

    # Only remove templates that are no longer assigned
    removed_template_ids = current_template_ids - new_template_ids
    templates_clear = [ {"templateid": tid} for tid in removed_template_ids ]

    # Build payload for update
    payload = build_payload( host_config, for_update=True )
    if templates_clear:
        payload[ "templates_clear" ] = templates_clear

    try:
        update_host( **payload )
    except Exception as e:
        # Don’t wrap twice – keep context if already ExceptionWithData
        if isinstance( e, ExceptionWithData ):
            raise
        raise ExceptionWithData(
            f"Failed to update Zabbix host {host_config.name}: {e}",
            pre_data=pre_data,
            post_data=payload,
        )

    # Add a change log entry for the update
    changelog_update( host_config, user, request_id )

    return {
        "message":  f"Updated Zabbix host {host_config.hostid}",
        "pre_data": pre_data,
        "post_data": payload,
    }


#-------------------------------------------------------------------------------
# Delete Zabbix Host
# ------------------------------------------------------------------------------


def hard_delete_zabbix_host(hostid):
    """
    Permanently deletes a Zabbix host by its ID.
    
    Args:
        hostid (int): The ID of the Zabbix host to delete.
    
    Returns:
        dict: Message confirming deletion and the original host data.
    
    Raises:
        Exception: If deletion fails unexpectedly.
    """
    if hostid:
        try:
            data = get_host_by_id( hostid )
            delete_host( hostid )
            return { "message": f"Deleted zabbix host {hostid}", "data": data }
        
        except ZabbixHostNotFound as e:
            msg = f"Failed to soft delete Zabbix host {hostid}: {str( e )}"
            logger.info( msg )
            return { "message": msg }
        
        except Exception as e:
            msg = f"Failed to delete Zabbix host {hostid}: {str( e )}"
            raise Exception( msg )


def soft_delete_zabbix_host(hostid):
    """
    Soft-deletes a Zabbix host by renaming it, disabling it, and moving it to a graveyard group.
    
    Args:
        hostid (int): The ID of the Zabbix host to soft-delete.
    
    Returns:
        dict: Message confirming soft deletion, the new host name, and original host data.
    
    Notes:
        - Ensures unique host names in the graveyard by appending a counter if necessary.
        - Creates the graveyard group if it does not exist.
    """
    if hostid:
        try:
            data = get_host_by_id( hostid )
            hostname = data["host"]

            suffix = get_graveyard_suffix()
            base_archived_name = f"{hostname}{suffix}"
            archived_host_name = base_archived_name
            
            # Ensure uniqueness by checking existence
            counter = 1
            while True:
                try:
                    get_host( archived_host_name )

                    # Try next if the host already exists
                    archived_host_name = f"{base_archived_name}-{counter}"
                    counter += 1

                except Exception as e:
                    break
            

            # Ensure graveyard group exists
            graveyard_group_name = get_graveyard()
            
            try:
                # Try to fetch the graveyard group
                graveyard_group = get_host_group( name=graveyard_group_name )
                graveyard_group_id = graveyard_group["groupid"]
            except Exception:
                # Group does not exist create it
                result = create_host_group( name=graveyard_group_name )
                graveyard_group_id = result["groupids"][0]
                import_host_groups()
                

            # Rename, disable and move the host in Zabbix.
            update_host( hostid=hostid, host=archived_host_name, groups=[{"groupid": graveyard_group_id}], status=1 )

            return {
                "message": f"Soft-deleted Zabbix host {hostid}, renamed to '{archived_host_name}' moved to group '{graveyard_group_name}'",
                "data": data,
            }

        except ZabbixHostNotFound as e:
            logger.info( f"Failed to soft delete Zabbix host {hostid}: {str( e )}" )

        except Exception as e:
            msg = f"Failed to soft delete Zabbix host {hostid}: {str( e )}"
            raise Exception( msg )


#-------------------------------------------------------------------------------
# Import Zabbix Settings
# ------------------------------------------------------------------------------


def import_zabbix_settings():
    """
    Imports Zabbix configuration objects into NetBox.
    
    Imports templates, proxies, proxy groups, and host groups from Zabbix.
    
    Returns:
        dict: Message confirming import and details of added/deleted objects.
    
    Raises:
        Exception: If any import step fails.
    """
    try:
        added_templates, deleted_templates       = import_templates()
        added_proxies, deleted_proxies           = import_proxies()
        added_proxy_groups, deleted_proxy_groups = import_proxy_groups()
        added_host_groups, deleted_host_groups   = import_host_groups()

        return { 
            "message": "imported zabbix configuration", 
            "data": { 
                "templates":    { "added": added_templates,    "deleted": deleted_templates    },
                "proxies":      { "added": added_proxies,      "deleted": deleted_proxies      },
                "proxy_groups": { "added": added_proxy_groups, "deleted": deleted_proxy_groups },
                "host_groups":  { "added": added_host_groups,  "deleted": deleted_host_groups  }
            }
        }
    except Exception as e:
        raise e


# ------------------------------------------------------------------------------
# Import host from Zabbix
# ------------------------------------------------------------------------------


@dataclass
class ImportHostContext:
    """
    Context object holding all information required to import a Zabbix host
    into NetBox for a device or virtual machine.
    
    Attributes:
        zabbix_host (dict): Zabbix host configuration.
        obj_instance (Device | VirtualMachine): The target NetBox instance.
        content_type (ContentType): The content type of the object instance.
        job (Any): JobResult instance representing the import job.
        user (User): The user triggering the import.
        request_id (str): HTTP request ID that initiated the import.
    """

    zabbix_host: dict
    # The host data fetched from Zabbix for this device/VM. Typically a dictionary
    # containing the configuration information that will be imported.

    obj_instance: Union[Device, VirtualMachine]
    # The Django model instance representing the object being imported.
    # Can be either a Device or a VirtualMachine instance.

    content_type: ContentType
    # The instance content type.

    job: Any
    # The NetBox JobResult instance representing the background job that is
    # performing the import. Used to log messages and associate the imported
    # configuration with the job.

    user: User
    # The user who triggered the import. Required for logging and for creating
    # change log entries.

    request_id: str
    # The ID of the HTTP request that initiated the job, if available.
    # Useful for tracing imports back to the original request in logs or changelog entries.


def import_zabbix_host(ctx: ImportHostContext):
    """
    Creates a HostConfig in NetBox from a Zabbix host configuration.
    
    Args:
        ctx (ImportHostContext): Context containing all import information.
    
    Returns:
        dict: Message confirming import and the original Zabbix host data.
    
    Raises:
        Exception: If validation fails, host config already exists, or interfaces cannot be created.
    """
    try:
        validate_zabbix_host( ctx.zabbix_host, ctx.obj_instance )
    except Exception as e:
        raise Exception( f"Validation failed: {str( e )}" )

    if ctx.obj_instance.host_config is not None:
        raise Exception( f"Host config for '{ctx.obj_instance.name}' already exists" )

    # Create config instance
    config              = HostConfig( name=f"z-{ctx.obj_instance.name}", content_type=ctx.content_type, object_id=ctx.obj_instance.pk )
    config.hostid       = int( ctx.zabbix_host["hostid"] )
    config.status       = StatusChoices.DISABLED if int( ctx.zabbix_host.get( "status", 0 ) ) else StatusChoices.ENABLED
    config.monitored_by = int( ctx.zabbix_host.get( "monitored_by" ) )
    config.description  = ctx.zabbix_host.get( "description", "" )

    # Disable signals to prevent trying to create the host in Zabbix.
    config._skip_signal = True

    # Add Proxy - needs to be added before calling config.save()
    proxyid = int( ctx.zabbix_host.get( "proxyid" ) )
    if proxyid:
        try:
            config.proxy = Proxy.objects.get( proxyid=proxyid )
        except Proxy.DoesNotExist:
            raise Exception(f"Proxy '{proxyid}' not found in NetBox")
    
    # Add Proxy Group - needs to be added before calling config.save()
    proxy_groupid = int( ctx.zabbix_host.get( "proxy_groupid" ) )
    if proxy_groupid > 0:
        try:
            config.proxy_group = ProxyGroup.objects.get( proxy_groupid=proxy_groupid )
        except ProxyGroup.DoesNotExist:
            raise Exception(f"Proxy group with hostid '{proxy_groupid}' not found in NetBox")

    config.full_clean()
    config.save()
    changelog_create( config, ctx.user, ctx.request_id )

    # Add Host Groups
    for group in ctx.zabbix_host.get( "groups", [] ):
        group_name = group.get( "name", "" )
        if group_name:
            group_obj = HostGroup.objects.get( name=group_name )
            config.host_groups.add( group_obj )


    # Add Templates
    for template in ctx.zabbix_host.get( "parentTemplates", [] ):
        template_name = template.get( "name", "" )
        if template_name:
            template_obj = Template.objects.get( name=template_name )
            config.templates.add( template_obj )

    # Add interfaces
    for iface in map( normalize_interface, ctx.zabbix_host.get( "interfaces", [] ) ):
        # Resolve IP address
        if iface["useip"] == 1 and iface["ip"]:
            # Search NetBox for the Zabbix IP
            nb_ip_address = find_ip_address( iface['ip'] )

        elif iface["useip"] == 0 and iface["dns"]:
            nb_ip_address = IPAddress.objects.get( dns_name=iface["dns"] )
        else:
            raise Exception( f"Cannot resolve IP for Zabbix interface {iface['interfaceid']}" )

        # Resolve the NetBox interface
        if ctx.content_type == ContentType.objects.get_for_model( VirtualMachine ):
            nb_interface = VMInterface.objects.get( id=nb_ip_address.assigned_object_id )
        else:
            nb_interface = DeviceInterface.objects.get( id=nb_ip_address.assigned_object_id )

        if iface["type"] == 1:  # Agent
            try:
                agent_iface = AgentInterface.objects.create(
                    name        = f"{ctx.obj_instance.name}-agent",
                    hostid      = config.hostid,
                    interfaceid = iface["interfaceid"],
                    useip       = iface["useip"],
                    main        = iface["main"],
                    port        = iface["port"],
                    host_config        = config,
                    interface   = nb_interface,
                    ip_address  = nb_ip_address,
                )
                agent_iface.full_clean()
                agent_iface.save()
                changelog_create( agent_iface, ctx.user, ctx.request_id )
                logger.debug( f"Added AgentInterface for {ctx.obj_instance.name} using IP {nb_ip_address}" )

            except Exception as e:
                raise Exception( f"Failed to create agent interface for '{ctx.obj_instance.name}', reason: {str( e )}" )

        elif iface["type"] == 2 and iface["version"] == 3:
            try:
                snmp_iface = SNMPInterface.objects.create(
                    name        = f"{ctx.obj_instance.name}-snmp",
                    hostid      = config.hostid,
                    interfaceid = iface["interfaceid"],
                    useip       = iface["useip"],
                    main        = iface["main"],
                    port        = iface["port"],
                    host_config        = config,
                    interface   = nb_interface,
                    ip_address  = nb_ip_address,

                    # SNMP details
                    version         = iface["version"],
                    bulk            = iface["bulk"],
                    max_repetitions = iface["max_repetitions"],
                    securityname    = iface["securityname"],
                    securitylevel   = iface["securitylevel"],
                    authpassphrase  = iface["authpassphrase"],
                    privpassphrase  = iface["privpassphrase"],
                    authprotocol    = iface["authprotocol"],
                    privprotocol    = iface["privprotocol"],
                    contextname     = iface["contextname"],
                )
                snmp_iface.full_clean()
                snmp_iface.save()
                changelog_create( snmp_iface, ctx.user, ctx.request_id )
                logger.debug( f"Added SNMPInterface for {ctx.obj_instance.name} using IP {nb_ip_address}" )

            except Exception as e:
                raise Exception( f"Failed to create snmp interface for '{ctx.obj_instance.name}', reason: {str( e )}" )
        else:
            raise Exception( f"Unsupported Zabbix interface type {iface['type']}" )


    # Associate the DeviceZabbixConfig instance with the job
    associate_instance_with_job( ctx.job, config )
    
    return { "message": f"imported {ctx.obj_instance.name} from Zabbix to NetBox",  "data": ctx.zabbix_host }



#-------------------------------------------------------------------------------
# Jobs
# ------------------------------------------------------------------------------

#
# Pickle! Should all jobs pass the instance id? If so, then all jobs
# must know the model of the instance so that it can ask the db for the instance.
#
# Note: A job can take instance as an argument which is used by the job internally,
# and "our" jobs should not touch this instance beacuse of pickle.
#

def require_kwargs(kwargs, *required):
    """
    Ensures that required keyword arguments are present.
    
    Args:
        kwargs (dict): Dictionary of keyword arguments.
        *required (str): Names of required arguments.
    
    Returns:
        Single value if one argument requested, else tuple of values.
    
    Raises:
        ValueError: If a required argument is missing or None.
    """
    values = []
    for arg in required:
        if arg not in kwargs or kwargs[arg] is None:
            raise ValueError(f"Missing required argument '{arg}'.")
        values.append(kwargs[arg])
    
    if len(values) == 1:
        return values[0]
    return tuple(values)


def get_instance(content_type_id, instance_id):
    """
    Retrieves a model instance given a content type ID and instance ID.
    
    Args:
        content_type_id (int): ID of the ContentType.
        instance_id (int): ID of the model instance.
    
    Returns:
        Model instance corresponding to the content_type_id and instance_id.
    
    Raises:
        ValueError: If the content type is invalid or instance does not exist.
    """
    try:
        content_type = ContentType.objects.get( id=content_type_id )
    except ContentType.DoesNotExist:
        raise ValueError(f"Invalid content type id: {content_type_id}")

    model_class = content_type.model_class()
    if model_class is None:
        raise ValueError(f"Content type {content_type_id} has no associated model")

    try:
        return model_class.objects.get(id=instance_id)
    except model_class.DoesNotExist:
        raise ValueError(f"No instance with id={instance_id} for model {model_class.__name__}")


class ImportZabbixSettings( AtomicJobRunner ):
    """
    Job to import Zabbix settings into NetBox.
    
    This job imports templates, proxies, proxy groups, and host groups from Zabbix.
    """
    @classmethod
    def run(cls, *args, **kwargs):
        """
        Executes the import of Zabbix settings.
        
        Returns:
            dict: Imported configuration summary.
        
        Raises:
            Exception: If import fails.
        """
        try:
            return import_zabbix_settings()
        except Exception as e:
            msg = f"Failed to import zabbix settings: { str( e ) }"
            logger.error( msg )
            raise Exception( msg )
    
    @classmethod
    def run_job(cls, user=None, schedule_at=None, interval=None, immediate=False, name=None):
        """
        Schedules or enqueues the ImportZabbixSettings job.
        
        Args:
            user (User, optional): User triggering the job.
            schedule_at (datetime, optional): Schedule time.
            interval (int, optional): Interval in minutes for recurring job.
            immediate (bool, optional): Run job immediately.
            name (str, optional): Job name.
        
        Returns:
            Job: The enqueued job instance.
        """
        name = name or "Import Zabbix Settings"

        job_args = {
            "name":        name,
            "schedule_at": schedule_at,
            "interval":    interval,
            "immediate":   immediate,
            "user":        user,
        }

        if interval is None:
            netbox_job = cls.enqueue( **job_args )
        else:
            netbox_job = cls.enqueue_once( **job_args )

        return netbox_job


class ValidateHost( AtomicJobRunner ):
    """
    Job to validate a Zabbix host configuration against a NetBox device or VM.
    """
    @classmethod
    def run(cls, *args, **kwargs):
        """
        Validates the Zabbix host configuration for a given instance.
        
        Returns:
            bool: True if validation passes.
        
        Raises:
            Exception: If the host cannot be validated or instance is invalid.
        """

        # Require content_type and object id
        content_type = require_kwargs( kwargs, "content_type" )
        obj_id = require_kwargs( kwargs, "id" )

        # Retrieve the actual instance
        instance = get_instance( content_type.id, obj_id )
        
        if not isinstance( instance, (Device, VirtualMachine) ):
            raise Exception( "Missing required device or virtual machine instance" )
        
        try:
            zabbix_host = get_host( instance.name )
        except:
            raise 
        return validate_zabbix_host( zabbix_host, instance )

    @classmethod
    def run_job(cls, instance, request, schedule_at=None, interval=None, immediate=False, name=None):
        """
        Enqueues a host validation job.
        
        Args:
            instance (Device|VirtualMachine): Target instance.
            request (HttpRequest): HTTP request triggering the job.
            schedule_at (datetime, optional): Schedule time.
            interval (int, optional): Interval for recurring job.
            immediate (bool, optional): Run job immediately.
            name (str, optional): Job name.
        
        Returns:
            Job: Enqueued job instance.
        """
        if not isinstance( instance, (Device, VirtualMachine) ):
            raise Exception( "Missing required device or virtual machine instance" )
                
        name = name or f"Validate host {instance.name}"

        job_args = {
            # General Job arguments.
            "name":          name,
            "schedule_at":   schedule_at,
            "interval":      interval,
            "immediate":     immediate,

            # Specific Job arguments
            "content_type": ContentType.objects.get_for_model( instance, for_concrete_model=False ),
            "id":           instance.id
        }

        if request:
            job_args["user"]       = request.user
            job_args["request_id"] = request.id
        
        if interval is None:
            netbox_job = cls.enqueue( **job_args )
        else:
            netbox_job = cls.enqueue_once( **job_args )
    
        return netbox_job


    @classmethod
    def run_now(cls, instance=None, *args, **kwargs):
        """
        Executes the validation immediately.
        
        Args:
            instance (Device|VirtualMachine, optional): Target instance.
        
        Returns:
            dict: Validation result.
        """
        kwargs["eventlog"] = False # Disable logging to the event log
        if instance and "content_type" not in kwargs:
            kwargs["content_type"] = ContentType.objects.get_for_model( instance, for_concrete_model=False )
            kwargs["id"] = instance.id
        return super().run_now( *args, **kwargs )
    

class ImportHost( AtomicJobRunner ):
    """
    Job to import a Zabbix host into NetBox as a HostConfig.
    """
    @classmethod
    def run(cls, *args, **kwargs):
        """
        Imports a Zabbix host into NetBox using ImportHostContext.
        
        Returns:
            dict: Message confirming import and imported Zabbix host data.
        
        Raises:
            Exception: If instance is invalid or import fails.
        """
        # Require content_type and object id
        content_type = require_kwargs( kwargs, "content_type" )
        obj_id = require_kwargs( kwargs, "id" )

        # Retrieve the actual instance
        instance = get_instance( content_type.id, obj_id )

        if not isinstance( instance, (Device, VirtualMachine) ):
            raise Exception( "Missing required device or virtual machine instance" )
        

        job_args = {
            "obj_instance": instance,
            "content_type": content_type,
            "user":         cls.job.user,
            "request_id":   kwargs.get( "request_id" ),
            "job":          cls.job
        }
        
        try:
            job_args["zabbix_host"] = get_host( instance.name )
        except:
            raise
        return import_zabbix_host( ImportHostContext( **job_args ) )

    @classmethod
    def run_job(cls, instance, request, schedule_at=None, interval=None, immediate=False, name=None):
        """
        Schedules an ImportHost job.
        
        Args:
            instance (Device|VirtualMachine): Target instance.
            request (HttpRequest): Triggering request.
            schedule_at (datetime, optional): Schedule time.
            interval (int, optional): Interval for recurring job.
            immediate (bool, optional): Run immediately.
            name (str, optional): Job name.
        
        Returns:
            Job: Enqueued job instance.
        """
        if not isinstance( instance, (Device, VirtualMachine) ):
            raise Exception( "Missing required device or virtual machine instance" )

        name = name or f"Import {instance.name}"
        
        job_args = {
            # General Job arguments - 'instance' cannot be used on Devices or VMs.
            "name":         name,
            "schedule_at":  schedule_at,
            "interval":     interval,
            "immediate":    immediate,

            # Specific Job arguments
            "content_type": ContentType.objects.get_for_model( instance, for_concrete_model=False ),
            "id":           instance.id
        }
        
        if request:
            job_args["user"]       = request.user
            job_args["request_id"] = request.id

        if interval is None:
            netbox_job = cls.enqueue( **job_args )
        else:
            netbox_job = cls.enqueue_once( **job_args )

        return netbox_job


class ProvisionAgent(AtomicJobRunner):
    """
    Job to provision an Agent interface in Zabbix for a device or VM
    This job creates a Host Configuration using the Agent interface model and 
    registers it in Zabbix.
    """
    @classmethod
    def run(cls, *args, **kwargs):
        """
        Provisions an Agent interface in Zabbix for the given instance.
        
        Returns:
            dict: Result of provisioning.
        
        Raises:
            Exception: If instance is invalid or provisioning fails.
        """
        # Require content_type and object id
        content_type = require_kwargs( kwargs, "content_type" )
        obj_id = require_kwargs( kwargs, "id" )
        
        # Retrieve the actual instance
        instance = get_instance( content_type.id, obj_id )
        
        if not isinstance( instance, (Device, VirtualMachine) ):
            raise Exception( "Missing required device or virtual machine instance" )

        job_args = {
            "object":                instance,
            "interface_model":       AgentInterface,
            "interface_name_suffix": "agent",
            "job":                   cls.job,
            "user":                  cls.job.user,
            "request_id":            kwargs.get( "request_id" ),
            "interface_kwargs_fn":   lambda: {},
        }

        return provision_zabbix_host( ProvisionContext( **job_args ) )

    @classmethod
    def run_job(cls, instance, request, schedule_at=None, interval=None, immediate=False, name=None):
        """
        Enqueues a ProvisionAgent job.
        
        Returns:
            Job: Enqueued job instance.
        """
        if not isinstance( instance, (Device, VirtualMachine) ):
            raise Exception( "Missing required device or virtual machine instance" )
        
        name = name or f"Provision Agent configuration for {instance.name}"

        job_args = {
            # General Job arguments.
            "name":         name,
            "schedule_at":  schedule_at,
            "interval":     interval,
            "immediate":    immediate,

            # Specific Job arguments
            "content_type": ContentType.objects.get_for_model( instance, for_concrete_model=False ),
            "id":           instance.id
        }

        if request:
            job_args["user"]       = request.user
            job_args["request_id"] = request.id

        if interval is None:
            netbox_job = cls.enqueue( **job_args )
        else:
            netbox_job = cls.enqueue_once( **job_args )

        return netbox_job

    @classmethod
    def run_now(cls, instance=None, *args, **kwargs):
        """
        Immediately provisions an Agent interface.
        
        Args:
            instance (Device|VirtualMachine, optional): Target instance.
        """
        if instance and "content_type" not in kwargs:
            kwargs["content_type"] = ContentType.objects.get_for_model( instance, for_concrete_model=False )
            kwargs["id"] = instance.id
        return super().run_now( *args, **kwargs )


class ProvisionSNMP( AtomicJobRunner ):
    """
    Job to provision an SNMP interface in Zabbix for a device or VM.    
    This job creates a Host configuration using the SNMP interface model and 
    registers it in Zabbix.
    """
    @classmethod
    def run(cls, *args, **kwargs):
        """
        Provisions an SNMP interface in Zabbix for the given instance.
        
        Returns:
            dict: Result of provisioning.
        
        Raises:
            Exception: If instance is invalid or provisioning fails.
        """
        # Require content_type and object id
        content_type = require_kwargs( kwargs, "content_type" )
        obj_id = require_kwargs( kwargs, "id" )
        
        # Retrieve the actual instance
        instance = get_instance( content_type.id, obj_id )
        
        if not isinstance( instance, (Device, VirtualMachine) ):
            raise Exception( "Missing required device or virtual machine instance" )
        
        
        snmp_defaults = {
            "securityname":   get_snmp_securityname(),
            "authprotocol":   get_snmp_authprotocol(),
            "authpassphrase": get_snmp_authpassphrase(),
            "privprotocol":   get_snmp_privprotocol(),
            "privpassphrase": get_snmp_privpassphrase()
        }
        
        job_args = {
            "object":                 instance,
            "interface_model":        SNMPInterface,
            "interface_name_suffix":  "snmp",
            "job":                    cls.job,
            "user":                   cls.job.user,
            "request_id":             kwargs.get( "request_id" ),
            "interface_kwargs_fn":    lambda: snmp_defaults,
        }
        
        try:
            return provision_zabbix_host( ProvisionContext( **job_args ) )
        except Exception as e:
            raise e


    @classmethod
    def run_job(cls, instance, request, schedule_at=None, interval=None, immediate=False, name=None):
        """
        Enqueues a ProvisionSNMP job.
        
        Returns:
            Job: Enqueued job instance.
        """
        if not isinstance( instance, (Device, VirtualMachine) ):
            raise Exception( "Missing required device or virtual machine instance" )
        
        name = name or f"Provision SNMP configuration for {instance.name}"

        job_args = {
            # General Job arguments.
            "name":         name,
            "schedule_at":  schedule_at,
            "interval":     interval,
            "immediate":    immediate,
            "object":       instance,

            # Specific Job arguments
            "content_type": ContentType.objects.get_for_model( instance, for_concrete_model=False ),
            "id":           instance.id
        }

        if request:
            job_args["user"]       = request.user
            job_args["request_id"] = request.id
            
        if interval is None:
            netbox_job = cls.enqueue( **job_args )
        else:
            netbox_job = cls.enqueue_once( **job_args )
        
        return netbox_job


    @classmethod
    def run_now(cls, instance=None, *args, **kwargs):
        """
        Immediately provisions an SNMP interface.
        
        Args:
            instance (Device|VirtualMachine, optional): Target instance.
        """
        if instance and "content_type" not in kwargs:
            kwargs["content_type"] = ContentType.objects.get_for_model( instance, for_concrete_model=False )
            kwargs["id"] = instance.id
        return super().run_now( *args, **kwargs )


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

        host_config = HostConfig.objects.get( id=host_config_id )

        try:
            hostid, payload = create_host_in_zabbix( host_config )
            host_config.hostid = hostid
            save_zabbix_config( host_config )
            changelog_create( host_config, user, request_id )
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
        if not isinstance( host_config, HostConfig ):
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
        
        host_config = HostConfig.objects.get( id=host_config_id )
        return update_host_in_zabbix( host_config, user, request_id )

    @classmethod
    def run_job(cls, host_config, request, user=None, schedule_at=None, interval=None, immediate=False, name=None, signal_id=None):
        """
        Enqueues an UpdateZabbixHost job.
        
        Returns:
            Job: Enqueued job instance.
        """
        if not isinstance( host_config, HostConfig ):
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
        if not isinstance( host_config, HostConfig ):
            raise ValueError( "host_config must be an instance of HostConfig" )
        
        if name is None:
            name = f"Update Host in Zabbix for {host_config.name}"
    
        return cls.run_now(
            host_config_id=host_config.id,
            user=request.user,
            request_id=request.id,
            name=name
        )


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
        if not isinstance( host_config, HostConfig ):
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
        config_id = require_kwargs( kwargs, "config_id" )
        host_config = HostConfig.objects.get( id=config_id )

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
        config_id = require_kwargs( kwargs, "config_id" )
        host_config = HostConfig.objects.get( id=config_id )
        
        if not host_config.hostid:
            raise Exception(
                f"Cannot update interface for '{host_config.assigned_object.name}': "
                f"Host Config '{host_config.name}' has no associated Zabbix host id."
            )

        # Assoicate the interface with the interfaceid
        link_missing_interface( host_config, host_config.hostid )
        return update_host_in_zabbix( host_config, kwargs.get( "user" ), kwargs.get( "request_id" ) )


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

            if get_delete_setting() == DeleteSettingChoices.HARD:
                return hard_delete_zabbix_host( hostid )
            else:
                return soft_delete_zabbix_host( hostid )

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


#-------------------------------------------------------------------------------
# System Jobs
# ------------------------------------------------------------------------------


class ImportZabbixSystemJob( AtomicJobRunner ):
    """
    System job to import Zabbix settings on a recurring interval.
    """
    class Meta:
        name = "Import Zabbix System Job"
    
    @classmethod
    def run(cls, *args, **kwargs):
        """
        Imports Zabbix settings.
        
        Returns:
            dict: Import summary.
        
        Raises:
            Exception: If import fails.
        """
        try:
            return import_zabbix_settings()
        except Exception as e:
            msg = f"Failed to import zabbix settings: { str( e ) }"
            logger.error( msg )
            raise Exception( msg )
        
    @classmethod
    def schedule(cls, interval=None):
        """
        Schedules the system job at a recurring interval.
        
        Args:
            interval (int): Interval in minutes.
        
        Returns:
            Job: Scheduled job instance.
        
        Notes:
            - Only one instance of the system job is allowed at a time.
        """
        if interval == None:
            logger.error( "Import Zabbix System Job required an interval" )
            return None
        
        name = cls.Meta.name

        jobs = Job.objects.filter( name=name, status__in = [ "scheduled", "pending", "running" ] )

        if len(jobs) > 1:
            logger.error( f"Internal error: there can only be one instance of system job '{name}'" )
            return None
        
        existing_job = jobs[0] if len(jobs) == 1 else None

        if existing_job:
            if existing_job.interval == interval:
                logger.error( f"No need to update interval for system job {name}" )
                return existing_job
            logger.error( f"Deleted old job instance for '{name}'")
            existing_job.delete()
        
        
        job_args = {
            "name":         name,
            "interval":     interval,
            "schedule_at":  datetime.now() + timedelta(minutes=interval),
        }

        job = cls.enqueue_once( **job_args )
        logger.error( f"Scheduled new system job '{name}' with interval {interval}" )
        return job



# end