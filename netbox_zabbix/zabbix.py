# zabbix.py
# 
# Description: Wrapper functions for the Zabbix API
#

from django.utils import timezone
from django.core.cache import cache
from dcim.models import Device
from virtualization.models import VirtualMachine
from pyzabbix import ZabbixAPI
from netbox_zabbix import models
from netbox_zabbix.settings import (
    ZabbixSettingNotFound,
    get_max_deletions,
    get_zabbix_api_endpoint,
    get_zabbix_token,
)
from netbox_zabbix import utils as utils
from netbox_zabbix.logger import logger


class ZabbixHostNotFound(Exception):
    """Raised when a Zabbix host is not present in Zabbix."""
    pass


def get_zabbix_client():
    """
    Initializes and returns an authenticated Zabbix API client.
    
    Retrieves the Zabbix configuration from the database and uses it to 
    instantiate and authenticate a ZabbixAPI client. If configuration is missing 
    or authentication fails, an exception is raised.
    
    Returns:
        ZabbixAPI: An authenticated Zabbix API client instance.
    
    Raises:
        ZabbixSettingNotFound: If the configuration is missing.
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
        ZabbixSettingNotFound: If configuration is missing.
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
        ZabbixSettingNotFound: If the Zabbix configuration is missing.
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
        ZabbixSettingNotFound: If the Zabbix configuration is missing.
        Exception: If there is an error communicating with the Zabbix API.
    """
    try:
        z = get_zabbix_client()
        return z.template.get( output=["name"], sortfield = "name", selectParentTemplates=["templateid", "name"] )
    
    except Exception as e:
        raise e


def get_template_with_parents(templateid):
    """
    Retrieve a template and its parent templates from Zabbix.
    
    Connects to the Zabbix API using the configured client and fetches details 
    about a single template, including its parent templates.
    
    Args:
        templateid (int or str): The ID of the template to retrieve.
    
    Returns:
        list: A list containing the requested template with its ID, name, 
              and parent templates.
    """
    try:
        z = get_zabbix_client()
        return z.template.get( templateids=[templateid], output=["templateid", "name"], selectParentTemplates=["templateid", "name"] )

    except Exception as e:
        raise e


def get_item_types(template_ids:list):
    """
    Retrieve item types for the given Zabbix templates.
    
    Connects to the Zabbix API and fetches items associated with the 
    specified templates.
    
    Args:
        template_ids (list): A list of template IDs.
    
    Returns:
        list: A list of items containing item ID, type, and host ID.
    """
    try:
        z = get_zabbix_client()
        return z.item.get( templateids=template_ids, output=["itemid", "type", "hostid"] )
    except Exception as e:
        raise e


def get_triggers( template_ids:list):
    """
    Retrieve triggers for the given Zabbix templates.
    
    Connects to the Zabbix API and fetches triggers associated with the 
    specified templates, including their dependencies and host information.
    
    Args:
        template_ids (list): A list of template IDs.
    
    Returns:
        list: A list of triggers with trigger ID, description, dependencies, 
              and associated hosts.
    """
    try:
        z = get_zabbix_client()
        return z.trigger.get( templateids=template_ids, 
                              output=["triggerid", "description"], 
                              selectDependencies=["triggerid"], 
                              selectHosts=["hostid", "name"] 
                            )
    except Exception as e:
        raise e


def get_trigger( triggerid ):
    """
    Retrieve a single trigger by its ID.
    
    Connects to the Zabbix API and fetches details about a specific trigger, 
    including its associated hosts.
    
    Args:
        triggerid (int or str): The ID of the trigger to retrieve.
    
    Returns:
        list: A list containing the requested trigger with its ID and 
              associated host information.
    """
    try:
        z = get_zabbix_client()
        return z.trigger.get( triggerids=[triggerid],
                       output=["triggerid"],
                       selectHosts=["hostid", "name"]
                      )
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
        ZabbixSettingNotFound: If the Zabbix configuration is missing.
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
        ZabbixSettingNotFound: If the Zabbix configuration is missing.
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
            ZabbixSettingNotFound: If the Zabbix configuration is missing.
    
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
            hostnames = {host["name"] for host in get_zabbix_hostnames()}
            cache.set( cache_key, hostnames, timeout=60 )  # Cache for 60 seconds
        except Exception:
            raise
            #hostnames = set()
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
        ZabbixSettingNotFound: If the Zabbix configuration is missing.
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

    except ZabbixSettingNotFound as e:
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


def get_host_group(name=None, groupid=None):
    """
    Fetch a single host group from Zabbix, by name or groupid.

    Args:
        name (str, optional): The name of the host group.
        groupid (str, optional): The ID of the host group.

    Returns:
        dict: Host group dict containing name and groupid.

    Raises:
        ValueError: If neither name nor groupid is provided.
        Exception: If no group is found, multiple groups are found, or API fails.
    """
    if not name and not groupid:
        raise ValueError("Either 'name' or 'groupid' must be provided")

    try:
        z = get_zabbix_client()

        filter_args = {}
        if name:
            filter_args["name"] = name
        if groupid:
            filter_args["groupid"] = groupid

        groups = z.hostgroup.get( output=["name", "groupid"], filter=filter_args )

        if not groups:
            raise Exception(f"No host group found for filter {filter_args}")
        if len(groups) > 1:
            raise Exception(f"Multiple host groups found for filter {filter_args}")

        return groups[0]

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
        ZabbixSettingNotFound: If the Zabbix configuration is missing.
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

    except ZabbixSettingNotFound as e:
        raise e
    
    except Exception as e:
        msg = f"Failed to retrieve host with host id '{hostid}' from Zabbix, error: {e}"
        logger.error( msg )
        raise Exception( msg )
    
    if not hosts:
        msg = f"No host with host id '{hostid}' found in Zabbix"
        logger.error( msg )
        raise ZabbixHostNotFound( msg )
    
    if len(hosts) > 1:
        msg = f"Multiple hosts with host id '{hostid}' found in Zabbix"
        logger.error( msg )
        raise Exception( msg )
    
    return hosts[0]


def get_host_by_id_with_templates(hostid):
    """
    Retrieves detailed information about a single host from Zabbix by hostid.
    
    The returned host includes interfaces, templates, tags, groups, and inventory
    data. Validates that exactly one host is found. The key 'parentTemplates'
    that is returned from Zabbix is renamed to 'templates'.
    
    Args:
        hostid (str): The hostid of the Zabbix host to retrieve.
    
    Returns:
        dict: A dictionary containing the Zabbix host's details.
    
    Raises:
        ZabbixSettingNotFound: If the Zabbix configuration is missing.
        Exception: If no host, multiple hosts, or an API error occurs.
    """

    try:
        host = get_host_by_id( hostid )
        host["templates"] = host.pop( "parentTemplates", [] )
        return host
    except:
        raise
    

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
    except ZabbixSettingNotFound as e:
        raise
    except Exception as e:
        logger.error( f"Failed to fetch Zabbix {name}" )
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

        obj, created = model.objects.update_or_create( **{id_field: item[id_field]}, defaults=defaults )
        if created:
            logger.info( f"Added {name} {item['name']} ({item[id_field]})" )
            added.append(item)

        if "parentTemplates" in item:
            parent_ids = [ p["templateid"] for p in item["parentTemplates"] ]
            
            parents = []
            for pid in parent_ids:
                parent, _ = model.objects.get_or_create( templateid=pid, defaults={"name": f"Placeholder-{pid}"} )
                parents.append( parent )
            obj.parents.set( parents )


    to_delete_ids = current_ids - remote_ids
    deleted = []

    if max_deletions is None:
        max_deletions = get_max_deletions()

    if len(to_delete_ids) >= max_deletions:
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
    added_templates, deleted_templates =  import_items( fetch_remote=get_templates, 
                                                        model=models.Template, 
                                                        id_field="templateid", 
                                                        name="template", 
                                                        max_deletions=max_deletions )

    # Calculate and store the interface type for each template
    try:
        utils.populate_templates_with_interface_type()
    except Exception as e:
        raise e
    
    # Populate the template with template dependencies.
    utils.populate_templates_with_dependencies()

    return added_templates, deleted_templates


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
# Host Groups
# ------------------------------------------------------------------------------


def create_host_group(**hostgroup):
    """
    Create a new Zabbix host group.

    Connects to the Zabbix API and creates a host group with the provided parameters.

    Args:
        **hostgroup: Arbitrary keyword arguments representing the host group configuration
                     (e.g., name).

    Returns:
        dict: The response from the Zabbix API containing details of the created host group.

    Raises:
        Exception: If creation fails or API returns an error.
    """
    try:
        z = get_zabbix_client()
        return z.hostgroup.create( **hostgroup )
    except Exception as e:
        raise e


# ------------------------------------------------------------------------------
# Hosts
# ------------------------------------------------------------------------------


def create_host(**host):
    """
    Create a new Zabbix host.
    
    Connects to the Zabbix API and creates a host with the provided parameters.
    
    Args:
        **host: Arbitrary keyword arguments representing the host configuration 
                (e.g., host name, interfaces, groups, templates).
    
    Returns:
        dict: The response from the Zabbix API containing details of the created host.
    """
    try:
        z = get_zabbix_client()
        return z.host.create( **host )
    except Exception as e:
        raise e


def update_host(**host):
    """
     Update an existing Zabbix host.
    
     Connects to the Zabbix API and updates the host with the given parameters.
    
     Args:
         **host: Arbitrary keyword arguments representing the updated host configuration 
                 (must include the `hostid` field).
    
     Returns:
         dict: The response from the Zabbix API containing details of the updated host.
    """
    try:
        z = get_zabbix_client()
        return z.host.update( **host )
    except Exception as e:
        raise e


def delete_host(hostid):
    """
    Delete a Zabbix host.
    
    Connects to the Zabbix API and deletes the specified host.
    
    Args:
        hostid (int or str): The ID of the host to delete.
    
    Returns:
        dict: The response from the Zabbix API confirming deletion.
    """
    hostids = [ hostid ]
    try:
        z = get_zabbix_client()
        return z.host.delete( *hostids ) 
    except Exception as e:
        raise e


def get_host_interfaces(hostid):
    """
    Retrieve interfaces for a specific Zabbix host.
    
    Connects to the Zabbix API and fetches all interfaces associated 
    with the given host.
    
    Args:
        hostid (int or str): The ID of the host whose interfaces should be retrieved.
    
    Returns:
        list: A list of host interfaces with their interface IDs and types.
    """
    try:
        z = get_zabbix_client()
        return z.hostinterface.get( output=["interfaceid", "type", "ip", "dns" ], hostids=hostid )
    except Exception as e:
        raise e


def can_remove_interface(hostid, interfaceid):
    """
    Check if an interface can be safely removed from a host.
    
    Connects to the Zabbix API and verifies whether the given interface 
    is used by any items. An interface can be removed only if no items 
    are linked to it.
    
    Args:
        hostid (int or str): The ID of the host.
        interfaceid (int or str): The ID of the interface to check.
    
    Returns:
        bool: True if the interface can be removed (no items depend on it), 
              False otherwise.
    """
    try:
        z = get_zabbix_client()
        items = z.item.get( hostids=[hostid], filter={'interfaceid': interfaceid} )
        return True if len(items) == 0 else False
    except Exception as e:
        raise e


# ------------------------------------------------------------------------------
# Misc.
# ------------------------------------------------------------------------------


def get_problems(hostname):
    try:
        z = get_zabbix_client()
        hosts = z.host.get( filter={"host": hostname} )
        if len(hosts) == 1:
            host = hosts[0]
        else:
            return []
        
        hostid = host["hostid"]

        problems = z.problem.get(
                   output=["eventid", "severity", "acknowledged", "name", "clock"],
                   hostids=[hostid],
                   sortfield="eventid",
                   sortorder="DESC"
               )

        return problems

    except Exception as e:
        raise e


# end