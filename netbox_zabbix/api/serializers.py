from dcim.api.serializers import InterfaceSerializer
from virtualization.api.serializers import VMInterfaceSerializer
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
# Hostgroups
#

class HostGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model =models.HostGroup
        fields = ['id', 'groupid', 'name']

class HostGroupMappingSerializer(serializers.ModelSerializer):
    hostgroup = HostGroupSerializer( read_only=True )
    hostgroup_id = serializers.PrimaryKeyRelatedField( queryset=models.HostGroup.objects.all(), source='hostgroup', write_only=True )

    class Meta:
        model = models.HostGroupMapping
        fields = [
            'id',
            'hostgroup',
            'hostgroup_id',
            'sites',
            'roles',
            'platforms',
            'tags',
        ]

# ------------------------------------------------------------------------------
# Zabbix Configurations
#

class DeviceZabbixConfigSerializer(NetBoxModelSerializer):
    name = serializers.SerializerMethodField()
    display = serializers.SerializerMethodField()

    class Meta:
        model = models.DeviceZabbixConfig
        fields = ( 'id', 'name', 'display', 'hostid', 'status', 'templates', )
    
    templates = TemplateSerializer( many=True, read_only=True )

    def get_display(self, obj):
        return obj.get_name()
    
    def get_name(self, obj):
        # This method is called to get the value for the `name` field
        return obj.get_name()

class VMZabbixConfigSerializer(NetBoxModelSerializer):
    name = serializers.SerializerMethodField()
    display = serializers.SerializerMethodField()
    
    class Meta:
        model = models.VMZabbixConfig
        fields = ( 'id', 'name', 'display', 'hostid', 'status', 'templates', )
        
    templates = TemplateSerializer( many=True, read_only=True )

    def get_display(self, obj):
        return obj.get_name()
    
    def get_name(self, obj):
        # This method is called to get the value for the `name` field
        return obj.get_name()
    
# ------------------------------------------------------------------------------
# Interfaces
#


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


class AvailableVMInterfaceSerializer(VMInterfaceSerializer):
    class Meta(VMInterfaceSerializer.Meta):
        model = models.AvailableDeviceInterface
        fields = '__all__'


class VMAgentInterfaceSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.VMAgentInterface
        fields = '__all__'


class VMSNMPv3InterfaceSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.VMSNMPv3Interface
        fields = '__all__'
