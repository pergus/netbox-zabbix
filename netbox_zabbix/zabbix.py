from pyzabbix import ZabbixAPI
from netbox_zabbix import models
from django.utils import timezone
from django.conf import settings
from dcim.models import Device
from virtualization.models import VirtualMachine


from netbox_zabbix.job import RaisingJobRunner

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



from django_rq import get_queue
from rq.job import Job as RQJob

class ImportFromZabbix( RaisingJobRunner ):
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
    
    Meta:
        name (str): Human-readable job name in the UI.
        description (str): Description shown in the NetBox UI.
    """
    class Meta:
        name = "Zabbix Importer"
        description = "Import host settings from Zabbix"
    
    def run(self, *args, **kwargs):
        api_endpoint = kwargs.get("api_endpoint")
        token = kwargs.get("token")
        device = kwargs.get("device")
        
        if not all([api_endpoint, token, device]):
            raise ValueError("Missing required arguments: api_endpoint, token, or device.")        

        try:
            zbx_host = get_host( api_endpoint, token, device.name )
        except Exception as e:
            raise e
        
        return zbx_host
    
    @classmethod
    def run_job(self, api_endpoint, token, device, user, schedule_at=None, interval=None, immediate=False):
        name =f"Zabbix Import {device.name}"
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

        # Todo:
        # Add name to the meta field in the RQ job so that it is possible to
        # identify the RQ job. I would like to be able to set the func_name
        # but that doesn't seem to work.
        #rq_job_id = str(netbox_job.job_id)
        #rq_job = get_queue().fetch_job(rq_job_id)
        #if rq_job:
        #    rq_job.meta = name
        #    rq_job.save_meta()
                
        return netbox_job