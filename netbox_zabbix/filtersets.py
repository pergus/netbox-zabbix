import django_filters
from django_filters import rest_framework as filters
from extras.filters import TagFilter

from netbox.filtersets import NetBoxModelFilterSet
from netbox_zabbix import models

from dcim.models import Device
from dcim.filtersets import DeviceFilterSet
from virtualization.models import VirtualMachine
from virtualization.filtersets import VirtualMachineFilterSet


from netbox_zabbix.utils import get_device_hostgroups


# Configuration doesn't have a filterset

# ------------------------------------------------------------------------------
# Templates
#

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
# Template Mappings
#

class TemplateMappingFilterSet(NetBoxModelFilterSet):
    tags = TagFilter()

    class Meta:
        model = models.TemplateMapping
        fields = ['template', 'sites', 'roles', 'platforms', 'tags']


class TemplateDeviceFilterSet(DeviceFilterSet):
    class Meta(DeviceFilterSet.Meta):
        model = Device
        fields = DeviceFilterSet.Meta.fields


class TemplateVMFilterSet(VirtualMachineFilterSet):
    class Meta(VirtualMachineFilterSet.Meta):
        model = VirtualMachine
        fields = VirtualMachineFilterSet.Meta.fields


# ------------------------------------------------------------------------------
# Proxy
#

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
# Proxy Mappings
#

class ProxyMappingFilterSet(NetBoxModelFilterSet):
    tags = TagFilter()

    class Meta:
        model = models.ProxyMapping
        fields = ['proxy', 'sites', 'roles', 'platforms', 'tags']



# ------------------------------------------------------------------------------
# Proxy Group
#

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
# Host Group Mappings
#

class HostGroupMappingFilterSet(NetBoxModelFilterSet):
    tags = TagFilter()

    class Meta:
        model = models.HostGroupMapping
        fields = ['hostgroup', 'sites', 'roles', 'platforms', 'tags']

# ------------------------------------------------------------------------------
# Host Group Device
#

class HostGroupDeviceFilterSet(DeviceFilterSet):
    class Meta(DeviceFilterSet.Meta):
        model = Device
        fields = DeviceFilterSet.Meta.fields


# ------------------------------------------------------------------------------
# Host Group VM
#

class HostGroupVMFilterSet(VirtualMachineFilterSet):
    class Meta(VirtualMachineFilterSet.Meta):
        model = VirtualMachine
        fields = VirtualMachineFilterSet.Meta.fields

# ------------------------------------------------------------------------------
# Device Host Group
#

class DeviceHostGroupFilterSet(DeviceFilterSet):

    hostgroups = filters.ModelMultipleChoiceFilter(
        field_name='hostgroups',
        queryset=models.HostGroupMapping.objects.all(),
        conjoined=True,  # or True if you want all selected hostgroups to match
        method='filter_hostgroups',
        label="Host Groups"
    )

    def filter_hostgroups(self, queryset, name, value):
        if not value:
            return queryset
    
        selected_mapping_ids = {mapping.id for mapping in value}
        matching_device_ids = []

        for device in queryset:
            matched = get_device_hostgroups(device)  # returns a list of HostGroupMapping
            matched_mapping_ids = {mapping.id for mapping in matched}
    
            if matched_mapping_ids & selected_mapping_ids:
                matching_device_ids.append(device.id)
    
        return queryset.filter(id__in=matching_device_ids)


# ------------------------------------------------------------------------------
# Zabbix Configurations
#

class DeviceZabbixConfigFilterSet(NetBoxModelFilterSet):
    class Meta:
        model = models.DeviceZabbixConfig
        fields = [ 'status', 'templates']

class VMZabbixConfigFilterSet(NetBoxModelFilterSet):
    class Meta:
        model = models.VMZabbixConfig
        fields = ['status', 'templates']

class NetBoxOnlyDevicesFilterSet(NetBoxModelFilterSet):
    class Meta:
        model = Device
        fields = ( 'name', )

class NetBoxOnlyVMsFilterSet(NetBoxModelFilterSet):
    class Meta:
        model = VirtualMachine
        fields = [ 'name' ]


# ------------------------------------------------------------------------------
# Interfaces
#

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