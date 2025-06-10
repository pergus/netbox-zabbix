from django.utils.text import slugify
from django.db import transaction

from ipam.models import IPAddress
from dcim.models import Device, Interface as DeviceInterface, Platform, DeviceRole
from virtualization.models import VirtualMachine, VMInterface

import netaddr
from typing import Union

# NetBox Zabbix Imports
from netbox_zabbix.job import AtomicJobRunner
from netbox_zabbix.zabbix import get_host
from netbox_zabbix.models import DeviceSNMPv3Interface, DeviceZabbixConfig, DeviceAgentInterface, VMSNMPv3Interface, VMZabbixConfig, VMAgentInterface, Template, StatusChoices
from netbox_zabbix.config import get_zabbix_api_endpoint, get_zabbix_token, get_default_cidr
from netbox_zabbix.logger import logger


#-------------------------------------------------------------------------------
# Helper Classes and Functions 
#

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
    if not isinstance(details, dict):
        details = {}

    base = {
            **iface,
            "type": int( iface["type"] ),
            "useip": int( iface["useip"] ),
            "available": int(iface["available"] ),
            "main": int( iface["main"] ),
            "port": int( iface["port"] ),
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
            "snmp_version":         int( details.get("version", "0") ),
            "snmp_bulk":            int( details.get("bulk", "1") ),
            "snmp_max_repetitions": int( details.get("max_repetitions", "10") ),
            "snmp_securityname":    details.get("securityname", ""),
            "snmp_securitylevel":   int( details.get("securitylevel", "0") ),
            "snmp_authpassphrase":  details.get("authpassphrase", ""),
            "snmp_privpassphrase":  details.get("privpassphrase", ""),
            "snmp_authprotocol":    int( details.get("authprotocol", "") ),
            "snmp_privprotocol":    int( details.get("privprotocol", "") ),
            "snmp_contextname":     details.get("contextname", ""),
        })

    # These are not implemented!
    elif version == 2:    
        base.update({
            # SNMPv2c
            "snmp_version":         int( details.get("version", "0") ),
            "snmp_bulk":            int( details.get("bulk", "0") ),
            "snmp_max_repetitions": int( details.get("max_repetitions", "0") ),
            "snmp_community":       details.get("snmp_community", ""),
        })
    
    elif version == 1:    
        base.update({
            # SNMPv1
            "snmp_version":   int( details.get("version", "0") ),
            "snmp_bulk":      int( details.get("bulk", "0") ),
            "snmp_community": details.get("snmp_community", ""),
        })
    else:
        pass

    return base


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
    if isinstance(host, Device):
        if hasattr(host, 'devicezabbixconfig') and host.devicezabbixconfig is not None:
            raise Exception(f"Device '{host.name}' already has a DeviceZabbixConfig associated")
    else:  # VirtualMachine
        if hasattr(host, 'vmzabbixconfig') and host.vmzabbixconfig is not None:
            raise Exception(f"VM '{host.name}' already has a VMZabbixConfig associated")
    
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
        
        
    return True


def import_zabbix_config(zabbix_host: dict, instance, config_model, agent_interface_model, snmpv3_interface_model, interface_model, is_vm: bool = False):
    """
    Generic helper to create Device or VirtualMachine Zabbix Configation from
    a Zabbix Host configuration
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
            # searching for an IP, a configuratbe CIDR is added to the Zabbix IP.
            cidr = get_default_cidr()
            address = f"{iface['ip']}{cidr}"
            logger.info( f"Looking up {address=}" )
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
        
         
        if iface["type"] == 1:  # Agent
            try:
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
            except Exception as e:
                raise Exception( f"Failed to create agent interface for '{instance.name}', reason: {str( e )}" )

        elif iface["type"] == 2 and iface["snmp_version"] == 3:
            try:
                snmpv3_iface = snmpv3_interface_model.objects.create(
                    name=f"{instance.name}-snmpv3",
                    hostid=config.hostid,
                    interfaceid=iface["interfaceid"],
                    available=iface["available"],
                    useip=iface["useip"],
                    main=iface["main"],
                    port=iface["port"],
                    host=config,
                    interface=nb_interface,
                    ip_address=nb_ip_address,

                    # SNMPv3 details
                    snmp_version=iface["snmp_version"],
                    snmp_bulk=iface["snmp_bulk"],
                    snmp_max_repetitions=iface["snmp_max_repetitions"],
                    snmp_securityname=iface["snmp_securityname"],
                    snmp_securitylevel=iface["snmp_securitylevel"],
                    snmp_authpassphrase=iface["snmp_authpassphrase"],
                    snmp_privpassphrase=iface["snmp_privpassphrase"],
                    snmp_authprotocol=iface["snmp_authprotocol"],
                    snmp_privprotocol=iface["snmp_privprotocol"],
                    snmp_contextname=iface["snmp_contextname"],
                )
                snmpv3_iface.full_clean()
                snmpv3_iface.save()
                logger.info( f"Added SNMPv3tInterface for {instance.name} using IP {nb_ip_address}" )
            except Exception as e:
                raise Exception( f"Failed to create snmpv3 interface for '{instance.name}', reason: {str( e )}" )
        else:
            raise Exception( f"Unsupported Zabbix interface type {iface['type']}" )


def import_device_config(zabbix_host: dict, device: Device):
    import_zabbix_config(
        zabbix_host,
        instance=device,
        config_model=DeviceZabbixConfig,
        agent_interface_model=DeviceAgentInterface,
        snmpv3_interface_model=DeviceSNMPv3Interface,
        interface_model=DeviceInterface,
        is_vm=False
    )


def import_vm_config(zabbix_host: dict, vm: VirtualMachine):
    import_zabbix_config(
        zabbix_host,
        instance=vm,
        config_model=VMZabbixConfig,
        agent_interface_model=VMAgentInterface,
        snmpv3_interface_model=VMSNMPv3Interface,
        interface_model=VMInterface,
        is_vm=True
    )


def build_zabbix_host_payload_from_config(zcfg: DeviceZabbixConfig) -> dict:
    """
    Build a Zabbix API-compatible payload for creating a host from a DeviceZabbixConfig.

    Args:
        zcfg (DeviceZabbixConfig): Zabbix config object linked to a NetBox device.

    Returns:
        dict: JSON payload for Zabbix API `host.create`

    Raises:
        Exception: If required fields like device, agent interface, or templates are missing.
    """
    device = zcfg.device

    if not device:
        raise Exception("Zabbix config is not linked to a device.")

    # 1. Host name
    host_name = zcfg.get_name()

    # 2. Interfaces
    interfaces = []

    for agent_iface in zcfg.agent_interfaces.all():
        interfaces.append({
            "type": 1,  # Zabbix Agent
            "main": agent_iface.main,
            "useip": agent_iface.useip,
            "ip": str(agent_iface.resolved_ip_address.address.ip) if agent_iface.resolved_ip_address else "",
            "dns": agent_iface.resolved_dns_name or "",
            "port": str(agent_iface.port),
        })

    for snmp_iface in zcfg.snmpv3_interfaces.all():
        interfaces.append({
            "type": 2,  # SNMP
            "main": snmp_iface.main,
            "useip": snmp_iface.useip,
            "ip": str(snmp_iface.resolved_ip_address.address.ip) if snmp_iface.resolved_ip_address else "",
            "dns": snmp_iface.resolved_dns_name or "",
            "port": str(snmp_iface.port),
        })

    if not interfaces:
        raise Exception(f"No interfaces defined for host '{host_name}'")

    # 3. Templates
    templates = zcfg.templates.all()
    if not templates:
        raise Exception(f"No templates assigned to host '{host_name}'")

    template_list = [{ "templateid": t.templateid } for t in templates]

    # 4. Groups (REQUIRED by Zabbix). Adjust this to dynamically assign based on site/role/etc.
    # For now, use a default group ID (replace this with real logic or lookup)
    group_list = [{ "groupid": "1" }]

    return {
        "host": host_name,
        "interfaces": interfaces,
        "groups": group_list,
        "templates": template_list,
    }


# The string "agent_default_templates" should be in Config
def device_quick_add_agent(device):
    """
    Automatically creates a Zabbix configuration and agent interface for the given NetBox device.
    
    Steps:
    - Creates a DeviceZabbixConfig object with ENABLED status.
    - Adds default agent templates from the platform and role (via custom fields).
    - Uses the device's primary IPv4 address to create a DeviceAgentInterface.
    
    Requirements:
    - The device must have a primary IPv4 address.
    - The platform and role must exist and (optionally) define 'agent_default_templates' in custom fields.
    
    Raises:
        Exception: If any step fails due to missing data or validation errors.
    """
    # Note:
    # The Zabbix host ID (zcfg.hostid) and interface ID (iface.interfaceid)
    # are not available at this stage—they will be set after the corresponding
    # host and interface are created in Zabbix.

    zcfg = DeviceZabbixConfig( device=device, status=StatusChoices.ENABLED )

    try:
        zcfg.full_clean()
        zcfg.save()
    except Exception as e:
        raise Exception(f"Failed to create Zabbix configuration: {e}")

    def add_templates_from(source, label):
        if not source:
            raise Exception(f"Unable to find {label} for device '{device.name}'")

        for tmpl in source.cf.get("agent_default_templates") or []:
            zcfg.templates.add(Template.objects.get(name=tmpl.name))

    add_templates_from(device.platform, "platform")
    add_templates_from(device.role, "role")


    ip = device.primary_ip4
    if ip is None:
        raise Exception(f"Device '{device.name}' does not have a primary IPv4 address set")
    
    interface = ip.assigned_object
    iface = DeviceAgentInterface( name=f"{device.name}-agent", host=zcfg, interface=interface, ip_address=ip )

    try:
        iface.full_clean()
        iface.save()
    except Exception as e:
        raise Exception(f"Failed to create agent interface: {e}")
    
    try:
        payload = build_zabbix_host_payload_from_config( zcfg )
    except Exception as e:
        raise Exception(f"Failed to create zabbix host payload: {e}")

    logger.info( f"{payload}" )


#-------------------------------------------------------------------------------
# Jobs
#

class ValidateDeviceOrVM( AtomicJobRunner ):

    @classmethod
    def run(cls, *args, **kwargs):
        device_or_vm = kwargs.get( "device_or_vm" )
        if not device_or_vm:
            raise ValueError( "Missing required argument: device_or_vm." )
        try:
            zabbix_host = get_host( device_or_vm.name )
        except Exception as e:
            logger.info( f"get zabbix host '{device_or_vm.name}' failed: {str( e ) }" )
            raise ValueError( e )
        
        try:
            validate_zabbix_host( zabbix_host, device_or_vm )
        except Exception as e:
            logger.info( f"validating '{device_or_vm.name}' failed: {str( e ) }" )
            raise ValueError( e )
        
        logger.info( f"'{device_or_vm.name}' is valid" )
        return f"'{device_or_vm.name}' is valid"

    @classmethod
    def run_job(cls, device_or_vm, user, schedule_at=None, interval=None, immediate=False):
        name = slugify(f"ZBX Validate {device_or_vm.name}")
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
        device_or_vm = kwargs.get( "device_or_vm" )

        if not device_or_vm:
            raise ValueError( "Missing required argument: device_or_vm." )

        try:
            zbx_host = get_host( device_or_vm.name )
            
            # Call appropriate create function based on type
            if isinstance( device_or_vm, Device):
                import_device_config( zbx_host, device_or_vm )
            elif isinstance( device_or_vm, VirtualMachine ):
                import_vm_config( zbx_host, device_or_vm )
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


class DeviceQuickAddAgent( AtomicJobRunner ):

    @classmethod
    def run(cls, *args, **kwargs):
        device = kwargs.get( "device" )

        if not device:
            raise ValueError( "Missing required argument: device." )
        
        try:
            device_quick_add_agent( device )
        except Exception as e:
            msg = f"Failed to create Zabbix configuration for device '{device.name}': { str( e ) }"
            logger.info( msg )
            raise Exception( msg )
        
        return f"Created Zabbix configuration and agent interface for device '{device.name}'"
            
    @classmethod
    def run_job(cls, device, user, schedule_at=None, interval=None, immediate=False):

        name = slugify(f"ZBX Device Quick Add Agent {device.name}")
        
        job_args = {
                    "name": name,
                    "schedule_at": schedule_at,
                    "interval": interval,
                    "immediate": immediate,
                    "user": user,
                    "api_endpoint": get_zabbix_api_endpoint(),
                    "token": SecretStr(get_zabbix_token()),
                    "device": device,
                }
        
        if interval is None:
            netbox_job = cls.enqueue(**job_args)
        else:
            netbox_job = cls.enqueue_once(**job_args)
        
        return netbox_job