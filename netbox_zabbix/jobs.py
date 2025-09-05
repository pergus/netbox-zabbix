# jobs.py
#
#


from dataclasses import dataclass, field
from typing import Callable, Any, Type, Union

from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType

from ipam.models import IPAddress
from dcim.models import Device, Interface as DeviceInterface
from virtualization.models import VirtualMachine, VMInterface

from core.models import Job
from datetime import timedelta, datetime

import netaddr

# NetBox Zabbix Imports
from netbox_zabbix.job import AtomicJobRunner
from netbox_zabbix.zabbix import get_host
from netbox_zabbix.models import (
    DeviceZabbixConfig,
    DeviceAgentInterface,
    DeviceSNMPv3Interface,
    InterfaceTypeChoices,
    TypeChoices,
#    VMAgentInterface,
#    VMSNMPv3Interface,
    DeviceMapping,
    VMMapping,
    Template,
    HostGroup,
    Proxy,
    ProxyGroup,
    VMSNMPv3Interface,
    VMZabbixConfig,
    VMAgentInterface,
    UseIPChoices,
    StatusChoices,
    MonitoredByChoices,
    InventoryModeChoices,
    TLSConnectChoices,
    TagNameFormattingChoices,
)

from netbox_zabbix.config import (
    get_inventory_mode,
    get_zabbix_api_endpoint, 
    get_zabbix_token, 
    get_default_cidr,
    get_monitored_by, 
    get_tls_accept, 
    get_tls_connect, 
    get_tls_psk, 
    get_tls_psk_identity,
    get_snmpv3_securityname,
    get_snmpv3_authprotocol,
    get_snmpv3_authpassphrase,
    get_snmpv3_privprotocol,
    get_snmpv3_privpassphrase,
    get_tag_name_formatting,
)

from netbox_zabbix.utils import ( 
    get_zabbix_tags_for_object,
    get_zabbix_inventory_for_object
)

from netbox_zabbix.zabbix import (
    import_templates,
    import_proxies,
    import_proxy_groups,
    import_host_groups,
    get_host_by_id,
    create_host,
    update_host,
    delete_host,
    get_host_interfaces,
)

from core.choices import ObjectChangeActionChoices


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
        super().__init__( message )
        self.data = data
        self.pre_data = pre_data
        self.post_data = post_data


class SecretStr(str):
    """
    A string subclass that masks its value when represented.
    
    This is useful for preventing sensitive information such as API tokens
    or passwords from being displayed in logs or debug output. The actual
    value is still accessible as a normal string, but its `repr()` output
    will be masked.
    
    Example:
        token = SecretStr("super-secret-token")
        print(token)         # Output: super-secret-token
        print(repr(token))   # Output: '*******'
    """
    def __repr__(self):
        return "'*******'"


def normalize_interface(iface: dict) -> dict:
    """Convert string values in Zabbix interface dict to appropriate types."""

    details = iface.get("details")
    if not isinstance( details, dict ):
        details = {}

    base = {
            **iface,
            "type":        int( iface["type"] ),
            "useip":       int( iface["useip"] ),
            "available":   int( iface["available"] ),
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
            # SNMPv3
            "version":         int( details.get("version", "0") ),
            "bulk":            int( details.get("bulk", "1") ),
            "max_repetitions": int( details.get("max_repetitions", "10") ),
            "securityname":    details.get("securityname", ""),
            "securitylevel":   int( details.get("securitylevel", "0") ),
            "authpassphrase":  details.get("authpassphrase", ""),
            "privpassphrase":  details.get("privpassphrase", ""),
            "authprotocol":    int( details.get("authprotocol", "") ),
            "privprotocol":    int( details.get("privprotocol", "") ),
            "contextname":     details.get("contextname", ""),
        })

    # These are not implemented!
    elif version == 2:    
        base.update({
            # SNMPv2c
            "version":         int( details.get("version", "0") ),
            "bulk":            int( details.get("bulk", "0") ),
            "max_repetitions": int( details.get("max_repetitions", "0") ),
            "community":       details.get("snmp_community", ""),
        })
    
    elif version == 1:    
        base.update({
            # SNMPv1
            "version":   int( details.get("version", "0") ),
            "bulk":      int( details.get("bulk", "0") ),
            "community": details.get("snmp_community", ""),
        })
    else:
        pass

    return base


# ------------------------------------------------------------------------------
# Validate Zabbix Hosts
# ------------------------------------------------------------------------------

def validate_zabbix_host(zabbix_host: dict, host: Union[Device, VirtualMachine]) -> bool:
    """
    Validates a Zabbix host definition against a corresponding NetBox Device or VirtualMachine.

    This validation checks for:
    - Matching hostnames between Zabbix and NetBox
    - No existing Zabbix configuration already assigned in NetBox
    - All Zabbix templates used are present in NetBox
    - Only supported interface types are used (1=Agent, 2=SNMP)
    - Each Zabbix interface resolves to a valid NetBox IP address or DNS name
    - Each IP/DNS used maps to a NetBox IP address assigned to an interface
    - No duplicate use of the same (IP + port) combination within or across interface types
    - No multiple Agent or SNMP interfaces mapped to the same NetBox interface

    Args:
        zabbix_host (dict): A Zabbix host object as returned by the Zabbix API.
        host (Device | VirtualMachine): The corresponding NetBox object to validate against.

    Returns:
        bool: True if validation is successful.

    Raises:
        Exception: If any validation rule is violated.
    """
    # Validate hostname
    zabbix_name = zabbix_host.get( "host", "" )
    if host.name != zabbix_name: # This should never happen, but...
        raise Exception( f"NetBox host name '{host.name}' does not match Zabbix host name '{zabbix_name}'" )

    # Check for existing Zabbix config objects
    if isinstance( host, Device ):
        if hasattr( host, 'devicezabbixconfig' ) and host.devicezabbixconfig is not None:
            raise Exception(f"Device '{host.name}' already has a DeviceZabbixConfig associated")
    else:  # VirtualMachine
        if hasattr( host, 'vmzabbixconfig' ) and host.vmzabbixconfig is not None:
            raise Exception( f"VM '{host.name}' already has a VMZabbixConfig associated" )
    
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
    Generate a list of Zabbix-compatible tags, including dynamic tags from NetBox,
    preserved existing tags, and enforced required tags such as 'netbox'.

    Args:
        obj: A Device or VirtualMachine instance.
        existing_tags (list): Optional list of existing tag dicts, each with 'tag' and 'value' keys.

    Returns:
        list: List of tag dicts with keys 'tag' and 'value'.
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


def build_payload(zcfg) -> dict:
    """
    Build a Zabbix API-compatible payload from either DeviceZabbixConfig or VMZabbixConfig.

    Args:
        zcfg: A Zabbix config model instance (device or VM).

    Returns:
        dict: Zabbix `host.create` or `host.update` payload.

    Raises:
        Exception: On missing associations or invalid data.
    """
    # Get the linked NetBox object (device or VM)
    linked_obj = getattr( zcfg, 'device', None ) or getattr( zcfg, 'virtual_machine', None )
    if not linked_obj:
        raise Exception( "Zabbix config is not linked to a device or virtual machine." )

    payload = {}
    payload["host"] = linked_obj.name

    # Host ID (for updates)
    if zcfg.hostid:
        payload["hostid"] = str( zcfg.hostid )

    # Status
    payload["status"] = str( zcfg.status )

    # Monitoring proxy/proxy group
    monitored_by = zcfg.monitored_by
    payload["monitored_by"] = str( monitored_by )

    if monitored_by == MonitoredByChoices.Proxy:
        if not zcfg.proxy:
            raise Exception( f"Host '{payload['host']}' is set to use a proxy, but none is configured." )
        payload["proxyid"] = zcfg.proxy.proxyid

    if monitored_by == MonitoredByChoices.ProxyGroup:
        if not zcfg.proxy_group:
            raise Exception( f"Host '{payload['host']}' is set to use a proxy group, but none is configured." )
        payload["proxy_groupid"] = zcfg.proxy_group.proxy_groupid

    # Interfaces
    interfaces = []
    for iface in zcfg.agent_interfaces.all():
        entry = {
            "type":        str( 1 ),  # Zabbix Agent
            "main":        str( iface.main ),
            "useip":       str( iface.useip ),
            "ip":          str( iface.resolved_ip_address.address.ip ) if iface.resolved_ip_address else "",
            "dns":         iface.resolved_dns_name or "",
            "port":        str( iface.port ),
        }
        if iface.interfaceid:
            entry["interfaceid"] = str( iface.interfaceid )
        interfaces.append( entry )

    for iface in zcfg.snmpv3_interfaces.all():
        entry = {
            "type":        str( 2 ),  # SNMP
            "main":        str( iface.main ),
            "useip":       str( iface.useip ),
            "ip":          str( iface.resolved_ip_address.address.ip ) if iface.resolved_ip_address else "",
            "dns":         iface.resolved_dns_name or "",
            "port":        str( iface.port ),
            "details": {
                "version":         str( iface.version ) ,
                "bulk":            str( iface.bulk ),
                "max_repetitions": str( iface.max_repetitions ),
                "contextname":     str( iface.contextname ),
                "securityname":    str( iface.securityname ),
                "securitylevel":   str( iface.securitylevel ),
                "authprotocol":    str( iface.authprotocol ),
                "authpassphrase":  str( iface.authpassphrase ),
                "privprotocol":    str( iface.privprotocol ),
                "privpassphrase":  str( iface.privpassphrase ),
            }
        }
        if iface.interfaceid:
            entry["interfaceid"] = str( iface.interfaceid )
        interfaces.append( entry )


    #if not interfaces:
    #    raise Exception(f"No interfaces defined for host '{payload['host']}'")

    payload["interfaces"] = interfaces

    # Host groups
    host_groups = zcfg.host_groups.all()
    if not host_groups:
        raise Exception(f"No host groups assigned to host '{payload['host']}'")

    payload["groups"] = [ { "groupid": g.groupid } for g in host_groups ]


    # Description
    payload["description"] = zcfg.description
    

    # Tags
    payload["tags"] = get_tags( linked_obj )

    # Templates
    cfg_templates = zcfg.templates.all()
    #if not cfg_templates:
    #    raise Exception( f"No templates assigned to host '{payload['host']}'" )

    payload["templates"] = [ { "templateid": t.templateid } for t in cfg_templates ]

    # Inventory mode
    payload["inventory_mode"] = str( get_inventory_mode() )

    # Inventory
    if payload["inventory_mode"] == str( InventoryModeChoices.MANUAL ):
        payload["inventory"] = get_zabbix_inventory_for_object( linked_obj )

    # TLS settings
    if get_tls_connect() == TLSConnectChoices.PSK or get_tls_accept() == TLSConnectChoices.PSK:
        payload["tls_psk_identity"] = get_tls_psk_identity()
        payload["tls_psk"] = get_tls_psk()

    return payload


# ------------------------------------------------------------------------------
#  Mapping
# ------------------------------------------------------------------------------


def _resolve_mapping(obj, interface_model, mapping_model, mapping_name: str):
    """
    Shared logic to resolve a mapping for Device or VM.
    """
    
    interface_model_to_interface_type = {
        DeviceAgentInterface:  InterfaceTypeChoices.Agent,
        DeviceSNMPv3Interface: InterfaceTypeChoices.SNMP,
        VMAgentInterface:      InterfaceTypeChoices.Agent,
        VMSNMPv3Interface:     InterfaceTypeChoices.SNMP
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
    Resolve mapping for a Device.
    """
    return _resolve_mapping( obj, interface_model, DeviceMapping, "Device" )


def resolve_vm_mapping(obj, interface_model):
    """
    Resolve mapping for a Virtual Machine.
    """
    return _resolve_mapping( obj, interface_model, VMMapping, "VM" )


# ------------------------------------------------------------------------------
#  NetBox
# ------------------------------------------------------------------------------


def changelog_create( obj, user, request_id ):
    """
    Manually create an ObjectChange log entry for the ZabbixConfig.

    Normally, when objects are created via the NetBox UI, the change log
    (ObjectChange) is automatically created by signals that have access to
    the current HTTP request. However, this code runs in a background job,
    which does not have a live request object, so the signals will not fire.
    To ensure the creation is logged, we manually create an ObjectChange.
    """

    if user and request_id:
        obj_change = obj.to_objectchange( action=ObjectChangeActionChoices.ACTION_CREATE )
        obj_change.user = user
        obj_change.request_id = request_id
        obj_change.save()


def changelog_update( obj, user, request_id ):
    """
    Manually create an ObjectChange log entry for the ZabbixConfig.

    Normally, when objects are created via the NetBox UI, the change log
    (ObjectChange) is automatically created by signals that have access to
    the current HTTP request. However, this code runs in a background job,
    which does not have a live request object, so the signals will not fire.
    To ensure the creation is logged, we manually create an ObjectChange.
    """

    if user and request_id:
        obj_change = obj.to_objectchange( action=ObjectChangeActionChoices.ACTION_UPDATE )
        obj_change.user = user
        obj_change.request_id = request_id
        obj_change.save()


def associate_instance_with_job(job, instance):
    """
    Associate a Django model instance with a job record.
    
    This sets the job's ``object_type_id`` and ``object_id`` fields to
    reference the given model instance, effectively linking the job to the
    instance in a way compatible with NetBox's changelog and object tracking.
    
    Parameters
    ----------
    job : JobResult
        The job record (e.g., NetBox JobResult or subclass) to update.
    instance : models.Model
        The Django model instance to associate with the job.
    
    Notes
    -----
    - Persists the association by calling ``job.save()``.
    - Can be used inside a job runner to link newly created or updated objects
      back to the job that created/modified them.
    - The association is stored using Django's ContentType framework for
      generic foreign key lookups.
    """
    job.object_type_id = ContentType.objects.get_for_model( instance ).pk
    job.object_id = instance.pk
    #job.save()


def create_zabbix_config( obj, host_field_name, zabbix_config_model ):
    """
    Create a ZabbixConfig object for the given device or VM.
    """
    try:
        zcfg_kwargs = { host_field_name: obj, "status": StatusChoices.ENABLED }
        zcfg = zabbix_config_model( **zcfg_kwargs )
        zcfg.full_clean()
        zcfg.save()
        return zcfg
    
    except Exception as e:
        raise Exception( f"Failed to create Zabbix configuration: {e}" )


def apply_mapping_to_config( zcfg, mapping, monitored_by ):
    """
    Apply templates, host groups, monitored_by, and proxies from the mapping onto the ZabbixConfig.
    """
    
    logger.debug( f"Apply mapping {mapping.name} to {zcfg.get_name()}" )

    # Templates
    for template in mapping.templates.all():
        try:
            zcfg.templates.add( Template.objects.get( name=template.name ) )
        except Exception as e:
            msg = f"Failed to add template {template.name}: {e}"
            logger.error( msg )
            raise Exception( msg )

    # Host Groups
    for hostgroup in mapping.host_groups.all():
        try:
            zcfg.host_groups.add( HostGroup.objects.get( name=hostgroup.name ) )
        except Exception as e:
            msg = f"Failed to add host group {hostgroup.name}: {e}"
            logger.error( msg )
            raise Exception( msg )

    # Monitored by
    zcfg.monitored_by = monitored_by

    # Proxy
    if monitored_by == MonitoredByChoices.Proxy:
        try:
            zcfg.proxy = Proxy.objects.get( name=mapping.proxy.name )
        except Exception as e:
            msg = f"Failed to add proxy {mapping.proxy.name}: {e}"
            logger.error( msg )
            raise Exception( msg )

    # Proxy Group
    if monitored_by == MonitoredByChoices.ProxyGroup:
        try:
            zcfg.proxy_group = ProxyGroup.objects.get( name=mapping.proxy_group.name )
        except Exception as e:
            msg = f"Failed to add proxy group {mapping.proxy_group.name}: {e}"
            logger.error( msg )
            raise Exception( msg )


def add_zabbix_interface( obj, zcfg, interface_model, interface_name_suffix, interface_kwargs_fn, user, request_id ):
    """
    Create and persist a Zabbix interface in NetBox for the given object.
    """
    ip = getattr( obj, "primary_ip4", None )
    if not ip:
        raise Exception( f"{obj.name} does not have a primary IPv4 address" )

    useip = UseIPChoices.DNS if getattr( ip, "dns_name", None ) else UseIPChoices.IP

    try:
        interface_fields = dict(
            name=f"{obj.name}-{interface_name_suffix}",
            host=zcfg,
            interface=ip.assigned_object,
            ip_address=ip,
            useip=useip,
        )
        interface_fields.update( interface_kwargs_fn() )
        iface = interface_model( **interface_fields )
        iface.full_clean()
        iface.save()
        changelog_create( iface, user, request_id )

        return iface
    except Exception as e:
        msg = f"Failed to create {interface_name_suffix} interface for {obj.name}: {e}"
        logger.error( msg )
        raise Exception( msg )


def save_zabbix_config( zcfg ):
    """
    Save the ZabbixConfig to NetBox after it has been updated.
    """
    zcfg.full_clean()
    zcfg.save()


def create_zabbix_host( zcfg, iface, obj, user, request_id ):
    """
    Register a host in Zabbix and link the interface with its Zabbix ID.
    """
    try:
        payload = build_payload( zcfg )
    except Exception as e:
        msg = f"Failed to build payload for {obj.name}: {e}"
        logger.error( msg )
        raise Exception( msg )

    try:
        result = create_host( **payload )
        hostid = result.get( "hostids", [None] )[0]
        if not hostid:
            msg = f"Zabbix failed to return hostid for {obj.name}"
            logger.error( msg )
            raise ExceptionWithData( msg, payload )
        zcfg.hostid = int( hostid )
    except Exception as e:
        msg = f"Failed to create host configuration in Zabbix for {obj.name}: {e}"
        logger.error( msg )
        raise ExceptionWithData( msg, payload )

    try:
        result = get_host_interfaces( hostid )
        if len( result ) == 1:
            iface.interfaceid = result[0].get( "interfaceid", None )
            iface.full_clean()
            iface.save()
        else:
            msg = f"Unexpected number of interfaces returned for {obj.name}"
            logger.error( msg )
            raise ExceptionWithData( msg, payload )
    except Exception as e:
        delete_host( hostid )
        msg = f"Failed to link interface to host {obj.name}: {e}"
        logger.error( msg )
        raise ExceptionWithData( msg, payload )

    try:
        zcfg.full_clean()
        zcfg.save()
    except Exception as e:
        delete_host( hostid )
        msg = f"Failed to save Zabbix configuration for {obj.name}: {e}"
        logger.error( msg )
        raise ExceptionWithData( msg, payload )

    return { "message": f"Created {obj.name}", "data": payload }


# ------------------------------------------------------------------------------
#  Zabbix
# ------------------------------------------------------------------------------


def register_host_in_zabbix( zcfg, obj ):
    """
    Create the host in Zabbix via API.
    """
    payload = build_payload( zcfg )
        
    try:
        result = create_host( **payload )
    except Exception as e:
        raise ExceptionWithData( f"Failed to create host in Zabbix {str( e) }", payload )
    
    hostid = result.get( "hostids", [None] )[0]
    if not hostid:
        raise ExceptionWithData( f"Zabbix failed to return hostid for {obj.name}", payload )
    return int( hostid ), payload


def link_interface_in_zabbix( hostid, iface, obj ):
    """
    Fetch Zabbix interface IDs and link to local iface.
    """
    result = get_host_interfaces( hostid )
    if len( result ) != 1:
        raise ExceptionWithData( f"Unexpected number of interfaces returned for {obj.name}", result )

    iface.interfaceid = result[0].get( "interfaceid", None )
    iface.full_clean()
    iface.save()


# ------------------------------------------------------------------------------
# Import from Zabbix
# ------------------------------------------------------------------------------

@dataclass
class ImportContext:
    """
    Context object holding all information required to import Zabbix configuration
    into NetBox for a device or virtual machine.
    """

    zabbix_host: dict
    # The host data fetched from Zabbix for this device/VM. Typically a dictionary
    # containing the configuration information that will be imported.

    model_instance: Any
    # The Django model instance representing the object being imported.
    # Can be either a Device or a VirtualMachine instance.

    config_model: Type
    # The Django model class used to store the imported configuration.
    # For devices, this would be DeviceZabbixConfig; for VMs, VMZabbixConfig.

    agent_interface_model: Type
    # The model class representing agent interfaces on the device/VM.
    # Used to create or update agent interface records.

    snmpv3_interface_model: Type
    # The model class representing SNMPv3 interfaces on the device/VM.
    # Used to create or update SNMPv3 interface records.

    is_vm: bool
    # Boolean flag indicating whether the import is for a VirtualMachine (True)
    # or a Device (False). This controls how the `instance` is handled in the import.

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


def import_zabbix_config(ctx: ImportContext):
    """
    Generic helper to create Device or VirtualMachine Zabbix Configation from
    a Zabbix Host configuration
    """
    try:
        validate_zabbix_host( ctx.zabbix_host, ctx.model_instance )
    except Exception as e:
        raise Exception( f"Validation failed: {str( e )}" )

    # Map the instance type to its field name on the config model
    instance_type = "virtual_machine" if ctx.is_vm else "device"

    # Ensure config doesn't already exist
    if ctx.config_model.objects.filter( **{instance_type: ctx.model_instance} ).exists():
        raise Exception( f"Zabbix config for '{ctx.model_instance.name}' already exists" )

    # Create config instance
    config             = ctx.config_model( **{instance_type: ctx.model_instance} )
    config.hostid      = int( ctx.zabbix_host["hostid"] )
    config.status      = StatusChoices.DISABLED if int( ctx.zabbix_host.get( "status", 0 ) ) else StatusChoices.ENABLED
    config.description = ctx.zabbix_host.get( "description", "" )
    config.full_clean()
    config.save()
    changelog_create( config, ctx.user, ctx.request_id )
    

    # Add Host Groups
    for group in ctx.zabbix_host.get( "groups", [] ):
        group_name = group.get( "name", "" )
        if group_name:
            group_obj = HostGroup.objects.get( name=group_name )
            config.host_groups.add( group_obj )


    # Add templates
    for template in ctx.zabbix_host.get( "parentTemplates", [] ):
        template_name = template.get( "name", "" )
        if template_name:
            template_obj = Template.objects.get( name=template_name )
            config.templates.add( template_obj )


    # Add interfaces
    for iface in map( normalize_interface, ctx.zabbix_host.get( "interfaces", [] ) ):
        # Resolve IP address
        if iface["useip"] == 1 and iface["ip"]:
            # Since it isn't possible to use CIDR notation when specifying
            # the IP address in Zabbix and NetBox require a CIDR when
            # searching for an IP, a configuratbe CIDR is added to the Zabbix IP.
            cidr          = get_default_cidr()
            address       = f"{iface['ip']}{cidr}"
            nb_ip_address = IPAddress.objects.get( address=address )

        elif iface["useip"] == 0 and iface["dns"]:
            nb_ip_address = IPAddress.objects.get( dns_name=iface["dns"] )
        else:
            raise Exception( f"Cannot resolve IP for Zabbix interface {iface['interfaceid']}" )

        # Resolve the NetBox interface
        if ctx.is_vm:
            nb_interface = VMInterface.objects.get( id=nb_ip_address.assigned_object_id )
        else:
            nb_interface = DeviceInterface.objects.get( id=nb_ip_address.assigned_object_id )
        
         
        if iface["type"] == 1:  # Agent
            try:
                agent_iface = ctx.agent_interface_model.objects.create(
                    name        = f"{ctx.model_instance.name}-agent",
                    hostid      = config.hostid,
                    interfaceid = iface["interfaceid"],
                    available   = iface["available"],
                    useip       = iface["useip"],
                    main        = iface["main"],
                    port        = iface["port"],
                    host        = config,
                    interface   = nb_interface,
                    ip_address  = nb_ip_address,
                )
                agent_iface.full_clean()
                agent_iface.save()
                changelog_create( agent_iface, ctx.user, ctx.request_id )
                
                logger.error( f"Added AgentInterface for {ctx.model_instance.name} using IP {nb_ip_address}" )
            except Exception as e:
                raise Exception( f"Failed to create agent interface for '{ctx.model_instance.name}', reason: {str( e )}" )

        elif iface["type"] == 2 and iface["version"] == 3:
            try:
                snmpv3_iface = ctx.snmpv3_interface_model.objects.create(
                    name        = f"{ctx.model_instance.name}-snmpv3",
                    hostid      = config.hostid,
                    interfaceid = iface["interfaceid"],
                    available   = iface["available"],
                    useip       = iface["useip"],
                    main        = iface["main"],
                    port        = iface["port"],
                    host        = config,
                    interface   = nb_interface,
                    ip_address  = nb_ip_address,

                    # SNMPv3 details
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
                snmpv3_iface.full_clean()
                snmpv3_iface.save()
                changelog_create( snmpv3_iface, ctx.user, ctx.request_id )
                
                logger.error( f"Added SNMPv3tInterface for {ctx.model_instance.name} using IP {nb_ip_address}" )
            except Exception as e:
                raise Exception( f"Failed to create snmpv3 interface for '{ctx.model_instance.name}', reason: {str( e )}" )
        else:
            raise Exception( f"Unsupported Zabbix interface type {iface['type']}" )


    # Associate the DeviceZabbixConfig instance with the job
    associate_instance_with_job( ctx.job, config )
    
    return { "message": f"imported {ctx.model_instance.name} from Zabbix to NetBox",  "data": ctx.zabbix_host }


# ------------------------------------------------------------------------------
#  Provision an new Zabbix Configuration in NetBox and a Host in Zabbix
# ------------------------------------------------------------------------------

@dataclass
class ProvisionContext:
    """
    Context object for provisioning a Zabbix host and creating its
    corresponding NetBox configuration.
    """
    
    obj: Any  
    # The Device or VM being provisioned
        
    host_field_name: str  
    # Field name on the config model that points back to obj (e.g., "device" or "virtual_machine")
        
    zabbix_config_model: Type  
    # The Zabbix config model (e.g., DeviceZabbixConfig, VMZabbixConfig)
    
    interface_model: Type  
    # The interface model (Agent or SNMPv3)
    
    interface_name_suffix: str  
    # Name suffix to append to the interface name (e.g., "agent", "snmpv3")
    
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
    monitored_by = get_monitored_by()

    mapping = (resolve_device_mapping if isinstance( ctx.obj, Device ) else resolve_vm_mapping)( ctx.obj, ctx.interface_model )

    zabbix_config = create_zabbix_config( ctx.obj, ctx.host_field_name, ctx.zabbix_config_model )
    apply_mapping_to_config( zabbix_config, mapping, monitored_by )
    iface = add_zabbix_interface( 
        ctx.obj, 
        zabbix_config, 
        ctx.interface_model, 
        ctx.interface_name_suffix, 
        ctx.interface_kwargs_fn, 
        ctx.user, 
        ctx.request_id 
    )

    try:
        hostid, payload = register_host_in_zabbix( zabbix_config, ctx.obj )
        zabbix_config.hostid = hostid
        link_interface_in_zabbix( hostid, iface, ctx.obj )
        save_zabbix_config( zabbix_config )
        changelog_create( zabbix_config, ctx.user, ctx.request_id )
        associate_instance_with_job(ctx.job, zabbix_config )

    except Exception as e:
        if 'hostid' in locals():
            delete_host( hostid )
        raise
    
    # Associate the DeviceZabbixConfig instance with the job
    associate_instance_with_job( ctx.job, zabbix_config )

    return { "message": f"Created {ctx.obj.name} with {mapping.name} mapping", "data": payload }



#-------------------------------------------------------------------------------
# Update Zabbix Host
# ------------------------------------------------------------------------------


def device_update_zabbix_host( zabbix_config, user, request_id ):

    if zabbix_config:
        # Fetch current state of the host in Zabbix
        pre_data = get_host_by_id( zabbix_config.hostid )
        
        # Current template IDs in Zabbix (directly assigned to host)
        current_template_ids = set( t["templateid"] for t in pre_data.get( "templates", [] ) )
        
        # Templates currently assigned in NetBox
        new_template_ids = set( str(tid) for tid in zabbix_config.templates.values_list( "templateid", flat=True ) )
        
        # Only remove templates that are no longer assigned
        removed_template_ids = current_template_ids - new_template_ids
        
        templates_clear = [ {"templateid": tid} for tid in removed_template_ids ]

        payload = build_payload( zabbix_config )
        if len (templates_clear ) > 0:
            payload["templates_clear"] = templates_clear

        try:
            update_host( **payload )
        except Exception as e:
            raise ExceptionWithData( e, pre_data=pre_data, post_data=payload )

        # Add  a change log entry for the update
        changelog_update( zabbix_config, user, request_id )
        
        return { 
            "message":   f"Updated Zabbix host {zabbix_config.hostid}", 
            "pre_data":  pre_data, 
            "post_data": payload 
        }


#-------------------------------------------------------------------------------
# Delete Zabbix Host
# ------------------------------------------------------------------------------


def delete_zabbix_host( hostid ):

    if hostid:
        try:
            data = get_host_by_id( hostid )
            delete_host( hostid )
            return { "message": f"Deleted zabbix host {hostid}", "data": data }
        except Exception as e:
            msg = f"Failed to delete zabbix host {hostid}: {str( e )}"
            raise Exception( msg )


#-------------------------------------------------------------------------------
# Import Zabbix Settings
# ------------------------------------------------------------------------------


def import_zabbix_settings():
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


#-------------------------------------------------------------------------------
# Jobs
# ------------------------------------------------------------------------------


def require_kwargs(kwargs, *required):
    """
    Retrieve required arguments from a kwargs dict.

    Raises a ValueError if any required argument is missing or None.

    Returns:
        - Single value if only one argument is requested.
        - Tuple of values if multiple arguments are requested.
    """
    values = []
    for arg in required:
        if arg not in kwargs or kwargs[arg] is None:
            raise ValueError(f"Missing required argument '{arg}'.")
        values.append(kwargs[arg])
    
    if len(values) == 1:
        return values[0]
    return tuple(values)


class ValidateDeviceOrVM( AtomicJobRunner ):

    @classmethod
    def run(cls, *args, **kwargs):

        model_instance = require_kwargs( kwargs, "model_instance" )

        try:
            zabbix_host = get_host( model_instance.name )
        except Exception as e:
            logger.error( f"Get Zabbix host '{model_instance.name}' failed: {str( e ) }" )
            raise ValueError( e )
        
        try:
            return validate_zabbix_host( zabbix_host, model_instance )
        except Exception as e:
            logger.error( f"Validating '{model_instance.name}' failed: {str( e ) }" )
            raise ValueError( e )

    @classmethod
    def run_job(cls, model_instance, request, schedule_at=None, interval=None, immediate=False, name=None):
        
        if not model_instance:
            raise Exception( "Missing required device or virtual machine instance" )
        
        if name is None:
            name = f"Validate {model_instance.name}"

        job_args = {
            "name":           name,
            "schedule_at":    schedule_at,
            "interval":       interval,
            "immediate":      immediate,
            "api_endpoint":   get_zabbix_api_endpoint(),
            "token":          SecretStr(get_zabbix_token()),
            "model_instance": model_instance
        }

        if request:
            job_args["user"]       = request.user
            job_args["request_id"] = request.id
        
        if interval is None:
            netbox_job = cls.enqueue(**job_args)
        else:
            netbox_job = cls.enqueue_once(**job_args)
    
        return netbox_job


class ImportFromZabbix( AtomicJobRunner ):
    """
    A custom NetBox JobRunner implementation to import host data from a
    Zabbix server.

    This job fetches the Zabbix configuration for a device or vm using the
    provided API endpoint and token, and returns the host configuration data. 
    It raises an exception if any required input is missing or if the Zabbix API
    call fails.

    This class also works around a known NetBox bug where `JobRunner.handle()`
    fails to propagate exceptions back to the background task system. By
    extending RaisingJobRunner, this job ensures that job failures are correctly
    marked as errored and reported.
    """

    @classmethod
    def run(cls, *args, **kwargs):

        model_instance = require_kwargs( kwargs, "model_instance" )

        job_args = {
            "model_instance": model_instance,
            "user":           cls.job.user,
            "request_id":     kwargs.get( "request_id" ),
            "job":            cls.job
        }

        try:
            job_args["zabbix_host"] = get_host( model_instance.name )

            # Determine model-specific context
            if isinstance( model_instance, Device):
                job_args["config_model"] = DeviceZabbixConfig
                job_args["agent_interface_model"]  = DeviceAgentInterface
                job_args["snmpv3_interface_model"] = DeviceSNMPv3Interface
                job_args["is_vm"] = False
                
                return import_zabbix_config( ImportContext( **job_args ) )

            elif isinstance( model_instance, VirtualMachine ):
                job_args["config_model"] = VMZabbixConfig
                job_args["agent_interface_model"]  = VMAgentInterface
                job_args["snmpv3_interface_model"] = VMSNMPv3Interface
                job_args["is_vm"] = True

                return import_zabbix_config( ImportContext( **job_args ) )

            else:
                raise TypeError(f"Unsupported object type: {type( model_instance ).__name__}")

        except Exception as e:
            raise e

    @classmethod
    def run_job(cls, model_instance, request, schedule_at=None, interval=None, immediate=False, name=None):

        if not model_instance:
            raise Exception( "Missing required device or virtual machine instance" )
        
        if name is None:
            name = f"Import {model_instance.name}"

        job_args = {
            "name":           name,
            "schedule_at":    schedule_at,
            "interval":       interval,
            "immediate":      immediate,
            "api_endpoint":   get_zabbix_api_endpoint(),
            "token":          SecretStr( get_zabbix_token() ),
            "model_instance": model_instance,
        }

        if request:
            job_args["user"]       = request.user
            job_args["request_id"] = request.id
            

        if interval is None:
            netbox_job = cls.enqueue( **job_args )
        else:
            netbox_job = cls.enqueue_once( **job_args )

        return netbox_job


class ProvisionDeviceAgent( AtomicJobRunner ):
    """
    A NetBox JobRunner to provision a Device with an Agent interface in Zabbix.
    
    This job creates a Zabbix configuration for a Device using the agent
    interface model and registers it in Zabbix.
    """

    @classmethod
    def run(cls, *args, **kwargs):

        job_args = {
            "obj":                   require_kwargs(kwargs, "device"),
            "host_field_name":       "device",
            "zabbix_config_model":   DeviceZabbixConfig,
            "interface_model":       DeviceAgentInterface,
            "interface_name_suffix": "agent",
            "job":                   cls.job,
            "user":                  cls.job.user,
            "request_id":            kwargs.get("request_id"),
            "interface_kwargs_fn":   lambda: {},
            
        }

        try:
            return provision_zabbix_host( ProvisionContext( **job_args ) )
        except Exception as e:
            raise e

    @classmethod
    def run_job(cls, device, request, schedule_at=None, interval=None, immediate=False, name=None):

        if not device:
            raise Exception( "Missing required device instance" )

        if name is None:
            name = f"Provision Agent configuration for {device.name}"

        job_args = {
            "name":         name,
            "schedule_at":  schedule_at,
            "interval":     interval,
            "immediate":    immediate,
            "api_endpoint": get_zabbix_api_endpoint(),
            "token":        SecretStr(get_zabbix_token()),
            "device":       device,
        }
        
        if request:
            job_args["user"]       = request.user
            job_args["request_id"] = request.id
        

        if interval is None:
            netbox_job = cls.enqueue( **job_args )
        else:
            netbox_job = cls.enqueue_once( **job_args )
        
        return netbox_job


class ProvisionDeviceSNMPv3( AtomicJobRunner ):
    """
    A NetBox JobRunner to provision a Device with a SNMPv3 interface in Zabbix.
    
    This job creates a Zabbix configuration for a Device using the SNMPv3
    interface model and registers it in Zabbix.
    """

    @classmethod
    def run(cls, *args, **kwargs):

        snmp_defaults = {
            "securityname":   get_snmpv3_securityname(),
            "authprotocol":   get_snmpv3_authprotocol(),
            "authpassphrase": get_snmpv3_authpassphrase(),
            "privprotocol":   get_snmpv3_privprotocol(),
            "privpassphrase": get_snmpv3_privpassphrase()
        }
        
        job_args = {
            "obj":                   require_kwargs(kwargs, "device"),
            "host_field_name":       "device",
            "zabbix_config_model":   DeviceZabbixConfig,
            "interface_model":       DeviceSNMPv3Interface,
            "interface_name_suffix": "snmpv3",
            "job":                   cls.job,
            "user":                  cls.job.user,
            "request_id":            kwargs.get("request_id"),
            "interface_kwargs_fn":   lambda: snmp_defaults,
            
        }
        
        try:
            return provision_zabbix_host( ProvisionContext( **job_args ) )
        except Exception as e:
            raise e


    @classmethod
    def run_job(cls, device, request, schedule_at=None, interval=None, immediate=False, name=None):

        if not device:
            raise Exception( "Missing required device instance" )

        if name is None:
            name = f"Provision SNMPv3 configuration for {device.name}"
    
        job_args = {
            "name":         name,
            "schedule_at":  schedule_at,
            "interval":     interval,
            "immediate":    immediate,
            "api_endpoint": get_zabbix_api_endpoint(),
            "token":        SecretStr(get_zabbix_token()),
            "device":       device,
        }
        if request:
            job_args["user"]       = request.user
            job_args["request_id"] = request.id
            
        if interval is None:
            netbox_job = cls.enqueue( **job_args )
        else:
            netbox_job = cls.enqueue_once( **job_args )
        
        return netbox_job


class ImportZabbixSetting( AtomicJobRunner ):

    @classmethod
    def run(cls, *args, **kwargs):
        try:
            return import_zabbix_settings()
        except Exception as e:
            msg = f"Failed to import zabbix settings: { str( e ) }"
            logger.error( msg )
            raise Exception( msg )
    
    @classmethod
    def run_job(cls, user=None, schedule_at=None, interval=None, immediate=False, name=None):
        if name is None:
            name = f"Zabbix Sync"

        job_args = {
            "name": name,
            "schedule_at": schedule_at,
            "interval": interval,
            "immediate": immediate,
            "user": user,
            "api_endpoint": get_zabbix_api_endpoint(),
            "token": SecretStr( get_zabbix_token() ),
        }

        if interval is None:
            netbox_job = cls.enqueue( **job_args )
        else:
            netbox_job = cls.enqueue_once( **job_args )

        return netbox_job


class DeviceUpdateZabbixHost( AtomicJobRunner ):

    @classmethod
    def run(cls, *args, **kwargs):

        device_name, device_zabbix_config = require_kwargs( kwargs, "device_name", "device_zabbix_config" )

        # Optional arguments
        user = kwargs.get( "_user", None )
        request_id = kwargs.get( "request_id", None )
        

        try:
            return device_update_zabbix_host( device_zabbix_config, user, request_id )
        except Exception as e:
            msg = f"Failed update Zabbix host for device '{device_name}': { str( e ) }"
            logger.error( msg )
            if hasattr( e, "data" ):
                data = getattr( e, "data", "")
                raise ExceptionWithData( e, data )
            else:
                raise Exception( e )

    @classmethod
    def run_job(cls, device_name, device_zabbix_config, user, request_id, schedule_at=None, interval=None, immediate=False, name=None):
        # TODO: Add parameter checks here
        
        if name is None:
            name = f"Update device {device_name}"

        job_args = {
            "name":                 name,
            "instance":             device_zabbix_config,
            "schedule_at":          schedule_at,
            "interval":             interval,
            "immediate":            immediate,
            "user":                 user,
            "_user":                user, # This user instance is required to add the zabbix configuration to the change log
            "request_id":           request_id,
            "api_endpoint":         get_zabbix_api_endpoint(),
            "token":                SecretStr(get_zabbix_token()),
            "device_name":          device_name,
            "device_zabbix_config": device_zabbix_config,
        }
        
        if interval is None:
            netbox_job = cls.enqueue( **job_args )
        else:
            netbox_job = cls.enqueue_once( **job_args )
        
        return netbox_job


class DeleteZabbixHost( AtomicJobRunner ):
    @classmethod
    def run(cls, *args, **kwargs):

        hostid = require_kwargs( kwargs, "hostid" )

        try:
            return delete_zabbix_host( hostid )
        except Exception as e:
            msg = f"{ str( e ) }"
            logger.error( msg )
            raise Exception( msg )

    @classmethod
    def run_job(cls, hostid, user=None, schedule_at=None, interval=None, immediate=False, name=None):
        if name is None:
            name = f"Delete Zabbix host '{hostid}'" 
        
        job_args = {
                    "name": name,
                    "schedule_at": schedule_at,
                    "interval": interval,
                    "immediate": immediate,
                    "user": user,
                    "api_endpoint": get_zabbix_api_endpoint(),
                    "token": SecretStr(get_zabbix_token()),
                    "hostid": hostid,
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
    class Meta:
        name = "Import Zabbix System Job"
    
    @classmethod
    def run(cls, *args, **kwargs):
        try:
            return import_zabbix_settings()
        except Exception as e:
            msg = f"Failed to import zabbix settings: { str( e ) }"
            logger.error( msg )
            raise Exception( msg )
        
    @classmethod
    def schedule(cls, interval=None):
        
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
            "api_endpoint": get_zabbix_api_endpoint(),
            "token":        SecretStr( get_zabbix_token() ),
        }

        job = cls.enqueue_once( **job_args )
        logger.error( f"Scheduled new system job '{name}' with interval {interval}" )
        return job





# end