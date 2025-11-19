"""
NetBox Zabbix Plugin — General utility functions supporting the NetBox-Zabbix integration.

Provides a collection of helper functions.
"""

# Django imports
from django.contrib.contenttypes.models import ContentType

# NetBox imports
from ipam.models import IPAddress


def resolve_attribute_path(obj, path):
    """
    Resolve a dotted attribute path on an object.
    
    Args:
        obj: Any Python object (e.g., a Django model instance).
        path (str): Dotted attribute path, e.g., "site.name" or "tags".
    
    Returns:
        Any: Value of the attribute, a list if `all()` exists, or None if missing.
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


def get_instance(content_type_id, instance_id):
    """
    Retrieves a model instance given a content type ID and instance ID.
    
    Args:
        content_type_id (int): ID of the ContentType.
        instance_id (int): ID of the model instance.
    
    Returns:
        Model instance corresponding to the content_type_id and instance_id.
    
    Raises:
        ValueError: If the content type is invalid or instance does not exist.
    """
    try:
        content_type = ContentType.objects.get( id=content_type_id )
    except ContentType.DoesNotExist:
        raise ValueError( f"Invalid content type id: {content_type_id}" )

    model_class = content_type.model_class()
    if model_class is None:
        raise ValueError( f"Content type {content_type_id} has no associated model" )

    try:
        return model_class.objects.get(id=instance_id)
    except model_class.DoesNotExist:
        raise ValueError( f"No instance with id={instance_id} for model {model_class.__name__}" )


def lookup_ip_address(address:str):
    """
    Lookup IPAddress objects in NetBox starting with a given address.
    
    Args:
        address (str): IPv4 or IPv6 address without CIDR, e.g., "10.0.0.46".
    
    Returns:
        QuerySet[IPAddress]: Matching IP addresses (may be empty).
    """

    if not address.endswith( "/" ):
        address += "/"

    return IPAddress.objects.filter( address__startswith=address ).first()


