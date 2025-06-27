from netbox.api.viewsets import NetBoxModelViewSet
from netbox_zabbix import models
from netbox_zabbix.api import serializers
from django_filters import rest_framework as filters

from dcim.models import Interface
from virtualization.models import VMInterface
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404


# ------------------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------------------

class ConfigViewSet(NetBoxModelViewSet):
    queryset = models.Config.objects.all()
    serializer_class = serializers.ConfigSerializer

# ------------------------------------------------------------------------------
# Templates
# ------------------------------------------------------------------------------

class TemplateFilter(filters.FilterSet):
    # The TemplateFilter class is a filter set designed to filter templates based on the name field.
    # This is required to search for template names in filter forms.
    q = filters.CharFilter( field_name="name", lookup_expr="icontains", label="Search Template" )

    class Meta:
        model = models.Template
        fields = ["q"]

        
class TemplateViewSet(NetBoxModelViewSet):
    queryset = models.Template.objects.all()
    serializer_class = serializers.TemplateSerializer
    filterset_class = TemplateFilter 


class TemplateMappingFilter(filters.FilterSet):
    q = filters.CharFilter( field_name="name", lookup_expr="icontains", label="Search Template Mappings" )

    class Meta:
        model = models.TemplateMapping
        fields = ["q"]


# ------------------------------------------------------------------------------
# Template Mapping
# ------------------------------------------------------------------------------

class TemplateMappingViewSet(NetBoxModelViewSet):
    queryset = models.TemplateMapping.objects.all()
    serializer_class = serializers.TemplateMappingSerializer
    filterset_class = TemplateMappingFilter



# ------------------------------------------------------------------------------
# Proxy
# ------------------------------------------------------------------------------

class ProxyFilter(filters.FilterSet):
    # The ProxyFilter class is a filter set designed to filter proxies based on the name field.
    # This is required to search for proxy names in filter forms.
    q = filters.CharFilter( field_name="name", lookup_expr="icontains", label="Search Proxies" )

    class Meta:
        model = models.Proxy
        fields = ["q"]

        
class ProxyViewSet(NetBoxModelViewSet):
    queryset = models.Proxy.objects.all()
    serializer_class = serializers.ProxySerializer
    filterset_class = ProxyFilter 



# ------------------------------------------------------------------------------
# Proxy Mapping
# ------------------------------------------------------------------------------

class ProxyMappingFilter(filters.FilterSet):
    q = filters.CharFilter( field_name="name", lookup_expr="icontains", label="Search Proxy Mappings" )

    class Meta:
        model = models.ProxyMapping
        fields = ["q"]

class ProxyMappingViewSet(NetBoxModelViewSet):
    queryset = models.ProxyMapping.objects.all()
    serializer_class = serializers.ProxyMappingSerializer
    filterset_class = ProxyMappingFilter




# ------------------------------------------------------------------------------
# Proxy Group
# ------------------------------------------------------------------------------

class ProxyGroupFilter(filters.FilterSet):
    # The ProxyFilter class is a filter set designed to filter proxies based on the name field.
    # This is required to search for proxy names in filter forms.
    q = filters.CharFilter( field_name="name", lookup_expr="icontains", label="Search Proxy Groups" )

    class Meta:
        model = models.ProxyGroup
        fields = ["q"]

        
class ProxyGroupViewSet(NetBoxModelViewSet):
    queryset = models.ProxyGroup.objects.all()
    serializer_class = serializers.ProxyGroupSerializer
    filterset_class = ProxyGroupFilter 

# ------------------------------------------------------------------------------
# Proxy Group Mapping
# ------------------------------------------------------------------------------

class ProxyGroupMappingFilter(filters.FilterSet):
    q = filters.CharFilter( field_name="name", lookup_expr="icontains", label="Search Proxy Group Mappings" )

    class Meta:
        model = models.ProxyGroupMapping
        fields = ["q"]

class ProxyGroupMappingViewSet(NetBoxModelViewSet):
    queryset = models.ProxyGroupMapping.objects.all()
    serializer_class = serializers.ProxyGroupMappingSerializer
    filterset_class = ProxyGroupMappingFilter



# ------------------------------------------------------------------------------
# Host Groups
# ------------------------------------------------------------------------------

class HostGroupViewSet(NetBoxModelViewSet):
    queryset = models.HostGroup.objects.all()
    serializer_class = serializers.HostGroupSerializer
    filterset_fields = ['groupid', 'name']


# ------------------------------------------------------------------------------
# Host Group Mapping
# ------------------------------------------------------------------------------

class HostGroupMappingFilter(filters.FilterSet):
    q = filters.CharFilter( field_name="name", lookup_expr="icontains", label="Search Group Mappings" )

    class Meta:
        model = models.HostGroupMapping
        fields = ["q"]

class HostGroupMappingViewSet(NetBoxModelViewSet):
    queryset = models.HostGroupMapping.objects.all()
    serializer_class = serializers.HostGroupMappingSerializer
    filterset_class = HostGroupMappingFilter


# ------------------------------------------------------------------------------
# Host Group Mapping
# ------------------------------------------------------------------------------

class TagMappingViewSet(NetBoxModelViewSet):
    queryset = models.TagMapping.objects.all()
    serializer_class = serializers.TagMappingSerializer
    
# ------------------------------------------------------------------------------
# Zabbix Configurations
# ------------------------------------------------------------------------------

class DeviceZabbixConfigViewSet(NetBoxModelViewSet):
    queryset = models.DeviceZabbixConfig.objects.all()
    serializer_class = serializers.DeviceZabbixConfigSerializer

    @action(detail=True, methods=['get'], url_path='primary-interface-data')
    def primary_interface_data(self, request, pk=None):
        zabbix_config = get_object_or_404(models.DeviceZabbixConfig, pk=pk)
        device = zabbix_config.device
    
        if not device.primary_ip4:
            return Response({})
    
        primary_ip = device.primary_ip4
        if primary_ip:
            assigned_object_id = primary_ip.assigned_object_id
            interface = Interface.objects.get( id=assigned_object_id )
    
            data = {
                'name': zabbix_config.get_name(),
                'interface': interface.name,
                'interface_id': interface.pk,
                'ip_address': str( primary_ip.address ),
                'ip_address_id': primary_ip.pk,
                'dns_name': str( primary_ip.dns_name or "" ),
            }

            return Response(data)
        
        return Response({})

class VMZabbixConfigViewSet(NetBoxModelViewSet):
    queryset = models.VMZabbixConfig.objects.all()
    serializer_class = serializers.VMZabbixConfigSerializer

    @action(detail=True, methods=['get'], url_path='primary-interface-data')
    def primary_interface_data(self, request, pk=None):
        zabbix_config = get_object_or_404(models.VMZabbixConfig, pk=pk)
        vm = zabbix_config.virtual_machine
    
        if not vm.primary_ip4:
            return Response({})
    
        primary_ip = vm.primary_ip4
        if primary_ip:
            assigned_object_id = primary_ip.assigned_object_id
            interface = Interface.objects.get( id=assigned_object_id )
    
            data = {
                'name': zabbix_config.get_name(),
                'interface': interface.name,
                'interface_id': interface.pk,
                'ip_address': str( primary_ip.address ),
                'ip_address_id': primary_ip.pk,
                'dns_name': str( primary_ip.dns_name or "" ),
            }
    
            return Response(data)
        
        return Response({})
    
# ------------------------------------------------------------------------------
# Interfaces
# ------------------------------------------------------------------------------


class AvailableDeviceInterfaceFilter(filters.FilterSet):
    device_id = filters.NumberFilter( method='filter_device_id' )

    class Meta:
        model = Interface
        fields = ['device_id']
    
    def filter_device_id(self, queryset, name, value):

        zabbix_config = models.DeviceZabbixConfig.objects.get( id=value )

        used_ids_agent = set( models.DeviceAgentInterface.objects.values_list( 'interface_id', flat=True ) )
        used_ids_snmp = set( models.DeviceSNMPv3Interface.objects.values_list( 'interface_id', flat=True ) )
        used_ids = used_ids_agent | used_ids_snmp

        return queryset.filter( device_id=zabbix_config.device_id ).exclude( id__in=used_ids )


class AvailableDeviceInterfaceViewSet(NetBoxModelViewSet):
    queryset = Interface.objects.all()
    serializer_class = serializers.AvailableDeviceInterfaceSerializer
    filterset_class = AvailableDeviceInterfaceFilter


class AvailableVMInterfaceFilter(filters.FilterSet):
    virtual_machine_id = filters.NumberFilter( method='filter_virtual_machine_id' )

    class Meta:
        model = VMInterface
        fields = ['virtual_machine_id']
    
    def filter_virtual_machine_id(self, queryset, name, value):

        zabbix_config = models.VMZabbixConfig.objects.get( id=value )

        used_ids_agent = set( models.VMAgentInterface.objects.values_list( 'interface_id', flat=True ) )
        used_ids_snmp = set( models.VMSNMPv3Interface.objects.values_list( 'interface_id', flat=True ) )
        used_ids = used_ids_agent | used_ids_snmp

        return queryset.filter( virtual_machine_id=zabbix_config.virtual_machine_id ).exclude( id__in=used_ids )


class AvailableVMInterfaceViewSet(NetBoxModelViewSet):
    queryset = VMInterface.objects.all()
    serializer_class = serializers.AvailableVMInterfaceSerializer
    filterset_class = AvailableVMInterfaceFilter


# ------------------------------------------------------------------------------
# Device Mapping
# ------------------------------------------------------------------------------


class DeviceMappingViewSet(NetBoxModelViewSet):
    queryset = models.DeviceMapping.objects.all()
    serializer_class = serializers.DeviceMappingSerializer
    #filterset_class = DeviceMappingFilter

# ------------------------------------------------------------------------------
# VM Mapping
# ------------------------------------------------------------------------------


class VMMappingViewSet(NetBoxModelViewSet):
    queryset = models.VMMapping.objects.all()
    serializer_class = serializers.VMMappingSerializer
    #filterset_class = VMMappingFilter

# end