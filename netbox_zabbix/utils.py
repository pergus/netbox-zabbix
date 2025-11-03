# utils.py

import json
from django.contrib.contenttypes.models import ContentType
from extras.models import CustomField
from dcim.models import Device
from virtualization.models import VirtualMachine

from ipam.models import IPAddress
from netbox_zabbix import models
from netbox_zabbix.settings import get_default_tag, get_tag_prefix
from netbox_zabbix.inventory_properties import inventory_properties
from netbox_zabbix import zabbix as z
from netbox_zabbix.logger import logger


# ------------------------------------------------------------------------------
# Build payload helpers
# ------------------------------------------------------------------------------


def resolve_field_path(obj, path):
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


def get_zabbix_inventory_for_object(obj):
    """
    Generate a Zabbix inventory dictionary for a Device or VirtualMachine.
    
    Args:
        obj: Device or VirtualMachine instance.
    
    Returns:
        dict: Keys are inventory property names, values are string representations.
    
    Raises:
        ValueError: If the object type is unsupported.
    """
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
        if invkey not in inventory_properties:
            logger.info( f"{invkey} is not a legal inventory property" )
            continue

        paths = field.get( "paths" )

        for path in paths:
            value = resolve_field_path( obj, path )
            if value is None:
                continue
            inventory[invkey] = str( value )
            break

    return inventory


def get_zabbix_tags_for_object(obj):
    """
    Generate a list of Zabbix tag dictionaries for a Device or VirtualMachine.
    
    Args:
        obj: Device or VirtualMachine instance.
    
    Returns:
        list[dict]: Each dict has "tag" and "value" keys.
    
    Raises:
        ValueError: If the object type is unsupported.
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



# ------------------------------------------------------------------------------
# Template helper functions
# ------------------------------------------------------------------------------


def compute_interface_type(items):
    """
    Determine the Zabbix interface type based on item types.
    
    Agent types (0) → Agent
    SNMPv3 types (20) → SNMP
    Mixed or empty → Any
    
    Args:
        items (list[dict]): List of Zabbix item dictionaries.
    
    Returns:
        InterfaceTypeChoices: Agent, SNMP, or Any
    """
    required = set()

    for item in items:
        item_type = int( item.get( "type", -1 ) )

        # Zabbix agent types
        if item_type == 0:
            required.add( models.InterfaceTypeChoices.Agent )

        # Simplified SNMPv3 detection since we treat all SNMP agents as SNMPv3
        elif item_type == 20:
            required.add( models.InterfaceTypeChoices.SNMP )

    if not required:
        return models.InterfaceTypeChoices.Any

    # If both types present, default to Any
    if len( required ) > 1:
        return models.InterfaceTypeChoices.Any

    return required.pop()


def collect_template_ids(template, visited=None):
    """
    Recursively collect template IDs including all parent templates.
    
    Args:
        template: Template instance.
        visited (set, optional): IDs already visited.
    
    Returns:
        set[int]: Set of template IDs including parents.
    """
    if visited is None:
        visited = set()
    if template.id in visited:
        return set()
    visited.add( template.id )

    ids = {template.templateid}
    for parent in template.parents.all():
        ids |= collect_template_ids( parent, visited )
    return ids


def get_template_dependencies(templateid):
    """
    Retrieve Zabbix template IDs that the given template depends on.
    
    Args:
        templateid (int): Zabbix template ID.
    
    Returns:
        list[int]: List of dependent template IDs, excluding the input template.
    """

    # Fetch triggers for the template, including their dependencies
    try:
        triggers = z.get_triggers( [ templateid ] )
    except:
        raise

    deps = []
    for trig in triggers:
        for dep in trig.get( "dependencies", [] ):
            dep_triggerid = dep["triggerid"]

            try:
                dep_trigger = z.get_trigger( dep_triggerid )[0]
            except:
                raise

            for host in dep_trigger.get("hosts", []):
                dep_templateid = host["hostid"]
                if int( dep_templateid ) != int( templateid ):  # exclude the original template
                    deps.append( int( dep_templateid ) )

    return deps


def populate_templates_with_interface_type():
    """
    Populate all Template objects with their computed interface type
    based on associated Zabbix items.
    """
    # This function is called by import template to add the interface type for
    # each template in the database.
    
    # Fetch ALL items for ALL templates in one call
    all_template_ids = list( models.Template.objects.values_list( "templateid", flat=True ) )

    try:
        all_items = z.get_item_types( all_template_ids )
    except:
        raise

    # Group items by templateid
    items_by_template = {}
    for item in all_items:
        tid = item["hostid"] # hostid is the templateid in our case.
        items_by_template.setdefault( tid, [] ).append( item )


    # Calculate and store the interface type for each template
    for template in models.Template.objects.all():
        logger.info( f"{template.name}" )
        all_ids = collect_template_ids( template )

        # Collect items for this template and all its parents
        items = []
        for tid in all_ids:
            items.extend( items_by_template.get( tid, [] ) )

        template.interface_type = compute_interface_type( items )
        template.save()


def populate_templates_with_dependencies():
    """
    Populate all Template objects with dependencies based on triggers
    retrieved from Zabbix.
    """
    # This function is called by import template to add dependencies for
    # each template in the database.
    
    for template in models.Template.objects.all():
        try:
            # Get dependent template IDs from triggers
            dependent_template_ids = get_template_dependencies(template.templateid)

            # Resolve Template objects (exclude missing templates)
            dependent_templates = models.Template.objects.filter(templateid__in=dependent_template_ids)

            # Set the dependencies for this template
            template.dependencies.set(dependent_templates)

        except Exception as e:
            logger.error(f"Failed to populate dependencies for template {template.name} ({template.templateid}): {e}")


def validate_templates(templateids: list):
    """
    Validate that selected templates can be combined without conflicts
    and all dependencies are included.
    
    Args:
        templateids (list[int]): List of template IDs to validate.
    
    Returns:
        bool: True if valid, raises Exception otherwise.
    """

    seen = {}
    template_objects = models.Template.objects.filter( templateid__in=templateids )

    def get_all_parents(template, visited=None):
        """Recursively collect all parents of a template."""
        if visited is None:
            visited = set()
        if template.id in visited:
            return set()
        visited.add( template.id )

        parents = set(template.parents.all())
        for parent in template.parents.all():
            parents |= get_all_parents( parent, visited )
        return parents

    def get_all_dependencies(template, visited=None):
        """Recursively collect all dependencies of a template."""
        if visited is None:
            visited = set()
        if template.id in visited:
            return set()
        visited.add( template.id )

        deps = set( template.dependencies.all() )
        for dep in template.dependencies.all():
            deps |= get_all_dependencies( dep, visited )
        return deps

    for template in template_objects:
        # Check for conflicts through parent inheritance
        inherited_templates = {template} | get_all_parents( template )
        for inherited_template in inherited_templates:
            if inherited_template.id in seen:
                raise Exception(
                    f"Conflict: '{template.name}' and "
                    f"'{seen[inherited_template.id].name}' both include "
                    f"'{inherited_template.name}'"
                )
            seen[inherited_template.id] = template

        # Check for missing dependencies (recursive)
        for dependent_template in get_all_dependencies( template ):
            if dependent_template.templateid not in templateids:
                raise Exception(
                    f"Missing dependency: '{template.name}' depends on "
                    f"'{dependent_template.name}', which is not included."
                )

    return True


def validate_template_interface(templateids: list, interface_type):
    """
    Validate that templates are compatible with a specified interface type.
    
    Args:
        templateids (list[int]): List of template IDs.
        interface_type (InterfaceTypeChoices): Interface type to validate.
    
    Returns:
        bool: True if all templates are compatible, raises Exception otherwise.
    """

    template_objects = models.Template.objects.filter( templateid__in=templateids )

    def get_all_parents(template, visited=None):
        """Recursively collect all parents of a template."""
        if visited is None:
            visited = set()
        if template.id in visited:
            return set()
        visited.add( template.id )

        parents = set( template.parents.all() )
        for parent in template.parents.all():
            parents |= get_all_parents( parent, visited )
        return parents

    def get_all_dependencies(template, visited=None):
        """Recursively collect all dependencies of a template."""
        
        if visited is None:
            visited = set()
        
        if template.id in visited:
            return set()
        
        visited.add( template.id )

        deps = set( template.dependencies.all() )
        for dep in template.dependencies.all():
            deps |= get_all_dependencies( dep, visited )
        
        return deps

    def is_interface_compatible(template_iftype, target_iftype):
        """Check if a template interface type is compatible with target type."""
        
        if target_iftype == models.InterfaceTypeChoices.Any:
            return True
        
        if template_iftype == models.InterfaceTypeChoices.Any:
            return True
        
        return template_iftype == target_iftype

    for template in template_objects:
        all_related = {template} | get_all_parents(template) | get_all_dependencies(template)
        for related_template in all_related:
            if not is_interface_compatible( related_template.interface_type, interface_type ):
                raise Exception(
                    f"Interface type mismatch: '{related_template.name}' "
                    f"requires {models.InterfaceTypeChoices(related_template.interface_type).label}, "
                    f"but target is {models.InterfaceTypeChoices(interface_type).label}."
                )

    return True


def validate_templates_and_interface(templateids: list, interface_type=models.InterfaceTypeChoices.Any):
    """
    Validate template combination and interface compatibility.
    
    Args:
        templateids (list[int]): Template IDs to validate.
        interface_type (InterfaceTypeChoices, optional): Target interface type.
    
    Returns:
        bool: True if valid, raises Exception otherwise.
    """
    validate_templates( templateids )
    validate_template_interface( templateids, interface_type )
    return True


def is_valid_interface(host_config, interface_type=models.InterfaceTypeChoices.Any):
    """
    Check if a host has a valid interface compatible with assigned templates.
    
    Args:
        host_config: HostConfig instance.
        interface_type (InterfaceTypeChoices, optional): Interface type to validate.
    
    Returns:
        bool: True if a valid interface exists.
    
    Raises:
        ValueError: If no templates are assigned.
    """
    if not host_config.templates.exists():
        raise ValueError( f"HostConfig '{host_config}' has no templates assigned." )

    template_ids = list( host_config.templates.values_list( "templateid", flat=True ) )

    # Validate templates and interface compatibility
    validate_templates_and_interface( template_ids, interface_type )
    
    return True


# ------------------------------------------------------------------------------
# Quick Add helper functions
# ------------------------------------------------------------------------------


def validate_quick_add( host ):
    """
    Validate a host before performing a Quick Add operation.
    
    Args:
        host: Device or VM instance.
    
    Raises:
        Exception: If primary IP or DNS name is missing.
    """
    if not host.primary_ip4_id:
        raise Exception( f"{host.name} is missing Primary IPv4 address." )
    if not host.primary_ip.dns_name:
        raise Exception( f"{host.name} is missing DNS name." )


# ------------------------------------------------------------------------------
# Compare Zabbix Configuration and Zabbix Host
# ------------------------------------------------------------------------------


def compare_json(obj_a, obj_b):
    """
    Recursively compare two JSON-compatible objects.
    
    Args:
        obj_a, obj_b: Dictionaries, lists, or primitive types.
    
    Returns:
        tuple: (a_diff, b_diff) showing differences from each perspective.
    """

    # Case 1: both are dicts
    if isinstance( obj_a, dict ) and isinstance( obj_b, dict ):
        a_diff, b_diff = {}, {}                 # Initialize differences for each object
        all_keys = set( obj_a ) | set( obj_b )  # All keys present in either dict

        for key in all_keys:

            # Key exists in both dicts, compare values recursively
            if key in obj_a and key in obj_b:
                sub_a, sub_b = compare_json( obj_a[key], obj_b[key] )

                # Only store differences if there are any
                if sub_a != {} and sub_a != [] and sub_a is not None:
                    a_diff[key] = sub_a
                
                if sub_b != {} and sub_b != [] and sub_b is not None:
                    b_diff[key] = sub_b

            # Key exists only in obj_a
            elif key in obj_a:
                a_diff[key] = obj_a[key]
            
            # Key exists only in obj_b
            else:
                b_diff[key] = obj_b[key]

        return a_diff, b_diff

    # Case 2: both are lists
    if isinstance( obj_a, list ) and isinstance( obj_b, list ):

        # Items in obj_a not in obj_b
        a_only = [ item for item in obj_a if item not in obj_b ]

        # Items in obj_b not in obj_a
        b_only = [ item for item in obj_b if item not in obj_a ]

        return ( a_only if a_only else [], b_only if b_only else [] )


    # Case 3: primitives (string, number, bool, None)
    # If the values are the same, return None for both
    # If different, return the differing values
    return ( obj_a if obj_a != obj_b else None, obj_b if obj_a != obj_b else None )


def normalize_host(zabbix_host, payload_template):
    """
    Normalize a Zabbix host to match a payload template structure.
    
    Args:
        zabbix_host (dict): Zabbix host dictionary.
        payload_template (dict): Template structure dictionary.
    
    Returns:
        dict: Normalized host dictionary.
    """
    normalized = {}

    for key, template_value in payload_template.items():
        if key not in zabbix_host:
            # If a key is missing then set the value to represent 'empty'.
            if isinstance( template_value, dict ):
                normalized[key] = {}
            elif isinstance( template_value, list ):
                normalized[key] = []
            else:
                normalized[key] = ""
            continue

        value = zabbix_host[key]

        if isinstance( template_value, dict ) and isinstance( value, dict ):
            normalized[key] = normalize_host( value, template_value )

        elif isinstance( template_value, list ) and isinstance( value, list ):
            if template_value and isinstance( template_value[0], dict ):
                template_elem = template_value[0]
                normalized[key] = [ normalize_host( item, template_elem ) for item in value ]
            else:
                normalized[key] = list( value )

        else:
            normalized[key] = value

    return normalized


def preprocess_host(host, template):
    """
    Preprocess a host dictionary for comparison:
    - Normalize structure
    - Rewrite tags as {tag: value}
    - Convert groups/templates to sorted string lists
    
    Args:
        host (dict): Host dictionary.
        template (dict): Template dictionary.
    
    Returns:
        dict: Preprocessed host ready for JSON comparison.
    """
    # Step 1: Normalize host
    normalized = normalize_host( host, template )

    # Step 2: Rewrite tags
    if "tags" in normalized and isinstance( normalized["tags"], list ):
        normalized["tags"] = [
            {t["tag"]: t.get("value", "")} for t in normalized["tags"] if "tag" in t
        ]

    # Step 3: Convert groups and templates to sorted lists of strings
    for key in ["groups", "templates"]:
        if key in normalized and isinstance( normalized[key], list ):
            normalized[key] = sorted(
                list( item.values() )[0] for item in normalized[key] 
                if isinstance( item, dict ) and len( item ) == 1
            )

    return normalized


def compare_zabbix_config_with_host(zabbix_config):
    """
    Compare a NetBox host configuration with its Zabbix counterpart.
    
    Args:
        zabbix_config: DeviceZabbixConfig instance.
    
    Returns:
        dict: {
            "differ": bool,
            "netbox": dict of differences,
            "zabbix": dict of differences
        }
    """
    retval = { "differ": False, "netbox": {}, "zabbix": {} }

    from netbox_zabbix.jobs import build_payload
    payload = build_payload( zabbix_config, True )

    zabbix_host_raw = {}
    if zabbix_config.hostid:
        try:
            zabbix_host_raw = z.get_host_by_id_with_templates( zabbix_config.hostid )
        except:
            pass
    
    # Preprocess both the payload and zabbix host
    payload_processed = preprocess_host( payload, payload )
    zabbix_processed  = preprocess_host( zabbix_host_raw, payload )

    # Compare the json documents
    netbox_config, zabbix_config = compare_json( payload_processed, zabbix_processed )
    
    retval["differ"] = False if netbox_config == {} and zabbix_config == {} else True
    retval["netbox"] = netbox_config
    retval["zabbix"] = zabbix_config

    return retval


def cli_compare_config(name="dk-ece003w"):
    """
    DO NOT CALL THIS FUNCTION
    CLI test function to compare configuration for a host by name.
    
    Args:
        name (str, optional): Device name. Defaults to "dk-ece003w".
    
    Prints JSON differences.

    # Before using new_compare()
    import netbox_zabbix.utils
    from importlib import reload
    from netbox_zabbix.utils import new_compare

    # To reload new_compare()
    reload(netbox_zabbix.utils) ; from netbox_zabbix.utils import new_compare
    """

    # Retrieve device and config
    device = models.Device.objects.get( name=name )
    config = models.DeviceZabbixConfig.objects.get( device=device )

    result = compare_zabbix_config_with_host( config )

    print( f"{json.dumps( result, indent=2 ) }" )



# ------------------------------------------------------------------------------
# Custom Fields
# ------------------------------------------------------------------------------


def create_custom_field(name, defaults):
    """
    Create a custom field for Device and VirtualMachine if it doesn't exist.
    
    Args:
        name (str): Custom field name.
        defaults (dict): Field attributes such as type, label, etc.
    """
    device_ct = ContentType.objects.get_for_model( Device )
    vm_ct     = ContentType.objects.get_for_model( VirtualMachine )
    
    # Create or get the custom field
    cf, created = CustomField.objects.get_or_create( name=name, defaults=defaults )
    if created:
        cf.object_types.set( [ device_ct.id, vm_ct.id ] )
        cf.save()
        logger.info( f"Created new custom field" )
    else:
        logger.info( f"Did not create new custom field" )


# ------------------------------------------------------------------------------
# Find IPAddress
# ------------------------------------------------------------------------------


def find_ip_address(address:str):
    """
    Find IPAddress objects in NetBox starting with a given address.
    
    Args:
        address (str): IPv4 or IPv6 address without CIDR, e.g., "10.0.0.46".
    
    Returns:
        QuerySet[IPAddress]: Matching IP addresses (may be empty).
    """

    if not address.endswith("/"):
        address += "/"

    return IPAddress.objects.filter( address__startswith=address )


# ------------------------------------------------------------------------------
# Interfaces
# ------------------------------------------------------------------------------


def can_delete_interface(interface):
    """
    Check if a Zabbix interface can be deleted.
    
    Args:
        interface: Host interface instance.
    
    Returns:
        bool: True if deletion is allowed, False otherwise.
    """
    try:
        hostid      = int( interface.host_config.hostid )
        interfaceid = int( interface.interfaceid )

        # Check if there are templates that need to be deleted before we can delete the interface.
        if not z.can_remove_interface( hostid, interfaceid ):
            return False

    except:
        # Default to False if Zabbix isn't responding.
        return False
    return True


def is_interface_available(interface):
    """
    Check if a Zabbix interface is available.
    
    Args:
        interface: Host interface instance.
    
    Returns:
        bool: True if available, False otherwise.
    """
    try:
        hostid      = int( interface.host_config.hostid )
        interfaceid = int( interface.interfaceid )
    
        # Check if there are templates that need to be deleted before we can delete the interface.
        if not z.interface_availability( hostid, interfaceid ):
            return False
    
    except:
        # Default to False if Zabbix isn't responding.
        return False
    return True
    

# end
