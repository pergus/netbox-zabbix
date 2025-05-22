import django_filters
from django.db.models import Q

from netbox.filtersets import NetBoxModelFilterSet
from netbox_zabbix import models

from dcim.models import Device
from virtualization.models import VirtualMachine

# ------------------------------------------------------------------------------
# Configuration
#
 
# No filter for the configuration

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
# Hosts
#

class DeviceHostFilterSet(NetBoxModelFilterSet):
    class Meta:
        model = models.DeviceHost
        fields = ['status', 'templates']

class VMHostFilterSet(NetBoxModelFilterSet):
    class Meta:
        model = models.DeviceHost
        fields = ['status', 'templates']

class DevicesExclusiveToNetBoxFilterSet(NetBoxModelFilterSet):
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

class VirtualMachinesExclusiveToNetBoxFilterSet(NetBoxModelFilterSet):
    class Meta:
        model = VirtualMachine
        fields = [ 'name' ]