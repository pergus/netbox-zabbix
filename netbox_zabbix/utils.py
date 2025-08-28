# utils.py
from netbox_zabbix import models
from netbox_zabbix.config import get_default_tag, get_tag_prefix
from netbox_zabbix.inventory_properties import inventory_properties

from netbox_zabbix import zabbix as z

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



#-------------------------------------------------------------------------------
# Tempalte helper functions
#


def compute_interface_type(items):
    """
    Determine the interface type from a list of Zabbix items.
    Only considers Agent (0,7) and SNMPv3 (20) items.

    Args:
        items (list[dict]): List of item dictionaries with at least 'type'.

    Returns:
        InterfaceTypeChoices: Agent, SNMP, or Any
    """
    required = set()

    for item in items:
        item_type = int( item.get( "type", -1 ) )

        # Zabbix agent types
        if item_type == 0:
            required.add( models.InterfaceTypeChoices.Agent )

        # SNMPv3 detection (simplified: treat all SNMP agent as SNMPv3)
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
    Recursively collect this template and all its parents (from DB, not Zabbix).
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
    Return a set of template IDs that the given template depends on via triggers.
    Excludes the template itself.
    """
    
    # Fetch triggers for the template, including their dependencies
    triggers = z.get_triggers( [ templateid ] )

    deps = []
    for trig in triggers:
        for dep in trig.get("dependencies", []):
            dep_triggerid = dep["triggerid"]
            dep_trigger = z.get_trigger( dep_triggerid )[0]

            for host in dep_trigger.get("hosts", []):
                dep_templateid = host["hostid"]
                if int( dep_templateid ) != int( templateid ):  # exclude the original template
                    deps.append( int( dep_templateid ) )

    return deps



# This function is called by import template to add the interface type for
# each template in the database.
def populate_templates_with_interface_type():

    # Fetch ALL items for ALL templates in one call
    all_template_ids = list( models.Template.objects.values_list( "templateid", flat=True ) )
    all_items = z.get_item_types( all_template_ids )
        
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

# This function is called by import template to add dependencies for
# each template in the database.
def populate_templates_with_dependencies():

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


# This function can be called from clean_template to validate template combinations
def validate_template_combination(templateids: list, interface_type=models.InterfaceTypeChoices.Any):
    """
    Validate if a selection of templates can be combined without conflict,
    and if they are valid for the given interface type.

    - Conflicts: two selected templates (or their parents) include the same template.
    - Missing dependencies: any dependency (direct or recursive) not in the selection.
    - Interface type mismatch: all included templates must be compatible with `interface_type`.
    """
    seen = {}
    template_objects = models.Template.objects.filter(templateid__in=templateids)

    def get_all_parents(template, visited=None):
        """Recursively collect all parents of a template."""
        if visited is None:
            visited = set()
        if template.id in visited:
            return set()
        visited.add(template.id)

        parents = set(template.parents.all())
        for parent in template.parents.all():
            parents |= get_all_parents(parent, visited)
        return parents

    def get_all_dependencies(template, visited=None):
        """Recursively collect all dependencies of a template."""
        if visited is None:
            visited = set()
        if template.id in visited:
            return set()
        visited.add(template.id)

        deps = set(template.dependencies.all())
        for dep in template.dependencies.all():
            deps |= get_all_dependencies(dep, visited)
        return deps

    def is_interface_compatible(template_iftype, target_iftype):
        """Check if a template interface type is compatible with target type."""
        if target_iftype == models.InterfaceTypeChoices.Any:
            return True
        if template_iftype == models.InterfaceTypeChoices.Any:
            return True
        return template_iftype == target_iftype

    for template in template_objects:
        # Check for conflicts through parent inheritance
        inherited_templates = {template} | get_all_parents(template)
        for inherited_template in inherited_templates:
            if inherited_template.id in seen:
                raise Exception(
                    f"Conflict: '{template.name}' and "
                    f"'{seen[inherited_template.id].name}' both include "
                    f"'{inherited_template.name}'"
                )
            seen[inherited_template.id] = template

        # Check for missing dependencies (recursive)
        for dependent_template in get_all_dependencies(template):
            if dependent_template.templateid not in templateids:
                raise Exception(
                    f"Missing dependency: '{template.name}' depends on "
                    f"'{dependent_template.name}', which is not included."
                )

        # Check interface type compatibility for this template and its hierarchy
        all_related = inherited_templates | get_all_dependencies(template)
        for related_template in all_related:
            if not is_interface_compatible(related_template.interface_type, interface_type):
                raise Exception(
                    f"Interface type mismatch: '{related_template.name}' "
                    f"requires {models.InterfaceTypeChoices(related_template.interface_type).label}, "
                    f"but target is {models.InterfaceTypeChoices(interface_type).label}."
                )

    return True



# end