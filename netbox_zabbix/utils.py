# utils.py
from collections import defaultdict
from django.core.cache import cache

from netbox_zabbix import models
from netbox_zabbix.config import get_default_tag, get_tag_prefix

def get_hostgroups_mappings( obj ):
    """
    Retrieves the host groups associated with a given object based on host group mappings.
    
    This function checks the object against all host group mappings and collects the
    mappings that match the object's site, role, platform, and tags. If a mapping has
    no specific criteria for a field (e.g., no sites, roles, platforms, or tags), it
    is considered a match.
    
    Args:
        obj: The object to find host groups for.
    
    Returns:
        A list of host group mappings that match the object's criteria.
    """
    mappings = models.HostGroupMapping.objects.all()
    matches = []

    for mapping in mappings:
        if mapping.sites.exists() and obj.site_id not in mapping.sites.values_list( 'id', flat=True ):
            continue
        if mapping.roles.exists() and obj.role_id not in mapping.roles.values_list( 'id', flat=True ):
            continue
        if mapping.platforms.exists() and obj.platform_id not in mapping.platforms.values_list( 'id', flat=True ):
            continue
        if mapping.tags.exists():
            obj_tag_slugs = set( obj.tags.values_list( 'slug', flat=True ) )
            mapping_tag_slugs = set( mapping.tags.values_list( 'slug', flat=True ) )
            if not mapping_tag_slugs.issubset( obj_tag_slugs ):
                continue
        matches.append( mapping )
    return matches


def get_templates_mappings( obj ):
    """
    Retrieves the templates associated with a given object based on template mappings.
    
    This function checks the object against all template mappings and collects the
    mappings that match the object's site, role, platform, and tags. If a mapping has
    no specific criteria for a field (e.g., no sites, roles, platforms, or tags), it
    is considered a match.
    
    Args:
        obj: The object to find templates for.
    
    Returns:
        A list of template mappings that match the object's criteria.
    """
    mappings = models.TemplateMapping.objects.all()
    matches = []

    for mapping in mappings:
        if mapping.sites.exists() and obj.site_id not in mapping.sites.values_list( 'id', flat=True ):
            continue
        if mapping.roles.exists() and obj.role_id not in mapping.roles.values_list( 'id', flat=True ):
            continue
        if mapping.platforms.exists() and obj.platform_id not in mapping.platforms.values_list( 'id', flat=True ):
            continue
        if mapping.tags.exists():
            obj_tag_slugs = set( obj.tags.values_list( 'slug', flat=True ) )
            mapping_tag_slugs = set( mapping.tags.values_list( 'slug', flat=True ) )
            if not mapping_tag_slugs.issubset( obj_tag_slugs ):
                continue
        matches.append( mapping )
    return matches


def get_proxy_mapping( obj ):
    """
    Retrieves the proxy associated with a given object based on proxy mapping.
    
    Args:
        obj: The object to find proxy for.
    
    Returns:
        The proxy mapping that match the object's criteria.
    """
    mappings = models.ProxyMapping.objects.all()
    matches = []

    for mapping in mappings:
        if mapping.sites.exists() and obj.site_id not in mapping.sites.values_list( 'id', flat=True ):
            continue
        if mapping.roles.exists() and obj.role_id not in mapping.roles.values_list( 'id', flat=True ):
            continue
        if mapping.platforms.exists() and obj.platform_id not in mapping.platforms.values_list( 'id', flat=True ):
            continue
        if mapping.tags.exists():
            obj_tag_slugs = set( obj.tags.values_list( 'slug', flat=True ) )
            mapping_tag_slugs = set( mapping.tags.values_list( 'slug', flat=True ) )
            if not mapping_tag_slugs.issubset( obj_tag_slugs ):
                continue
        matches.append( mapping )
    
    if len( matches ) > 1:
        raise ValueError("Multiple proxy mappings match this object.")
    if len( matches ) == 0:
        return None
    return matches[0]


def get_proxy_group_mapping( obj ):
    """
    Retrieves the proxy group associated with a given object based on proxy group mapping.
    
    Args:
        obj: The object to find proxy group for.
    
    Returns:
        The proxy group mapping that match the object's criteria.
    """
    mappings = models.ProxyGroupMapping.objects.all()
    matches = []

    for mapping in mappings:
        if mapping.sites.exists() and obj.site_id not in mapping.sites.values_list( 'id', flat=True ):
            continue
        if mapping.roles.exists() and obj.role_id not in mapping.roles.values_list( 'id', flat=True ):
            continue
        if mapping.platforms.exists() and obj.platform_id not in mapping.platforms.values_list( 'id', flat=True ):
            continue
        if mapping.tags.exists():
            obj_tag_slugs = set( obj.tags.values_list( 'slug', flat=True ) )
            mapping_tag_slugs = set( mapping.tags.values_list( 'slug', flat=True ) )
            if not mapping_tag_slugs.issubset( obj_tag_slugs ):
                continue
        matches.append( mapping )
    
    if len( matches ) > 1:
        raise ValueError("Multiple proxy group mappings match this object.")
    if len( matches ) == 0:
        return None
    return matches[0]


def validate_and_get_mappings( obj, monitored_by ):
    # Check if an 'object' has all requied mappings    
    if not (templates := get_templates_mappings( obj )):
        raise Exception( f"No template mappings found for obj '{obj.name}'" )
    
    if not (hostgroups := get_hostgroups_mappings( obj )):
        raise Exception( f"No host groups mappings found for obj '{obj.name}'" )
        
    proxy = get_proxy_mapping(obj) if monitored_by == models.MonitoredByChoices.Proxy else None
    if monitored_by == models.MonitoredByChoices.Proxy and proxy is None:
        raise Exception(f"obj '{obj.name}' is set to be monitored by Proxy, but no proxy mapping was found.")
    
    proxy_group = get_proxy_group_mapping(obj) if monitored_by == models.MonitoredByChoices.ProxyGroup else None
    if monitored_by == models.MonitoredByChoices.ProxyGroup and proxy_group is None:
        raise Exception(f"obj '{obj.name}' is set to be monitored by Proxy Group, but no proxy group mapping was found.")
        
    return ( templates, hostgroups, proxy, proxy_group )


def resolve_field_path(obj, path):
    """
    Resolve a dotted attribute path from an object (e.g., 'site.name', 'tags').
    """
    try:
        for part in path.split( '.' ):
            obj = getattr( obj, part )
            if obj is None:
                return None

        if hasattr( obj, 'all' ) and callable( obj.all ):
            return list( obj.all() )  # Return a list instead of string
        return obj
    except AttributeError:
        return None


def get_zabbix_tags_for_object(obj):
    """
    Given a Device or VirtualMachine object, return a list of Zabbix tag dicts:
    e.g., [ {'tag': 'Site', 'value': 'Lund'}, {'tag': 'core', 'value': 'core'} ]
    """
    if obj._meta.model_name == 'device':
        object_type = 'device'
    elif obj._meta.model_name == 'virtualmachine':
        object_type = 'virtualmachine'
    else:
        raise ValueError(f"Unsupported object type: {obj._meta.model_name}")

    tags = []
    
    # Get the tag prefix
    tag_prefix = get_tag_prefix()

    # Add the default tag if it exists. Set the primary key of the obj as value.
    default_tag_name = get_default_tag()
    if default_tag_name:
        tags.append( { "tag": f"{tag_prefix}{default_tag_name}", "value": str( obj.pk ) } )
    
    try:
        mapping = models.TagMapping.objects.get( object_type=object_type )
    except models.TagMapping.DoesNotExist:
        return tags
    
    for field in mapping.field_selection:
        if not field.get( "enabled" ):
            continue

        name = field.get( "name" )
        path = field.get( "value" )
        value = resolve_field_path( obj, path )

        if value is None:
            continue

        if isinstance( value, list ):
            # Special case: 'tags' (or other iterables) become multiple Zabbix tags
            for v in value:
                label = str( v )
                tags.append({
                    "tag": f"{tag_prefix}{label}",
                    "value": label
                })
        else:
            tags.append({
                "tag": f"{tag_prefix}{name}",
                "value": str( value )
            })

    return tags


# ------------------------------------------------------------------------------
# Mapping Functions
# ------------------------------------------------------------------------------


def _make_cache_key_for_devices(devices, name):
    # Use min and max device id plus count as a simple proxy
    ids = list(devices.values_list('id', flat=True))
    if not ids:
        return f"{name}_empty"
    return f"{name}_{min(ids)}_{max(ids)}_{len(ids)}"


def device_matches_mapping(device, mapping):
    site_match = not mapping.sites.exists() or device.site in mapping.sites.all()
    role_match = not mapping.roles.exists() or device.device_role in mapping.roles.all()
    platform_match = not mapping.platforms.exists() or device.platform in mapping.platforms.all()
    return site_match and role_match and platform_match


def get_host_groups_mapping_bulk(devices, use_cache=False, timeout=300):
    """
    Get host groups mapping for a list/queryset of devices.

    :param devices: Iterable of device instances
    :param use_cache: If True, attempt to retrieve mapping from cache
    :param timeout: Cache timeout in seconds (default 5 minutes)
    :return: defaultdict(list) mapping device IDs to host groups
    """

    def compute_host_groups_mapping():
        mappings = models.HostGroupMapping.objects.prefetch_related( "sites", "roles", "platforms", "host_groups" ).all()
        result = defaultdict( list )

        for device in devices:
            for mapping in mappings:
                if device_matches_mapping( device, mapping ):
                    result[device.id].extend( mapping.host_groups.all() )
        return result

    if not use_cache:
        return compute_host_groups_mapping()

    cache_key = _make_cache_key_for_devices( devices, "host_groups" )
    cached_result = cache.get( cache_key )
    if cached_result is not None:
        return cached_result

    result = compute_host_groups_mapping()
    cache.set( cache_key, result, timeout=timeout )
    return result


def get_templates_mapping_bulk(devices, use_cache=False, timeout=300):
    """
    Get templates mapping for a list/queryset of devices.

    :param devices: Iterable of device instances
    :param use_cache: If True, attempt to retrieve mapping from cache
    :param timeout: Cache timeout in seconds (default 5 minutes)
    :return: defaultdict(list) mapping device IDs to host groups
    """

    def compute_templates_mapping():
        mappings = models.TemplateMapping.objects.prefetch_related( "sites", "roles", "platforms", "templates" ).all()
        result = defaultdict( list )
    
        for device in devices:
            for mapping in mappings:
                if device_matches_mapping( device, mapping ):
                    result[device.id].extend( mapping.templates.all() )
        return result

    if not use_cache:
        return compute_templates_mapping()

    cache_key = _make_cache_key_for_devices( devices, "templates" )
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        return cached_result

    result = compute_templates_mapping()
    cache.set( cache_key, result, timeout=timeout )
    return result


def get_proxy_mapping_bulk(devices, use_cache=False, timeout=300):
    """
    Get proxy mapping for a list/queryset of devices.

    :param devices: Iterable of device instances
    :param use_cache: If True, attempt to retrieve mapping from cache
    :param timeout: Cache timeout in seconds (default 5 minutes)
    :return: defaultdict(list) mapping device IDs to host groups
    """

    def compute_proxy_mapping():
    #    mappings = models.ProxyMapping.objects.select_related( "proxy" ).prefetch_related( "sites", "roles", "platforms" )    
        mappings = models.ProxyMapping.objects.prefetch_related( "sites", "roles", "platforms", "proxy" )
        
        result = defaultdict(list)
    
        for device in devices:
            for mapping in mappings:
                if device_matches_mapping( device, mapping ):
                    result[device.id].append( mapping.proxy )
        return result
    

    if not use_cache:
        return compute_proxy_mapping()

    cache_key = _make_cache_key_for_devices( devices, "proxy" )
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        return cached_result

    result = compute_proxy_mapping()
    cache.set( cache_key, result, timeout=timeout )
    return result


def get_proxy_group_mapping_bulk(devices, use_cache=False, timeout=300):
    """
    Get proxy group mapping for a list/queryset of devices.

    :param devices: Iterable of device instances
    :param use_cache: If True, attempt to retrieve mapping from cache
    :param timeout: Cache timeout in seconds (default 5 minutes)
    :return: defaultdict(list) mapping device IDs to host groups
    """

    def computer_proxy_group_mapping():
    #    mappings = models.ProxyGroupMapping.objects.select_related( "proxy_group" ).prefetch_related( "sites", "roles", "platforms" )
        mappings = models.ProxyGroupMapping.objects.prefetch_related( "sites", "roles", "platforms", "proxy_group" )
        result = defaultdict( list )
    
        for device in devices:
            for mapping in mappings:
                if device_matches_mapping( device, mapping ):
                    result[device.id].append( mapping.proxy_group )
        return result
    
    

    if not use_cache:
        return computer_proxy_group_mapping()

    cache_key = _make_cache_key_for_devices( devices, "proxy_group" )
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        return cached_result

    result = computer_proxy_group_mapping()
    cache.set( cache_key, result, timeout=timeout )
    return result


def validate_and_get_mappings_bulk(device, monitored_by, templates_map, host_groups_map, proxy_map, proxy_group_map):
    device_id = device.id

    templates = templates_map.get( device_id )
    if not templates:
        raise Exception( f"No template mappings found for obj '{device.name}'" )

    host_groups = host_groups_map.get(device_id)
    if not host_groups:
        raise Exception( f"No host groups mappings found for obj '{device.name}'" )

    proxy = None
    if monitored_by == models.MonitoredByChoices.Proxy:
        proxy = proxy_map.get( device_id )
        if proxy is None:
            raise Exception( f"obj '{device.name}' is set to be monitored by Proxy, but no proxy mapping was found." )

    proxy_group = None
    if monitored_by == models.MonitoredByChoices.ProxyGroup:
        proxy_group = proxy_group_map.get( device_id )
        if proxy_group is None:
            raise Exception( f"obj '{device.name}' is set to be monitored by Proxy Group, but no proxy group mapping was found." )

    return ( templates, host_groups, proxy, proxy_group )


def get_valid_device_ids(devices, monitored_by):
    host_groups_map = get_host_groups_mapping_bulk( devices, use_cache=True)
    templates_map = get_templates_mapping_bulk( devices, use_cache=True )
    proxy_map = get_proxy_mapping_bulk( devices, use_cache=True )
    proxy_group_map = get_proxy_group_mapping_bulk( devices, use_cache=True )

    valid_ids = set()

    for device in devices:
        try:
            validate_and_get_mappings_bulk(
                device,
                monitored_by,
                templates_map,
                host_groups_map,
                proxy_map,
                proxy_group_map
            )
            valid_ids.add( device.id )
        except Exception:
            continue

    return valid_ids


