"""
NetBox Zabbix Plugin — Validation and Compatibility Checks

This module provides validation routines used to ensure that Zabbix host
definitions are compatible with the corresponding NetBox objects before any
synchronization or import operations occur.

It includes:

- Full validation of Zabbix host data against NetBox devices/VMs
- Verification of template existence and compatibility
- Interface-level validation, including IP/DNS resolution, type checks,
  duplication detection, and NetBox interface mapping
- Lightweight validations used by streamlined workflows such as Quick Add

These checks ensure data integrity and prevent invalid or inconsistent Zabbix
configurations from being imported into NetBox.
"""


# Standard library
from typing import Union

# Third-party imports
import netaddr

# NetBox imports
from dcim.models import Device
from virtualization.models import VirtualMachine
from ipam.models import IPAddress

# NetBox Zabbix Imports
from netbox_zabbix import models


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
        if not models.Template.objects.filter( templateid=template_id ).exists():
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


def validate_quick_add( host ):
    """
    Validate a host before performing a Quick Add operation.
    
    Args:
        host: Device or VM instance.
    
    Raises:
        Exception: If primary IP or DNS name is missing.
    """
    if not host.primary_ip4_id:
        raise Exception( f"{host.name} is missing Primary IPv4 address." )
    if not host.primary_ip.dns_name:
        raise Exception( f"{host.name} is missing DNS name." )

