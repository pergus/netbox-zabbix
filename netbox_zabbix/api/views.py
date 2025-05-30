from netbox.api.viewsets import NetBoxModelViewSet
from netbox_zabbix import models
from netbox_zabbix.api import serializers
from django_filters import rest_framework as filters


# ------------------------------------------------------------------------------
# Configuration
#

class ConfigViewSet(NetBoxModelViewSet):
    queryset = models.Config.objects.all()
    serializer_class = serializers.ConfigSerializer

# ------------------------------------------------------------------------------
# Templates
#

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


# ------------------------------------------------------------------------------
# Zabbix Configs
#

from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

class DeviceZabbixConfigViewSet(NetBoxModelViewSet):
    queryset = models.DeviceZabbixConfig.objects.all()
    serializer_class = serializers.DeviceZabbixConfigSerializer

    @action(detail=True, methods=['get'], url_path='primary-interface-data')
    def primary_interface_data(self, request, pk=None):
        host = get_object_or_404(models.DeviceZabbixConfig, pk=pk)
        device = host.device
    
        if not device.primary_ip4:
            return Response({})
    
        primary_ip = device.primary_ip4
        if primary_ip:
            assigned_object_id = primary_ip.assigned_object_id
            interface = Interface.objects.get( id=assigned_object_id )
    
            data = {
                'name': host.get_name(),
                'interface': interface.name,
                'interface_id': interface.pk,
                'ip_address': str(primary_ip.address),
                'ip_address_id': primary_ip.pk,
                'dns_name': str(primary_ip.dns_name or ""),
            }

            return Response(data)
        
        return Response({})

class VMZabbixConfigViewSet(NetBoxModelViewSet):
    queryset = models.VMZabbixConfig.objects.all()
    serializer_class = serializers.VMZabbixConfigSerializer

# ------------------------------------------------------------------------------
# Interfaces
#


from dcim.models import Interface

import logging
logger = logging.getLogger('netbox.plugins.netbox_zabbix')


class AvailableDeviceInterfaceFilter(filters.FilterSet):
    device_id = filters.NumberFilter( method='filter_device_id' )

    class Meta:
        model = Interface
        fields = ['device_id']
    
    def filter_device_id(self, queryset, name, value):

        host = models.DeviceZabbixConfig.objects.get(id=value)

        used_ids_agent = set( models.DeviceAgentInterface.objects.values_list( 'interface_id', flat=True ) )
        used_ids_snmp = set( models.DeviceSNMPv3Interface.objects.values_list( 'interface_id', flat=True ) )
        used_ids = used_ids_agent | used_ids_snmp

        return queryset.filter( device_id=host.device_id ).exclude( id__in=used_ids )


class AvailableDeviceInterfaceViewSet(NetBoxModelViewSet):
    queryset = Interface.objects.all()
    serializer_class = serializers.AvailableDeviceInterfaceSerializer
    filterset_class = AvailableDeviceInterfaceFilter


