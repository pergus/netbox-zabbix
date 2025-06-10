import django_filters
from django.db.models import Q

from netbox.filtersets import NetBoxModelFilterSet
from netbox_zabbix import models

from dcim.models import Device
from dcim.filtersets import DeviceFilterSet
from virtualization.models import VirtualMachine
from virtualization.filtersets import VirtualMachineFilterSet

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
# Host Group Mappings
#


from extras.filters import TagFilter
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

#from netbox_zabbix.logger import logger
#from netbox_zabbix import forms
#class DeviceHostGroupFilterSet(DeviceFilterSet):
#    hostgroups = django_filters.ModelMultipleChoiceFilter(
#        queryset=models.HostGroupMapping.objects.all(),
#        method='filter_hostgroups',
#        label='Zabbix Host Groups',
#        conjoined=False,
#    )
#
#    def filter_hostgroups(self, queryset, name, value):
#        logger.info(f"Filtering with hostgroups: {value}")
#        if value:
#            return queryset.filter(zabbix_hostgroups__in=value)
#        return queryset
#
#    class Meta(DeviceFilterSet.Meta):
#        model = Device
#        fields = list(DeviceFilterSet.Meta.fields) + ['hostgroups']
#
#    # Add this line to use your custom form
#    filterset_form = forms.DeviceHostGroupFilterForm


from django_filters import rest_framework as filters
from netbox_zabbix import models
from dcim.models import Device

# note(pergus): This code should not be repeated.
def get_device_hostgroups(device):
    mappings = models.HostGroupMapping.objects.all()
    matches = []

    for mapping in mappings:
        if mapping.sites.exists() and device.site_id not in mapping.sites.values_list( 'id', flat=True ):
            continue
        if mapping.roles.exists() and device.role_id not in mapping.roles.values_list( 'id', flat=True ):
            continue
        if mapping.platforms.exists() and device.platform_id not in mapping.platforms.values_list( 'id', flat=True ):
            continue
        if mapping.tags.exists():
            device_tag_slugs = set( device.tags.values_list( 'slug', flat=True ) )
            mapping_tag_slugs = set( mapping.tags.values_list( 'slug', flat=True ) )
            if not mapping_tag_slugs.issubset( device_tag_slugs ):
                continue
        matches.append(mapping)
    return matches


#class DeviceHostGroupFilterSet(filters.FilterSet):
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

#    class Meta:
#        model = Device
#        fields = []  #['hostgroups']

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
#        fields = (
#                    'pk', 'id', 'name', 'status', 'tenant', 'tenant_group', 'role', 'manufacturer', 'device_type',
#                    'serial', 'asset_tag', 'region', 'site_group', 'site', 'location', 'rack', 'parent_device',
#                    'device_bay_position', 'position', 'face', 'latitude', 'longitude', 'airflow', 'primary_ip', 'primary_ip4',
#                    'primary_ip6', 'oob_ip', 'cluster', 'virtual_chassis', 'vc_position', 'vc_priority', 'description',
#                    'config_template', 'comments', 'contacts', 'tags', 'created', 'last_updated',
#                )

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