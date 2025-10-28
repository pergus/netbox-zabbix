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
        fields = [ 'name', 'templateid' ]

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
        fields = [ 'name', 'proxyid', 'proxy_groupid']

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
        fields = [ 'name', 'proxy_groupid' ]

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
# Host Configuration
# ------------------------------------------------------------------------------



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

# ------------------------------------------------------------------------------
# LAB
# ------------------------------------------------------------------------------

class AgentInterfaceFilterSet(django_filters.FilterSet):
    host_config_id = django_filters.NumberFilter( field_name='host_config__id' )

    class Meta:
        model = models.AgentInterface
        fields = ['host_config_id']


class SNMPInterfaceFilterSet(django_filters.FilterSet):
    host_config_id = django_filters.NumberFilter( field_name='host_config__id' )

    class Meta:
        model = models.SNMPInterface
        fields = ['host_config_id']


# end