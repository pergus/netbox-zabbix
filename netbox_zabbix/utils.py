# utils.py

from math import remainder
from netbox_zabbix import models
from netbox_zabbix.config import get_default_tag, get_tag_prefix
from netbox_zabbix.inventory_properties import inventory_properties
from netbox_zabbix import zabbix as z
import json


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
# ------------------------------------------------------------------------------

def validate_quick_add( devm ):
    if not devm.primary_ip4_id:
        raise Exception( f"{devm.name} is missing the required primary IPv4 address." )
    if not devm.primary_ip.dns_name:
        raise Exception( f"{devm.name} is missing the required DNS name." )


# ------------------------------------------------------------------------------
# Validate Zabbix Configuration against Zabbix Host
# ------------------------------------------------------------------------------


def diff_lists(source_list, target_list, current_path=""):
    diff_result = {"added": {}, "removed": {}, "changed": {}}

    max_len = max(len(source_list), len(target_list))
    for idx in range(max_len):
        source_item = source_list[idx] if idx < len(source_list) else None
        target_item = target_list[idx] if idx < len(target_list) else None

        if source_item != target_item:
            # Recursively diff dictionaries/lists, else mark changed
            if isinstance(source_item, dict) and isinstance(target_item, dict):
                child_diff = json_diff(source_item, target_item)
                if child_diff["changed"] or child_diff["added"] or child_diff["removed"]:
                    diff_result["changed"][f"{current_path}[{idx}]"] = {
                        "from": source_item,
                        "to": target_item
                    }
            else:
                diff_result["changed"][f"{current_path}[{idx}]"] = {
                    "from": source_item,
                    "to": target_item
                }

    return diff_result

def json_diff(source_data, target_data, special_keys_set=None, list_identity_key_map=None, current_path=""):
    """
    Compare source_data (A) to target_data (B) and return dict with 'added', 'removed', 'changed'.

    Rules:
    - Keys only in B are ignored unless they exist in A.
    - Keys only in A are reported as removed.
    - Keys in both but with different values are reported as changed.
    - Lists are compared element-wise; only changed items are included in the output list.
    """

    def join_path(current_path, key_name):
        return f"{current_path}.{key_name}" if current_path else key_name

    if special_keys_set is None:
        special_keys_set = set()
    if list_identity_key_map is None:
        list_identity_key_map = {}

    diff_result = {"added": {}, "removed": {}, "changed": {}}

    # --- Compare dictionaries ---
    if isinstance(source_data, dict) and isinstance(target_data, dict):
        source_keys = set(source_data.keys())
        target_keys = set(target_data.keys())

        for key in source_keys - target_keys:
            diff_result["removed"][join_path(current_path, key)] = source_data[key]

        for key in target_keys - source_keys:
            diff_result["added"][join_path(current_path, key)] = target_data[key]

        for key in source_keys & target_keys:
            current_key_path = join_path(current_path, key)

            src_val = source_data[key]
            tgt_val = target_data[key]

            # Special keys logic (optional)
            if key in special_keys_set and isinstance(src_val, list) and isinstance(tgt_val, list):
                identity_key = list_identity_key_map.get(key)
                if identity_key:
                    changed_from, changed_to = diff_special_list_items(src_val, tgt_val, identity_key)
                    if changed_from or changed_to:
                        diff_result["changed"][current_key_path] = {"from": changed_from, "to": changed_to}
                    continue

            # Normal recursive diff
            child_diff = json_diff(src_val, tgt_val, special_keys_set, list_identity_key_map, current_key_path)
            for diff_type in ("added", "removed", "changed"):
                diff_result[diff_type].update(child_diff.get(diff_type, {}))

    # --- Compare lists and preserve list structure ---
    elif isinstance(source_data, list) and isinstance(target_data, list):
        # Only include items that differ
        changed_from = []
        changed_to = []
        max_len = max(len(source_data), len(target_data))
        for idx in range(max_len):
            src_item = source_data[idx] if idx < len(source_data) else None
            tgt_item = target_data[idx] if idx < len(target_data) else None
            if src_item != tgt_item:
                changed_from.append(src_item)
                changed_to.append(tgt_item)
        if changed_from or changed_to:
            diff_result["changed"][current_path] = {"from": changed_from, "to": changed_to}

    # --- Compare primitive values ---
    else:
        if source_data != target_data:
            diff_result["changed"][current_path] = {"from": source_data, "to": target_data}

    diff_result["differ"] = bool(diff_result["added"] or diff_result["removed"] or diff_result["changed"])
    return diff_result

def get_by_path(obj, parts):
    """Return nested value in dict by parts list, or None if missing."""
    cur = obj
    for p in parts:
        if not isinstance( cur, dict ):
            return None
        cur = cur.get( p )
    return cur

def set_by_path(dest, parts, value):
    """Set nested value into dest (creating dicts along the way)."""
    cur = dest
    for p in parts[:-1]:
        if p not in cur or not isinstance( cur[p], dict ):
            cur[p] = {}
        cur = cur[p]
    cur[parts[-1]] = value

def extract_changed_fields(original_obj, diff_result):
    """
    From original_obj and a json_diff result, build a smaller object that contains
    only the keys/paths that showed up in diff_result (changed/added/removed).
    This is used to build the 'from' and 'to' compact items for special-list diffs.
    """
    result = {}
    # collect all relevant paths
    paths = set()
    paths.update( diff_result.get( "changed", {}).keys() )
    paths.update( diff_result.get( "added", {}).keys() )
    paths.update( diff_result.get( "removed", {}).keys() )
  
    for path in paths:
        # ignore empty path
        if not path:
            continue
        # path is a dotted key like 'details.securitylevel'
        parts = path.split( "." )
        value = get_by_path( original_obj, parts )
        # include the value (may be None), but only if original actually had something
        # (get_by_path returning None for a missing key -> still set None if we want explicitness)
        set_by_path( result, parts, value )

    return result

def diff_special_list_items(source_list, target_list, identity_key,
                            special_keys_set=None, list_identity_key_map=None):
    """
    Compare two lists-of-dict keyed by identity_key.
    Return only items that exist in both and differ, and *only* with the fields that differ.
    """
    if special_keys_set is None:
        special_keys_set = set()

    if list_identity_key_map is None:
        list_identity_key_map = {}

    source_map = { item[identity_key]: item for item in source_list if identity_key in item }
    target_map = { item[identity_key]: item for item in target_list if identity_key in item }

    changed_from_list = []
    changed_to_list = []

    for identity_value, source_item in source_map.items():
        target_item = target_map.get( identity_value )
        if target_item is None:
            # item missing in target -> ignore (as per your original rule)
            continue

        # get a fine-grained nested diff for this pair
        nested_diff = json_diff( source_item, target_item, special_keys_set, list_identity_key_map )

        if nested_diff.get( "differ" ):
            # extract only the fields that actually changed/added/removed
            compact_from = extract_changed_fields( source_item, nested_diff )
            compact_to   = extract_changed_fields( target_item, nested_diff )

            # include the identity key so we can tell which interface this is
            compact_from[identity_key] = identity_value
            compact_to[identity_key]   = identity_value

            changed_from_list.append( compact_from )
            changed_to_list.append( compact_to )

    return changed_from_list, changed_to_list

def normalize_inventory(payload_inventory, zabbix_inventory):
    """
    Keep only the inventory fields present in the payload,
    ignoring any extra fields in Zabbix inventory.
    """
    normalized_inventory = {}
    for key in payload_inventory.keys():
        normalized_inventory[key] = zabbix_inventory.get( key, "" )
    return normalized_inventory

def normalize_zabbix_host_dynamic_v1(zabbix_host, payload_template):
    """
    Normalize Zabbix host to match the structure of payload_template.

    Args:
        zabbix_host: Host dict from Zabbix API.
        payload_template: Dict with the same structure as build_payload output.
    """
    normalized_host = {
        "host":           zabbix_host.get( "host", "" ),
        "status":         zabbix_host.get( "status", "0" ),
        "monitored_by":   zabbix_host.get( "monitored_by", "0" ),
        "description":    zabbix_host.get( "description", "" ),
        "tags":           [ {"tag": t["tag"], "value": t["value"]} for t in zabbix_host.get("tags", []) ],
        "groups":         [ {"groupid": g["groupid"]} for g in zabbix_host.get("groups", []) ],
        "templates":      [ {"templateid": t["templateid"]} for t in zabbix_host.get("parentTemplates", []) ],
        "inventory_mode": zabbix_host.get( "inventory_mode", "0" ),
        "hostid":         zabbix_host.get( "hostid" ),
        "proxyid":        zabbix_host.get( "proxyid" ),
        "inventory":      normalize_inventory( payload_template.get( "inventory", {}), zabbix_host.get("inventory", {} ) ),
        "interfaces": [
            {
                "type":        i.get( "type", "1" ),
                "main":        i.get( "main", "1" ),
                "useip":       i.get( "useip", "0" ),
                "ip":          i.get( "ip", "" ),
                "dns":         i.get( "dns", "" ),
                "port":        i.get( "port", "" ),
                "interfaceid": i.get( "interfaceid", "" )
            }
            for i in zabbix_host.get("interfaces", [])
        ],
    }
    return normalized_host

def normalize_details(payload_details, zabbix_details):
    return {k: zabbix_details.get(k, "") for k in payload_details.keys()}

def normalize_zabbix_host_dynamic(zabbix_host, payload_template):
    """
    Normalize Zabbix host to match the structure of payload_template.

    Args:
        zabbix_host: Host dict from Zabbix API.
        payload_template: Dict with the same structure as build_payload output.
    """
    normalized_host = {
        "host":           zabbix_host.get( "host", "" ),
        "status":         zabbix_host.get( "status", "0" ),
        "monitored_by":   zabbix_host.get( "monitored_by", "0" ),
        "description":    zabbix_host.get( "description", "" ),
        "tags":           [ {"tag": t["tag"], "value": t["value"]} for t in zabbix_host.get("tags", []) ],
        "groups":         [ {"groupid": g["groupid"]} for g in zabbix_host.get("groups", []) ],
        "templates":      [ {"templateid": t["templateid"]} for t in zabbix_host.get("parentTemplates", []) ],
        "inventory_mode": zabbix_host.get( "inventory_mode", "0" ),
        "hostid":         zabbix_host.get( "hostid" ),
        "proxyid":        zabbix_host.get( "proxyid" ),
        "proxy_groupid":  zabbix_host.get( "proxy_groupid" ),
        "inventory":      normalize_inventory( payload_template.get( "inventory", {} ), zabbix_host.get( "inventory", {} ) ),
        "interfaces": []
    }

    for i in zabbix_host.get("interfaces", []):
        interface = {
            "type":        i.get( "type", "1" ),
            "main":        i.get( "main", "1" ),
            "useip":       i.get( "useip", "0" ),
            "ip":          i.get( "ip", "" ),
            "dns":         i.get( "dns", "" ),
            "port":        i.get( "port", "" ),
            "interfaceid": i.get( "interfaceid", " " )
        }

        # Include SNMPv3 details if present
        if "details" in i and i.get( "type" ) == "2":  # SNMP interface
            payload_interface = next(
                (pi for pi in payload_template.get( "interfaces", [] )
                 if pi.get( "interfaceid" ) == i.get( "interfaceid") ),
                {}
            )
            interface["details"] = normalize_details(
                payload_interface.get( "details", {} ),
                i.get( "details", {} )
            )

        normalized_host["interfaces"].append( interface )

    return normalized_host

def compare_zabbix_config_with_host(zabbix_config, debug=False):
    """
    Compare a NetBox Zabbix configuration object with the corresponding
    host definition retrieved from Zabbix and return a structured diff.
    """

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
    payload = build_payload( zabbix_config, True )

    zabbix_host = normalize_zabbix_host_dynamic( zabbix_host_raw, payload )

    # Diff
    special_keys_set = { "interfaces", "templates", "groups", "tags" }
    list_identity_key_map = { "interfaces": "interfaceid", "templates": "templateid", "groups": "groupid",  "tags": "tag" }

    diff_result = json_diff( payload, zabbix_host, special_keys_set, list_identity_key_map )

    if debug:
        logger.info( f"zabbix_host_raw { json.dumps( zabbix_host_raw, indent=2 ) }" )
        logger.info( f"payload { json.dumps( payload, indent=2 ) }" )

    return diff_result


# Function used to test the 'compare_zabbix_config_with_host' function
def config_compare(name, debug=False):
    try:
        device = models.Device.objects.get( name=name )
        zabbix_config = models.DeviceZabbixConfig.objects.get( device=device )
        result = compare_zabbix_config_with_host( zabbix_config, debug )
        print( f"{json.dumps( result, indent=2 )}" )
    except:
        print( f"Could't compare {name}." )


# ------------------------------------------------------------------------------
# New Implementation of compare configuration
# ------------------------------------------------------------------------------

def compare_json(obj_a, obj_b):
    """
    Recursively compare two JSON-compatible objects.

    Returns (a_diff, b_diff):
      - a_diff: what is different in obj_a relative to obj_b
      - b_diff: what is different in obj_b relative to obj_a
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


def rewrite_tags(host_dict):
    """
    Rewrite the tags in a host dictionary to be a list of single-key dicts,
    where the original 'tag' becomes the key and 'value' becomes the value.

    Args:
        host_dict (dict): The host dictionary containing 'tags' key.

    Returns:
        dict: The same host dictionary with rewritten 'tags'.
    """


    if "tags" in host_dict and isinstance( host_dict["tags"], list ):
        new_tags = [ { t["tag"]: t.get("value", "") } for t in host_dict["tags"] if "tag" in t ]
        host_dict["tags"] = new_tags
    return host_dict


def convert_single_obj_array_to_sorted_strings(arr):
    """
    Convert a list of single-key dicts to a sorted list of their values as strings.

    Example:
    [ {"groupid": "7"}, {"groupid": "75"} ] -> [ "7", "75" ]
    """
    # Extract the single value from each dict
    values = [list(item.values())[0] for item in arr if isinstance(item, dict) and len(item) == 1]
    # Sort the list as strings
    return sorted(values)


def normalize_host(zabbix_host, payload_template):
    """
    Simplified normalization of a Zabbix host dict to match the structure of a payload template.

    - Recursively matches nested dicts.
    - Preserves all lists in order.
    - Missing keys get default empty values from template.
    """
    normalized = {}

    for key, template_value in payload_template.items():
        value = zabbix_host.get( key, None )

        if value is None:
            # Missing key -> use empty/default from template
            if isinstance( template_value, dict ):
                normalized[key] = {}
            elif isinstance( template_value, list ):
                normalized[key] = []
            else:
                normalized[key] = template_value
            continue

        if isinstance( template_value, dict ):
            normalized[key] = normalize_host( value, template_value )

        elif isinstance( template_value, list ):
            if template_value and isinstance( template_value[0], dict ):
                # List of dicts -> normalize each item recursively using template element
                template_elem = template_value[0]
                normalized[key] = [ normalize_host( item, template_elem ) for item in value ]
            else:
                # List of primitives -> preserve order
                normalized[key] = list( value )

        else:
            normalized[key] = value

    return normalized


def preprocess_host(host, template):
    """
    Normalize a host dictionary (payload or Zabbix) and rewrite its structure 
    for comparison.

    Steps:
    1. Normalize host to match template structure.
    2. Rewrite tags to { "tag": "value" } format.
    3. Convert 'groups' and 'templates' to sorted lists of strings.
    
    Args:
        host (dict): The host dictionary (NetBox payload or Zabbix host).
        template (dict): Template dictionary to guide normalization.
    
    Returns:
        dict: Preprocessed host ready for comparison.
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


def new_compare(name="dk-ece003w", debug=False):
    """
    Function used to test compare configuration

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
    from netbox_zabbix.jobs import build_payload
    payload = build_payload(config, True)

    zabbix_host_raw = z.get_host_by_id_with_templates( config.hostid )

    # Preprocess both payload and Zabbix host
    payload_processed = preprocess_host( payload, payload )
    zabbix_processed = preprocess_host( zabbix_host_raw, payload )

    # Compare recursively
    netbox_config, zabbix_config = compare_json( payload_processed, zabbix_processed )

    print( f"*" * 60 )
    print( f"** CONFIGURATION DIFFERENCE **")
    print( f"*" * 60 )
    print( "NETBOX" )
    print( f"{json.dumps( netbox_config, indent=2 ) }" )
    print( "ZABBIX" )
    print( f"{json.dumps( zabbix_config, indent=2 ) }" )

# ------------------------------------------------------------------------------
# Custom Fields
# ------------------------------------------------------------------------------

from django.contrib.contenttypes.models import ContentType
from extras.models import CustomField
from dcim.models import Device
from virtualization.models import VirtualMachine

def create_custom_field(name, defaults):
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

# end
