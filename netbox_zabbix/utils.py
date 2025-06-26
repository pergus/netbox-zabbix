# utils.py
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


def old_resolve_field_path(obj, path):
    """
    Resolve a dotted attribute path from an object (e.g., 'site.name').
    """
    try:
        for part in path.split('.'):
            obj = getattr(obj, part)
            if obj is None:
                return None
        return obj
    except AttributeError:
        return None

def old_get_zabbix_tags_for_object(obj):
    """
    Given a Device or VirtualMachine instance, return a list of Zabbix tag dicts.
    Includes only enabled fields from the associated TagMapping.
    """
    model_map = {
        'device': 'device',
        'virtualmachine': 'virtualmachine',
    }

    object_type = model_map.get(obj._meta.model_name)
    if not object_type:
        raise ValueError(f"Unsupported object type: {obj._meta.model_name}")

    try:
        mapping = models.TagMapping.objects.get(object_type=object_type)
    except models.TagMapping.DoesNotExist:
        return []

    return [
        {"tag": field["name"], "value": str(value)}
        for field in mapping.field_selection
        if field.get("enabled") and (value := resolve_field_path(obj, field.get("value")))
    ]


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
