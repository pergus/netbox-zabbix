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