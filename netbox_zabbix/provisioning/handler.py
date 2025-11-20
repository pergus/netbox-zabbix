
"""
NetBox Zabbix Plugin — Zabbix Host Provisioning Orchestration

This module provides orchestration logic for provisioning and updating 
Zabbix hosts from NetBox objects (Devices or VirtualMachines).

Key functionalities:

- Full provisioning workflow:
    - Create HostConfig for the NetBox object
    - Apply mapping (templates, host groups, proxies, monitored_by)
    - Create interfaces and associate them with the host
    - Create the host in Zabbix
    - Link interfaces in Zabbix
    - Record changelogs and associate the instance with the job

- Partial update workflow for existing HostConfigs:
    - Add new interfaces
    - Update host in Zabbix
    - Link interfaces in Zabbix
    - Save and log updates

The `provision_zabbix_host` function handles errors gracefully,
ensuring partial creations are cleaned up and the job state remains consistent.
"""

# Django imports
from django.contrib.contenttypes.models import ContentType

# NetBox imports
from dcim.models import Device

# NetBox Zabbix plugin imports
from netbox_zabbix.provisioning.context import ProvisionContext
from netbox_zabbix.mapping.resolver import (
      resolve_device_mapping,
      resolve_vm_mapping,
      apply_mapping_to_host_config
)
from netbox_zabbix.netbox.host_config import (
    create_host_config,
    save_host_config, 
)
from netbox_zabbix.netbox.interfaces import (
    create_zabbix_interface
)
from netbox_zabbix.netbox.changelog import log_creation_event
from netbox_zabbix.netbox.jobs import associate_instance_with_job

from netbox_zabbix.zabbix.hosts import create_zabbix_host, update_zabbix_host
from netbox_zabbix.zabbix.interfaces import link_zabbix_interface
from netbox_zabbix.zabbix.api import delete_host

from netbox_zabbix import settings, models

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
        monitored_by = settings.get_monitored_by()

        mapping = ( resolve_device_mapping if isinstance( ctx.object, Device ) else resolve_vm_mapping )( ctx.object, ctx.interface_model )

        # Check if a Zabbix config already exists
        host_config = models.HostConfig.objects.filter( content_type=ContentType.objects.get_for_model( ctx.object ), object_id=ctx.object.id ).first()

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
            update_zabbix_host( host_config, ctx.user, ctx.request_id )
            link_zabbix_interface (host_config.hostid, iface, ctx.object.name )

            save_host_config( host_config )
            log_creation_event( host_config, ctx.user, ctx.request_id )
            associate_instance_with_job( ctx.job, host_config )

            return {
                "message": f"Updated {ctx.object.name} with new interface {iface.name} in Zabbix",
                "data": {"hostid": host_config.hostid}
            }

        # No existing config exists so we do a full provisioning
        host_config = create_host_config( ctx.object )
        apply_mapping_to_host_config( host_config, mapping, monitored_by )

        iface = create_zabbix_interface(
            ctx.object,
            host_config,
            ctx.interface_model,
            ctx.interface_name_suffix,
            ctx.interface_kwargs_fn,
            ctx.user,
            ctx.request_id
        )

        hostid, payload = create_zabbix_host( host_config )
        host_config.hostid = hostid
        link_zabbix_interface( hostid, iface, ctx.object.name )

        save_host_config( host_config )
        log_creation_event( host_config, ctx.user, ctx.request_id )
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

