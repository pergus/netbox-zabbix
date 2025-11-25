"""
NetBox Zabbix Plugin — Host Import Utilities

This module provides the functionality required to import Zabbix hosts into
NetBox. It defines the `ImportHostContext` dataclass, which encapsulates all
runtime context needed for an import operation, and the `import_zabbix_host`
function, which performs the actual creation of NetBox HostConfig objects.

Functionality includes:

- Validating Zabbix host data before import
- Creating HostConfig objects and linking host groups, templates, and proxies
- Resolving and attaching Agent and SNMP interfaces based on Zabbix definitions
- Mapping Zabbix interface IP/DNS information to NetBox IP address and interface objects
- Creating NetBox changelog entries and associating results with background jobs

These utilities ensure reliable, consistent import of Zabbix host data into
NetBox for both Devices and Virtual Machines.
"""

# Standard library
from typing import Union
from dataclasses import dataclass
from typing import Any

# Django imports
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType


# NetBox imports
from dcim.models import Device, Interface as DeviceInterface
from virtualization.models import VirtualMachine, VMInterface
from ipam.models import IPAddress

# NetBox Zabbix Imports
from netbox_zabbix import models
from netbox_zabbix.zabbix.validation import validate_zabbix_host
from netbox_zabbix.zabbix.interfaces import normalize_interface
from netbox_zabbix.netbox.changelog import log_creation_event
from netbox_zabbix.netbox.jobs import associate_instance_with_job
from netbox_zabbix.helpers import lookup_ip_address
from netbox_zabbix.logger import logger

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
    config              = models.HostConfig( name=f"z-{ctx.obj_instance.name}", content_type=ctx.content_type, object_id=ctx.obj_instance.pk )
    config.hostid       = int( ctx.zabbix_host["hostid"] )
    config.status       = models.StatusChoices.DISABLED if int( ctx.zabbix_host.get( "status", 0 ) ) else models.StatusChoices.ENABLED
    config.monitored_by = int( ctx.zabbix_host.get( "monitored_by" ) )
    config.description  = ctx.zabbix_host.get( "description", "" )

    # Disable signals to prevent trying to create the host in Zabbix.
    config._skip_signal = True

    # Add Proxy - needs to be added before calling config.save()
    proxyid = int( ctx.zabbix_host.get( "proxyid" ) )
    if proxyid:
        try:
            config.proxy = models.Proxy.objects.get( proxyid=proxyid )
        except models.Proxy.DoesNotExist:
            raise Exception(f"Proxy '{proxyid}' not found in NetBox")
    
    # Add Proxy Group - needs to be added before calling config.save()
    proxy_groupid = int( ctx.zabbix_host.get( "proxy_groupid" ) )
    if proxy_groupid > 0:
        try:
            config.proxy_group = models.ProxyGroup.objects.get( proxy_groupid=proxy_groupid )
        except models.ProxyGroup.DoesNotExist:
            raise Exception(f"Proxy group with hostid '{proxy_groupid}' not found in NetBox")

    config.full_clean()
    config.save()
    log_creation_event( config, ctx.user, ctx.request_id )

    # Add Host Groups
    for group in ctx.zabbix_host.get( "groups", [] ):
        group_name = group.get( "name", "" )
        if group_name:
            group_obj = models.HostGroup.objects.get( name=group_name )
            config.host_groups.add( group_obj )


    # Add Templates
    for template in ctx.zabbix_host.get( "parentTemplates", [] ):
        template_name = template.get( "name", "" )
        if template_name:
            template_obj = models.Template.objects.get( name=template_name )
            config.templates.add( template_obj )

    # Add interfaces
    for iface in map( normalize_interface, ctx.zabbix_host.get( "interfaces", [] ) ):
        # Resolve IP address
        if iface["useip"] == 1 and iface["ip"]:
            # Search NetBox for the Zabbix IP
            nb_ip_address = lookup_ip_address( iface['ip'] )

        elif iface["useip"] == 0 and iface["dns"]:
            nb_ip_address = IPAddress.objects.get( dns_name=iface["dns"] )
        else:
            raise Exception( f"Cannot resolve IP for Zabbix interface {iface['interfaceid']}" )

        # Resolve the NetBox interface
        if ctx.content_type == ContentType.objects.get_for_model( VirtualMachine ):
            try:
                nb_interface = VMInterface.objects.get( id=nb_ip_address.assigned_object_id )
            except Exception as e:
                raise 
        else:
            try:
                nb_interface = DeviceInterface.objects.get( id=nb_ip_address.assigned_object_id )
            except Exception as e:
                raise

        if iface["type"] == 1:  # Agent
            try:
                agent_iface = models.AgentInterface.objects.create(
                    name        = f"{ctx.obj_instance.name}-agent",
                    hostid      = config.hostid,
                    interfaceid = iface["interfaceid"],
                    useip       = iface["useip"],
                    main        = iface["main"],
                    port        = iface["port"],
                    host_config = config,
                    interface   = nb_interface,
                    ip_address  = nb_ip_address,
                )
                agent_iface.full_clean()
                agent_iface.save()
                log_creation_event( agent_iface, ctx.user, ctx.request_id )
                logger.debug( f"Added AgentInterface for {ctx.obj_instance.name} using IP {nb_ip_address}" )

            except Exception as e:
                raise Exception( f"Failed to create agent interface for '{ctx.obj_instance.name}', reason: {str( e )}" )

        elif iface["type"] == 2 and iface["version"] == 3:
            try:
                snmp_iface = models.SNMPInterface.objects.create(
                    name        = f"{ctx.obj_instance.name}-snmp",
                    hostid      = config.hostid,
                    interfaceid = iface["interfaceid"],
                    useip       = iface["useip"],
                    main        = iface["main"],
                    port        = iface["port"],
                    host_config = config,
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
                log_creation_event( snmp_iface, ctx.user, ctx.request_id )
                logger.debug( f"Added SNMPInterface for {ctx.obj_instance.name} using IP {nb_ip_address}" )

            except Exception as e:
                raise Exception( f"Failed to create snmp interface for '{ctx.obj_instance.name}', reason: {str( e )}" )
        else:
            raise Exception( f"Unsupported Zabbix interface type {iface['type']}" )


    # Associate the DeviceZabbixConfig instance with the job
    associate_instance_with_job( ctx.job, config )
    
    return { "message": f"imported {ctx.obj_instance.name} from Zabbix to NetBox",  "data": ctx.zabbix_host }
