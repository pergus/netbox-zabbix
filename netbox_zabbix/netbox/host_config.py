"""
NetBox Zabbix Plugin — HostConfig Management Utilities

This module provides helper functions for creating and saving HostConfig
objects that link NetBox Device and VirtualMachine instances to their
corresponding Zabbix configuration entries.

Key functionality:

- `create_host_config(obj)`: Creates a HostConfig for a Device or VirtualMachine,
  including validation, content type resolution, signal bypassing, and error
  handling.

- `save_host_config(host_config)`: Validates and persists an existing HostConfig
  object, ensuring that plugin-related signals can be bypassed when needed.
"""


# Django imports
from django.contrib.contenttypes.models import ContentType

# NetBox Zabbix plugin imports
from netbox_zabbix import models

def create_host_config( obj ):
    """
    Create a HostConfig object for a Device or VirtualMachine.
    
    Args:
        obj (Device | VirtualMachine): Object for which to create the config.
    
    Returns:
        HostConfig: Newly created configuration object.
    
    Raises:
        Exception: If creation or validation fails.
    """
    try:
        content_type = ContentType.objects.get_for_model( obj )
        host_config = models.HostConfig( name=f"z-{obj.name}", content_type=content_type, object_id=obj.id )
        host_config.full_clean()

        # Mark this instance to bypass signals for this save operation only
        host_config._skip_signal = True
        host_config.save()

        return host_config
    
    except Exception as e:
        raise Exception( f"Failed to create Zabbix configuration: {e}" )


def save_host_config( host_config ):
    """
    Validate and save a HostConfig object to NetBox.
    
    Args:
        host_config (HostConfig): The configuration to save.
    """
    host_config.full_clean()
    host_config._skip_signal = True
    host_config.save()
