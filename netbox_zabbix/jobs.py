from django.utils.text import slugify

from ipam.models import IPAddress
from dcim.models import Device
from virtualization.models import VirtualMachine

import netaddr
import json
from typing import Union

# NetBox Zabbix Imports
from netbox_zabbix.job import AtomicJobRunner
from netbox_zabbix.zabbix import get_host
from netbox_zabbix.models import DeviceAgentInterface, Template, DeviceHost, StatusChoices



import logging

logger = logging.getLogger('netbox.plugins.netbox_zabbix')

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


def validate_zabbix_host(zabbix_host, host: Union[Device, VirtualMachine]):
    """ 
    Validates that the given Zabbix host data matches the corresponding
    NetBox resource.
    
    This method checks the following:
    1. The hostname in Zabbix matches the name of the NetBox resource.
    2. All Zabbix templates assigned to the host exist in NetBox.
    3. All IP addresses and DNS names defined in Zabbix interfaces are present
       on the NetBox resource's interfaces.
    
    Args:
        zabbix_host (dict): The host data retrieved from the Zabbix API, including
            host details, parent templates, and interfaces.

        host (Device or VirtualMachine): The NetBox resource object to validate
        against, which must have a `name` attribute and related interfaces with
        IP addresses.

    Raises:
        Exception: If there is a mismatch in hostnames, missing templates, or
        unmatched IP addresses or DNS names between Zabbix and NetBox.
    
    Returns:
        bool: True if validation passes without exceptions.
    """


    # Todo - add check for the interface type to make sure it is either 1 (agent) or 0 (snmp)

    # Validate hostname
    name = zabbix_host.get( "host", "" )
    if host.name != name:
        raise Exception( f"NetBox host name '{host.name}' does not match Zabbix host name '{name}'." )


    # Validate that the templates exist in NetBox
    for template in zabbix_host.get( "parentTemplates", [] ):
        template_id = template.get( "templateid" )
        template_name = template.get( "name" )
        if not Template.objects.filter( templateid=template_id ).exists():
            raise Exception( f"Template {template_name} with ID {template_id} not found in NetBox" )

    # Build NetBox IP and DNS sets
    netbox_ip_set = set()
    netbox_dns_set = set()

    # Helper to get interfaces for Device or VirtualMachine
    def get_interfaces(obj):
        # Both Device and VirtualMachine have an interfaces manager
        return obj.interfaces.all()
    
    for iface in get_interfaces(host):
        addresses = IPAddress.objects.filter(interface=iface.id)
        for addr in addresses:
            if addr.address:
                netbox_ip_set.add( str( netaddr.IPAddress( addr.address.ip ) ) )
            if addr.dns_name:
                netbox_dns_set.add( addr.dns_name.lower() )

    # Build Zabbix IP and DNS sets based on useip
    zabbix_ip_set = {
        iface["ip"]
        for iface in zabbix_host.get( "interfaces", [] )
        if int( iface.get( "useip", -1 ) ) == 1 and iface.get( "ip" )
    }
    zabbix_dns_set = {
        iface["dns"].lower()
        for iface in zabbix_host.get( "interfaces", [] )
        if int( iface.get( "useip", -1 ) ) == 0 and iface.get( "dns" )
    }

    # Set comparison
    unmatched_ips = zabbix_ip_set - netbox_ip_set
    unmatched_dns = zabbix_dns_set - netbox_dns_set

    if unmatched_ips:
        ip_list = ", ".join(sorted(unmatched_ips))
        label = "IP" if len(unmatched_ips) == 1 else "IPs"
        raise Exception( f"{label} {ip_list} not found in NetBox for '{host.name}'" )

    if unmatched_dns:
        dns_list = ", ".join(sorted(unmatched_dns))
        label = "DNS name" if len(unmatched_dns) == 1 else "DNS names"
        raise Exception( f"{label} {dns_list} not found in NetBox for '{host.name}'" )

    return True


def create_device_host(zabbix_host, device):

    # Does the device host already exists?
    if DeviceHost.objects.filter( device=device ).exists():
        raise Exception( f"Device host for '{device.name}' already exists" )

    # Get the 'device'
    try:
        device = Device.objects.get( name=device.name )
    except Exception as e:
        raise Exception( f"No device named {device.name} found in NetBox, error {str(e)}" )

    logger.info( f"Create device host for {device.name}")

    # Create the 'Device Host'
    device_host = DeviceHost(device=device)

    # Zabbix host id
    zabbix_host_id = int( zabbix_host.get( "hostid", 0 ) )
    device_host.zabbix_host_id = zabbix_host_id
    
    logger.info( f"Create device host for {device.name} adding zabbix_host_id {zabbix_host_id}")

    # Is the host monitored or not - default to 0 monitored
    status = int( zabbix_host.get( "status", 0 ) )
    device_host.status = StatusChoices.DISABLED if status else StatusChoices.ENABLED

    logger.info( f"Create device host for {device.name} setting status to {StatusChoices.DISABLED if status else StatusChoices.ENABLED}")
    
    # Before templates can be added the host has to have an id, hence the save here
    device_host.save()
    
    # Add templates
    for template in zabbix_host.get( "parentTemplates", [] ):
        template_name = template.get( "name", "" )
        if template_name != "":
            try:
                template = Template.objects.get( name=template_name )
                device_host.templates.add( template )
                logger.info( f"Create device host for {device.name} adding template {template}" )
            except Exception as e:
                raise Exception( f"No template named {template_name} in NetBox. {str(e)}" )
    
    # Add interfaces
    for interface in zabbix_host.get( "interfaces", [] ):

        if interface["type"] == "1":   # Agent
            print( f"{interface=}" )

            # Look up the IPAddress object in NetBox

            # 1. Use the ip if it exists

            # 2. Use the dns name.

            #DeviceAgentInterface()

        elif interface["type"]  == "2": # SNMP
            print( f"{interface=}" )
        else:
            raise Exception( f"Unsupported Zabbix interface {interface["type"]}" )


    # Save the host
    device_host.save()
    logger.info( f"Saved device host with id {device_host.id} for {device.name}" )

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
        api_endpoint = kwargs.get("api_endpoint")
        token = kwargs.get("token")
        device = kwargs.get("device")
        
        if not all( [api_endpoint, token, device] ):
            raise ValueError("Missing required arguments: api_endpoint, token, or device.")        

        try:
            zbx_host = get_host( api_endpoint, token, device.name )
            validate_zabbix_host( zbx_host, device )
            create_device_host ( zbx_host, device )
            
        except Exception as e:
            raise e
        
        return ""
    
    @classmethod
    def run_job(self, api_endpoint, token, device, user, schedule_at=None, interval=None, immediate=False):
        name = slugify( f"ZBX Import {device.name}" )
        if interval is None:
            netbox_job = self.enqueue( name=name, 
                                schedule_at=schedule_at, 
                                interval=interval, 
                                immediate=immediate, 
                                user=user, 
                                api_endpoint=api_endpoint, 
                                token=SecretStr(token), 
                                device=device )
        else:
            netbox_job = self.enqueue_once( name=name, 
                                     schedule_at=schedule_at, 
                                     interval=interval, 
                                     immediate=immediate, 
                                     user=user, 
                                     api_endpoint=api_endpoint, 
                                     token=SecretStr(token), 
                                     device=device )
                
        return netbox_job