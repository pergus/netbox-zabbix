# filterset.py
import django_filters

from dcim.models import Device
from dcim.filtersets import DeviceFilterSet

from virtualization.models import VirtualMachine
from virtualization.filtersets import VirtualMachineFilterSet
from netbox.filtersets import NetBoxModelFilterSet
from netbox_zabbix import models


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
# Proxy Groups
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
# Device Host Groups
# ------------------------------------------------------------------------------


#class HostGroupDeviceFilterSet(DeviceFilterSet):
#    class Meta(DeviceFilterSet.Meta):
#        model = Device
#        fields = DeviceFilterSet.Meta.fields


# ------------------------------------------------------------------------------
# VM Host Groups
# ------------------------------------------------------------------------------


#class HostGroupVMFilterSet(VirtualMachineFilterSet):
#    class Meta(VirtualMachineFilterSet.Meta):
#        model = VirtualMachine
#        fields = VirtualMachineFilterSet.Meta.fields


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

class VMMappingFilterSet(VirtualMachineFilterSet):
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
    zcfg_id = django_filters.NumberFilter( field_name='zcfg__id' )

    class Meta:
        model = models.DeviceAgentInterface
        fields = ['zcfg_id']


class DeviceSNMPv3InterfaceFilterSet(django_filters.FilterSet):
    zcfg_id = django_filters.NumberFilter( field_name='zcfg__id' )

    class Meta:
        model = models.DeviceSNMPv3Interface
        fields = ['zcfg_id']


class VMAgentInterfaceFilterSet(django_filters.FilterSet):
    zcfg_id = django_filters.NumberFilter( field_name='zcfg__id' )

    class Meta:
        model = models.VMAgentInterface
        fields = ['zcfg_id']


class VMSNMPv3InterfaceFilterSet(django_filters.FilterSet):
    zcfg_id = django_filters.NumberFilter( field_name='zcfg__id' )

    class Meta:
        model = models.VMSNMPv3Interface
        fields = ['zcfg_id']


# ------------------------------------------------------------------------------
# NetBox Only Devices
# ------------------------------------------------------------------------------

class NetBoxOnlyDevicesFilterSet(DeviceFilterSet):
    class Meta(DeviceFilterSet.Meta):
        model = Device
        fields = DeviceFilterSet.Meta.fields


# ------------------------------------------------------------------------------
# NetBox Only VMs
# ------------------------------------------------------------------------------

class NetBoxOnlyVMsFilterSet(VirtualMachineFilterSet):
    class Meta(VirtualMachineFilterSet.Meta):
        model = VirtualMachine
        fields = VirtualMachineFilterSet.Meta.fields


# end