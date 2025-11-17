"""
NetBox Zabbix Plugin — Provisioning Context Data Structures

This module defines data structures used for Zabbix host provisioning
operations in NetBox.

Main class:

- `ProvisionContext`: Encapsulates all necessary information for creating
  and configuring a Zabbix host, including:
    - Target object (Device or VirtualMachine)
    - Interface model (AgentInterface or SNMPInterface)
    - Interface naming suffix
    - Associated background job and user
    - Request ID for changelog tracking
    - Callable providing additional interface parameters

This structured context is used to standardize provisioning operations
and facilitate reliable creation of host configurations and interfaces.
"""

# Standard library
from dataclasses import dataclass, field
from typing import Any, Type, Callable


@dataclass
class ProvisionContext:
    """
    Context object for provisioning a Zabbix host.
    
    Attributes:
        object (Device | VirtualMachine): Host being provisioned.
        interface_model (Type): Interface class (AgentInterface or SNMPInterface).
        interface_name_suffix (str): Suffix for interface names.
        job (JobResult): Background job performing the import.
        user (User): NetBox user performing the action.
        request_id (str): Request ID for changelog tracking.
        interface_kwargs_fn (Callable): Function returning extra kwargs for interface creation.
    """
    object: Any
    # The Device or VM being provisioned

    interface_model: Type  
    # The interface model (Agent or SNMP)

    interface_name_suffix: str  
    # Name suffix to append to the interface name (e.g., "agent", "snmp")

    job: Any
    # The NetBox JobResult instance representing the background job that is
    # performing the import. Used to log messages and associate the imported
    # configuration with the job.

    user: Any  
    # NetBox user performing the action

    request_id: str 
    # Request ID for changelog tracking

    interface_kwargs_fn: Callable[[], dict] = field(default_factory=dict)  
    # Function that returns extra kwargs for interface creation

