from pyzabbix import ZabbixAPI
from netbox_zabbix import models
from django.utils import timezone
from django.conf import settings
from dcim.models import Device
from virtualization.models import VirtualMachine

from netbox_zabbix.logger import logger
from netbox_zabbix.config import get_zabbix_api_endpoint, get_zabbix_token, get_max_deletions, ZabbixConfigNotFound


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
   

def synchronize_templates(max_deletions=None):
    """
    Synchronize templates from Zabbix with the local database.
    
    Fetches the list of templates from Zabbix and updates or creates corresponding
    Template records in the local database. It also deletes templates locally that
    no longer exist in Zabbix, respecting a maximum number of deletions.
    
    Args:
        max_deletions (int, optional): Maximum number of templates allowed to delete
            in one synchronization. If None, uses the default from config settings.
    
    Returns:
        tuple: A tuple containing two lists:
            - added_templates: List of newly added template dicts.
            - deleted_templates: List of tuples (name, templateid) of deleted templates.
    
    Raises:
        ZabbixConfigNotFound: If the Zabbix configuration is missing.
        RuntimeError: If the number of templates to delete exceeds max_deletions.
        Exception: For other errors during fetching or updating templates.
    """
    try:
        templates = get_templates()
    
    except ZabbixConfigNotFound as e:
        raise e
    
    except Exception as e:
        logger.error( "Failed to fetch Zabbix templates" )
        raise e
        
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
        max_deletions =  get_max_deletions()

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
    

def synchronize_proxies(max_deletions=None):
    """
    Synchronize proxies from Zabbix with the local database.
    
    Fetches the list of proxies from Zabbix and updates or creates corresponding
    Proxy records in the local database. It also deletes proxies locally that
    no longer exist in Zabbix, respecting a maximum number of deletions.
    
    Args:
        max_deletions (int, optional): Maximum number of proxies allowed to delete
            in one synchronization. If None, uses the default from config settings.
    
    Returns:
        tuple: A tuple containing two lists:
            - added_proxies: List of newly added proxy dicts.
            - deleted_proxies: List of tuples (name, proxy_id) of deleted proxies.
    
    Raises:
        ZabbixConfigNotFound: If the Zabbix configuration is missing.
        RuntimeError: If the number of proxies to delete exceeds max_deletions.
        Exception: For other errors during fetching or updating proxies.
    """
    try:
        proxies = get_proxies()
    
    except ZabbixConfigNotFound as e:
        raise e
    
    except Exception as e:
        logger.error( "Failed to fetch Zabbix proxies" )
        raise e
        
    proxyids = { item['proxyid'] for item in proxies }

    current_proxies = models.Proxy.objects.all()
    current_ids = set( current_proxies.values_list( 'proxyid', flat=True ) )

    now = timezone.now()
    added_proxies = []

    # Add all new proxies
    for item in proxies:
        _, created = models.Proxy.objects.update_or_create( proxyid=item['proxyid'], proxy_groupid=item['proxy_groupid'], defaults={"name": item['name'], "last_synced": now} )
        if created:
            logger.info( f"Added proxy {item['name']} ({item['proxyid']})" )
            added_proxies.append( item )

    proxies_to_delete = current_ids - proxyids
    deleted_proxies = []
    
    # Check if there is a limit to the number of proxies to delete.
    if max_deletions is None:
        max_deletions =  get_max_deletions()

    if len( proxies_to_delete ) >= max_deletions:
        # Mark the proxies as deleted but don't delete them.
        models.Proxy.objects.filter(proxyid__in=proxies_to_delete).update(marked_for_deletion=True)
        logger.info( f"proxies to delete: {proxies_to_delete}" ) 
        raise RuntimeError( f"Too many deletions ({len(proxies_to_delete)}), max allowed is {max_deletions}" )

    # Delete the tempaltes
    for proxyid in proxies_to_delete:
        proxy = models.Proxy.objects.get( proxyid=proxyid )
        logger.info( f"Deleted proxy {proxy.name} ({proxy.proxyid})" )
        deleted_proxies.append( ( proxy.name, proxy.proxyid ) )
        proxy.delete()
    
    return added_proxies, deleted_proxies


def get_proxygroups():
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
    

def synchronize_proxygroups(max_deletions=None):
    """
    Synchronize proxy groups from Zabbix with the local database.
    
    Fetches the list of proxy groups from Zabbix and updates or creates corresponding
    Proxy records in the local database. It also deletes proxy groups locally that
    no longer exist in Zabbix, respecting a maximum number of deletions.
    
    Args:
        max_deletions (int, optional): Maximum number of proxy groups allowed to delete
            in one synchronization. If None, uses the default from config settings.
    
    Returns:
        tuple: A tuple containing two lists:
            - added_proxy_groups: List of newly added proxy dicts.
            - deleted_proxy_groups: List of tuples (name, proxy_id) of deleted proxy groups.
    
    Raises:
        ZabbixConfigNotFound: If the Zabbix configuration is missing.
        RuntimeError: If the number of proxy groups to delete exceeds max_deletions.
        Exception: For other errors during fetching or updating proxy groups.
    """
    try:
        proxy_groups = get_proxygroups()
    
    except ZabbixConfigNotFound as e:
        raise e
    
    except Exception as e:
        logger.error( "Failed to fetch Zabbix proxy groups" )
        raise e
        
    proxy_groupids = { item['proxy_groupid'] for item in proxy_groups }

    current_proxy_groups = models.ProxyGroup.objects.all()
    current_ids = set( current_proxy_groups.values_list( 'proxy_groupid', flat=True ) )

    now = timezone.now()
    added_proxy_groups = []

    # Add all new proxy_groups
    for item in proxy_groups:
        _, created = models.ProxyGroup.objects.update_or_create( proxy_groupid=item['proxy_groupid'], defaults={"name": item['name'], "last_synced": now} )
        if created:
            logger.info( f"Added proxy {item['name']} ({item['proxy_groupid']})" )
            added_proxy_groups.append( item )

    proxy_groups_to_delete = current_ids - proxy_groupids
    deleted_proxy_groups = []
    
    # Check if there is a limit to the number of proxy groups to delete.
    if max_deletions is None:
        max_deletions =  get_max_deletions()

    if len( proxy_groups_to_delete ) >= max_deletions:
        # Mark the proxy groups as deleted but don't delete them.
        models.ProxyGroup.objects.filter(proxy_groupid__in=proxy_groups_to_delete).update(marked_for_deletion=True)
        logger.info( f"proxy groups to delete: {proxy_groups_to_delete}" ) 
        raise RuntimeError( f"Too many deletions ({len(proxy_groups_to_delete)}), max allowed is {max_deletions}" )

    # Delete the tempaltes
    for proxy_groupid in proxy_groups_to_delete:
        proxy = models.ProxyGroup.objects.get( proxy_groupid=proxy_groupid )
        logger.info( f"Deleted proxy {proxy.name} ({proxy.proxy_groupid})" )
        deleted_proxy_groups.append( ( proxy.name, proxy.proxy_groupid ) )
        proxy.delete()
    
    return added_proxy_groups, deleted_proxy_groups


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
        
    except ZabbixConfigNotFound as e:
        raise e
     
    except Exception as e:
        logger.error( f"Get Zabbix hostnames from {get_zabbix_api_endpoint()} failed: {e}" )
        return []
    

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


def hostgroup_get():
    """
    Fetch all hostgroups from Zabbix.

    Returns:
        list: List of hostgroup dicts from Zabbix.
    """

    try:
        z = get_zabbix_client()
        return z.hostgroup.get(output=["name", "groupid" ], limit=10000)
    except Exception as e:
        raise e        


def synchronize_hostgroups(max_deletions=None):
    """
    Synchronize Zabbix hostgroups into the local NetBox plugin database.

    Args:
        max_deletions (int, optional): Max allowed deletions in one run.

    Returns:
        tuple: (added, deleted) lists of hostgroup names
    """
    try:
        hostgroups = hostgroup_get()
    except Exception as e:
        raise RuntimeError( "Zabbix hostgroup sync failed" ) from e

    current = models.HostGroup.objects.all()
    current_ids = set( current.values_list( "groupid", flat=True ) )
    new_ids = set( hg["groupid"] for hg in hostgroups )
    
    added = []
    for hg in hostgroups:
        obj, created = models.HostGroup.objects.update_or_create( groupid=hg["groupid"], defaults={"name": hg["name"]} )
        if created:
            logger.info( f"Added hostgroup {hg['name']} ({hg['groupid']})" )
            added.append( hg["name"] )
    
    to_delete = current_ids - new_ids
    deleted = []
    
    for groupid in to_delete:
        hg = models.HostGroup.objects.get( groupid=groupid )
        logger.info( f"Deleted hostgroup {hg.name} ({hg.groupid})" )
        deleted.append( hg.name )
        hg.delete()
    
    return added, deleted


def create_host(**host):
    try:
        z = get_zabbix_client()
        z.host.create(**host)
    except Exception as e:
        raise e