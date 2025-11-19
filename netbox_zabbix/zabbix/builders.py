"""
NetBox Zabbix Plugin — Payload Builders

This module constructs and validates payloads for communication with the Zabbix API.
It handles the extraction of inventory properties, generation of Zabbix-compatible
tags, and preparation of host, group, template, interface, and TLS data for API
operations.

Key functionality:
- Build host.create() and host.update() payloads from NetBox HostConfig instances
- Extract inventory data from Device or VirtualMachine objects based on configured mappings
- Generate Zabbix-compatible tags from object fields and NetBox tags
- Resolve interface details and ensure existing interface IDs are preserved during updates
- Handle monitored_by settings, proxies, TLS credentials, and inventory modes
"""


# NetBox Zabbix Imports
from netbox_zabbix.zabbix.inventory_properties import inventory_properties
from netbox_zabbix.helpers import resolve_attribute_path
from netbox_zabbix import settings, models
from netbox_zabbix.logger import logger

# ------------------------------------------------------------------------------
# Internal Helper Functions
# ------------------------------------------------------------------------------


def generate_zabbix_inventory(obj):
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
            logger.error( f"{invkey} is not a legal inventory property" )
            continue

        paths = field.get( "paths" )

        for path in paths:
            value = resolve_attribute_path( obj, path )
            if value is None:
                continue
            inventory[invkey] = str( value )
            break

    return inventory


def generate_zabbix_tags(obj):
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
    tag_prefix = settings.get_tag_prefix()

    # Add the default tag if it exists. Set the primary key of the obj as value.
    default_tag_name = settings.get_default_tag()
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
        value = resolve_attribute_path( obj, path )

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
# Interface Functions
# ------------------------------------------------------------------------------


def get_tags(obj, existing_tags=None):
    """
    Generate Zabbix-compatible tags for a NetBox object.
    
    Combines dynamic tags derived from the object with any existing tags,
    applies configured formatting (upper/lower), and deduplicates tags.
    
    Args:
        obj (Device | VirtualMachine): NetBox object for which to generate tags.
        existing_tags (list, optional): Pre-existing tag dictionaries to include.
    
    Returns:
        list[dict]: List of tag dictionaries with keys 'tag' and 'value'.
    """
    if existing_tags is None:
        existing_tags = []

    tag_name_formatting = settings.get_tag_name_formatting()
    tag_seen = set()
    result = []

    # Combine existing and dynamic tags, format and deduplicate in one loop
    for tag in existing_tags + generate_zabbix_tags( obj ):
        name = tag['tag']

        if tag_name_formatting == models.TagNameFormattingChoices.LOWER:
            name = name.lower()
        elif tag_name_formatting == models.TagNameFormattingChoices.UPPER:
            name = name.upper()

        key = (name, tag['value'])
        if key not in tag_seen:
            tag_seen.add( key )
            result.append( {'tag': name, 'value': tag['value']} )

    return result


def payload(host_config, for_update=False, pre_data=None) -> dict:
    """
    Construct a Zabbix host payload from a HostConfig instance.
    
    Includes:
        - Host details (name, status, monitored_by)
        - Host groups and templates
        - Inventory data if enabled
        - TLS credentials if required
        - Interfaces (Agent and SNMP) with proper IDs for updates
    
    Args:
        host_config (HostConfig): NetBox Zabbix configuration instance.
        for_update (bool, optional): Whether payload is for host.update() vs. host.create().
        pre_data (dict, optional): Existing Zabbix data to recover interface IDs.
    
    Returns:
        dict: Dictionary suitable for Zabbix API calls (host.create() or host.update()).
    
    Raises:
        Exception: If configuration is invalid or required proxies are missing.
    """

    payload = {
        "host":           host_config.assigned_object.name,
        "status":         str( host_config.status ),
        "monitored_by":   str( host_config.monitored_by ),
        "proxyid":        "0",
        "proxy_groupid":  "0",
        "description":    str( host_config.description ) if host_config.description else "",
        "tags":           get_tags( host_config.assigned_object ),
        "groups":         [ {"groupid": g.groupid} for g in host_config.host_groups.all() ],
        "templates":      [ {"templateid": t.templateid} for t in host_config.templates.all() ],
        "inventory_mode": str( settings.get_inventory_mode() ),
    }

    if host_config.hostid:
        payload["hostid"] = str( host_config.hostid )

    # Monitoring proxy/proxy group
    if host_config.monitored_by == models.MonitoredByChoices.Proxy:
        if not host_config.proxy:
            raise Exception( f"Host '{payload['host']}' is set to use a proxy, but none is configured." )
        payload["proxyid"] = host_config.proxy.proxyid

    if host_config.monitored_by == models.MonitoredByChoices.ProxyGroup:
        if not host_config.proxy_group:
            raise Exception( f"Host '{payload['host']}' is set to use a proxy group, but none is configured." )
        payload["proxy_groupid"] = host_config.proxy_group.proxy_groupid

    # Inventory
    if payload["inventory_mode"] == str( models.InventoryModeChoices.MANUAL ):
        payload["inventory"] = generate_zabbix_inventory( host_config.assigned_object )

    # TLS
    if settings.get_tls_connect() == models.TLSConnectChoices.PSK or settings.get_tls_accept() == models.TLSConnectChoices.PSK:
        payload["tls_psk_identity"] = settings.get_tls_psk_identity()
        payload["tls_psk"] = settings.get_tls_psk()

    # Build a map of existing Zabbix interfaces (only for updates)
    existing_ifaces = {}
    if for_update and pre_data and "interfaces" in pre_data:
        for iface in pre_data["interfaces"]:
            key = ( iface.get("ip"), iface.get( "dns" ), iface.get( "type" ), iface.get( "port" ) )
            existing_ifaces[key] = iface.get( "interfaceid" )

    # Interfaces handling
    interfaces = []
    for iface in host_config.agent_interfaces.all():
        entry = {
            "type":  "1",
            "main":  str( iface.main ),
            "useip": str( iface.useip ),
            "ip":    str( iface.resolved_ip_address.address.ip ) if iface.resolved_ip_address else "",
            "dns":   iface.resolved_dns_name or "",
            "port":  str( iface.port ),
        }

        if for_update:
            if iface.interfaceid:
                entry["interfaceid"] = str( iface.interfaceid )

        interfaces.append( entry )

    for iface in host_config.snmp_interfaces.all():
        entry = {
            "type":  "2",
            "main":  str( iface.main ),
            "useip": str( iface.useip),
            "ip":    str( iface.resolved_ip_address.address.ip ) if iface.resolved_ip_address else "",
            "dns":   iface.resolved_dns_name or "",
            "port":  str( iface.port ),
            "details": {
                "version":         str( iface.version ),
                "bulk":            str( iface.bulk ),
                "max_repetitions": str( iface.max_repetitions ),
                "contextname":     str( iface.contextname ),
                "securityname":    str( iface.securityname ),
                "securitylevel":   str( iface.securitylevel ),
                "authprotocol":    str( iface.authprotocol ),
                "authpassphrase":  str( iface.authpassphrase ),
                "privprotocol":    str( iface.privprotocol ),
                "privpassphrase":  str( iface.privpassphrase ),
            },
        }

        if for_update:
            if iface.interfaceid:
                entry["interfaceid"] = str( iface.interfaceid )
            else:
                key = ( entry["ip"], entry["dns"], entry["type"], entry["port"] )
                if key in existing_ifaces:
                    entry["interfaceid"] = existing_ifaces[key]

        interfaces.append( entry )

    payload["interfaces"] = interfaces

    return payload

