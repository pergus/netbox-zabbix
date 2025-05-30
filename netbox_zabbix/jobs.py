from django.utils.text import slugify

from ipam.models import IPAddress
from dcim.models import Device, Interface as DeviceInterface
from virtualization.models import VirtualMachine, VMInterface

import netaddr
from typing import Union

# NetBox Zabbix Imports
from netbox_zabbix.job import AtomicJobRunner
from netbox_zabbix.zabbix import get_host
from netbox_zabbix.models import DeviceZabbixConfig, DeviceAgentInterface, VMZabbixConfig, VMAgentInterface, Template, StatusChoices
from netbox_zabbix.config import get_zabbix_api_endpoint, get_zabbix_token
from netbox_zabbix.logger import logger

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
    return {
        **iface,
        "type": int(iface["type"]),
        "useip": int(iface["useip"]),
        "available": int(iface["available"]),
        "main": int(iface["main"]),
        "port": int(iface["port"]),
        "interfaceid": int(iface["interfaceid"]),
    }


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

    # Determine the correct IPAddress foreign key field based on host type
    ip_field = "interface" if isinstance(host, Device) else "vminterface"
    

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


def create_zabbix_config(zabbix_host: dict, instance, config_model, agent_interface_model, interface_model, is_vm: bool = False):
    """
    Generic helper to create a ZabbixConfig for either a Device or VirtualMachine.
    """
    try:
        validate_zabbix_host( zabbix_host, instance )
    except Exception as e:
        raise Exception( f"validation failed: {str(e)}" )

    # Map the instance type to its field name on the config model
    instance_type = "virtual_machine" if is_vm else "device"
    

    # Ensure config doesn't already exist
    if config_model.objects.filter( **{instance_type: instance} ).exists():
        raise Exception( f"Zabbix config for '{instance.name}' already exists" )

    logger.info( f"Creating Zabbix config for {instance.name}" )

    # Create config instance
    config = config_model( **{instance_type: instance} )
    config.hostid = int( zabbix_host["hostid"] )
    config.status = StatusChoices.DISABLED if int( zabbix_host.get( "status", 0 ) ) else StatusChoices.ENABLED
    config.full_clean()
    config.save()

    # Add templates
    for template in zabbix_host.get( "parentTemplates", [] ):
        template_name = template.get( "name", "" )
        if template_name:
            template_obj = Template.objects.get( name=template_name )
            config.templates.add( template_obj )
            logger.info( f"Added template '{template_name}' to {instance.name}" )

    # Add interfaces
    for iface in map( normalize_interface, zabbix_host.get( "interfaces", [] ) ):

        # Resolve IP address
        if iface["useip"] == 1 and iface["ip"]:
            # Since it isn't possible to use CIDR notation when specifying
            # the IP address in Zabbix and NetBox require a CIDR when
            # searching for an IP, the CIDR /24 is added to the Zabbix IP.
            address = f"{iface['ip']}/23"
            nb_ip_address = IPAddress.objects.get( address=address )

        elif iface["useip"] == 0 and iface["dns"]:
            nb_ip_address = IPAddress.objects.get( dns_name=iface["dns"] )

        else:
            raise Exception( f"Cannot resolve IP for Zabbix interface {iface['interfaceid']}" )

        # Resolve the NetBox interface
        if is_vm:
            nb_interface = VMInterface.objects.get( id=nb_ip_address.assigned_object_id )
        else:
            nb_interface = DeviceInterface.objects.get( id=nb_ip_address.assigned_object_id )

        #nb_interface = interface_model.objects.get( id=nb_ip_address.assigned_object_id )

        if iface["type"] == 1:  # Agent
            agent_iface = agent_interface_model.objects.create(
                name=f"{instance.name}-agent",
                hostid=config.hostid,
                interfaceid=iface["interfaceid"],
                available=iface["available"],
                useip=iface["useip"],
                main=iface["main"],
                port=iface["port"],
                host=config,
                interface=nb_interface,
                ip_address=nb_ip_address,
            )
            agent_iface.full_clean()
            agent_iface.save()
            logger.info( f"Added AgentInterface for {instance.name} using IP {nb_ip_address}" )

        elif iface["type"] == 2:
            logger.info( f"Skipping SNMP interface: {iface}" )
        else:
            raise Exception( f"Unsupported Zabbix interface type {iface['type']}" )


def create_device_zabbix_config(zabbix_host: dict, device: Device):
    create_zabbix_config(
        zabbix_host,
        instance=device,
        config_model=DeviceZabbixConfig,
        agent_interface_model=DeviceAgentInterface,
        interface_model=DeviceInterface,
        is_vm=False
    )

def create_vm_zabbix_config(zabbix_host: dict, vm: VirtualMachine):
    create_zabbix_config(
        zabbix_host,
        instance=vm,
        config_model=VMZabbixConfig,
        agent_interface_model=VMAgentInterface,
        interface_model=VMInterface,
        is_vm=True
    )


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

    def run(self, *args, **kwargs):
        device_or_vm = kwargs.get("device_or_vm")

        if not device_or_vm:
            raise ValueError("Missing required argument: device_or_vm.")

        try:
            zbx_host = get_host( device_or_vm.name )
            
            # Call appropriate create function based on type
            if isinstance( device_or_vm, Device):
                create_device_zabbix_config( zbx_host, device_or_vm )
            elif isinstance( device_or_vm, VirtualMachine ):
                create_vm_zabbix_config( zbx_host, device_or_vm )
            else:
                raise TypeError(f"Unsupported object type: {type(device_or_vm).__name__}")
            
        except Exception as e:
            raise e
        
        return f"imported {device_or_vm.name} from Zabbix to NetBox"

    @classmethod
    def run_job(cls, device_or_vm, user, schedule_at=None, interval=None, immediate=False):
        name = slugify(f"ZBX Import {device_or_vm.name}")
        job_args = {
            "name": name,
            "schedule_at": schedule_at,
            "interval": interval,
            "immediate": immediate,
            "user": user,
            "api_endpoint": get_zabbix_api_endpoint(),
            "token": SecretStr(get_zabbix_token()),
            "device_or_vm": device_or_vm,
        }

        if interval is None:
            netbox_job = cls.enqueue(**job_args)
        else:
            netbox_job = cls.enqueue_once(**job_args)

        return netbox_job
