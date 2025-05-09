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
    q = filters.CharFilter(field_name="name", lookup_expr="icontains", label="Search Template")

    class Meta:
        model = models.Template
        fields = ["q"]
        
class TemplateViewSet(NetBoxModelViewSet):
    queryset = models.Template.objects.all()
    serializer_class = serializers.TemplateSerializer
    filterset_class = TemplateFilter 


# ------------------------------------------------------------------------------
# Hosts
#


class DeviceHostViewSet(NetBoxModelViewSet):
    queryset = models.DeviceHost.objects.all()
    serializer_class = serializers.DeviceHostSerializer


class VMHostViewSet(NetBoxModelViewSet):
    queryset = models.VMHost.objects.all()
    serializer_class = serializers.VMHostSerializer

# ------------------------------------------------------------------------------
# Interfaces
#


from dcim.models import Interface

class AvailableDeviceInterfaceFilter(filters.FilterSet):
    device_id = filters.NumberFilter(method='filter_device_id')

    class Meta:
        model = Interface
        fields = ['device_id']

    def filter_device_id(self, queryset, name, value):
        used_ids = models.DeviceAgentInterface.objects.values_list( 'interface_id', flat=True )
        return queryset.filter( device_id=value ).exclude( id__in=used_ids )


class AvailableDeviceInterfaceViewSet(NetBoxModelViewSet):
    queryset = Interface.objects.all()
    serializer_class = serializers.AvailableDeviceInterfaceSerializer
    filterset_class = AvailableDeviceInterfaceFilter