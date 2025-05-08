import django_filters
from django.db.models import Q

from netbox.filtersets import NetBoxModelFilterSet
from netbox_zabbix import models


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
