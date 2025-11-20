"""
NetBox Zabbix Plugin — Custom Field Utilities

This module provides helper functionality for ensuring that required NetBox
custom fields exist and are correctly associated with both Device and
VirtualMachine objects.

Key functionality:

- `create_netbox_custom_field(name, defaults)`: Creates a custom field if it
  does not already exist and assigns it to the Device and VirtualMachine
  content types. Ensures consistent field configuration and avoids duplicate
  field definitions across plugin components.
"""

# Django imports
from django.contrib.contenttypes.models import ContentType

# NetBox imports
from extras.models import CustomField
from dcim.models import Device
from virtualization.models import VirtualMachine


def create_netbox_custom_field(name, defaults):
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
