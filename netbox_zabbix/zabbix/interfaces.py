"""
NetBox Zabbix Plugin — Zabbix Interface Linking and Normalization

This module provides functionality for managing the relationship between
Zabbix host interfaces and their corresponding NetBox interface objects.

It includes:

- Linking newly created NetBox AgentInterface and SNMPInterface instances
  to their assigned Zabbix interface IDs
- Identifying and associating NetBox interfaces that are missing Zabbix
  interface IDs
- Fetching and matching Zabbix interface data based on IP, DNS, and type
- Normalizing Zabbix interface dictionaries to ensure consistent structure
  and proper Python types for use in further processing

These utilities ensure reliable synchronization of interface state between
NetBox and Zabbix during host import, provisioning, or repair operations.
"""


# NetBox Zabbix Imports
from netbox_zabbix.zabbix import api as zapi
from netbox_zabbix.exceptions import ExceptionWithData
from netbox_zabbix.logger import logger

def link_interface_in_zabbix( hostid, iface, name ):
    """
    Link a NetBox interface to its Zabbix interface ID after creation.
    
    Args:
        hostid (int): Zabbix host ID.
        iface (AgentInterface | SNMPInterface): Interface object.
        name (str): Human-readable name for logging.
    
    Raises:
        Exception: If linking fails or interfaces cannot be fetched.
    """
    try:
        result = zapi.get_host_interfaces( hostid )
        if len( result ) != 1:
            raise ExceptionWithData( f"Unexpected number of interfaces returned for {name}", result )
    except Exception as e:
        raise Exception( f"Failed to link interface for {name}: {str( e )}" )

    iface.interfaceid = result[0].get( "interfaceid", None )
    iface.hostid = hostid
    iface.full_clean()

    # Disable signals
    iface._skip_signal = True
    iface.save()


def link_missing_interface(host_config, hostid):
    """
    Ensure that any NetBox interface missing a Zabbix interface ID is linked.
   
    Args:
        host_config (HostConfig): Device or VM Zabbix configuration.
        hostid (int): Zabbix host ID.
   
    Raises:
        ExceptionWithData: If no matching Zabbix interface can be found.
    """
    # Fetch all Zabbix interfaces for this host
    try:
        zbx_interfaces = zapi.get_host_interfaces( hostid )
    except Exception as e:
        raise Exception( f"Failed to link missing interface for hostid {hostid}: {str( e )}" )

    # Find the unlinked interface (Agent or SNMP)
    unlinked_iface = None
    for iface in list( host_config.agent_interfaces.all() ) + list( host_config.snmp_interfaces.all() ):
        if iface.interfaceid is None:
            unlinked_iface = iface
            break

    if not unlinked_iface:
        logger.debug( f"All interfaces for {host_config.name} are already linked")
        return

    if not zbx_interfaces:
        logger.debug( f"No interfaces found in Zabbix for host {host_config.name} hostid ({host_config.hostid})" )
        return

    # Normalize unlinked IP (remove /prefix) for comparison
    unlinked_ip_obj = unlinked_iface.resolved_ip_address
    unlinked_ip = str( unlinked_ip_obj.address ) if unlinked_ip_obj else ""
    unlinked_dns = str( unlinked_iface.resolved_dns_name ) if unlinked_iface.resolved_dns_name else ""
    iface_type = unlinked_iface.type

    # Find the matching Zabbix interface
    target_iface = None
    for z in zbx_interfaces:
        z_ip = z.get( "ip", "" )
        z_dns = z.get( "dns", "" )
        z_type = int( z.get( "type", 0 ) )

        if z_type != iface_type:
            continue

        # Found a match
        if z_ip == unlinked_ip or z_dns == unlinked_dns:
            target_iface = z
            break


    # Fallback: if no match but only one interface exists, use it
    if not target_iface and len(zbx_interfaces) == 1:
        logger.debug( f"No exact match found; only one Zabbix interface exists, linking it anyway." )
        target_iface = zbx_interfaces[0]


    if not target_iface:
        raise ExceptionWithData( f"Could not find a matching Zabbix interface for {unlinked_iface}", 
                                data={  "zbx_interfaces": [ str( iface ) for iface in zbx_interfaces ],
                                        "unlinked_iface": str( unlinked_iface ) } )

    # Update the interface
    unlinked_iface.interfaceid = target_iface["interfaceid"]
    unlinked_iface.hostid = hostid
    unlinked_iface.full_clean()

    # Mark this instance to bypass signals for this save operation only
    unlinked_iface._skip_signal = True
    unlinked_iface.save( update_fields=["interfaceid", "hostid"] )


def normalize_interface(iface: dict) -> dict:
    """
    Normalize a Zabbix interface dictionary to ensure correct types and structure.
    
    Converts string representations of integers and nested SNMP fields into
    proper Python types. Supports Agent and SNMPv3 interfaces.
    
    Args:
        iface (dict): Zabbix interface dictionary as returned by the API.
    
    Returns:
        dict: Normalized interface dictionary with integer fields and proper SNMP details.
    
    Notes:
        - Unrecognized SNMP versions are ignored.
        - Does not modify the original input dictionary.
    """

    details = iface.get( "details" )
    if not isinstance( details, dict ):
        details = {}

    base = {
            **iface,
            "type":        int( iface["type"] ),
            "useip":       int( iface["useip"] ),
            "main":        int( iface["main"] ),
            "port":        int( iface["port"] ),
            "interfaceid": int( iface["interfaceid"] ),
    }
    
    version = details.get("version")
    if version is not None:
        try:
            version = int(version)
        except ValueError:
            version = None

    if version == 3:
        base.update({
            # SNMP
            "version":         int( details.get( "version", "0") ),
            "bulk":            int( details.get( "bulk", "1") ),
            "max_repetitions": int( details.get( "max_repetitions", "10") ),
            "securityname":    details.get( "securityname", "" ),
            "securitylevel":   int( details.get( "securitylevel", "0") ),
            "authpassphrase":  details.get( "authpassphrase", "" ),
            "privpassphrase":  details.get( "privpassphrase", "" ),
            "authprotocol":    int( details.get( "authprotocol", "") ),
            "privprotocol":    int( details.get( "privprotocol", "") ),
            "contextname":     details.get( "contextname", "" ),
        })

    # These are not implemented!
    elif version == 2:
        base.update({
            # SNMPv2c
            "version":         int( details.get( "version", "0") ),
            "bulk":            int( details.get( "bulk", "0") ),
            "max_repetitions": int( details.get( "max_repetitions", "0") ),
            "community":       details.get( "snmp_community", "" ),
        })
    
    elif version == 1:
        base.update({
            # SNMPv1
            "version":   int( details.get( "version", "0") ),
            "bulk":      int( details.get( "bulk", "0") ),
            "community": details.get( "snmp_community", "" ),
        })
    else:
        pass

    return base

