from django.utils.text import slugify

from ipam.models import IPAddress
from dcim.models import Device, Interface
from virtualization.models import VirtualMachine

import netaddr
from typing import Union

# NetBox Zabbix Imports
from netbox_zabbix.job import AtomicJobRunner
from netbox_zabbix.zabbix import get_host
from netbox_zabbix.models import DeviceZabbixConfig, DeviceAgentInterface, Template, StatusChoices
from netbox_zabbix.config import get_zabbix_api_endpoint, get_zabbix_token
from netbox_zabbix.logger import logger



def validate_zabbix_host(zabbix_host: dict, host: Union[Device, VirtualMachine]) -> bool:
    """
    Validates the given Zabbix host data against the NetBox host.

    This includes:
    - Host name match
    - Existence of all Zabbix templates in NetBox
    - Interfaces are of supported type (1=Agent, 2=SNMP)
    - IPs/DNS names on interfaces exist in NetBox and resolve to IPAddress + Interface

    Args:
        zabbix_host (dict): Host dict from Zabbix API.
        host (Device | VirtualMachine): NetBox object.

    Raises:
        Exception: On any validation failure.
    """

    # 1. Validate hostname
    zabbix_name = zabbix_host.get( "host", "" )
    if host.name != zabbix_name:
        raise Exception( f"NetBox host name '{host.name}' does not match Zabbix host name '{zabbix_name}'" )

    # 2. Validate templates
    for tmpl in zabbix_host.get( "parentTemplates", [] ):
        template_id = tmpl.get( "templateid" )
        template_name = tmpl.get( "name" )
        if not Template.objects.filter( templateid=template_id ).exists():
            raise Exception( f"Template '{template_name}' (ID {template_id}) not found in NetBox" )

    # 3. Validate interfaces
    valid_interface_types = {1, 2}  # 1 = Agent, 2 = SNMP

    netbox_ips = {
        str(netaddr.IPAddress(ip.address.ip)): ip
        for iface in host.interfaces.all()
        for ip in IPAddress.objects.filter(interface=iface)
        if ip.address
    }
    netbox_dns = {
        ip.dns_name.lower(): ip
        for iface in host.interfaces.all()
        for ip in IPAddress.objects.filter(interface=iface)
        if ip.dns_name
    }

    for iface in zabbix_host.get( "interfaces", [] ):
        try:
            iface_type = int( iface.get( "type" ) )
            useip = int( iface.get("useip") )
        except (TypeError, ValueError):
            raise Exception( f"Invalid 'type' or 'useip' in interface: {iface}" )

        if iface_type not in valid_interface_types:
            raise Exception( f"Unsupported interface type {iface_type} in Zabbix interface: {iface}" )

        if useip == 1:
            ip = iface.get( "ip" )
            if not ip:
                raise Exception( f"Missing IP address for interface with useip=1: {iface}" )
            if ip not in netbox_ips:
                raise Exception( f"Zabbix interface IP {ip} not found in NetBox for '{host.name}'" )
            # Also confirm the related NetBox Interface exists
            if not netbox_ips[ip].assigned_object_id:
                raise Exception( f"NetBox IP {ip} does not have an assigned interface" )

        elif useip == 0:
            dns = iface.get( "dns", "" ).lower()
            if not dns:
                raise Exception( f"Missing DNS name for interface with useip=0: {iface}" )
            if dns not in netbox_dns:
                raise Exception( f"Zabbix DNS '{dns}' not found in NetBox for '{host.name}'" )
            if not netbox_dns[dns].assigned_object_id:
                raise Exception( f"NetBox DNS '{dns}' does not resolve to a valid interface" )

        else:
            raise Exception( f"Unsupported 'useip' value {useip} in interface: {iface}" )

    return True

def normalize_interface(iface: dict) -> dict:
    """Convert string values in Zabbix interface dict to appropriate types."""
    return {
        **iface,
        "type": int(iface["type"]),
        "useip": int(iface["useip"]),
        "available": int(iface["available"]),
        "main": int(iface["main"]),
        "port": int(iface["port"]),
        "interfaceid": int(iface["interfaceid"]),
    }

def create_device_zabbix_config(zabbix_host: dict, device: Device):
    """
    Creates a ZabbixConfig instance for a given NetBox Device from Zabbix host data.
    Assumes `validate_zabbix_host()` has already passed successfully.
    """

    # Is the Zabbix Host configuration valid?
    try:
        validate_zabbix_host( zabbix_host, device )
    except Exception as e:
        raise Exception( f"validation failed: {str(e)}" )

    # Does the Device Host already exists?
    if DeviceZabbixConfig.objects.filter(device=device).exists():
        raise Exception(f"Device host for '{device.name}' already exists")

    logger.info(f"Creating device host for {device.name}")


    # Create the Device Host
    device_zabbix_config = DeviceZabbixConfig(device=device)

    device_zabbix_config.hostid = int( zabbix_host["hostid"] )
    device_zabbix_config.status = ( StatusChoices.DISABLED if int( zabbix_host.get( "status", 0 ) ) else StatusChoices.ENABLED )

    # Before Templates and Interfaces can be added the host has to have an id,
    # hence the host has to be saved here.
    device_zabbix_config.full_clean()
    device_zabbix_config.save()

    # Add templates
    for template in zabbix_host.get( "parentTemplates", [] ):
        template_name = template.get( "name", "" )
        if template_name:
            template_obj = Template.objects.get( name=template_name )
            device_zabbix_config.templates.add( template_obj )
            logger.info(f"Added template '{template_name}' to device host")

    # Add interfaces
    interfaces = map( normalize_interface, zabbix_host.get( "interfaces", [] ) )

    for iface in interfaces:

        # Get the IP address
        if iface["useip"] == 1 and iface["ip"]:
            # Since it isn't possible to use cidr notation when specifying
            # the IP address in Zabbix and NetBox require a cidr when
            # searching for an IP, the cidr /24 is added to the Zabbix IP.
            address = f"{iface['ip']}/24"
            nb_ip_address = IPAddress.objects.get( address=address )
        elif iface["useip"] == 0 and iface["dns"]:
            nb_ip_address = IPAddress.objects.get( dns_name=iface["dns"] )
        else:
            raise Exception(f"Cannot resolve IP for Zabbix interface {iface['interfaceid']}")
        
        # Get the Interface for the IP address
        nb_interface = Interface.objects.get( id=nb_ip_address.assigned_object_id )
        
        if iface["type"] == 1:  # Agent

            # Create DeviceAgentInterface
            agent_iface = DeviceAgentInterface.objects.create( 
                name=f"{device.name}-agent",
                hostid=device_zabbix_config.hostid,
                interfaceid=iface["interfaceid"],
                available=iface["available"],
                useip=iface["useip"],
                main=iface["main"],
                port=iface["port"],
                host=device_zabbix_config,
                interface=nb_interface,
                ip_address=nb_ip_address,
            )
            agent_iface.full_clean()
            agent_iface.save()
            logger.info(f"Added DeviceAgentInterface for {device.name} using IP {nb_ip_address}")

        elif iface["type"] == 2:  # SNMP (stub)
            logger.info(f"Skipping SNMP interface for now: {iface}")
        else:
            raise Exception(f"Unsupported Zabbix interface type {iface['type']}")


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


class ImportDeviceFromZabbix( AtomicJobRunner ):
    """ 
    A custom NetBox JobRunner implementation to import host data from a
    Zabbix server.

    This job fetches a device's Zabbix configuration using the provided API
    endpoint and token, and returns the host configuration data. It raises an
    exception if any required input is missing or if the Zabbix API call fails.
    
    This class also works around a known NetBox bug where `JobRunner.handle()`
    fails to propagate exceptions back to the background task system. By
    extending RaisingJobRunner, this job ensures that job failures are correctly
    marked as errored and reported.
    
    """

    def run(self, *args, **kwargs):
        device = kwargs.get("device")
        
        if not all( [ device ] ):
            raise ValueError("Missing required arguments: device.")        

        try:
            zbx_host = get_host( device.name )
            create_device_zabbix_config ( zbx_host, device )
            
        except Exception as e:
            raise e
        
        return f"imported {device.name} from Zabbix to NetBox"
    
    @classmethod
    def run_job(self, device, user, schedule_at=None, interval=None, immediate=False):
        name = slugify( f"ZBX Import {device.name}" )
        if interval is None:
            netbox_job = self.enqueue( name=name, 
                                schedule_at=schedule_at, 
                                interval=interval, 
                                immediate=immediate, 
                                user=user, 
                                api_endpoint=get_zabbix_api_endpoint(), 
                                token=SecretStr( get_zabbix_token() ), 
                                device=device )
        else:
            netbox_job = self.enqueue_once( name=name, 
                                     schedule_at=schedule_at, 
                                     interval=interval, 
                                     immediate=immediate, 
                                     user=user, 
                                     api_endpoint=get_zabbix_api_endpoint(), 
                                     token=SecretStr( get_zabbix_token() ), 
                                     device=device )
                
        return netbox_job