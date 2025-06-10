from netbox_zabbix import models

def get_device_hostgroups(device):
    """
    Retrieves the host groups associated with a given device based on host group mappings.
    
    This function checks the device against all host group mappings and collects the
    mappings that match the device's site, role, platform, and tags. If a mapping has
    no specific criteria for a field (e.g., no sites, roles, platforms, or tags), it
    is considered a match.
    
    Args:
        device: The device to find host groups for.
    
    Returns:
        A list of host group mappings that match the device's criteria.

    Note:
        This function is used in tables.py and filtersets.py.
    """
    mappings = models.HostGroupMapping.objects.all()
    matches = []

    for mapping in mappings:
        if mapping.sites.exists() and device.site_id not in mapping.sites.values_list( 'id', flat=True ):
            continue
        if mapping.roles.exists() and device.role_id not in mapping.roles.values_list( 'id', flat=True ):
            continue
        if mapping.platforms.exists() and device.platform_id not in mapping.platforms.values_list( 'id', flat=True ):
            continue
        if mapping.tags.exists():
            device_tag_slugs = set( device.tags.values_list( 'slug', flat=True ) )
            mapping_tag_slugs = set( mapping.tags.values_list( 'slug', flat=True ) )
            if not mapping_tag_slugs.issubset( device_tag_slugs ):
                continue
        matches.append(mapping)
    return matches



def get_hostgroups( obj ):
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



def get_templates( obj ):
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


