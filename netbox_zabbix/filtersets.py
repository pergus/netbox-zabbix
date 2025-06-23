# filterset.py
import django_filters
from django_filters import rest_framework as filters

from dcim.models import Device
from dcim.filtersets import DeviceFilterSet

from virtualization.models import VirtualMachine
from virtualization.filtersets import VirtualMachineFilterSet

from extras.filters import TagFilter
from netbox.filtersets import NetBoxModelFilterSet
from netbox_zabbix import models

from netbox_zabbix.utils import (
    get_hostgroups_mappings, 
    get_templates_mappings,
    get_proxy_mapping,
    get_proxygroup_mapping
)


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
# Template Mappings
# ------------------------------------------------------------------------------

class TemplateMappingFilterSet(NetBoxModelFilterSet):
    tags = TagFilter()

    class Meta:
        model = models.TemplateMapping
        fields = ['templates', 'sites', 'roles', 'platforms', 'tags']


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
# Proxy Mappings
# ------------------------------------------------------------------------------

class ProxyMappingFilterSet(NetBoxModelFilterSet):
    tags = TagFilter()

    class Meta:
        model = models.ProxyMapping
        fields = ['proxy', 'sites', 'roles', 'platforms', 'tags']


class ProxyDeviceFilterSet(DeviceFilterSet):
    class Meta(DeviceFilterSet.Meta):
        model = Device
        fields = DeviceFilterSet.Meta.fields


class ProxyVMFilterSet(VirtualMachineFilterSet):
    class Meta(VirtualMachineFilterSet.Meta):
        model = VirtualMachine
        fields = VirtualMachineFilterSet.Meta.fields



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
# Proxy Group Mappings
# ------------------------------------------------------------------------------

class ProxyGroupMappingFilterSet(NetBoxModelFilterSet):
    tags = TagFilter()

    class Meta:
        model = models.ProxyGroupMapping
        fields = ['proxygroup', 'sites', 'roles', 'platforms', 'tags']


class ProxyGroupDeviceFilterSet(DeviceFilterSet):
    class Meta(DeviceFilterSet.Meta):
        model = Device
        fields = DeviceFilterSet.Meta.fields


class ProxyGroupVMFilterSet(VirtualMachineFilterSet):
    class Meta(VirtualMachineFilterSet.Meta):
        model = VirtualMachine
        fields = VirtualMachineFilterSet.Meta.fields



# ------------------------------------------------------------------------------
# Host Group Mappings
# ------------------------------------------------------------------------------

class HostGroupMappingFilterSet(NetBoxModelFilterSet):
    tags = TagFilter()

    class Meta:
        model = models.HostGroupMapping
        fields = ['hostgroups', 'sites', 'roles', 'platforms', 'tags']

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
# Device Mappings
# ------------------------------------------------------------------------------

class DeviceMappingsFilterSet(DeviceFilterSet):

    hostgroups = filters.ModelMultipleChoiceFilter(
        field_name='hostgroups',
        queryset=models.HostGroupMapping.objects.all(),
        conjoined=True,
        method='filter_by_mapping_list',
        label="Host Groups"
    )

    templates = filters.ModelMultipleChoiceFilter(
        field_name='templates',
        queryset=models.TemplateMapping.objects.all(),
        conjoined=True,
        method='filter_by_mapping_list',
        label="Templates"
    )
    
    proxy = filters.ModelChoiceFilter(
        field_name='proxy',
        queryset=models.ProxyMapping.objects.all(),
        method='filter_by_mapping_single',
        label="Proxy"
    )

    proxygroup = filters.ModelChoiceFilter(
        field_name='proxygroup',
        queryset=models.ProxyGroupMapping.objects.all(),
        method='filter_by_mapping_single',
        label="Proxy Group"
    )

    def filter_by_mapping_list(self, queryset, name, value):
        if not value:
            return queryset

        mapping_fn_map = {
            'hostgroups': get_hostgroups_mappings,
            'templates': get_templates_mappings,
        }

        mapping_fn = mapping_fn_map.get( name )
        if not mapping_fn:
            return queryset

        selected_mapping_ids = {m.id for m in value}
        matching_ids = []

        for device in queryset:
            mappings = mapping_fn( device )
            if any(m.id in selected_mapping_ids for m in mappings):
                matching_ids.append( device.id )

        return queryset.filter(id__in=matching_ids)

    def filter_by_mapping_single(self, queryset, name, value):
        if not value:
            return queryset

        mapping_fn_map = {
            'proxy': get_proxy_mapping,
            'proxygroup': get_proxygroup_mapping,
        }

        mapping_fn = mapping_fn_map.get( name )
        if not mapping_fn:
            return queryset

        selected_id = value.id
        matching_ids = []

        for device in queryset:
            mapping = mapping_fn( device )
            if mapping and mapping.id == selected_id:
                matching_ids.append( device.id )

        return queryset.filter( id__in=matching_ids )

# ------------------------------------------------------------------------------
# VM Mappings
# ------------------------------------------------------------------------------

class VMMappingsFilterSet(VirtualMachineFilterSet):

    hostgroups = filters.ModelMultipleChoiceFilter(
        field_name='hostgroups',
        queryset=models.HostGroupMapping.objects.all(),
        conjoined=True,
        method='filter_by_mapping_list',
        label="Host Groups"
    )

    templates = filters.ModelMultipleChoiceFilter(
        field_name='templates',
        queryset=models.TemplateMapping.objects.all(),
        conjoined=True,
        method='filter_by_mapping_list',
        label="Templates"
    )
    
    proxy = filters.ModelChoiceFilter(
        field_name='proxy',
        queryset=models.ProxyMapping.objects.all(),
        method='filter_by_mapping_single',
        label="Proxy"
    )

    proxygroup = filters.ModelChoiceFilter(
        field_name='proxygroup',
        queryset=models.ProxyGroupMapping.objects.all(),
        method='filter_by_mapping_single',
        label="Proxy Group"
    )

    def filter_by_mapping_list(self, queryset, name, value):
        if not value:
            return queryset

        mapping_fn_map = {
            'hostgroups': get_hostgroups_mappings,
            'templates': get_templates_mappings,
        }

        mapping_fn = mapping_fn_map.get( name )
        if not mapping_fn:
            return queryset

        selected_mapping_ids = {m.id for m in value}
        matching_ids = []

        for device in queryset:
            mappings = mapping_fn( device )
            if any(m.id in selected_mapping_ids for m in mappings):
                matching_ids.append( device.id )

        return queryset.filter( id__in=matching_ids )

    def filter_by_mapping_single(self, queryset, name, value):
        if not value:
            return queryset

        mapping_fn_map = {
            'proxy': get_proxy_mapping,
            'proxygroup': get_proxygroup_mapping,
        }

        mapping_fn = mapping_fn_map.get( name )
        if not mapping_fn:
            return queryset

        selected_id = value.id
        matching_ids = []

        for device in queryset:
            mapping = mapping_fn( device )
            if mapping and mapping.id == selected_id:
                matching_ids.append( device.id )

        return queryset.filter( id__in=matching_ids )


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