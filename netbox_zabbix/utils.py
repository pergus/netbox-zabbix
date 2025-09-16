# utils.py

from netbox_zabbix import models, config
from netbox_zabbix.config import get_default_tag, get_tag_prefix
from netbox_zabbix.inventory_properties import inventory_properties
from netbox_zabbix import zabbix as z
from netbox_zabbix.logger import logger



# ------------------------------------------------------------------------------
# Build payload helpers
#


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


def get_zabbix_inventory_for_object(obj):
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



# ------------------------------------------------------------------------------
# Template helper functions
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


def validate_templates(templateids: list):
    """
    Validate if templates can be combined without conflicts or missing dependencies.

    - Conflicts: two selected templates (or their parents) include the same template.
    - Missing dependencies: any dependency (direct or recursive) not in the selection.
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

    return True


def validate_template_interface(templateids: list, interface_type):
    """
    Validate if all templates are compatible with the given interface type.
    """
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
        all_related = {template} | get_all_parents(template) | get_all_dependencies(template)
        for related_template in all_related:
            if not is_interface_compatible(related_template.interface_type, interface_type):
                raise Exception(
                    f"Interface type mismatch: '{related_template.name}' "
                    f"requires {models.InterfaceTypeChoices(related_template.interface_type).label}, "
                    f"but target is {models.InterfaceTypeChoices(interface_type).label}."
                )

    return True


def validate_templates_and_interface(templateids: list, interface_type=models.InterfaceTypeChoices.Any):
    """
    Validate if a selection of templates can be combined without conflict,
    and if they are valid for the given interface type.
    """
    validate_templates(templateids)
    validate_template_interface(templateids, interface_type)
    return True



# ------------------------------------------------------------------------------
# Quick Add helper functions
#

def validate_quick_add( devm ):
    if not devm.primary_ip4_id:
        raise Exception( f"{devm.name} is missing the required primary IPv4 address." )
    if not devm.primary_ip.dns_name:
        raise Exception( f"{devm.name} is missing the required DNS name." )


# ------------------------------------------------------------------------------
# Validate Zabbix Configuration against Zabbix Host
#

def normalize_host( host_data ):
    """
    Normalize host data from either Zabbix API or NetBox payload for comparison.
    """

    # Groups
    resolved_groups = []
    for group_entry in host_data.get( "groups", [] ):
        # Zabbix data (dict with groupid)
        if isinstance( group_entry, dict ) and "groupid" in group_entry:
            try:
                host_group_object = models.HostGroup.objects.get( groupid=int( group_entry["groupid"] ) )
                resolved_groups.append( host_group_object.name )
            except models.HostGroup.DoesNotExist:
                resolved_groups.append( f"<unknown:{group_entry['groupid']}>" )
        # NetBox payload (string)
        elif isinstance( group_entry, str ):
            resolved_groups.append( group_entry )
    resolved_groups = sorted( resolved_groups )

    # Templates
    resolved_templates = []
    for template_entry in host_data.get( "templates", [] ) + host_data.get( "parentTemplates", [] ):
        if isinstance( template_entry, dict ) and "templateid" in template_entry:
            try:
                template_object = models.Template.objects.get( templateid=int( template_entry["templateid"] ) )
                resolved_templates.append( template_object.name )
            except models.Template.DoesNotExist:
                resolved_templates.append( f"<unknown:{template_entry['templateid']}>" )
        elif isinstance( template_entry, str ):
            resolved_templates.append( template_entry )
    resolved_templates = sorted( resolved_templates )

    # Interfaces
    resolved_interfaces = sorted(
        [
            {
                "ip":    interface_entry.get( "ip", "" ),
                "dns":   interface_entry.get( "dns", "" ),
                "type":  int( interface_entry.get( "type", 0 ) ),
                "useip": int( interface_entry.get( "useip", 0 ) ),
                "main":  int( interface_entry.get( "main", 0 ) ),
                "port":  int( interface_entry.get( "port", 0 ) ),
            }
            for interface_entry in host_data.get( "interfaces", [] )
        ],
        key=lambda interface: ( interface["ip"], interface["dns"] )
    )

    # Tags
    possible_tags = []
    prefix = config.get_tag_prefix()
    for field in models.TagMapping.objects.all()[0].selection:
        possible_tags.append( f"{prefix}{field.get( 'name' )}" )
    
    resolved_tags = {}
    for tag_entry in host_data.get( "tags", [] ):
        if tag_entry.get( "tag" ) in possible_tags:
            resolved_tags[ tag_entry.get( "tag", "" ) ] = tag_entry.get( "value", "" )

    # Inventory
    possible_inventory_items = [ field.get( "invkey" ) for field in models.InventoryMapping.objects.all()[0].selection ]
    resolved_inventory = {
        inventory_key: inventory_value
        for inventory_key, inventory_value in host_data.get( "inventory", {} ).items()
        if inventory_key in possible_inventory_items
    }

    # Other fields
    host_name = host_data.get( "host" ) or resolved_inventory.get( "name" ) or ""
    host_status = int( host_data.get( "status", 0 ) )
    host_proxy_id = host_data.get( "proxyid" ) or None

    return {
        "host":       host_name,
        "status":     host_status,
        "proxyid":    host_proxy_id,
        "groups":     resolved_groups,
        "templates":  resolved_templates,
        "interfaces": resolved_interfaces,
        "tags":       resolved_tags,
        "inventory":  resolved_inventory,
    }


def verify_config(zcfg):
    """
    Verify that a DeviceZabbixConfig or VMZabbixConfig in NetBox
    matches the current configuration in Zabbix.

    Args:
        zcfg: DeviceZabbixConfig or VMZabbixConfig instance.

    Returns:
        dict containing:
            - in_sync (bool): True if everything matches
            - differences (dict): key/value pairs of mismatched fields
            - zabbix_data (dict): raw Zabbix host data (for debugging)
    """
    if not zcfg.hostid:
        return {
            "in_sync": False,
            "differences": { "netbox": {"hostid": None}, "zabbix": None },
        }

    # Fetch host info from Zabbix
    try:
        zbx_host = z.get_host_by_id( zcfg.hostid )
    except Exception:
        return {
            "in_sync": False,
            "differences": { "netbox": {"hostid": zcfg.hostid}, "zabbix": None },
        }

    # Build payload from NetBox for fields we care about - prevent circular include
    from netbox_zabbix.jobs import build_payload
    
    nb_payload = build_payload( zcfg )

    simplified_zbx = normalize_host( zbx_host )
    simplified_nb  = normalize_host( nb_payload )

    # Compare
    differences = {}
    for key in simplified_nb.keys():
        if simplified_nb[key] != simplified_zbx.get( key ):
            differences[key] = { "netbox": simplified_nb[key], "zabbix": simplified_zbx.get( key ) }

    in_sync = not bool(differences)

    return {
        "in_sync": in_sync,
        "differences": differences,
    }


# end