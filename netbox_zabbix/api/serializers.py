from django.contrib.contenttypes.models import ContentType
from rest_framework import serializers

from netbox.api.serializers import NetBoxModelSerializer
from netbox_zabbix import models

# ------------------------------------------------------------------------------
# Configuration
#

class ConfigSerializer(NetBoxModelSerializer):
    class Meta:
        model = models.Config
        fields = ( 'name', 'api_endpoint', 'web_address', 'version', 'connection', 'last_checked_at', 'token' )

# ------------------------------------------------------------------------------
# Templates
#

class TemplateSerializer(NetBoxModelSerializer):
    class Meta:
        model = models.Template
        fields = ("name", "display", "id", "templateid", "last_synced" )
    
    def get_display(self, obj):
        return str( obj.name )

# ------------------------------------------------------------------------------
# Hosts
#

class HostSerializer(NetBoxModelSerializer):
    class Meta:
        model = models.Host
        fields = (
            'id',
            'content_type',
            'object_id',
            'associated_object',
            'zabbix_host_id',
            'status',
            'templates',
        )
    
    content_type      = serializers.SlugRelatedField( slug_field='model', queryset=ContentType.objects.all() )
    templates         = TemplateSerializer( many=True, read_only=True )
    associated_object = serializers.SerializerMethodField()
    
    def get_associated_object(self, obj):
        try:
            return str(obj.associated_object)
        except Exception:
            return None