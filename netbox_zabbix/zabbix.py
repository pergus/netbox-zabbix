from pyzabbix import ZabbixAPI
from netbox_zabbix import models
from django.utils import timezone
from django.conf import settings
from dcim.models import Device
from virtualization.models import VirtualMachine

import logging


logger = logging.getLogger('netbox.plugins.netbox_zabbix')
PLUGIN_SETTINGS = settings.PLUGINS_CONFIG.get("netbox_zabbix", {})


def get_version( api_endpoint, token ):
    try:
        z = ZabbixAPI( api_endpoint )
        z.login( api_token = token )
        return z.apiinfo.version()
    except Exception as e:
        raise Exception( e )


def get_templates( api_endpoint, token ):    
    try:
        z = ZabbixAPI( api_endpoint )
        z.login( api_token = token )
        return z.template.get(output=["name"], sortfield = "name")
    except Exception as e:
        raise Exception( e )


def verify_token( api_endpoint, token ):
    # Apparently a clean installation of Zabbix always includes templates,
    # which is why get_templates is called here. However any function
    # that require authentication would do.
    # Make sure the called function raises an exception on error.
    get_templates( api_endpoint, token )


def synchronize_templates(api_endpoint, token, max_deletions=None):
    """
    Synchronize Zabbix templates with the database.
    From Zabbix to NetBox Sync.

    Returns:
        tuple: (added_templates, deleted_templates)

    Raises:
        RuntimeError: If number of deletions exceeds max_deletions.
        Exception: On API or DB error.
    """
    try:
        templates = get_templates( api_endpoint, token )
    except Exception as e:
        logger.error( "Failed to fetch Zabbix templates" )
        raise
        
    template_ids = { item['templateid'] for item in templates }

    current_templates = models.Template.objects.all()
    current_ids = set( current_templates.values_list( 'templateid', flat=True ) )

    now = timezone.now()
    added_templates = []

    # Add all new templates
    for item in templates:
        _, created = models.Template.objects.update_or_create( templateid=item['templateid'], defaults={"name": item['name'], "last_synced": now} )
        if created:
            logger.info( f"Added template {item['name']} ({item['templateid']})" )
            added_templates.append( item )

    templates_to_delete = current_ids - template_ids
    deleted_templates = []

    # Check if there is a limit to the number of templates to delete.
    if max_deletions is None:
        max_deletions = PLUGIN_SETTINGS.get( "max_template_changes" )

    if len( templates_to_delete ) >= max_deletions:
        # Mark the templates as deleted but don't delete them.
        models.Template.objects.filter(templateid__in=templates_to_delete).update(marked_for_deletion=True)
        logger.info( f"templates to delete: {templates_to_delete}" ) 
        raise RuntimeError( f"Too many deletions ({len(templates_to_delete)}), max allowed is {max_deletions}" )

    # Delete the tempaltes
    for templateid in templates_to_delete:
        tmpl = models.Template.objects.get( templateid=templateid )
        logger.info( f"Deleted template {tmpl.name} ({tmpl.templateid})" )
        deleted_templates.append( ( tmpl.name, tmpl.templateid ) )
        tmpl.delete()
    
    return added_templates, deleted_templates



def get_zabbix_hostnames(api_endpoint, token):
    """
     Retrieve a list of hostnames from Zabbix.
    
     Returns:
         list: A list of dictionaries containing Zabbix host names (e.g., [{'name': 'host1'}, {'name': 'host2'}]).
               Returns an empty list if an error occurs during the API call.
     """
    z = ZabbixAPI( api_endpoint )
    z.login( api_token=token )

    try:
        hostnames = z.host.get( output=["name"], sortfield=["name"] )
    except Exception as e:
        logger.error( f"Get Zabbix hostnames from {api_endpoint} failed: {e}" )
        return []
    
    return hostnames


def get_zabbix_only_hostnames( api_endpoint, token ):
    """
      Identify Zabbix hosts that do not exist in NetBox.
    
      Returns:
          list: A list of dictionaries representing hostnames that exist in Zabbix but are missing in NetBox.
                Compares Zabbix hostnames to names of NetBox Devices and Virtual Machines.
    """
    try:
        zabbix_hostnames = get_zabbix_hostnames( api_endpoint, token )
    except Exception as e:
        raise e

    netbox_hostnames = set( Device.objects.values_list( 'name', flat=True ) ).union( VirtualMachine.objects.values_list( 'name', flat=True ) )
    return [ h for h in zabbix_hostnames if h[ "name" ] not in netbox_hostnames ]


def get_host(api_endpoint, token, hostname):
    z = ZabbixAPI( api_endpoint )
    z.login( api_token=token )

    try:
        hosts = z.host.get(
            filter={"host": hostname},
            selectInterfaces="extend",
            selectParentTemplates="extend",
            selectTags="extend",
            selectGroups="extend",
            selectInventory="extend"
        )
    except Exception as e:
        msg = f"Failed to retrieve host '{hostname}' from Zabbix, error: {e}"
        logger.error( msg )
        raise Exception( msg )
    
    if not hosts:
        msg = f"No host named '{hostname}' found in Zabbix"
        logger.error( msg )
        raise Exception( msg )
    
    if len(hosts) > 1:
        msg = f"Multiple hosts named '{hostname}' found in Zabbix"
        logger.error( msg )
        raise Exception( msg )
    

    return hosts[0]
            
import json
def import_from_zabbix( api_endpoint, token, device):

    try:
        zbx_host = get_host( api_endpoint, token, device.name )
    except Exception as e:
        raise e
    logger.info( f"{json.dumps(zbx_host, indent=2)}" )
    logger.info( f"import_from_zabbix {api_endpoint} {device.name}" )