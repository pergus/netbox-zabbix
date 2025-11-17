"""
NetBox Zabbix Plugin — Data structures for Zabbix host import operations.

Defines the ImportHostContext dataclass that encapsulates all necessary information
for importing existing Zabbix hosts into NetBox as managed configurations.
"""

# Standard library
from typing import Union
from dataclasses import dataclass
from typing import Any

# Django imports
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType


# NetBox imports
from dcim.models import Device
from virtualization.models import VirtualMachine

@dataclass
class ImportHostContext:
    """
    Context object holding all information required to import a Zabbix host
    into NetBox for a device or virtual machine.
    
    Attributes:
        zabbix_host (dict): Zabbix host configuration.
        obj_instance (Device | VirtualMachine): The target NetBox instance.
        content_type (ContentType): The content type of the object instance.
        job (Any): JobResult instance representing the import job.
        user (User): The user triggering the import.
        request_id (str): HTTP request ID that initiated the import.
    """

    zabbix_host: dict
    # The host data fetched from Zabbix for this device/VM. Typically a dictionary
    # containing the configuration information that will be imported.

    obj_instance: Union[Device, VirtualMachine]
    # The Django model instance representing the object being imported.
    # Can be either a Device or a VirtualMachine instance.

    content_type: ContentType
    # The instance content type.

    job: Any
    # The NetBox JobResult instance representing the background job that is
    # performing the import. Used to log messages and associate the imported
    # configuration with the job.

    user: User
    # The user who triggered the import. Required for logging and for creating
    # change log entries.

    request_id: str
    # The ID of the HTTP request that initiated the job, if available.
    # Useful for tracing imports back to the original request in logs or changelog entries.

