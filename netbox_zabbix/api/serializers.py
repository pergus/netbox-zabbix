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

class DeviceHostSerializer(NetBoxModelSerializer):
    class Meta:
        model = models.DeviceHost
        fields = ( 'zabbix_host_id', 'status', 'templates', )
    
    templates         = TemplateSerializer( many=True, read_only=True )


class VMHostSerializer(NetBoxModelSerializer):
    class Meta:
        model = models.VMHost
        fields = ( 'zabbix_host_id', 'status', 'templates', )
        
    templates = TemplateSerializer( many=True, read_only=True )

# ------------------------------------------------------------------------------
# Interface
#

from dcim.api.serializers import InterfaceSerializer
class AvailableDeviceInterfaceSerializer(InterfaceSerializer):
    class Meta(InterfaceSerializer.Meta):
        model = models.AvailableDeviceInterface
        fields = '__all__'


class DeviceAgentInterfaceSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.DeviceAgentInterface
        fields = '__all__'