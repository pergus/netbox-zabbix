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

#def normalize_host( host_data, is_device=True ):
#    """
#    Normalize host data from either Zabbix API or NetBox payload for comparison.
#    """
#
#    # Groups
#    resolved_groups = []
#    for group_entry in host_data.get( "groups", [] ):
#        # Zabbix data (dict with groupid)
#        if isinstance( group_entry, dict ) and "groupid" in group_entry:
#            try:
#                host_group_object = models.HostGroup.objects.get( groupid=int( group_entry["groupid"] ) )
#                resolved_groups.append( host_group_object.name )
#            except models.HostGroup.DoesNotExist:
#                resolved_groups.append( f"<unknown:{group_entry['groupid']}>" )
#        # NetBox payload (string)
#        elif isinstance( group_entry, str ):
#            resolved_groups.append( group_entry )
#    resolved_groups = sorted( resolved_groups )
#
#    # Templates
#    resolved_templates = []
#    for template_entry in host_data.get( "templates", [] ) + host_data.get( "parentTemplates", [] ):
#        if isinstance( template_entry, dict ) and "templateid" in template_entry:
#            try:
#                template_object = models.Template.objects.get( templateid=int( template_entry["templateid"] ) )
#                resolved_templates.append( template_object.name )
#            except models.Template.DoesNotExist:
#                resolved_templates.append( f"<unknown:{template_entry['templateid']}>" )
#        elif isinstance( template_entry, str ):
#            resolved_templates.append( template_entry )
#    resolved_templates = sorted( resolved_templates )
#
#    # Interfaces
#    resolved_interfaces = sorted(
#        [
#            {
#                "ip":    interface_entry.get( "ip", "" ),
#                "dns":   interface_entry.get( "dns", "" ),
#                "type":  int( interface_entry.get( "type", 0 ) ),
#                "useip": int( interface_entry.get( "useip", 0 ) ),
#                "main":  int( interface_entry.get( "main", 0 ) ),
#                "port":  int( interface_entry.get( "port", 0 ) ),
#            }
#            for interface_entry in host_data.get( "interfaces", [] )
#        ],
#        key=lambda interface: ( interface["ip"], interface["dns"] )
#    )
#
#    # Tags
#    possible_tags = [ ]
#    prefix = config.get_tag_prefix()
#    default_tag = config.get_default_tag()
#
#    if default_tag:
#        possible_tags.append( f"{prefix}{default_tag}" )
#    
#    # There is a tag mapping for device and another for VMs.
#    tag_mappings = models.TagMapping.objects.filter(object_type='device' if is_device else 'virtual_machine')
#
#    for mapping in tag_mappings:
#        # Add tags
#        for tag in mapping.tags.all():
#            possible_tags.append(prefix + str(tag))
#        
#        # Add selections
#        for field in mapping.selection:
#            name = field.get('name')
#            if name:
#                possible_tags.append(prefix + name)
#
#    resolved_tags = {}
#    for tag_entry in host_data.get( "tags", [] ):
#        if tag_entry.get( "tag" ) in possible_tags:
#            resolved_tags[ tag_entry.get( "tag", "" ) ] = tag_entry.get( "value", "" )
#
#    # Inventory
#    possible_inventory_items = [ field.get( "invkey" ) for field in models.InventoryMapping.objects.all()[0].selection ]
#    resolved_inventory = {
#        inventory_key: inventory_value
#        for inventory_key, inventory_value in host_data.get( "inventory", {} ).items()
#        if inventory_key in possible_inventory_items
#    }
#
#    # Monitored by (agent)
#    monitored_by = host_data.get( "monitored_by", "0" )
#    
#    # Proxy group
#    proxy_groupid = host_data.get( "proxy_groupid", "0" )
#    
#
#    # Other fields
#    host_name = host_data.get( "host" ) or resolved_inventory.get( "name" ) or ""
#    host_status = int( host_data.get( "status", 0 ) )
#    host_proxy_id = host_data.get( "proxyid" ) or None
#
#    return {
#        "host":          host_name,
#        "status":        host_status,
#        "proxyid":       host_proxy_id,
#        "groups":        resolved_groups,
#        "templates":     resolved_templates,
#        "interfaces":    resolved_interfaces,
#        "tags":          resolved_tags,
#        "inventory":     resolved_inventory,
#        "monitored_by":  monitored_by,
#        "proxy_groupid": proxy_groupid
#    }
#
#def verify_config(zcfg, debug=False):
#    """
#    Verify that a DeviceZabbixConfig or VMZabbixConfig in NetBox
#    matches the current configuration in Zabbix.
#
#    Args:
#        zcfg: DeviceZabbixConfig or VMZabbixConfig instance.
#
#    Returns:
#        dict containing:
#            - in_sync (bool): True if everything matches
#            - differences (dict): key/value pairs of mismatched fields
#            - zabbix_data (dict): raw Zabbix host data (for debugging)
#    """
#    if not zcfg.hostid:
#        return {
#            "in_sync": False,
#            "differences": { "netbox": {"hostid": None}, "zabbix": None },
#        }
#
#    # Fetch host info from Zabbix
#    try:
#        zbx_host = z.get_host_by_id( zcfg.hostid )
#    except Exception:
#        return {
#            "in_sync": False,
#            "differences": { "netbox": {"hostid": zcfg.hostid}, "zabbix": None },
#        }
#
#    # Build payload from NetBox for fields we care about - prevent circular include
#    from netbox_zabbix.jobs import build_payload
#    
#    nb_payload = build_payload( zcfg )
#
#    is_device = hasattr(zcfg, "device")
#
#    simplified_zbx = normalize_host( zbx_host, is_device )
#    simplified_nb  = normalize_host( nb_payload, is_device )
#
#    # Compare
#    differences = {}
#    for key in simplified_nb.keys():
#        if simplified_nb[key] != simplified_zbx.get( key ):
#            differences[key] = { "netbox": simplified_nb[key], "zabbix": simplified_zbx.get( key ) }
#
#    in_sync = not bool(differences)
#
#    if debug:
#        import json
#        logger.info( f"Zabbix Host {json.dumps( zbx_host, indent=2 ) }" )
#        logger.info( f"NetBox Host {json.dumps( nb_payload, indent=2) }" )
#        logger.info( f"Zabbix Simple {json.dumps( simplified_zbx, indent=2 )}" )
#        logger.info( f"NetBox Simple {json.dumps( simplified_nb, indent=2 )}" )
#
#    return {
#        "in_sync": in_sync,
#        "differences": differences,
#    }
#
#def flatten_diff(diff):
#    """
#    Flatten a differences dict into a list of rows for template display.
#    Handles scalars and nested dicts.
#
#    Example row:
#        {"field": "tags.@Platform", "netbox": "Linux", "zabbix": "Linuxddddd"}
#    """
#    rows = []
#
#    for field, val in diff.get("differences", {}).items():
#        nb_val = val.get("netbox")
#        zbx_val = val.get("zabbix")
#
#        if isinstance(nb_val, dict) and isinstance(zbx_val, dict):
#            for subkey, subval in nb_val.items():
#                rows.append({
#                    "field": f"{field}.{subkey}",
#                    "netbox": subval,
#                    "zabbix": zbx_val.get(subkey)
#                })
#        else:
#            rows.append({
#                "field": field,
#                "netbox": nb_val,
#                "zabbix": zbx_val
#            })
#    return rows



# ------------------------------------------------------------------------------
# New Validate Implementation
#


def json_diff(source_data, target_data, special_keys_set = None, list_identity_key_map = None, current_path = "" ):
    """
    Compare source_data (A) to target_data (B) and return dict with 'added', 'removed', 'changed'.

    Rules:
    - Keys only in B are ignored unless they exist in A.
    - Keys only in A are reported as removed.
    - Keys in both but with different values are reported as changed.
    - special_keys_set: keys where extra items in B are ignored (like tags, groups, templates).
    - list_identity_key_map: for special keys, identity key to match list-of-dict items.
    """

    def join_path(current_path, key_name):
        return f"{current_path}.{key_name}" if current_path else key_name
    

    if special_keys_set is None:
        special_keys_set = set()
    if list_identity_key_map is None:
        list_identity_key_map = {}

    diff_result = { "added": {}, "removed": {}, "changed": {} }

    # Compare dictionaries
    if isinstance( source_data, dict ) and isinstance( target_data, dict ):
        source_keys_set = set( source_data.keys() )
        target_keys_set = set( target_data.keys() )

        # Keys only in A (removed)
        for key_name in sorted( source_keys_set - target_keys_set ):
            diff_result["removed"][ join_path( current_path, key_name ) ] = source_data[key_name]

        # Keys only in B (added)
        for key_name in sorted( target_keys_set - source_keys_set ):
            diff_result["added"][ join_path( current_path, key_name ) ] = target_data[key_name]

        # Keys present in both (recursive comparison)
        for key_name in sorted( source_keys_set & target_keys_set ):
            current_key_path = join_path( current_path, key_name )

            if key_name in special_keys_set and isinstance( source_data[key_name], list ) and isinstance( target_data[key_name], list ):
                identity_key = list_identity_key_map.get( key_name )
                if identity_key:
                    changed_from_list, changed_to_list = diff_special_list_items( source_data[key_name], target_data[key_name], identity_key )
                    if changed_from_list or changed_to_list:
                        diff_result["changed"][ current_key_path ] = { "from": changed_from_list, "to": changed_to_list }
                else:
                    if source_data[key_name] != target_data[key_name]:
                        diff_result["changed"][ current_key_path ] = { "from": source_data[key_name], "to": target_data[key_name] }
            else:
                child_diff = json_diff( source_data[key_name], target_data[key_name], special_keys_set, list_identity_key_map, current_key_path )
                for diff_type in ("added", "removed", "changed"):
                    diff_result[diff_type].update( child_diff.get( diff_type, {} ) )

    # Compare non-special lists
    elif isinstance( source_data, list ) and isinstance( target_data, list ):
        if source_data != target_data:
            diff_result["changed"][ current_path ] = { "from": source_data, "to": target_data }

    # Compare primitive values
    else:
        if source_data != target_data:
            diff_result["changed"][ current_path ] = { "from": source_data, "to": target_data }


    diff_result["differ"] = bool( diff_result["added"] or diff_result["removed"] or diff_result["changed"] )

    return diff_result

def diff_special_list_items( source_list, target_list, identity_key ):
    """
    Compare two lists-of-dict for a special key.
    Return only items that exist in both and differ.
    Extra items in B are ignored.
    """
    source_map = { item[identity_key]: item for item in source_list if identity_key in item }
    target_map = { item[identity_key]: item for item in target_list if identity_key in item }

    changed_from_list = []
    changed_to_list = []

    for identity_value, source_item in source_map.items():
        target_item = target_map.get( identity_value )
        if target_item is None:
            continue  # missing in B (ignore)
        if source_item != target_item:
            changed_from_list.append( source_item )
            changed_to_list.append( target_item )

    return changed_from_list, changed_to_list

def normalize_inventory(payload_inventory: dict, zabbix_inventory: dict) -> dict:
    """
    Keep only the inventory fields present in the payload,
    ignoring any extra fields in Zabbix inventory.
    """
    normalized_inventory = {}
    for key in payload_inventory.keys():
        normalized_inventory[key] = zabbix_inventory.get(key, "")
    return normalized_inventory

def normalize_zabbix_host_dynamic(zabbix_host: dict, payload_template: dict) -> dict:
    """
    Normalize Zabbix host to match the structure of payload_template.

    Args:
        zabbix_host: Host dict from Zabbix API.
        payload_template: Dict with the same structure as build_payload output.
    """
    normalized_host = {
        "host":          zabbix_host.get("host", ""),
        "status":        zabbix_host.get("status", "0"),
        "monitored_by":  zabbix_host.get("monitored_by", "0"),
        "description":   zabbix_host.get("description", ""),
        "tags":          [ {"tag": t["tag"], "value": t["value"]} for t in zabbix_host.get("tags", []) ],
        "groups":        [ {"groupid": g["groupid"]} for g in zabbix_host.get("groups", []) ],
        "templates":     [ {"templateid": t["templateid"]} for t in zabbix_host.get("parentTemplates", []) ],
        "inventory_mode": zabbix_host.get("inventory_mode", "0"),
        "hostid":        zabbix_host.get("hostid"),
        "proxyid":       zabbix_host.get("proxyid"),
        "inventory":     normalize_inventory(payload_template.get("inventory", {}), zabbix_host.get("inventory", {})),
        "interfaces": [
            {
                "type":  i.get("type", "1"),
                "main":  i.get("main", "1"),
                "useip": i.get("useip", "0"),
                "ip":    i.get("ip", ""),
                "dns":   i.get("dns", ""),
                "port":  i.get("port", ""),
            }
            for i in zabbix_host.get("interfaces", [])
        ],
    }
    return normalized_host

def verify_config_internal(zabbix_config):

    if not zabbix_config.hostid:
        return { 
            "differ": True,
            "added":   {},
            "removed": {},
            "changed": {}
        }
    
    # Get the host from Zabbix
    zabbix_host_raw = z.get_host_by_id( zabbix_config.hostid )

    # Build payload from the Zabbix configuration
    from netbox_zabbix.jobs import build_payload
    payload = build_payload( zabbix_config )
    
    zabbix_host = normalize_zabbix_host_dynamic( zabbix_host_raw, payload )

    # Diff
    special_keys_set = { "templates", "groups", "tags" }
    list_identity_key_map = {"tags": "tag", "groups": "groupid", "templates": "templateid"}
    
    diff_result = json_diff( payload, zabbix_host, special_keys_set, list_identity_key_map )
    return diff_result


def transform(data):
    result = { "changed": {} }
    changed = data.get("changed", {})

    for key, value in changed.items():
        from_val = value.get("from")
        to_val = value.get("to")

        # Handle arrays of objects with "tag" and "value" keys
        if isinstance(from_val, list) and isinstance(to_val, list):
            from_map = {item["tag"]: item["value"] for item in from_val if isinstance(item, dict) and "tag" in item and "value" in item}
            to_map   = {item["tag"]: item["value"] for item in to_val   if isinstance(item, dict) and "tag" in item and "value" in item}

            all_tags = set(from_map.keys()) | set(to_map.keys())

            for tag in sorted(all_tags):
                old_val = from_map.get(tag)
                new_val = to_map.get(tag)

                if old_val != new_val:
                    # Generic key: parent key singularized + tag
                    base_key = key.rstrip('s') if key.endswith('s') else key
                    new_key = f"{base_key}_{tag}"
                    result["changed"][new_key] = {
                        "from": old_val,
                        "to":   new_val
                    }
        else:
            # Normal primitive or dict diff
            result["changed"][key] = {
                "from": from_val,
                "to":   to_val
            }

    return result

# Test function not used
def verify_config_v2(name):
    import json
    try:
        device = models.Device.objects.get( name=name) 
        zabbix_config = models.DeviceZabbixConfig.objects.get( device=device )
        result = verify_config_internal( zabbix_config )
        print( f"{json.dumps( result, indent=2 )}" )
        print( f"{ json.dumps( transform( result ), indent=2 ) }" )
    except:
        print( f"Could't verify {name}." )



# end