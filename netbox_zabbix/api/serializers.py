from dcim.api.serializers import InterfaceSerializer
from virtualization.api.serializers import VMInterfaceSerializer
from rest_framework import serializers

from netbox.api.serializers import NetBoxModelSerializer
from netbox_zabbix import models

# ------------------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------------------


class ConfigSerializer(NetBoxModelSerializer):
    class Meta:
        model = models.Config
        fields = '__all__'


# ------------------------------------------------------------------------------
# Templates
# ------------------------------------------------------------------------------


class TemplateSerializer(NetBoxModelSerializer):
    class Meta:
        model = models.Template
        fields = '__all__'
    
    def get_display(self, obj):
        return str( obj.name )


# ------------------------------------------------------------------------------
# Proxy
# ------------------------------------------------------------------------------


class ProxySerializer(NetBoxModelSerializer):
    class Meta:
        model = models.Proxy
        fields = '__all__'
    
    def get_display(self, obj):
        return str( obj.name )


# ------------------------------------------------------------------------------
# Proxy Group
# ------------------------------------------------------------------------------


class ProxyGroupSerializer(NetBoxModelSerializer):
    class Meta:
        model = models.ProxyGroup
        fields = '__all__'
    
    def get_display(self, obj):
        return str( obj.name )


# ------------------------------------------------------------------------------
# Host Groups
# ------------------------------------------------------------------------------


class HostGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.HostGroup
        fields = '__all__'


# ------------------------------------------------------------------------------
# Zabbix Configurations
# ------------------------------------------------------------------------------


class DeviceZabbixConfigSerializer(NetBoxModelSerializer):
    templates = TemplateSerializer( many=True, read_only=True )
    
    class Meta:
        model = models.DeviceZabbixConfig
        fields = '__all__'
    

class VMZabbixConfigSerializer(NetBoxModelSerializer):
    templates = TemplateSerializer( many=True, read_only=True )

    class Meta:
        model = models.VMZabbixConfig
        fields = '__all__'

# ------------------------------------------------------------------------------
# Interfaces
# ------------------------------------------------------------------------------


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


# ------------------------------------------------------------------------------
# Tag Mapping
# ------------------------------------------------------------------------------


class TagMappingSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.TagMapping
        fields = '__all__'

# ------------------------------------------------------------------------------
# Inventory Mapping
# ------------------------------------------------------------------------------


class InventoryMappingSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.InventoryMapping
        fields = '__all__'


# ------------------------------------------------------------------------------
# Mapping
# ------------------------------------------------------------------------------


class MappingSerializer(serializers.ModelSerializer):

    class Meta:
        model = models.Mapping
        fields = '__all__'


# ------------------------------------------------------------------------------
# Device Mapping
# ------------------------------------------------------------------------------


class DeviceMappingSerializer(serializers.ModelSerializer):

    class Meta:
        model = models.DeviceMapping
        fields = '__all__'


# ------------------------------------------------------------------------------
# VM Mapping
# ------------------------------------------------------------------------------


class VMMappingSerializer(serializers.ModelSerializer):

    class Meta:
        model = models.VMMapping
        fields = '__all__'


# ------------------------------------------------------------------------------
# Event Log
# ------------------------------------------------------------------------------


class EventLogSerializer(serializers.ModelSerializer):

    class Meta:
        model = models.EventLog
        fields = '__all__'

# end