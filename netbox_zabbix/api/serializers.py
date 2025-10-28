# serializers.py

from dcim.api.serializers import InterfaceSerializer
from rest_framework import serializers

from netbox.api.serializers import NetBoxModelSerializer
from netbox_zabbix import models


# ------------------------------------------------------------------------------
# Setting
# ------------------------------------------------------------------------------


class SettingSerializer(NetBoxModelSerializer):
    class Meta:
        model = models.Setting
        fields = '__all__'

    # Exclude the following fields from the API.
    # Note: We do NOT use `exclude` here, because NetBox's internal utilities 
    # expect `Meta.fields` to exist. If we only use `exclude`, `Meta.fields` 
    # is undefined and API calls will crash. Instead, we include all fields 
    # with `fields="__all__"` and hide sensitive/unwanted fields by using 
    # serializers.HiddenField(default=None). This ensures `Meta.fields` exists 
    # while preventing exposure of private data like internal secrets or API keys.
    
    token               = serializers.HiddenField( default=None )
    tls_connect         = serializers.HiddenField( default=None )
    tls_accept          = serializers.HiddenField( default=None )
    tls_psk_identity    = serializers.HiddenField( default=None )
    tls_psk             = serializers.HiddenField( default=None )
    snmp_securityname   = serializers.HiddenField( default=None )
    snmp_authpassphrase = serializers.HiddenField( default=None )
    snmp_privpassphrase = serializers.HiddenField( default=None )


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
# Host Group
# ------------------------------------------------------------------------------


class HostGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.HostGroup
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
# Host Config
# ------------------------------------------------------------------------------


class HostConfigSerializer(serializers.ModelSerializer):

    class Meta:
        model = models.HostConfig
        fields = '__all__'


# ------------------------------------------------------------------------------
# Agent Interface
# ------------------------------------------------------------------------------


class AgentInterfaceSerializer(serializers.ModelSerializer):

    class Meta:
        model = models.AgentInterface
        fields = '__all__'


# ------------------------------------------------------------------------------
# SNMP Interface
# ------------------------------------------------------------------------------


class SNMPInterfaceSerializer(serializers.ModelSerializer):

    class Meta:
        model = models.SNMPInterface
        fields = '__all__'


# ------------------------------------------------------------------------------
# Event Log
# ------------------------------------------------------------------------------


class EventLogSerializer(serializers.ModelSerializer):

    class Meta:
        model = models.EventLog
        fields = '__all__'



# ------------------------------------------------------------------------------
# Un-assigned Hosts
# ------------------------------------------------------------------------------


class UnAssignedHostsSerializer(serializers.Serializer):
    id      = serializers.IntegerField()
    display = serializers.SerializerMethodField()
    
    def get_display(self, obj):
        return str(obj)

    class Meta:
        fields = ['id', 'display']


# ------------------------------------------------------------------------------
# Un-assigned Agent Interfaces
# ------------------------------------------------------------------------------


class UnAssignedAgentInterfacesSerializer(InterfaceSerializer):
    class Meta(InterfaceSerializer.Meta):
        model = models.UnAssignedAgentInterfaces
        fields = '__all__'


# ------------------------------------------------------------------------------
# Un-assigned SNMP Interfaces
# ------------------------------------------------------------------------------


class UnAssignedSNMPInterfaceSerializer(InterfaceSerializer):
    class Meta(InterfaceSerializer.Meta):
        model = models.UnAssignedSNMPInterfaces
        fields = '__all__'


# ------------------------------------------------------------------------------
# Un-assigned Host Interfaces
# ------------------------------------------------------------------------------


class UnAssignedHostInterfacesSerializer(serializers.Serializer):
    id      = serializers.IntegerField()
    display = serializers.SerializerMethodField()
    
    def get_display(self, obj):
        return str(obj)

    class Meta:
        fields = ['id', 'display']


# ------------------------------------------------------------------------------
# Un-assigned Host IP  Addresses
# ------------------------------------------------------------------------------


class UnAssignedHostIPAddressesSerializer(serializers.Serializer):
    id      = serializers.IntegerField()
    display = serializers.SerializerMethodField()
    
    def get_display(self, obj):
        return str(obj)

    class Meta:
        fields = ['id', 'display']


# end