"""
NetBox Zabbix Plugin — API Views

This module provides the REST API endpoints for the NetBox Zabbix plugin.
It defines viewsets for Zabbix-related models, including settings, templates,
proxies, host groups, mappings, and event logs. Each viewset integrates with
Django REST Framework and NetBox's API framework, supporting standard CRUD
operations as well as filtering and custom actions.
"""

# Django imports
from django.contrib.contenttypes.models import ContentType

# Third-party imports
from django_filters import rest_framework as filters
from rest_framework.decorators import action
from rest_framework.response import Response

# NetBox imports
from dcim.models import Device, Interface
from ipam.models import IPAddress
from virtualization.models import VirtualMachine, VMInterface
from netbox.api.viewsets import NetBoxModelViewSet

# NetBox Zabbix plugin imports
from netbox_zabbix.api import serializers
from netbox_zabbix.models import (
    # Models
    Setting,
    Template,
    Proxy,
    ProxyGroup,
    HostGroup,
    TagMapping,
    InventoryMapping,
    DeviceMapping,
    VMMapping,
    EventLog,
    HostConfig,
    AgentInterface,
    SNMPInterface,
    )

from netbox_zabbix.filtersets import (
    HostGroupFilterSet,
    TagMappingFilterSet,
    InventoryMappingFilterSet,
    DeviceMappingFilterSet,
    VMMappingFilterSet,
    HostConfigFilterSet,
    AgentInterfaceFilterSet,
    SNMPInterfaceFilterSet
)
from netbox_zabbix.logger import logger


# ------------------------------------------------------------------------------
# Setting
# ------------------------------------------------------------------------------


class SettingViewSet(NetBoxModelViewSet):
    """
    API endpoint for managing Zabbix plugin settings.
    Provides standard CRUD operations for the Setting model.
    """
    queryset = Setting.objects.all()
    serializer_class = serializers.SettingSerializer


# ------------------------------------------------------------------------------
# Templates
# ------------------------------------------------------------------------------


class TemplateFilter(filters.FilterSet):
    """
    FilterSet for Template model.
    Allows filtering templates by name using the `q` query parameter
    (case-insensitive, partial match).
    """
    # The TemplateFilter class is a filter set designed to filter templates based on the name field.
    # This is required to search for template names in filter forms.
    q = filters.CharFilter( field_name="name", lookup_expr="icontains", label="Search Template" )

    class Meta:
        model = Template
        fields = ["q"]


class TemplateViewSet(NetBoxModelViewSet):
    """
    API endpoint for managing Templates.
    Supports listing, retrieving, creating, updating, and deleting Templates.
    Filtering is available via TemplateFilter.
    """
    queryset = Template.objects.all()
    serializer_class = serializers.TemplateSerializer
    filterset_class = TemplateFilter 


# ------------------------------------------------------------------------------
# Proxy
# ------------------------------------------------------------------------------


class ProxyFilter(filters.FilterSet):
    """
    FilterSet for Proxy model.
    Supports searching by name using the `q` query parameter.
    """
    # The ProxyFilter class is a filter set designed to filter proxies based on the name field.
    # This is required to search for proxy names in filter forms.
    q = filters.CharFilter( field_name="name", lookup_expr="icontains", label="Search Proxies" )

    class Meta:
        model = Proxy
        fields = ["q"]


class ProxyViewSet(NetBoxModelViewSet):
    """
    API endpoint for managing Zabbix Proxies.
    Supports standard CRUD operations and filtering by name.
    """
    queryset = Proxy.objects.all()
    serializer_class = serializers.ProxySerializer
    filterset_class = ProxyFilter 


# ------------------------------------------------------------------------------
# Proxy Group
# ------------------------------------------------------------------------------


class ProxyGroupFilter(filters.FilterSet):
    """
    FilterSet for ProxyGroup model.
    Supports searching by name using the `q` query parameter.
    """
    # The ProxyFilter class is a filter set designed to filter proxies based on the name field.
    # This is required to search for proxy names in filter forms.
    q = filters.CharFilter( field_name="name", lookup_expr="icontains", label="Search Proxy Groups" )

    class Meta:
        model = ProxyGroup
        fields = ["q"]


class ProxyGroupViewSet(NetBoxModelViewSet):
    """
    API endpoint for managing Zabbix Proxy Groups.
    Supports standard CRUD operations and filtering by name.
    """
    queryset = ProxyGroup.objects.all()
    serializer_class = serializers.ProxyGroupSerializer
    filterset_class = ProxyGroupFilter 


# ------------------------------------------------------------------------------
# Host Group
# ------------------------------------------------------------------------------


class HostGroupViewSet(NetBoxModelViewSet):
    """
    API endpoint for managing Zabbix Host Groups.
    Supports standard CRUD operations.
    Filtering is provided via HostGroupFilterSet.
    """
    queryset = HostGroup.objects.all()
    serializer_class = serializers.HostGroupSerializer
    filterset_class = HostGroupFilterSet


# ------------------------------------------------------------------------------
# Tag Mapping
# ------------------------------------------------------------------------------


class TagMappingViewSet(NetBoxModelViewSet):
    """
    API endpoint for managing Tag Mappings.
    Supports standard CRUD operations.
    Filtering is provided via TagMappingFilterSet.
    """
    queryset = TagMapping.objects.all()
    serializer_class = serializers.TagMappingSerializer
    filterset_class = TagMappingFilterSet


# ------------------------------------------------------------------------------
# Inventory Mapping
# ------------------------------------------------------------------------------


class InventoryMappingViewSet(NetBoxModelViewSet):
    """
    API endpoint for managing Inventory Mappings.
    Supports standard CRUD operations.
    Filtering is provided via InventoryMappingFilterSet.
    """
    queryset = InventoryMapping.objects.all()
    serializer_class = serializers.InventoryMappingSerializer
    filterset_class = InventoryMappingFilterSet


# ------------------------------------------------------------------------------
# Device Mapping
# ------------------------------------------------------------------------------


class DeviceMappingViewSet(NetBoxModelViewSet):
    """
    API endpoint for managing Device Mappings.
    Supports standard CRUD operations.
    Filtering is provided via DeviceMappingFilterSet.
    """
    queryset = DeviceMapping.objects.all()
    serializer_class = serializers.DeviceMappingSerializer
    filterset_class  = DeviceMappingFilterSet


# ------------------------------------------------------------------------------
# VM Mapping
# ------------------------------------------------------------------------------


class VMMappingViewSet(NetBoxModelViewSet):
    """
    API endpoint for managing Virtual Machine Mappings.
    Supports standard CRUD operations.
    Filtering is provided via VMMappingFilterSet.
    """
    queryset = VMMapping.objects.all()
    serializer_class = serializers.VMMappingSerializer
    filterset_class = VMMappingFilterSet


# ------------------------------------------------------------------------------
# Host Config
# ------------------------------------------------------------------------------


class HostConfigViewSet(NetBoxModelViewSet):
    """
    API endpoint for managing Host Configurations.
    Supports standard CRUD operations.
    Filtering is provided via HostConfigFilterSet.
    """
    queryset = HostConfig.objects.all()
    serializer_class = serializers.HostConfigSerializer
    filterset_class = HostConfigFilterSet


# ------------------------------------------------------------------------------
# Agent Interface
# ------------------------------------------------------------------------------


class AgentInterfaceViewSet(NetBoxModelViewSet):
    """
    API endpoint for managing Agent Interfaces.
    Supports standard CRUD operations.
    Filtering is provided via AgentInterfaceFilterSet.
    """
    queryset = AgentInterface.objects.all()
    serializer_class = serializers.AgentInterfaceSerializer
    filterset_class = AgentInterfaceFilterSet


# ------------------------------------------------------------------------------
# SNMP Interface
# ------------------------------------------------------------------------------


class SNMPInterfaceViewSet(NetBoxModelViewSet):
    """
    API endpoint for managing SNMP Interfaces.
    Supports standard CRUD operations.
    Filtering is provided via SNMPInterfaceFilterSet.
    """
    queryset = SNMPInterface.objects.all()
    serializer_class = serializers.SNMPInterfaceSerializer
    filterset_class = SNMPInterfaceFilterSet


# ------------------------------------------------------------------------------
# Event Log
# ------------------------------------------------------------------------------


class EventLogViewSet(NetBoxModelViewSet):
    """
    API endpoint for viewing Zabbix Event Logs.
    Read-only: list and retrieve operations.
    """
    queryset = EventLog.objects.all()
    serializer_class = serializers.EventLogSerializer


# ------------------------------------------------------------------------------
# Unassgiend Hosts
# ------------------------------------------------------------------------------


class UnAssignedHostsViewSet(NetBoxModelViewSet):
    """
    API endpoint that returns Devices or VirtualMachines not yet assigned to a HostConfig.
    Used for dynamic model selection in forms (DynamicModelChoiceField).
    """
    queryset = Device.objects.none()
    serializer_class = serializers.UnAssignedHostsSerializer
    
    
    def get_queryset(self):
        """
        Dynamically builds and returns the queryset of unassigned Devices or VirtualMachines
        based on the `content_type` query parameter.
        
        Returns:
            QuerySet: Objects of the specified model type not linked to any HostConfig.
        """
        content_type_id = self.request.query_params.get( "content_type" )
        if not content_type_id:
            return Device.objects.none()
    
        # Identify the model from content type
        ct = ContentType.objects.get( pk=content_type_id )
        model = ct.model_class()
    
        # Get IDs already linked to a HostConfig
        used_ids = HostConfig.objects.filter( content_type=ct ).values_list( "object_id", flat=True )
        
        # Return objects that are not yet assigned
        qs =  model.objects.exclude( id__in=used_ids )
        return qs


# ------------------------------------------------------------------------------
# Unassigned Interfaces
# ------------------------------------------------------------------------------


class UnAssignedInterfacesViewSet(NetBoxModelViewSet):
    """
    Base API endpoint for returning unassigned interfaces (Agent or SNMP).
    Subclasses should set `queryset` and `serializer_class`.
    """

    queryset            = None         # override in subclass or instance
    serializer_class    = None         # override in subclass or instance

    @action(detail=True, methods=['get'], url_path='primary-interface')
    def primary_interface(self, request, pk=None):
        """
        Returns the primary interface and associated IP address for a HostConfig's assigned object.
        Supports both Device and VirtualMachine objects.
        
        Args:
            request (HttpRequest): The current HTTP request.
            pk (int, optional): The HostConfig primary key.
        
        Returns:
            Response: JSON object with `interface_id`, `ip_address_id`, and `dns_name`, or 404/500.
        """
        try:
            config = HostConfig.objects.filter(pk=pk).first()
            if not config:
                return Response({}, status=404)

            assigned_object = getattr(config, "assigned_object", None)
            if not assigned_object:
                return Response({}, status=404)

            primary_ip = getattr(assigned_object, "primary_ip4", None)
            if not primary_ip:
                return Response({}, status=404)

            interface_obj = getattr(primary_ip, "assigned_object", None)
            interface = getattr(interface_obj, "interface", None) or interface_obj

            if not interface:
                return Response({}, status=404)

            data = {
                "interface_id": interface.pk,
                "ip_address_id": primary_ip.pk,
                "dns_name": primary_ip.dns_name or "",
            }

            return Response(data)

        except Exception as e:
            return Response({}, status=500)


# ------------------------------------------------------------------------------
# Unassigned Agent Interfaces
# ------------------------------------------------------------------------------

class UnAssignedAgentInterfacesViewSet(UnAssignedInterfacesViewSet):
    """
    API endpoint for returning unassigned Agent Interfaces.
    """
    queryset = AgentInterface.objects.all()
    serializer_class = serializers.AgentInterfaceSerializer
    interface_type_name = "Agent"


# ------------------------------------------------------------------------------
# Unassigned SNMP Interfaces
# ------------------------------------------------------------------------------


class UnAssignedSNMPInterfacesViewSet(UnAssignedInterfacesViewSet):
    """
    API endpoint for returning unassigned SNMP Interfaces.
    """
    queryset = SNMPInterface.objects.all()
    serializer_class = serializers.SNMPInterfaceSerializer
    interface_type_name = "SNMP"



# ------------------------------------------------------------------------------
# Unassigned Host Interfaces
# ------------------------------------------------------------------------------


class UnAssignedHostInterfacesViewSet(NetBoxModelViewSet):
    """
    API endpoint that returns the unassigned interfaces for a Device or VirtualMachine.
    """
    queryset = Interface.objects.none()
    serializer_class = serializers.UnAssignedHostInterfacesSerializer

    def get_queryset(self):
        """
        Returns interfaces for the assigned object (Device or VirtualMachine)
        linked to the specified HostConfig, excluding interfaces already assigned.
        
        Returns:
            QuerySet: Unassigned Interface or VMInterface objects.
        """
        qs = self.queryset  # default empty queryset

        try:
            config_pk = self.request.query_params.get( "config_pk" )
            if not config_pk:
                return qs

            config = HostConfig.objects.filter( pk=config_pk ).first()
            if not config:
                return qs

            assigned_object = getattr( config, "assigned_object", None )
            if not assigned_object:
                return qs

            if isinstance( assigned_object, Device ):
                qs = Interface.objects.filter( device=assigned_object )
            elif isinstance( assigned_object, VirtualMachine ):
                qs = VMInterface.objects.filter( virtual_machine=assigned_object )
            else:
                return qs.none()
            
            # Exclude interfaces already assigned to AgentInterface or SNMPInterface
            assigned_interface_ids = list(
                AgentInterface.objects.filter( host_config=config ).values_list( "interface_id", flat=True )
            ) + list(
                SNMPInterface.objects.filter( host_config=config ).values_list( "interface_id", flat=True )
            )
            qs = qs.exclude( pk__in=assigned_interface_ids )


        except Exception as e:
            qs = qs.none()

        return qs


# ------------------------------------------------------------------------------
# Unassigned Host IP  Addresses
# ------------------------------------------------------------------------------


class UnAssignedHostIPAddressesViewSet(NetBoxModelViewSet):
    """
    API endpoint that returns the IP addresses for an Interface or VMInterface.
    """
    queryset = IPAddress.objects.none()
    serializer_class = serializers.UnAssignedHostIPAddressesSerializer

    def get_queryset(self):
        """
        Returns IP addresses for a given interface linked to a HostConfig's assigned object.
        
        Query parameters:
            config_pk (int): The HostConfig primary key.
            interface_pk (int): The Interface or VMInterface primary key.
        
        Returns:
            QuerySet: IPAddress objects associated with the interface.
        """
        qs = self.queryset
        request = self.request
        config_pk = request.query_params.get( "config_pk" )
        interface_pk = request.query_params.get( "interface_pk" )
        
        if not config_pk:
            return qs

        if not interface_pk:
            return qs
        
        try:
            config = HostConfig.objects.get( pk=config_pk )
        except Exception:
            return qs
    
        assigned_object = getattr( config, "assigned_object", None )
        if not assigned_object:
            return qs

        interface = None
        try:
            if isinstance( assigned_object, Device ):
                interface = Interface.objects.get( id=interface_pk )

            elif isinstance(assigned_object, VirtualMachine):
                interface = VMInterface.objects.get( id=interface_pk )

            else:
                return qs

        except Exception:
            return qs

        # Finally, return IPs linked to that interface
        if interface:
            qs = interface.ip_addresses.all()
    
        return qs

# ------------------------------------------------------------------------------
# Maintenance
# ------------------------------------------------------------------------------

from netbox_zabbix.models import Maintenance
from netbox_zabbix.api.serializers import MaintenanceSerializer
class MaintenanceViewSet(NetBoxModelViewSet):
    """
    API viewset for managing Maintenance objects.
    """
    queryset = Maintenance.objects.all()
    serializer_class = MaintenanceSerializer


# end