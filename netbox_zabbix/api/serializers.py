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
# Template Mappings
# ------------------------------------------------------------------------------

class TemplateMappingSerializer(serializers.ModelSerializer):
    templates    = TemplateSerializer( many=True, read_only=True )
    template_ids = serializers.PrimaryKeyRelatedField( queryset=models.Template.objects.all(), source='templates', write_only=True, many=True )

    class Meta:
        model = models.TemplateMapping
        fields = '__all__'


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
# Proxy Mappings
# ------------------------------------------------------------------------------

class ProxyMappingSerializer(serializers.ModelSerializer):
    proxy    = ProxySerializer( read_only=True )
    proxy_id = serializers.PrimaryKeyRelatedField( queryset=models.Proxy.objects.all(), source='proxy', write_only=True )

    class Meta:
        model = models.ProxyMapping
        fields = '__all__'


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
# Proxy Group Mappings
# ------------------------------------------------------------------------------

class ProxyGroupMappingSerializer(serializers.ModelSerializer):
    proxy_group    = ProxyGroupSerializer( read_only=True )
    proxy_groupid = serializers.PrimaryKeyRelatedField( queryset=models.ProxyGroup.objects.all(), source='proxy_group', write_only=True )

    class Meta:
        model = models.ProxyGroupMapping
        fields = '__all__'


# ------------------------------------------------------------------------------
# Host Groups
# ------------------------------------------------------------------------------

class HostGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.HostGroup
        fields = '__all__'


# ------------------------------------------------------------------------------
# Host Group Mappings
# ------------------------------------------------------------------------------

class HostGroupMappingSerializer(serializers.ModelSerializer):
    hostgroups = HostGroupSerializer( many=True, read_only=True )
    hostgroup_ids = serializers.PrimaryKeyRelatedField( queryset=models.HostGroup.objects.all(), source='hostgroup', write_only=True, many=True )

    class Meta:
        model = models.HostGroupMapping
        fields = '__all__'


# ------------------------------------------------------------------------------
# Tag Mapping
# ------------------------------------------------------------------------------

class TagMappingSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.TagMapping
        fields = '__all__'


# ------------------------------------------------------------------------------
# Zabbix Configurations
# ------------------------------------------------------------------------------

class DeviceZabbixConfigSerializer(NetBoxModelSerializer):
    name = serializers.SerializerMethodField()
    display = serializers.SerializerMethodField()

    class Meta:
        model = models.DeviceZabbixConfig
        fields = '__all__'
    
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
        fields = '__all__'
        
    templates = TemplateSerializer( many=True, read_only=True )

    def get_display(self, obj):
        return obj.get_name()
    
    def get_name(self, obj):
        # This method is called to get the value for the `name` field
        return obj.get_name()


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

# end