"""
NetBox Zabbix Plugin — API Serializers

This module defines serializers for the NetBox Zabbix plugin's API endpoints.
Serializers convert plugin models to and from JSON for REST API operations.
"""

# Third-party imports
from rest_framework import serializers

# NetBox imports
from dcim.api.serializers import InterfaceSerializer
from netbox.api.serializers import NetBoxModelSerializer

# NetBox Zabbix plugin imports
from netbox_zabbix import models


# ------------------------------------------------------------------------------
# Setting
# ------------------------------------------------------------------------------


class SettingSerializer(NetBoxModelSerializer):
    """
    Serializer for Zabbix plugin settings.
    
    Hides sensitive fields (API tokens, TLS/PSK secrets, SNMP passphrases)
    using HiddenField to prevent exposure in the API, while keeping Meta.fields defined
    to avoid NetBox API crashes.
    """
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
    """
    Serializer for Zabbix Templates.
    """
    class Meta:
        model = models.Template
        fields = '__all__'
    
    def get_display(self, obj):
        """
        Returns a human-readable display name for the template.
        
        Args:
            obj (Template): Template instance.
        
        Returns:
            str: Name of the template.
        """
        return str( obj.name )


# ------------------------------------------------------------------------------
# Proxy
# ------------------------------------------------------------------------------


class ProxySerializer(NetBoxModelSerializer):
    """
    Serializer for Zabbix Proxies.
    """
    class Meta:
        model = models.Proxy
        fields = '__all__'
    
    def get_display(self, obj):
        """
        Returns a human-readable display name for the proxy.
        
        Args:
            obj (Proxy): Proxy instance.
        
        Returns:
            str: Name of the proxy.
        """
        return str( obj.name )


# ------------------------------------------------------------------------------
# Proxy Group
# ------------------------------------------------------------------------------


class ProxyGroupSerializer(NetBoxModelSerializer):
    """
    Serializer for Zabbix Proxy Groups.
    """
    class Meta:
        model = models.ProxyGroup
        fields = '__all__'
    
    def get_display(self, obj):
        """
        Returns a human-readable display name for the proxy group.
        
        Args:
            obj (ProxyGroup): ProxyGroup instance.
        
        Returns:
            str: Name of the proxy group.
        """
        return str( obj.name )


# ------------------------------------------------------------------------------
# Host Group
# ------------------------------------------------------------------------------


class HostGroupSerializer(serializers.ModelSerializer):
    """
    Serializer for Zabbix Host Groups.
    """
    display = serializers.SerializerMethodField()
    
    class Meta:
        model = models.HostGroup
        fields = '__all__'
    
    
    def get_display(self, obj):
        """
        Returns a human-readable display value for the unassigned object.
        
        Args:
            obj: Instance of Device or VirtualMachine.
        
        Returns:
            str: Display string of the object.
        """
        return str(obj)
    

# ------------------------------------------------------------------------------
# Tag Mapping
# ------------------------------------------------------------------------------


class TagMappingSerializer(serializers.ModelSerializer):
    """
    Serializer for Tag Mappings.
    """
    class Meta:
        model = models.TagMapping
        fields = '__all__'

# ------------------------------------------------------------------------------
# Inventory Mapping
# ------------------------------------------------------------------------------


class InventoryMappingSerializer(serializers.ModelSerializer):
    """
    Serializer for Inventory Mappings.
    """
    class Meta:
        model = models.InventoryMapping
        fields = '__all__'


# ------------------------------------------------------------------------------
# Mapping
# ------------------------------------------------------------------------------


class MappingSerializer(serializers.ModelSerializer):
    """
    Base serializer for generic Mapping models.
    """
    class Meta:
        model = models.Mapping
        fields = '__all__'


# ------------------------------------------------------------------------------
# Device Mapping
# ------------------------------------------------------------------------------


class DeviceMappingSerializer(serializers.ModelSerializer):
    """
    Serializer for Device Mapping objects.
    """
    class Meta:
        model = models.DeviceMapping
        fields = '__all__'


# ------------------------------------------------------------------------------
# VM Mapping
# ------------------------------------------------------------------------------


class VMMappingSerializer(serializers.ModelSerializer):
    """
    Serializer for Virtual Machine Mapping objects.
    """
    class Meta:
        model = models.VMMapping
        fields = '__all__'


# ------------------------------------------------------------------------------
# Host Config
# ------------------------------------------------------------------------------


class HostConfigSerializer(serializers.ModelSerializer):
    """
    Serializer for Host Config objects.
    """
    class Meta:
        model = models.HostConfig
        fields = '__all__'


# ------------------------------------------------------------------------------
# Agent Interface
# ------------------------------------------------------------------------------


class AgentInterfaceSerializer(serializers.ModelSerializer):
    """
    Serializer for Agent Interface objects.
    """
    class Meta:
        model = models.AgentInterface
        fields = '__all__'


# ------------------------------------------------------------------------------
# SNMP Interface
# ------------------------------------------------------------------------------


class SNMPInterfaceSerializer(serializers.ModelSerializer):
    """
    Serializer for SNMP Interface objects.
    """
    class Meta:
        model = models.SNMPInterface
        fields = '__all__'


# ------------------------------------------------------------------------------
# Event Log
# ------------------------------------------------------------------------------


class EventLogSerializer(serializers.ModelSerializer):
    """
    Serializer for Zabbix Event Logs.
    """
    class Meta:
        model = models.EventLog
        fields = '__all__'



# ------------------------------------------------------------------------------
# Un-assigned Hosts
# ------------------------------------------------------------------------------


class UnAssignedHostsSerializer(serializers.Serializer):
    """
    Serializer for unassigned Device or VirtualMachine objects.
    Provides `id` and `display` fields for selection in API responses.
    """
    id      = serializers.IntegerField()
    display = serializers.SerializerMethodField()
    
    def get_display(self, obj):
        """
        Returns a human-readable display value for the unassigned object.
        
        Args:
            obj: Instance of Device or VirtualMachine.
        
        Returns:
            str: Display string of the object.
        """
        return str(obj)

    class Meta:
        fields = ['id', 'display']


# ------------------------------------------------------------------------------
# Un-assigned Agent Interfaces
# ------------------------------------------------------------------------------


class UnAssignedAgentInterfacesSerializer(InterfaceSerializer):
    """
    Serializer for unassigned Agent Interfaces.
    Inherits from InterfaceSerializer to include interface fields.
    """
    class Meta(InterfaceSerializer.Meta):
        model = models.UnAssignedAgentInterfaces
        fields = '__all__'


# ------------------------------------------------------------------------------
# Un-assigned SNMP Interfaces
# ------------------------------------------------------------------------------


class UnAssignedSNMPInterfaceSerializer(InterfaceSerializer):
    """
    Serializer for unassigned SNMP Interfaces.
    Inherits from InterfaceSerializer to include interface fields.
    """
    class Meta(InterfaceSerializer.Meta):
        model = models.UnAssignedSNMPInterfaces
        fields = '__all__'


# ------------------------------------------------------------------------------
# Un-assigned Host Interfaces
# ------------------------------------------------------------------------------


class UnAssignedHostInterfacesSerializer(serializers.Serializer):
    """
    Serializer for unassigned Host Interfaces (Device or VM).
    Provides `id` and `display` fields for selection in API responses.
    """
    id      = serializers.IntegerField()
    display = serializers.SerializerMethodField()
    
    def get_display(self, obj):
        """
        Returns a human-readable display value for the unassigned interface.
        
        Args:
            obj: Interface or VMInterface instance.
        
        Returns:
            str: Display string of the interface.
        """
        return str(obj)

    class Meta:
        fields = ['id', 'display']


# ------------------------------------------------------------------------------
# Un-assigned Host IP  Addresses
# ------------------------------------------------------------------------------


class UnAssignedHostIPAddressesSerializer(serializers.Serializer):
    """
    Serializer for unassigned IP addresses on a Host Interface or VMInterface.
    Provides `id` and `display` fields for selection in API responses.
    """
    id      = serializers.IntegerField()
    display = serializers.SerializerMethodField()
    
    def get_display(self, obj):
        """
        Returns a human-readable display value for the IP address.
        
        Args:
            obj (IPAddress): IP address instance.
        
        Returns:
            str: IP address string.
        """
        return str(obj)

    class Meta:
        fields = ['id', 'display']


# ------------------------------------------------------------------------------
# Maintenance
# ------------------------------------------------------------------------------

from netbox_zabbix.models import Maintenance

class MaintenanceSerializer(NetBoxModelSerializer):
    """
    API serializer for Maintenance.
    """

    class Meta:
        model = Maintenance
        fields = '__all__'


# ------------------------------------------------------------------------------
# Host Mapping
# ------------------------------------------------------------------------------


class HostMappingSerializer(serializers.ModelSerializer):
    """
    Serializer for Host Mapping objects.
    """
    class Meta:
        model = models.HostMapping
        fields = '__all__'



# end