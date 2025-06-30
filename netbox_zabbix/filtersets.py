# filterset.py
import django_filters

from dcim.models import Device
from dcim.filtersets import DeviceFilterSet

from virtualization.models import VirtualMachine
from virtualization.filtersets import VirtualMachineFilterSet
from netbox.filtersets import NetBoxModelFilterSet
from netbox_zabbix import models


# Configuration doesn't have a filterset

# ------------------------------------------------------------------------------
# Templates
# ------------------------------------------------------------------------------

class TemplateFilterSet(NetBoxModelFilterSet):
    class Meta:
        model = models.Template
        fields = [ 'name', 'templateid', 'marked_for_deletion' ]

    name = django_filters.ModelMultipleChoiceFilter(
            field_name='name',
            to_field_name='name',  # match by template name instead of PK
            queryset=models.Template.objects.all(),
            label="Name"
        )

# ------------------------------------------------------------------------------
# Proxy
# ------------------------------------------------------------------------------

class ProxyFilterSet(NetBoxModelFilterSet):
    class Meta:
        model = models.Proxy
        fields = [ 'name', 'proxyid', 'proxy_groupid', 'marked_for_deletion' ]

    name = django_filters.ModelMultipleChoiceFilter(
            field_name='name',
            to_field_name='name',  # match by template name instead of PK
            queryset=models.Proxy.objects.all(),
            label="Name"
        )


# ------------------------------------------------------------------------------
# Proxy Group
# ------------------------------------------------------------------------------

class ProxyGroupFilterSet(NetBoxModelFilterSet):
    class Meta:
        model = models.ProxyGroup
        fields = [ 'name', 'proxy_groupid', 'marked_for_deletion' ]

    name = django_filters.ModelMultipleChoiceFilter(
            field_name='name',
            to_field_name='name',  # match by template name instead of PK
            queryset=models.ProxyGroup.objects.all(),
            label="Name"
        )


# ------------------------------------------------------------------------------
# Host Group Device
# ------------------------------------------------------------------------------

class HostGroupDeviceFilterSet(DeviceFilterSet):
    class Meta(DeviceFilterSet.Meta):
        model = Device
        fields = DeviceFilterSet.Meta.fields


# ------------------------------------------------------------------------------
# Host Group VM
# ------------------------------------------------------------------------------

class HostGroupVMFilterSet(VirtualMachineFilterSet):
    class Meta(VirtualMachineFilterSet.Meta):
        model = VirtualMachine
        fields = VirtualMachineFilterSet.Meta.fields



# ------------------------------------------------------------------------------
# Zabbix Configurations
# ------------------------------------------------------------------------------

class DeviceZabbixConfigFilterSet(NetBoxModelFilterSet):
    class Meta:
        model = models.DeviceZabbixConfig
        fields = [ 'status', 'templates']

class VMZabbixConfigFilterSet(NetBoxModelFilterSet):
    class Meta:
        model = models.VMZabbixConfig
        fields = ['status', 'templates']


# ------------------------------------------------------------------------------
# Interfaces
# ------------------------------------------------------------------------------

class DeviceAgentInterfaceFilterSet(django_filters.FilterSet):
    host_id = django_filters.NumberFilter( field_name='host__id' )

    class Meta:
        model = models.DeviceAgentInterface
        fields = ['host_id']


class DeviceSNMPv3InterfaceFilterSet(django_filters.FilterSet):
    host_id = django_filters.NumberFilter( field_name='host__id' )

    class Meta:
        model = models.DeviceSNMPv3Interface
        fields = ['host_id']


class VMAgentInterfaceFilterSet(django_filters.FilterSet):
    host_id = django_filters.NumberFilter( field_name='host__id' )

    class Meta:
        model = models.VMAgentInterface
        fields = ['host_id']


class VMSNMPv3InterfaceFilterSet(django_filters.FilterSet):
    host_id = django_filters.NumberFilter( field_name='host__id' )

    class Meta:
        model = models.VMSNMPv3Interface
        fields = ['host_id']


# ------------------------------------------------------------------------------
# Device Mapping
# ------------------------------------------------------------------------------

class DeviceMappingFilterSet(DeviceFilterSet):
    class Meta(DeviceFilterSet.Meta):
        model = Device
        fields = DeviceFilterSet.Meta.fields
    
# ------------------------------------------------------------------------------
# VM Mapping
# ------------------------------------------------------------------------------

# end