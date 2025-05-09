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


# ------------------------------------------------------------------------------
#
#

from dcim.api.serializers import InterfaceSerializer
class AvailableDeviceInterfaceSerializer(InterfaceSerializer):
    class Meta(InterfaceSerializer.Meta):
        model = models.AvailableDeviceInterface
        fields = '__all__'

    def validate(self, data):
            interface = data.get( 'interface' )
            host = data.get( 'host' )
    
            if models.DeviceAgentInterface.objects.filter( interface=interface ).exclude( pk=self.instance.pk if self.instance else None ).exists():
                raise serializers.ValidationError({'interface': 'This interface is already assigned to another HostInterface.'})
    
            if host.device != interface.device:
                raise serializers.ValidationError({'interface': 'Selected interface does not belong to the same device as the host.'})
    
            return data

class DeviceAgentInterfaceSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.DeviceAgentInterface
        fields = '__all__'