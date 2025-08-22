# zabbix.py

from django.utils import timezone
from django.core.cache import cache
from dcim.models import Device
from virtualization.models import VirtualMachine
from pyzabbix import ZabbixAPI
from netbox_zabbix import models
from netbox_zabbix.config import (
    ZabbixConfigNotFound,
    get_max_deletions,
    get_zabbix_api_endpoint,
    get_zabbix_token,
)
from netbox_zabbix.logger import logger


def get_zabbix_client():
    """
    Initializes and returns an authenticated Zabbix API client.
    
    Retrieves the Zabbix configuration from the database and uses it to 
    instantiate and authenticate a ZabbixAPI client. If configuration is missing 
    or authentication fails, an exception is raised.
    
    Returns:
        ZabbixAPI: An authenticated Zabbix API client instance.
    
    Raises:
        ZabbixConfigNotFound: If the configuration is missing.
        Exception: If authentication fails or any other error occurs.
    """
    try:
        z = ZabbixAPI( get_zabbix_api_endpoint() )
        z.login( api_token=get_zabbix_token() )
        return z
            
    except Exception as e:
        raise e


def validate_zabbix_credentials(api_endpoint, token):
    """
    Validates the provided Zabbix API endpoint and API token.
    
    Attempts to authenticate with the Zabbix API using the given endpoint and token.
    If authentication is successful, an authenticated API call (`template.get`) is made
    to confirm the credentials are valid and usable. This call is chosen because 
    templates are always present in a default Zabbix installation, making it a reliable test.
    
    Raises:
        Exception: If authentication fails or the API call encounters an error.
    """
    try:
        z = ZabbixAPI( api_endpoint )
        z.login( api_token=token )
        z.template.get( output=["name"], sortfield="name" )

    except Exception as e:
        raise e


def fetch_version_from_credentials(api_endpoint, token):
    """
    Returns the Zabbix API version using the given endpoint and token.
    Raises an exception if the API call fails.
    """
    try:
        z = ZabbixAPI( api_endpoint )
        z.login( api_token=token )
        return z.apiinfo.version()
        
    except Exception as e:
        raise e


def validate_zabbix_credentials_from_config():
    """
    Validate the Zabbix API credentials from the stored configuration.
    
    Retrieves the API endpoint and token from the config model and validates
    them by calling `validate_zabbix_api_credentials`.
    
    Raises:
        ZabbixConfigNotFound: If configuration is missing.
        Exception: If authentication or the API call fails.
    """
    validate_zabbix_credentials( get_zabbix_api_endpoint(), get_zabbix_token() )


# ------------------------------------------------------------------------------
# Get Settings
# ------------------------------------------------------------------------------


def get_version():
    """
    Retrieves the Zabbix server version from the API.
    
    Connects to the Zabbix API using the configured client and returns the 
    version string of the connected Zabbix instance.
    
    Returns:
        str: The version of the Zabbix server.
    
    Raises:
        ZabbixConfigNotFound: If the Zabbix configuration is missing.
        Exception: If there is an error communicating with the Zabbix API.
    """
    try:
        z = get_zabbix_client()
        return z.apiinfo.version()
    
    except Exception as e:
        raise e


def get_templates():
    """
    Retrieves all Zabbix templates.
    
    Connects to the Zabbix API using the configured client and fetches a list of 
    templates sorted by name.
    
    Returns:
        list: A list of Zabbix templates with their names.
    
    Raises:
        ZabbixConfigNotFound: If the Zabbix configuration is missing.
        Exception: If there is an error communicating with the Zabbix API.
    """
    try:
        z = get_zabbix_client()
        return z.template.get( output=["name"], sortfield = "name" )
    
    except Exception as e:
        raise e


def get_proxies():
    """
    Retrieves all Zabbix proxies.
    
    Connects to the Zabbix API using the configured client and fetches a list of 
    proxies sorted by name.
    
    Returns:
        list: A list of Zabbix proxies with their names.
    
    Raises:
        ZabbixConfigNotFound: If the Zabbix configuration is missing.
        Exception: If there is an error communicating with the Zabbix API.
    """
    try:
        z = get_zabbix_client()
        return z.proxy.get( output=["name", "proxyid", "proxy_groupid"], sortfield = "name" )
    
    except Exception as e:
        raise e


def get_proxy_groups():
    """
    Retrieves all Zabbix proxy groups.
    
    Connects to the Zabbix API using the configured client and fetches a list of 
    proxy groups sorted by name.
    
    Returns:
        list: A list of Zabbix proxy groups with their names.
    
    Raises:
        ZabbixConfigNotFound: If the Zabbix configuration is missing.
        Exception: If there is an error communicating with the Zabbix API.
    """
    try:
        z = get_zabbix_client()
        return z.proxygroup.get( output=["name", "proxy_groupid"], sortfield = "name" )
    
    except Exception as e:
        raise e


def get_zabbix_hostnames():
    """
        Retrieve all hostnames from Zabbix.
    
        Connects to the Zabbix API and returns a list of hosts with their names,
        sorted alphabetically.
    
        Returns:
            list: List of dictionaries representing hosts, each with a "name" key.
    
        Raises:
            ZabbixConfigNotFound: If the Zabbix configuration is missing.
    
        Returns empty list on other errors while logging the error.
    """
    
    try:
        z = get_zabbix_client()
        hostnames = z.host.get( output=["name"], sortfield=["name"] )
        return hostnames

    except Exception as e:
        logger.error( f"Get Zabbix hostnames from {get_zabbix_api_endpoint()} failed: {e}" )
        raise e


def get_cached_zabbix_hostnames():
    cache_key = "zabbix_hostnames"
    hostnames = cache.get( cache_key )
    if hostnames is None:
        try:
            logger.info( f"get all hosts from Zabbix..." )
            hostnames = {host["name"] for host in get_zabbix_hostnames()}
            logger.info( f"got all hosts from Zabbix..." )
            cache.set( cache_key, hostnames, timeout=60 )  # Cache for 60 seconds
        except Exception as e:
            hostnames = set()
    return hostnames


def get_zabbix_only_hostnames():
    """
        Retrieve hostnames that exist in Zabbix but not in NetBox.
    
        Compares hostnames from Zabbix against those in NetBox devices and virtual machines,
        returning only those that are present in Zabbix but missing in NetBox.
    
        Returns:
            list: List of dictionaries representing Zabbix hosts not found in NetBox.
    """
    try:
        zabbix_hostnames = get_zabbix_hostnames()
    except Exception as e:
        raise e

    netbox_hostnames = set( Device.objects.values_list( 'name', flat=True ) ).union( VirtualMachine.objects.values_list( 'name', flat=True ) )
    return [ h for h in zabbix_hostnames if h[ "name" ] not in netbox_hostnames ]


def get_host(hostname):
    """
    Retrieves detailed information about a single host from Zabbix by hostname.
    
    The returned host includes interfaces, templates, tags, groups, and inventory
    data. Validates that exactly one host is found.
    
    Args:
        hostname (str): The name of the Zabbix host to retrieve.
    
    Returns:
        dict: A dictionary containing the Zabbix host's details.
    
    Raises:
        ZabbixConfigNotFound: If the Zabbix configuration is missing.
        Exception: If no host, multiple hosts, or an API error occurs.
    """
    try:
        z = get_zabbix_client()
        hosts = z.host.get(
            filter={"host": hostname},
            selectInterfaces="extend",
            selectParentTemplates="extend",
            selectTags="extend",
            selectGroups="extend",
            selectInventory="extend"
        )

    except ZabbixConfigNotFound as e:
        raise e
    
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


def get_host_groups():
    """
    Fetch all host groups from Zabbix.

    Returns:
        list: List of host group dicts from Zabbix.
    """

    try:
        z = get_zabbix_client()
        return z.hostgroup.get(output=["name", "groupid" ], limit=10000)
    except Exception as e:
        raise e        


def get_host_by_id(hostid):
    """
    Retrieves detailed information about a single host from Zabbix by hostid.
    
    The returned host includes interfaces, templates, tags, groups, and inventory
    data. Validates that exactly one host is found.
    
    Args:
        hostid (str): The hostid of the Zabbix host to retrieve.
    
    Returns:
        dict: A dictionary containing the Zabbix host's details.
    
    Raises:
        ZabbixConfigNotFound: If the Zabbix configuration is missing.
        Exception: If no host, multiple hosts, or an API error occurs.
    """
    try:
        z = get_zabbix_client()
        hosts = z.host.get(
            filter={"hostid": str( hostid )},
            selectInterfaces="extend",
            selectParentTemplates="extend",
            selectTags="extend",
            selectGroups="extend",
            selectInventory="extend"
        )

    except ZabbixConfigNotFound as e:
        raise e
    
    except Exception as e:
        msg = f"Failed to retrieve host with host id '{hostid}' from Zabbix, error: {e}"
        logger.error( msg )
        raise Exception( msg )
    
    if not hosts:
        msg = f"No host with host id '{hostid}' found in Zabbix"
        logger.error( msg )
        raise Exception( msg )
    
    if len(hosts) > 1:
        msg = f"Multiple hosts with host id '{hostid}' found in Zabbix"
        logger.error( msg )
        raise Exception( msg )
    
    return hosts[0]


# ------------------------------------------------------------------------------
# Import Settings
# ------------------------------------------------------------------------------


def import_items(*, fetch_remote, model, id_field, extra_fields=None, name="item", max_deletions=None ):
    """
    Generic import function for syncing Zabbix items (templates, proxies, etc).

    Args:
        fetch_remote (callable): Function to fetch the list of remote items.
        model (Django Model): Model to update.
        id_field (str): The name of the unique field (e.g., 'templateid').
        extra_fields (list of str, optional): Extra fields to include in `update_or_create`.
        name (str): Friendly name for logging (e.g., "template", "proxy group").
        max_deletions (int, optional): Maximum allowed deletions.

    Returns:
        tuple: (added_items, deleted_items)
    """
    extra_fields = extra_fields or []

    try:
        items = fetch_remote()
    except ZabbixConfigNotFound as e:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch Zabbix {name}s")
        raise

    remote_ids = {item[id_field] for item in items}
    current_qs = model.objects.all()
    current_ids = set( current_qs.values_list( id_field, flat=True ) )

    added = []
    now = timezone.now()

    for item in items:
        defaults = {"name": item["name"], "last_synced": now}
        for field in extra_fields:
            defaults[field] = item[field]

        _, created = model.objects.update_or_create( **{id_field: item[id_field]}, defaults=defaults )
        if created:
            logger.info( f"Added {name} {item['name']} ({item[id_field]})" )
            added.append(item)

    to_delete_ids = current_ids - remote_ids
    deleted = []

    if max_deletions is None:
        max_deletions = get_max_deletions()

    if len(to_delete_ids) >= max_deletions:
        model.objects.filter( **{f"{id_field}__in": to_delete_ids} ).update( marked_for_deletion=True )
        logger.info( f"{name}s to delete: {to_delete_ids}" )
        raise RuntimeError( f"Too many deletions ({len(to_delete_ids)}), max allowed is {max_deletions}" )

    for obj_id in to_delete_ids:
        obj = model.objects.get( **{id_field: obj_id} )
        logger.info( f"Deleted {name} {obj.name} ({getattr(obj, id_field)})" )
        deleted.append( ( obj.name, getattr( obj, id_field ) ) )
        obj.delete()

    return added, deleted


def import_templates(max_deletions=None):
    """
    Import templates from Zabbix into the local database.
    
    Creates or updates template records and deletes templates that no longer exist
    in Zabbix, unless the number of deletions exceeds the allowed limit.
    
    Args:
        max_deletions (int, optional): Maximum number of templates to delete. Uses default if not provided.
    
    Returns:
        tuple: A tuple of (added_templates, deleted_templates).
    """
    return import_items( fetch_remote=get_templates, 
                         model=models.Template, 
                         id_field="templateid", 
                         name="template", 
                         max_deletions=max_deletions )


def import_proxies(max_deletions=None):
    """
    Import proxies from Zabbix into the local database.
    
    Synchronizes proxy records by adding new ones, updating existing ones, and deleting
    those no longer present in Zabbix, within deletion limits.
    
    Args:
        max_deletions (int, optional): Maximum number of proxies to delete. Uses default if not provided.
    
    Returns:
        tuple: A tuple of (added_proxies, deleted_proxies).
    """
    return import_items( fetch_remote=get_proxies, 
                         model=models.Proxy, 
                         id_field="proxyid", 
                         extra_fields=["proxy_groupid"], 
                         name="proxy", max_deletions=max_deletions )


def import_proxy_groups(max_deletions=None):
    """
    Import proxy groups from Zabbix into the local database.
    
    Adds, updates, and deletes proxy group records to match the current state in Zabbix,
    enforcing a maximum allowed number of deletions.
    
    Args:
        max_deletions (int, optional): Maximum number of proxy groups to delete. Uses default if not provided.
    
    Returns:
        tuple: A tuple of (added_proxy_groups, deleted_proxy_groups).
    """
    return import_items( fetch_remote=get_proxy_groups, 
                         model=models.ProxyGroup, 
                         id_field="proxy_groupid", 
                         name="proxy group", 
                         max_deletions=max_deletions )


def import_host_groups(max_deletions=None):
    """
    Import host groups from Zabbix into the local database.
    
    Synchronizes host group records by adding or updating them and removing obsolete ones,
    subject to a configurable deletion limit.
    
    Args:
        max_deletions (int, optional): Maximum number of host groups to delete. Uses default if not provided.
    
    Returns:
        tuple: A tuple of (added_host_groups, deleted_host_groups).
    """
    return import_items(fetch_remote=get_host_groups, 
                        model=models.HostGroup, 
                        id_field="groupid", 
                        name="host group", 
                        max_deletions=max_deletions )


# ------------------------------------------------------------------------------
# Host Actions
# ------------------------------------------------------------------------------


def create_host(**host):
    try:
        z = get_zabbix_client()
        return z.host.create( **host )
    except Exception as e:
        raise e

def update_host(**host):
    try:
        z = get_zabbix_client()
        return z.host.update( **host )
    except Exception as e:
        raise e

def delete_host(hostid):
    hostids = [ hostid ]
    try:
        z = get_zabbix_client()
        return z.host.delete( *hostids ) 
    except Exception as e:
        raise e
    
def get_host_interfaces(hostid):
    try:
        z = get_zabbix_client()
        return z.hostinterface.get( output=["interfaceid", "type"], hostids=hostid )
    except Exception as e:
        raise e