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
        fields = ( 'name', 'api_endpoint', 'web_address', 'version', 'connection', 'last_checked_at', 'token', 'ip_assignment_method')

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
    name = serializers.SerializerMethodField()
    display = serializers.SerializerMethodField()

    class Meta:
        model = models.DeviceHost
        fields = ( 'id', 'name', 'display', 'zabbix_host_id', 'status', 'templates', )
    
    templates = TemplateSerializer( many=True, read_only=True )

    def get_display(self, obj):
        return obj.get_name()
    
    def get_name(self, obj):
        # This method is called to get the value for the `name` field
        return obj.get_name()

class VMHostSerializer(NetBoxModelSerializer):
    class Meta:
        model = models.VMHost
        fields = ( 'id', 'zabbix_host_id', 'status', 'templates', )
        
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

class DeviceAgentInterfaceSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.DeviceAgentInterface
        fields = '__all__'

class DeviceSNMPv3InterfaceSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.DeviceSNMPv3Interface
        fields = '__all__'
