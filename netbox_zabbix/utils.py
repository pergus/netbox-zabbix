# utils.py
from netbox_zabbix import models
from netbox_zabbix.config import get_default_tag, get_tag_prefix
from netbox_zabbix.logger import logger

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


def get_zabbix_inventory_for_object (obj):
    if obj._meta.model_name == 'device':
        object_type = 'device'
    elif obj._meta.model_name == 'virtualmachine':
        object_type = 'virtualmachine'
    else:
        raise ValueError( f"Unsupported object type: {obj._meta.model_name}" )
    
    inventory = {}

    try:
        mapping = models.InventoryMapping.objects.get( object_type=object_type )
    except models.InventoryMapping.DoesNotExist:
        return inventory
    
    for field in mapping.selection:
        if not field.get( "enabled" ):
            continue
        invkey = str( field.get( "invkey" ) )
        paths = field.get( "paths" )

        for path in paths:
            logger.info( f"{path=}" )
            value = resolve_field_path( obj, path )
            if value is None:
                logger.info( f"{value=} is None" )
                continue
            logger.info( f"adding {invkey=} {value=} to inventory" )
            inventory[invkey] = str( value )
            break

    return inventory


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
    
    # Add the tags that are the intersection between the mapping tags and the obj tags.
    for tag in set( mapping.tags.all() & obj.tags.all() ):
        tags.append({ "tag": f"{tag_prefix}{tag.name}", "value": tag.name })

    # Field Selection
    for field in mapping.selection:
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
