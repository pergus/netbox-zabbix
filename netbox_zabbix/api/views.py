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

class HostViewSet(NetBoxModelViewSet):
    queryset = models.Host.objects.all()
    serializer_class = serializers.HostSerializer
