"""
NetBox Zabbix Plugin — API Serializers Package

This module exposes all serializers for the NetBox Zabbix plugin's API.
Importing this package provides access to every serializer used by the
plugin's REST API viewsets.
"""

from .serializers import (
    SettingSerializer,
    TemplateSerializer,
    ProxySerializer,
    ProxyGroupSerializer,
    HostGroupSerializer,
    TagMappingSerializer,
    InventoryMappingSerializer,
    MappingSerializer,
    DeviceMappingSerializer,
    VMMappingSerializer,
    HostConfigSerializer,
    AgentInterfaceSerializer,
    SNMPInterfaceSerializer,
    EventLogSerializer,
    UnAssignedHostsSerializer,
    UnAssignedAgentInterfacesSerializer,
    UnAssignedSNMPInterfaceSerializer,
    UnAssignedHostInterfacesSerializer,
    UnAssignedHostIPAddressesSerializer,
    )