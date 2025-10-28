# api/views.py

# Django imports
from django.contrib.contenttypes.models import ContentType

# Third-party imports
from django_filters import rest_framework as filters
from rest_framework.decorators import action
from rest_framework.response import Response

# NetBox core imports
from dcim.models import Device, Interface
from ipam.models import IPAddress
from virtualization.models import VirtualMachine, VMInterface
from netbox.api.viewsets import NetBoxModelViewSet

# NetBox Zabbix plugin imports
from netbox_zabbix.api import serializers
from netbox_zabbix.logger import logger
from netbox_zabbix.models import (
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

# ------------------------------------------------------------------------------
# Setting
# ------------------------------------------------------------------------------


class SettingViewSet(NetBoxModelViewSet):
    queryset = Setting.objects.all()
    serializer_class = serializers.SettingSerializer


# ------------------------------------------------------------------------------
# Templates
# ------------------------------------------------------------------------------


class TemplateFilter(filters.FilterSet):
    # The TemplateFilter class is a filter set designed to filter templates based on the name field.
    # This is required to search for template names in filter forms.
    q = filters.CharFilter( field_name="name", lookup_expr="icontains", label="Search Template" )

    class Meta:
        model = Template
        fields = ["q"]


class TemplateViewSet(NetBoxModelViewSet):
    queryset = Template.objects.all()
    serializer_class = serializers.TemplateSerializer
    filterset_class = TemplateFilter 


# ------------------------------------------------------------------------------
# Proxy
# ------------------------------------------------------------------------------


class ProxyFilter(filters.FilterSet):
    # The ProxyFilter class is a filter set designed to filter proxies based on the name field.
    # This is required to search for proxy names in filter forms.
    q = filters.CharFilter( field_name="name", lookup_expr="icontains", label="Search Proxies" )

    class Meta:
        model = Proxy
        fields = ["q"]


class ProxyViewSet(NetBoxModelViewSet):
    queryset = Proxy.objects.all()
    serializer_class = serializers.ProxySerializer
    filterset_class = ProxyFilter 


# ------------------------------------------------------------------------------
# Proxy Group
# ------------------------------------------------------------------------------


class ProxyGroupFilter(filters.FilterSet):
    # The ProxyFilter class is a filter set designed to filter proxies based on the name field.
    # This is required to search for proxy names in filter forms.
    q = filters.CharFilter( field_name="name", lookup_expr="icontains", label="Search Proxy Groups" )

    class Meta:
        model = ProxyGroup
        fields = ["q"]


class ProxyGroupViewSet(NetBoxModelViewSet):
    queryset = ProxyGroup.objects.all()
    serializer_class = serializers.ProxyGroupSerializer
    filterset_class = ProxyGroupFilter 


# ------------------------------------------------------------------------------
# Host Group
# ------------------------------------------------------------------------------


class HostGroupViewSet(NetBoxModelViewSet):
    queryset = HostGroup.objects.all()
    serializer_class = serializers.HostGroupSerializer
    filterset_fields = ['groupid', 'name']


# ------------------------------------------------------------------------------
# Tag Mapping
# ------------------------------------------------------------------------------


class TagMappingViewSet(NetBoxModelViewSet):
    queryset = TagMapping.objects.all()
    serializer_class = serializers.TagMappingSerializer


# ------------------------------------------------------------------------------
# Inventory Mapping
# ------------------------------------------------------------------------------


class InventoryMappingViewSet(NetBoxModelViewSet):
    queryset = InventoryMapping.objects.all()
    serializer_class = serializers.InventoryMappingSerializer


# ------------------------------------------------------------------------------
# Device Mapping
# ------------------------------------------------------------------------------


class DeviceMappingViewSet(NetBoxModelViewSet):
    queryset = DeviceMapping.objects.all()
    serializer_class = serializers.DeviceMappingSerializer
    #filterset_class = DeviceMappingFilter


# ------------------------------------------------------------------------------
# VM Mapping
# ------------------------------------------------------------------------------


class VMMappingViewSet(NetBoxModelViewSet):
    queryset = VMMapping.objects.all()
    serializer_class = serializers.VMMappingSerializer
    #filterset_class = VMMappingFilter


# ------------------------------------------------------------------------------
# Event Log
# ------------------------------------------------------------------------------


class EventLogViewSet(NetBoxModelViewSet):
    queryset = EventLog.objects.all()
    serializer_class = serializers.EventLogSerializer


# ------------------------------------------------------------------------------
# Unassgiend Hosts
# ------------------------------------------------------------------------------


class UnAssignedHostsViewSet(NetBoxModelViewSet):
    """
    API endpoint that returns Devices or VMs not already assigned
    to a Config. Used by ConfigForm.object_id (DynamicModelChoiceField).
    """
    queryset = Device.objects.none()
    serializer_class = serializers.UnAssignedHostsSerializer
    
    
    def get_queryset(self):
        """
        Dynamically build the queryset based on the `content_type` query param.
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
        logger.info( f" {qs[0].name}" )
        logger.info( f" UnAssingedHostsViewSet qs {qs}" )
        return qs


# ------------------------------------------------------------------------------
# Unassigned Interfaces
# ------------------------------------------------------------------------------


class UnAssignedInterfacesViewSet(NetBoxModelViewSet):
    """
    Generic viewset for unassigned interfaces (Agent or SNMP).
    Subclass or configure `queryset` and `serializer_class` for specific interface types.
    """

    queryset            = None         # override in subclass or instance
    serializer_class    = None         # override in subclass or instance

    @action(detail=True, methods=['get'], url_path='primary-interface')
    def primary_interface(self, request, pk=None):
        """
        Return the primary interface + IP for a HostConfig's assigned object (Device or VirtualMachine).
        Always returns a safe response.
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
    queryset = AgentInterface.objects.all()
    serializer_class = serializers.AgentInterfaceSerializer
    interface_type_name = "Agent"


# ------------------------------------------------------------------------------
# Unassigned SNMP Interfaces
# ------------------------------------------------------------------------------


class UnAssignedSNMPInterfacesViewSet(UnAssignedInterfacesViewSet):
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
            logger.error( f"UnAssignedHostInterfacesViewSet: error { str( e )}" )
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


# end