"""
NetBox Zabbix Plugin — Host CRUD Operations

This module implements all create, update, and delete operations for Zabbix
hosts as managed through NetBox. It provides:

- Host creation using NetBox HostConfig definitions
- Full update logic respecting host synchronization modes
- Hard deletion (permanent removal) in Zabbix
- Soft deletion workflows including archival renaming and reassignment to a
  graveyard host group

All operations ensure data integrity, raise detailed exceptions on failure,
and integrate with NetBox’s changelog and job-tracking mechanisms.
"""


from netbox_zabbix import settings, models
from netbox_zabbix.zabbix import builders
from netbox_zabbix.zabbix import api as zapi
from netbox_zabbix.exceptions import ExceptionWithData
from netbox_zabbix.netbox.changelog import log_update_event


def create_zabbix_host( host_config ):
    """
    Create a host in Zabbix via the API using a HostConfig.
    
    Args:
        host_config (HostConfig): Configuration object representing the host.
    
    Returns:
        tuple[int, dict]: Zabbix host ID and the payload sent to the API.
    
    Raises:
        ExceptionWithData: If the creation fails or hostid is not returned.
    """
    payload = builders.payload( host_config, for_update=False )
        
    try:
        result = zapi.create_host( **payload )
    except Exception as e:
        raise ExceptionWithData( f"Failed to create host in Zabbix {str( e) }", payload )
    
    hostid = result.get( "hostids", [None] )[0]
    if not hostid:
        raise ExceptionWithData( f"Zabbix failed to return hostid for {host_config.devm_name()}", payload )
    return int( hostid ), payload


def update_zabbix_host(host_config, user, request_id):
    """
    Update an existing Zabbix host based on its HostConfig.

    Performs:
        - Fetching current host state from Zabbix
        - Determining templates/groups/tags to remove/add.
        - Sending host.update() payload to Zabbix
        - Logging changelog entry in NetBox

    Args:
        host_config (HostConfig): Configuration object representing the host.
        user (User): NetBox user performing the update.
        request_id (str): Request ID for changelog tracking.

    Returns:
        dict: Message and pre/post payload data.

    Raises:
        ExceptionWithData: If update fails.
    """
    if not isinstance( host_config, models.HostConfig ):
        raise ValueError( "host_config must be an instance of HostConfig" )

    # Fetch current state of the host in Zabbix
    try:
        pre_data = zapi.get_host_by_id_with_templates( host_config.hostid )

    except Exception as e:
        raise Exception( f"Failed to get host by id from Zabbix: {str(e)}" )

    # Build base payload
    payload = builders.payload( host_config, for_update=True )
    

    # Current template IDs in Zabbix (directly assigned to host)
    current_template_ids = set( t["templateid"] for t in pre_data.get( "templates", [] ) )
        
    # Templates currently assigned in NetBox
    new_template_ids = set( str( tid ) for tid in host_config.templates.values_list( "templateid", flat=True ) )
        
    # Only remove templates that are no longer assigned
    removed_template_ids = current_template_ids - new_template_ids
    templates_clear = [ {"templateid": tid} for tid in removed_template_ids ]
        
    # Build payload for update
    payload = builders.payload( host_config, for_update=True )
    if templates_clear:
        payload[ "templates_clear" ] = templates_clear

    # Update the host in Zabbix
    try:
        zapi.update_host( **payload )
    except Exception as e:
        if isinstance( e, ExceptionWithData ):
            raise
        raise ExceptionWithData(
            f"Failed to update Zabbix host {host_config.name}: {e}",
            pre_data=pre_data,
            post_data=payload,
        )

    # Document the update in NetBox
    log_update_event( host_config, user, request_id )

    return {
        "message": f"Updated Zabbix host {host_config.hostid}",
        "pre_data": pre_data,
        "post_data": payload,
    }


def delete_zabbix_host_hard(hostid):
    """
    Permanently deletes a Zabbix host by its ID.
    
    Args:
        hostid (int): The ID of the Zabbix host to delete.
    
    Returns:
        dict: Message confirming deletion and the original host data.
    
    Raises:
        Exception: If deletion fails unexpectedly.
    """
    if hostid:
        try:
            data = zapi.get_host_by_id_with_templates( hostid )
            zapi.delete_host( hostid )
            return { "message": f"Deleted zabbix host {hostid}", "data": data }
        
        except zapi.ZabbixHostNotFound as e:
            msg = f"Failed to soft delete Zabbix host {hostid}: {str( e )}"
            return { "message": msg }
        
        except Exception as e:
            msg = f"Failed to delete Zabbix host {hostid}: {str( e )}"
            raise Exception( msg )


def delete_zabbix_host_soft(hostid):
    """
    Soft-deletes a Zabbix host by renaming it, disabling it, and moving it to a graveyard group.
    
    Args:
        hostid (int): The ID of the Zabbix host to soft-delete.
    
    Returns:
        dict: Message confirming soft deletion, the new host name, and original host data.
    
    Notes:
        - Ensures unique host names in the graveyard by appending a counter if necessary.
        - Creates the graveyard group if it does not exist.
    """
    if hostid:
        try:
            data = zapi.get_host_by_id_with_templates( hostid )
            hostname = data["host"]

            suffix = settings.get_graveyard_suffix()
            base_archived_name = f"{hostname}{suffix}"
            archived_host_name = base_archived_name
            
            # Ensure uniqueness by checking existence
            counter = 1
            while True:
                try:
                    zapi.get_host( archived_host_name, log_errors=False )

                    # Try next if the host already exists
                    archived_host_name = f"{base_archived_name}-{counter}"
                    counter += 1

                except Exception as e:
                    break
            

            # Ensure graveyard group exists
            graveyard_group_name = settings.get_graveyard()
            
            try:
                # Try to fetch the graveyard group
                graveyard_group = zapi.get_host_group( name=graveyard_group_name )
                graveyard_group_id = graveyard_group["groupid"]
            except Exception:
                # Group does not exist create it
                result = zapi.create_host_group( name=graveyard_group_name )
                graveyard_group_id = result["groupids"][0]
                zapi.import_host_groups()
                

            # Rename, disable and move the host in Zabbix.
            zapi.update_host( hostid=hostid, host=archived_host_name, groups=[{"groupid": graveyard_group_id}], status=1 )

            return {
                "message": f"Soft-deleted Zabbix host {hostid}, renamed to '{archived_host_name}' moved to group '{graveyard_group_name}'",
                "data": data,
            }

        except zapi.ZabbixHostNotFound as e:
            msg = f"Failed to soft delete Zabbix host {hostid}: {str( e )}"
            return { "message": msg }

        except Exception as e:
            msg = f"Failed to soft delete Zabbix host {hostid}: {str( e )}"
            raise Exception( msg )

