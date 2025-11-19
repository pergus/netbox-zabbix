"""
NetBox Zabbix Plugin — Host Comparison Utilities

This module provides functions to compare a NetBox host configuration
(HostConfig) with its corresponding Zabbix host.

Key functionality includes:

- Normalizing host dictionaries to a consistent structure for comparison.
- Comparing tags, templates, groups, and other configuration elements.
- Supporting multiple comparison modes (overwrite vs. preserve).
- Reporting differences between NetBox and Zabbix hosts.

Intended for use in validation, synchronization, and auditing of
NetBox-managed Zabbix hosts.
"""

# NetBox Zabbix Imports
from netbox_zabbix import settings, models
from netbox_zabbix.zabbix import builders
from netbox_zabbix.zabbix.api import get_host_by_id_with_templates


# ------------------------------------------------------------------------------
# Private Helper Functions
# ------------------------------------------------------------------------------

def _compare_json(obj_a, obj_b, mode="overwrite"):
    """
    Recursively compare two JSON-compatible objects.
    Supports 'overwrite' and 'relaxed' modes.

    In relaxed mode:
      - Extra tags, templates, or groups in Zabbix are ignored.
      - Missing ones in Zabbix are reported.
    """

    # --- Case 1: both are dicts ---
    if isinstance( obj_a, dict ) and isinstance( obj_b, dict ):
        a_diff, b_diff = {}, {}
        all_keys = set( obj_a ) | set( obj_b )

        for key in all_keys:
            a_val, b_val = obj_a.get( key ), obj_b.get( key )

            # Recursive comparison, handle special fields below
            if key in obj_a and key in obj_b:
                # Apply relaxed rules only for known list-based keys
                if key in {"tags", "templates", "groups"}:
                    sub_a, sub_b = _compare_json( a_val, b_val, mode )
                else:
                    sub_a, sub_b = _compare_json( a_val, b_val, mode )

                if sub_a not in ( {}, [], None ):
                    a_diff[key] = sub_a
                if sub_b not in ( {}, [], None ):
                    b_diff[key] = sub_b

            elif key in obj_a:
                a_diff[key] = a_val
            else:
                b_diff[key] = b_val

        return a_diff, b_diff

    # --- Case 2: both are lists ---
    if isinstance( obj_a, list ) and isinstance( obj_b, list ):

        # Special handling for list of dicts with single keys (tags-like)
        if all( isinstance( item, dict ) and len( item ) == 1 for item in obj_a + obj_b ):
            a_map = {list( d.keys() )[0]: list( d.values() )[0] for d in obj_a}
            b_map = {list( d.keys() )[0]: list( d.values() )[0] for d in obj_b}

            a_diff, b_diff = {}, {}

            for key in set( a_map ) | set( b_map ):
                if key in a_map and key in b_map:
                    if a_map[key] != b_map[key]:
                        a_diff[key] = a_map[key]
                        b_diff[key] = b_map[key]
                elif key in a_map:
                    # Missing from Zabbix gives difference in both modes
                    a_diff[key] = a_map[key]
                elif key in b_map:
                    # Extra in Zabbix gives difference only in overwrite mode
                    if mode == models.HostSyncModeChoices.OVERWRITE:
                        b_diff[key] = b_map[key]

            return (
                [{k: v} for k, v in a_diff.items()],
                [{k: v} for k, v in b_diff.items()],
            )

        # Normal lists (e.g., primitive values)
        a_only = [item for item in obj_a if item not in obj_b]
        b_only = [item for item in obj_b if item not in obj_a]

        # In preserve mode, ignore extra items in Zabbix
        if mode == models.HostSyncModeChoices.PRESERVE:
            b_only = []

        return ( a_only, b_only )

    # --- Case 3: primitive values ---
    if obj_a != obj_b:
        return obj_a, obj_b
    return None, None


def _normalize_zabbix_host(zabbix_host, payload_template):
    """
    Normalize a Zabbix host to match a payload template structure.
    Ensures missing keys exist and have the correct empty type.
    """
    normalized = {}

    for key, template_value in payload_template.items():
        if key not in zabbix_host:
            if isinstance( template_value, dict ):
                normalized[key] = {}
            elif isinstance( template_value, list ):
                normalized[key] = []
            else:
                normalized[key] = ""
            continue

        value = zabbix_host[key]

        if isinstance( template_value, dict ) and isinstance( value, dict ):
            normalized[key] = _normalize_zabbix_host( value, template_value )

        elif isinstance( template_value, list ) and isinstance( value, list ):
            if template_value and isinstance( template_value[0], dict ):
                template_elem = template_value[0]
                normalized[key] = [_normalize_zabbix_host( item, template_elem ) for item in value]
            else:
                normalized[key] = list( value )
        else:
            normalized[key] = value

    return normalized


def _prepare_host_for_comparison(host, template):
    """
    Preprocess a host dictionary for comparison:
    - Normalize structure
    - Rewrite tags as [{tag: value}]
    - Convert groups/templates to sorted lists of strings
    """
    normalized = _normalize_zabbix_host( host, template )

    # Rewrite tags → [{tag: value}]
    if "tags" in normalized and isinstance( normalized["tags"], list ):
        normalized["tags"] = [
            {t["tag"]: t.get("value", "")} for t in normalized["tags"] if "tag" in t
        ]

    # Convert groups/templates → sorted string lists
    for key in ["groups", "templates"]:
        if key in normalized and isinstance( normalized[key], list ):
            normalized[key] = sorted(
                list( item.values() )[0]
                for item in normalized[key]
                if isinstance( item, dict ) and len( item ) == 1
            )

    return normalized


# ------------------------------------------------------------------------------
# Compare Zabbix Configuration and Zabbix Host 
# ------------------------------------------------------------------------------

def compare_host_configuration(host_config):
    """
    Compare a NetBox host configuration with its Zabbix counterpart.

    Args:
        host_config: HostConfig instance.

    Returns:
        dict:
        {
            "differ": bool,
            "netbox": dict of differences,
            "zabbix": dict of differences
        }
    """
    retval = {"differ": False, "netbox": {}, "zabbix": {}}
    mode = settings.get_host_sync_mode()

    payload = builders.payload( host_config, True )

    zabbix_host_raw = {}
    if host_config.hostid:
        try:
            zabbix_host_raw = get_host_by_id_with_templates( host_config.hostid )
        except Exception:
            pass

    payload_processed = _prepare_host_for_comparison( payload, payload )
    zabbix_processed = _prepare_host_for_comparison( zabbix_host_raw, payload )

    netbox_diff, zabbix_diff = _compare_json( payload_processed, zabbix_processed, mode )

    retval["differ"] = bool( netbox_diff or zabbix_diff )
    retval["netbox"] = netbox_diff
    retval["zabbix"] = zabbix_diff
    return retval


def cli_compare_config(name="dk-ece001w"):
    """
    DO NOT CALL THIS FUNCTION
    CLI test function to compare configuration for a host by name.
    
    Args:
        name (str, optional): Device name. Defaults to "dk-ece001w".
    
    Prints JSON differences.

    # Before using new_compare()
    import netbox_zabbix.utils
    from importlib import reload
    from netbox_zabbix.utils import new_compare

    # To reload new_compare()
    reload(netbox_zabbix.utils) ; from netbox_zabbix.utils import new_compare
    """
    import json
    # Retrieve device and config
    device = models.Device.objects.get( name=name )
    config = device.host_config

    result = compare_host_configuration( config )

    print( f"{json.dumps( result, indent=2 ) }" )


