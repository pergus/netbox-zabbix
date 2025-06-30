# forms.py
import re

from django import forms
from django.core.exceptions import ValidationError
from django.utils.safestring import mark_safe
from django.utils.timezone import now
from django.conf import settings
from django.utils.text import slugify

from ipam.models import IPAddress
from netbox.forms import NetBoxModelFilterSetForm, NetBoxModelForm
from utilities.forms.fields import DynamicModelChoiceField
from utilities.forms.rendering import FieldSet

from dcim.models import Device
from dcim.forms import DeviceFilterForm

from virtualization.models import VirtualMachine
from virtualization.forms import VirtualMachineFilterForm

from netbox_zabbix import models
from netbox_zabbix import zabbix as z
from netbox_zabbix.logger import logger


#
# Notes
#
# DynamicModelChoiceField expects a corresponding API endpoint to fetch and
# filter options dynamically as a single-select field. Since we need to support
# multiple selections without relying on a custom API endpoint, use
# ModelMultipleChoiceField instead.
#


PLUGIN_SETTINGS = settings.PLUGINS_CONFIG.get("netbox_zabbix", {})

# ------------------------------------------------------------------------------
# Settings
# ------------------------------------------------------------------------------

# Since only one configuration is allowed there is no need for a FilterForm.

class ConfigForm(NetBoxModelForm):
    fieldsets = (
        FieldSet( 'name', 'ip_assignment_method', 'auto_validate_importables', 
                  'max_deletions', 'max_success_notifications', name="General" ),
        FieldSet( 'api_endpoint', 'web_address', 'token', 
                  'default_cidr', 'inventory_mode', 'monitored_by', 
                  'tls_connect', 'tls_accept', 'tls_psk_identity', 'tls_psk', name="Zabbix" ),
        FieldSet( 'default_tag', 'tag_prefix', 'tag_name_formatting', name="Tags" )
    )
    class Meta:
        model = models.Config
        fields = '__all__'

    def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
    
            zhost = "localhost"
    
            # IMPORTANT: We cannot pass 'initial=...' as an argument to
            # CharField() when declaring the field in the class body, because
            # these fields are mapped to model fields and are automatically
            # populated from the instance. Django will ignore 'initial' in this
            # context unless the form is unbound and the instance field is
            # empty, which often causes confusion.
            #
            # Therefore, we set 'initial' in the __init__ method, but *only*
            # when adding a new object (instance.pk is None), to avoid
            # overwriting existing values when editing an existing instance.s
            if not self.instance.pk:
                self.initial['name'] = "config"
                self.initial['api_endpoint'] = f"https://{zhost}/api_jsonrpc.php"
                self.initial['web_address'] = f"https://{zhost}"

            # Hide the 'tags' field on "add" and "edit" view
            self.fields.pop('tags', None)


    def clean(self):
        super().clean()

        if self.errors:
            logger.error( f"Edit config form errors: {self.errors}" )
            raise ValidationError( f"{self.errors}" )
        
        if self.cleaned_data is None:
            logger.error( f"Edit config form cleaned_data is None" )
            raise ValidationError( f"Edit config form cleaned_data is None" )
        
        # Prevent second config
        if not self.instance.pk and models.Config.objects.exists():
            raise ValidationError("Only one Zabbix configuration is allowed.")

        # Check max deletions
        max_deletions = self.cleaned_data.get("max_deletions")
        if max_deletions is not None and (max_deletions <= 0 or max_deletions > 100):
            self.add_error("max_deletions", "Max deletions must be in the range 1 - 100.")
    
        # Check max_success_notifications
        max_success_notifications = self.cleaned_data.get("max_success_notifications")
        if max_success_notifications is not None and (max_success_notifications <= 0 or max_success_notifications > 5):
            self.add_error("max_success_notifications", "Max deletions must be in the range 1 - 5.")
            
        # Check tls settings
        tls_connect = self.cleaned_data.get('tls_connect')
        tls_psk = self.cleaned_data.get('tls_psk')
        tls_psk_identity = self.cleaned_data.get('tls_psk_identity')
    
        # Validate PSK requirements
        if tls_connect == models.TLSConnectChoices.PSK:
            if not tls_psk_identity:
                self.add_error('tls_psk_identity', "TLS PSK Identity is required when TLS Connect is set to PSK.")
            if not tls_psk or not re.fullmatch(r'[0-9a-fA-F]{32,}', tls_psk):
                self.add_error('tls_psk', "TLS PSK must be at least 32 hexadecimal digits.")
    
        # Check connection/token
        try:
            z.validate_zabbix_credentials(self.cleaned_data['api_endpoint'], self.cleaned_data['token'])
            self.instance.version = z.fetch_version_from_credentials(self.cleaned_data['api_endpoint'], self.cleaned_data['token'])
            self.instance.connection = True
            self.instance.last_checked_at = now()
        except Exception:
            self.add_error('api_endpoint', mark_safe( "Failed to verify connection to Zabbix.<br>Please check the API address and token." ))
        

# ------------------------------------------------------------------------------
# Templates
# ------------------------------------------------------------------------------

class TemplateForm(NetBoxModelForm):
    class Meta:
        model = models.Template
        fields = ( "name", "templateid", "marked_for_deletion" )


class TemplateFilterForm(NetBoxModelFilterSetForm):
    model = models.Template

    name = forms.ModelMultipleChoiceField( queryset=models.Template.objects.all(), to_field_name='name', label="Name", required=False )
    marked_for_deletion = forms.NullBooleanField( label = "Marked For Deletion", required = False )
    templateid = forms.ChoiceField( label = "Template ID", required = False )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
         # Set templateid choices dynamically on instantiation
        templateids = models.Template.objects.order_by('templateid').distinct('templateid').values_list('templateid', flat=True)
        choices = [("", "---------")] + [(zid, zid) for zid in templateids if zid is not None]
        self.fields["templateid"].choices = choices

# ------------------------------------------------------------------------------
# Template Mappings
# ------------------------------------------------------------------------------

class TemplateMappingForm(NetBoxModelForm):
        class Meta:
            model = models.TemplateMapping
            fields = [ 'name', 'templates', 'interface_type', 'sites', 'roles', 'platforms', 'tags' ]

        def clean(self):
            super().clean()
            
            sites = self.cleaned_data['sites']
            roles = self.cleaned_data['roles']
            platforms = self.cleaned_data['platforms']
                
            if not (sites or roles or platforms):
                raise forms.ValidationError(
                    "At least one of sites, roles or platforms must be set for mapping."
                )

# ------------------------------------------------------------------------------
# Base Proxy Mappings
# ------------------------------------------------------------------------------

class BaseProxyMappingForm(NetBoxModelForm):
    mapping_model = None  # To be set by subclasses

    def clean(self):
        super().clean()
    
        sites     = self.cleaned_data.get( 'sites' )
        roles     = self.cleaned_data.get( 'roles' )
        platforms = self.cleaned_data.get( 'platforms' )
        tags      = self.cleaned_data.get( 'tags' )
    
        if not (sites or roles or platforms):
            raise forms.ValidationError( "At least one of sites, roles or platforms must be set for mapping." )
    
        site_ids     = set( s.id for s in sites )
        role_ids     = set( r.id for r in roles )
        platform_ids = set( p.id for p in platforms )
        tag_slugs    = set( t.slug for t in tags )
    
        conflicting = []
    
        for other in self.mapping_model.objects.exclude( pk=self.instance.pk ):
    
            other_site_ids     = set( other.sites.values_list( 'id', flat=True ) ) if other.sites.exists() else set()
            other_role_ids     = set( other.roles.values_list( 'id', flat=True ) ) if other.roles.exists() else set()
            other_platform_ids = set( other.platforms.values_list( 'id', flat=True ) ) if other.platforms.exists() else set()
            other_tag_slugs    = set( other.tags.values_list( 'slug', flat=True ) ) if other.tags.exists() else set()
    
            # Helper function to check field overlap
            def overlap(set1, set2):
                # True if either set is empty (wildcard) or intersection is non-empty
                return not set1 or not set2 or bool(set1 & set2)
    
            # Check sites, roles, platforms for overlap
            if not (overlap( site_ids, other_site_ids ) and
                    overlap( role_ids, other_role_ids ) and
                    overlap( platform_ids, other_platform_ids ) ):
                continue  # No conflict, skip
    
            # For tags, conflict only if tags overlap by subset relationship in either direction
            # i.e., either other_tag_slugs is subset of tag_slugs, or vice versa,
            # or both empty means wildcard
            if other_tag_slugs and tag_slugs:
                tags_conflict = other_tag_slugs.issubset( tag_slugs ) or tag_slugs.issubset( other_tag_slugs )
                if not tags_conflict:
                    continue  # No conflict
            # If either tag set empty => wildcard => assume conflict
    
            conflicting.append( other.name )
    
        if conflicting:
            raise forms.ValidationError( f"This mapping overlaps with existing mapping(s): {', '.join(conflicting)}." )
        

# ------------------------------------------------------------------------------
# Proxy
# ------------------------------------------------------------------------------

class ProxyForm(NetBoxModelForm):
    class Meta:
        model = models.Proxy
        fields = ( "name", "proxyid", "proxy_groupid", "marked_for_deletion" )


class ProxyFilterForm(NetBoxModelFilterSetForm):
    model = models.Proxy

    name = forms.ModelMultipleChoiceField( queryset=models.Proxy.objects.all(), to_field_name='name', label="Name", required=False )
    proxyid = forms.ChoiceField( label = "Proxy ID", required = False )
    proxy_groupid = forms.ChoiceField( label = "Proxy Group ID", required = False )
    marked_for_deletion = forms.NullBooleanField( label = "Marked For Deletion", required = False )
    
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
         # Set proxyid choices dynamically on instantiation
        proxyids = models.Proxy.objects.order_by('proxyid').distinct('proxyid').values_list('proxyid', flat=True)
        choices = [("", "---------")] + [(zid, zid) for zid in proxyids if zid is not None]
        self.fields["proxyid"].choices = choices

         
# ------------------------------------------------------------------------------
# Proxy Mappings
# ------------------------------------------------------------------------------

class ProxyMappingForm(BaseProxyMappingForm):
    mapping_model = models.ProxyMapping
    
    class Meta:
        model = models.ProxyMapping
        fields = [ 'name', 'proxy', 'sites', 'roles', 'platforms', 'tags' ]


# ------------------------------------------------------------------------------
# Proxy Groups
# ------------------------------------------------------------------------------

class ProxyGroupForm(NetBoxModelForm):
    class Meta:
        model = models.ProxyGroup
        fields = ( "name", "proxy_groupid", "marked_for_deletion" )


class ProxyGroupFilterForm(NetBoxModelFilterSetForm):
    model = models.ProxyGroup

    name = forms.ModelMultipleChoiceField( queryset=models.ProxyGroup.objects.all(), to_field_name='name', label="Name", required=False )
    proxy_groupid = forms.ChoiceField( label = "Proxy Group ID", required = False )
    marked_for_deletion = forms.NullBooleanField( label = "Marked For Deletion", required = False )
    
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

         # Set proxyid choices dynamically on instantiation
        proxy_groupids = models.ProxyGroup.objects.order_by('proxy_groupid').distinct('proxy_groupid').values_list('proxy_groupid', flat=True)
        choices = [("", "---------")] + [(zid, zid) for zid in proxy_groupids if zid is not None]
        self.fields["proxy_groupid"].choices = choices

# ------------------------------------------------------------------------------
# Proxy Group Mappings
# ------------------------------------------------------------------------------

class ProxyGroupMappingForm(BaseProxyMappingForm):
    mapping_model = models.ProxyGroupMapping

    class Meta:
        model = models.ProxyGroupMapping
        fields = [ 'name', 'proxy_group', 'sites', 'roles', 'platforms', 'tags' ]
    

# ------------------------------------------------------------------------------
# Hostgroups
# ------------------------------------------------------------------------------

class HostGroupForm(NetBoxModelForm):
    class Meta:
        model = models.HostGroup
        fields = [ 'name', 'groupid', "marked_for_deletion" ]


# ------------------------------------------------------------------------------
# Hostgroup Mappings
# ------------------------------------------------------------------------------

class HostGroupMappingForm(NetBoxModelForm):
        class Meta:
            model = models.HostGroupMapping
            fields = [ 'name','host_groups','sites','roles','platforms','tags' ]


        def clean(self):
            super().clean()
            
            sites = self.cleaned_data['sites']
            roles = self.cleaned_data['roles']
            platforms = self.cleaned_data['platforms']
                
            if not (sites or roles or platforms):
                raise forms.ValidationError( "At least one of sites, roles or platforms must be set for mapping." )


# ------------------------------------------------------------------------------
# Device Mappings
# ------------------------------------------------------------------------------

class DeviceMappingsFilterForm(DeviceFilterForm):
    hostgroups  = forms.ModelMultipleChoiceField( queryset=models.HostGroupMapping.objects.all(), required=False, label="Host Groups" )
    templates   = forms.ModelMultipleChoiceField( queryset=models.TemplateMapping.objects.all(), required=False, label="Templates" )
    proxy       = forms.ModelChoiceField( queryset=models.ProxyMapping.objects.all(), required=False, label="Proxy" )
    proxy_group = forms.ModelChoiceField( queryset=models.ProxyGroupMapping.objects.all(), required=False, label="Proxy Group" )

    fieldsets = DeviceFilterForm.fieldsets + ( FieldSet( 'hostgroups', 'templates', 'proxy', 'proxy_group', name='Zabbix' ), )

    
# ------------------------------------------------------------------------------
# VM Mappings
# ------------------------------------------------------------------------------

class VMMappingsFilterForm(VirtualMachineFilterForm):
    hostgroups  = forms.ModelMultipleChoiceField( queryset=models.HostGroupMapping.objects.all(), required=False, label="Host Groups" )
    templates   = forms.ModelMultipleChoiceField( queryset=models.TemplateMapping.objects.all(), required=False, label="Templates" )
    proxy       = forms.ModelChoiceField( queryset=models.ProxyMapping.objects.all(), required=False, label="Proxy" )
    proxy_group = forms.ModelChoiceField( queryset=models.ProxyGroupMapping.objects.all(), required=False, label="Proxy Group" )

    fieldsets = DeviceFilterForm.fieldsets + ( FieldSet( 'hostgroups', 'templates', 'proxy', 'proxy_group', name='Zabbix' ), )


# ------------------------------------------------------------------------------
# NetBox Only Devices
# ------------------------------------------------------------------------------

class NetBoxOnlyDevicesFilterForm(DeviceFilterForm):
    hostgroups  = forms.ModelMultipleChoiceField( queryset=models.HostGroupMapping.objects.all(), required=False, label="Host Groups" )
    templates   = forms.ModelMultipleChoiceField( queryset=models.TemplateMapping.objects.all(), required=False, label="Templates" )
    proxy       = forms.ModelChoiceField( queryset=models.ProxyMapping.objects.all(), required=False, label="Proxy" )
    proxy_group = forms.ModelChoiceField( queryset=models.ProxyGroupMapping.objects.all(), required=False, label="Proxy Group" )

    fieldsets = DeviceFilterForm.fieldsets + ( FieldSet( 'hostgroups', 'templates', 'proxy', 'prox_ygroup', name='Zabbix' ), )



# ------------------------------------------------------------------------------
# NetBox Only VMs
# ------------------------------------------------------------------------------

class NetBoxOnlyVMsFilterForm(VirtualMachineFilterForm):
    hostgroups  = forms.ModelMultipleChoiceField( queryset=models.HostGroupMapping.objects.all(), required=False, label="Host Groups" )
    templates   = forms.ModelMultipleChoiceField( queryset=models.TemplateMapping.objects.all(), required=False, label="Templates" )
    proxy       = forms.ModelChoiceField( queryset=models.ProxyMapping.objects.all(), required=False, label="Proxy" )
    proxy_group = forms.ModelChoiceField( queryset=models.ProxyGroupMapping.objects.all(), required=False, label="Proxy Group" )

    fieldsets = VirtualMachineFilterForm.fieldsets + ( FieldSet( 'hostgroups', 'templates', 'proxy', 'proxy_group', name='Zabbix' ), )


# ------------------------------------------------------------------------------
# Zabbix Configurations
# ------------------------------------------------------------------------------

class DeviceZabbixConfigForm(NetBoxModelForm):
    device = forms.ModelChoiceField( queryset=Device.objects.all(), label='Device', help_text='Select the NetBox Device to link this Zabbix host to.' )

    class Meta:
        model = models.DeviceZabbixConfig
        fields = ('device', 'status', 'monitored_by', 'templates', 'proxy', 'proxy_group', 'host_groups' )

    def __init__(self, *args, **kwargs):
        instance = kwargs.get( 'instance', None )
    
        super().__init__(*args, **kwargs)

        # Add specific device 
        if self.initial.get('device_id'):
            specific_device_id = self.initial.get( 'device_id' )
            self.fields['device'].queryset = Device.objects.filter( pk=specific_device_id )
            self.initial['device'] = specific_device_id
            return

        # Exclude already used devices from the queryset
        if not instance:  
            # Creating a new DeviceZabbixConfig
            used_device_ids = models.DeviceZabbixConfig.objects.values_list( 'device_id', flat=True )
            self.fields['device'].queryset = Device.objects.exclude( id__in=used_device_ids )
        else:  
            # Editing an existing DeviceZabbixConfig
            used_device_ids = models.DeviceZabbixConfig.objects.exclude( id=instance.id ).values_list( 'device_id', flat=True )
            self.fields['device'].queryset = Device.objects.exclude( id__in=used_device_ids )


class DeviceZabbixConfigFilterForm(NetBoxModelFilterSetForm):
    model = models.DeviceZabbixConfig

    status       = forms.ChoiceField( label = "Status", choices = [ ("", "---------")] + models.StatusChoices.choices, required = False )
    templates    = forms.ModelMultipleChoiceField( label = "Templates",    queryset = models.Template.objects.all(),   required = False )
    proxies      = forms.ModelMultipleChoiceField( label = "Proxies",      queryset = models.Proxy.objects.all(),      required = False )
    proxy_groups = forms.ModelMultipleChoiceField( label = "Proxy Groups", queryset = models.ProxyGroup.objects.all(), required = False )
    host_groups  = forms.ModelMultipleChoiceField( label = "Host Groups",  queryset = models.HostGroup.objects.all(),  required = False )

    hostid    = forms.ChoiceField( label = "Zabbix Host ID", required = False )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

         # Set hostid choices dynamically on instantiation
        hostids = models.DeviceZabbixConfig.objects.order_by( 'hostid' ).distinct( 'hostid' ).values_list( 'hostid', flat=True )
        choices = [("", "---------")] + [(zid, zid) for zid in hostids if zid is not None]
        self.fields["hostid"].choices = choices


class VMZabbixConfigForm(NetBoxModelForm):
    virtual_machine = forms.ModelChoiceField( queryset=VirtualMachine.objects.all(), label='Virtual Machine', help_text='Select the NetBox Virtual Machine to link this Zabbix host to.' )

    class Meta:
        model = models.VMZabbixConfig
        fields = ('virtual_machine', 'status', 'monitored_by', 'templates', 'proxy', 'proxy_group', 'host_groups')

    def __init__(self, *args, **kwargs):
        instance = kwargs.get('instance', None)
    
        super().__init__(*args, **kwargs)


        # Add specific virtual machine 
        if self.initial.get('vm_id'):
            specific_vm_id = self.initial.get( 'vm_id' )
            self.fields['virtual_machine'].queryset = VirtualMachine.objects.filter( pk=specific_vm_id )
            self.initial['virtual_machine'] = specific_vm_id
            return
        
        # Exclude already used virtual machine from the queryset
        if not instance:  
            # Creating a new VMZabbixConfig
            used_vms_ids = models.VMZabbixConfig.objects.values_list( 'virtual_machine_id', flat=True )
            self.fields['virtual_machine'].queryset = VirtualMachine.objects.exclude( id__in=used_vms_ids )
        else:  
            # Editing an existing VMZabbixConfig
            used_vms_ids = models.VMZabbixConfig.objects.exclude( id=instance.id ).values_list( 'virtual_machine_id', flat=True )
            self.fields['virtual_machine'].queryset = VirtualMachine.objects.exclude( id__in=used_vms_ids )


class VMZabbixConfigFilterForm(NetBoxModelFilterSetForm):
    model = models.ZabbixConfig

    status       = forms.ChoiceField( label = "Status", choices = [ ("", "---------")] + models.StatusChoices.choices, required = False )
    templates    = forms.ModelMultipleChoiceField( label = "Templates",    queryset = models.Template.objects.all(),   required = False )
    proxies      = forms.ModelMultipleChoiceField( label = "Proxies",      queryset = models.Proxy.objects.all(),      required = False )
    proxy_groups = forms.ModelMultipleChoiceField( label = "Proxy Groups", queryset = models.ProxyGroup.objects.all(), required = False )
    host_groups  = forms.ModelMultipleChoiceField( label = "Host Groups",  queryset = models.HostGroup.objects.all(),  required = False )
    
    hostid    = forms.ChoiceField( label = "Zabbix Host ID", required = False )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

         # Set hostid choices dynamically on instantiation
        hostids = models.VMZabbixConfig.objects.order_by( 'hostid' ).distinct( 'hostid' ).values_list( 'hostid', flat=True )
        choices = [("", "---------")] + [(zid, zid) for zid in hostids if zid is not None]
        self.fields["hostid"].choices = choices


# ------------------------------------------------------------------------------
# Interfaces
# ------------------------------------------------------------------------------

class DeviceAgentInterfaceForm(NetBoxModelForm):
    class Meta:
        model = models.DeviceAgentInterface
        fields = ( 'name', 'host', 'interface', 'ip_address', 'dns_name', 'available', 'useip', 'useip', 'main', 'port' )

    name = forms.CharField( max_length=255, required=True )
    available = forms.ChoiceField( choices=models.AvailableChoices )
    useip = forms.ChoiceField( label="Connect using", choices=models.UseIPChoices )
    main = forms.ChoiceField( choices=models.MainChoices )
    port = forms.IntegerField( required=True )

    host = DynamicModelChoiceField( 
        label="Device Zabbix Config",      
        queryset=models.DeviceZabbixConfig.objects.all(),
        required=True,
    )

    interface = DynamicModelChoiceField( 
        label="Device Interface",
        queryset = models.AvailableDeviceInterface.objects.all(),
        query_params={"device_id": "$host"},
        required=True,
    )

    ip_address = DynamicModelChoiceField(
        label="IP Address",
        queryset=IPAddress.objects.all(),
        query_params={ "interface_id": "$interface" },
        required=True,
    )

    dns_name = forms.CharField(
           label="DNS Name",
           max_length=255,
           required=False,
           disabled=True,
           widget=forms.TextInput(attrs={'data-field': 'dns_name'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.initial.get('device_zabbix_config_id'):
            specific_device_zabbix_config_id = self.initial.get( 'device_zabbix_config_id' )
            queryset = models.DeviceZabbixConfig.objects.filter( pk=specific_device_zabbix_config_id )
            self.fields['host'].queryset = queryset
            self.initial['host'] = specific_device_zabbix_config_id
            self.initial['name'] = f"{queryset[0].get_name()}-agent"

        # Set the initial value of the calculated DNS name if editing an existing instance
        if self.instance.pk:
            self.fields['dns_name'].initial = self.instance.resolved_dns_name


class DeviceSNMPv3InterfaceForm(NetBoxModelForm):
    class Meta:
        model = models.DeviceSNMPv3Interface
        fields = ( 'name', 'host', 'interface', 'ip_address', 'dns_name', 
                   'available', 'useip', 'useip', 'main', 'port',
                   'snmp_max_repetitions',
                   'snmp_contextname',
                   'snmp_securityname',
                   'snmp_securitylevel',
                   'snmp_authprotocol',
                   'snmp_authpassphrase',
                   'snmp_privprotocol',
                   'snmp_privpassphrase',
                   'snmp_bulk' )

    name = forms.CharField( max_length=255, required=True )
    available = forms.ChoiceField( choices=models.AvailableChoices )
    useip = forms.ChoiceField( label="Connect using", choices=models.UseIPChoices )
    main = forms.ChoiceField( choices=models.MainChoices )
    port = forms.IntegerField( required=True )

    snmp_max_repetitions = forms.IntegerField( label="Max Repetition Count", initial=10 )
    snmp_contextname     = forms.CharField( label="Context Name", max_length=255 )
    snmp_securityname    = forms.CharField( max_length=255, label="Security Name" )
    snmp_securitylevel   = forms.ChoiceField( label="Security Level", choices=models.SNMPSecurityLevelChoices, initial=models.SNMPSecurityLevelChoices.authPriv )
    snmp_authprotocol    = forms.ChoiceField( label="Authentication Protocol", choices=models.SNMPAuthProtocolChoices, initial=models.SNMPAuthProtocolChoices.SHA1 )
    snmp_authpassphrase  = forms.CharField( max_length=255, label="Authentication Passphrase", initial="{$SNMPV3_AUTHPASS}" )
    snmp_privprotocol    = forms.ChoiceField( label="Privacy Protocol", choices=models.SNMPPrivProtocolChoices, initial=models.SNMPPrivProtocolChoices.AES128 )
    snmp_privpassphrase  = forms.CharField( max_length=255, label="Privacy Passphrase", initial="{$SNMPV3_PRIVPASS}" )
    snmp_bulk            = forms.ChoiceField( label="Bulk", choices=models.SNMPBulkChoices, initial=models.SNMPBulkChoices.YES )
    
    host = DynamicModelChoiceField( 
           label="Device Zabbix Config",      
           queryset=models.DeviceZabbixConfig.objects.all(),
           required=True,
       )
    
    interface = DynamicModelChoiceField( 
        label="Device Interface",
        queryset = models.AvailableDeviceInterface.objects.all(),
        query_params={"device_id": "$host"},
        required=True,
    )
    
    ip_address = DynamicModelChoiceField(
        label="IP Address",
        queryset=IPAddress.objects.all(),
        query_params={ "interface_id": "$interface" },    
        required=True,
    )
    
    dns_name = forms.CharField(
           label="DNS Name",
           max_length=255,
           required=False,
           disabled=True,
           widget=forms.TextInput(attrs={'data-field': 'dns_name'})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


        if self.initial.get('device_zabbix_config_id'):
            specific_device_zabbix_confighost_id = self.initial.get( 'device_zabbix_config_id' )
            queryset = models.DeviceZabbixConfig.objects.filter( pk=specific_device_zabbix_confighost_id )
            self.fields['host'].queryset = queryset
            self.initial['host'] = specific_device_zabbix_confighost_id
            self.initial['name'] = f"{queryset[0].get_name()}-snmpv3"
        
        # Set the initial value of the calculated DNS name if editing an existing instance
        if self.instance.pk:
            self.fields['dns_name'].initial = self.instance.resolved_dns_name


class VMAgentInterfaceForm(NetBoxModelForm):
    class Meta:
        model = models.DeviceAgentInterface
        fields = ( 'name', 'host', 'interface', 'ip_address', 'dns_name', 'available', 'useip', 'useip', 'main', 'port' )

    name = forms.CharField( max_length=255, required=True )
    available = forms.ChoiceField( choices=models.AvailableChoices )
    useip = forms.ChoiceField( label="Connect using", choices=models.UseIPChoices )
    main = forms.ChoiceField( choices=models.MainChoices )
    port = forms.IntegerField( required=True )

    host = DynamicModelChoiceField( 
        label="VM Zabbix Config",
        queryset=models.VMZabbixConfig.objects.all(),
        required=True,
    )

    interface = DynamicModelChoiceField( 
        label="VM Interface",
        queryset = models.AvailableVMInterface.objects.all(),
        query_params={"virtual_machine_id": "$host"},
        required=True,
    )

    ip_address = DynamicModelChoiceField(
        label="IP Address",
        queryset=IPAddress.objects.all(),
        query_params={ "vminterface_id": "$interface" },
        required=True,
    )

    dns_name = forms.CharField(
           label="DNS Name",
           max_length=255,
           required=False,
           disabled=True,
           widget=forms.TextInput(attrs={'data-field': 'dns_name'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.initial.get('vm_zabbix_config_id'):
            specific_vm_zabbix_config_id = self.initial.get( 'vm_zabbix_config_id' )
            queryset = models.VMZabbixConfig.objects.filter( pk=specific_vm_zabbix_config_id )
            self.fields['host'].queryset = queryset
            self.initial['host'] = specific_vm_zabbix_config_id
            self.initial['name'] = f"{queryset[0].get_name()}-agent"

        # Set the initial value of the calculated DNS name if editing an existing instance
        if self.instance.pk:
            self.fields['dns_name'].initial = self.instance.resolved_dns_name


class VMSNMPv3InterfaceForm(NetBoxModelForm):
    class Meta:
        model = models.VMSNMPv3Interface
        fields = ( 'name', 'host', 'interface', 'ip_address', 'dns_name', 
                   'available', 'useip', 'useip', 'main', 'port',
                   'snmp_max_repetitions',
                   'snmp_contextname',
                   'snmp_securityname',
                   'snmp_securitylevel',
                   'snmp_authprotocol',
                   'snmp_authpassphrase',
                   'snmp_privprotocol',
                   'snmp_privpassphrase',
                   'snmp_bulk' )

    name = forms.CharField( max_length=255, required=True )
    available = forms.ChoiceField( choices=models.AvailableChoices )
    useip = forms.ChoiceField( label="Connect using", choices=models.UseIPChoices )
    main = forms.ChoiceField( choices=models.MainChoices )
    port = forms.IntegerField( required=True )

    snmp_max_repetitions = forms.IntegerField( label="Max Repetition Count", initial=10 )
    snmp_contextname     = forms.CharField( label="Context Name", max_length=255 )
    snmp_securityname    = forms.CharField( max_length=255, label="Security Name" )
    snmp_securitylevel   = forms.ChoiceField( label="Security Level", choices=models.SNMPSecurityLevelChoices, initial=models.SNMPSecurityLevelChoices.authPriv )
    snmp_authprotocol    = forms.ChoiceField( label="Authentication Protocol", choices=models.SNMPAuthProtocolChoices, initial=models.SNMPAuthProtocolChoices.SHA1 )
    snmp_authpassphrase  = forms.CharField( max_length=255, label="Authentication Passphrase", initial="{$SNMPV3_AUTHPASS}" )
    snmp_privprotocol    = forms.ChoiceField( label="Privacy Protocol", choices=models.SNMPPrivProtocolChoices, initial=models.SNMPPrivProtocolChoices.AES128 )
    snmp_privpassphrase  = forms.CharField( max_length=255, label="Privacy Passphrase", initial="{$SNMPV3_PRIVPASS}" )
    snmp_bulk            = forms.ChoiceField( label="Bulk", choices=models.SNMPBulkChoices, initial=models.SNMPBulkChoices.YES )
    
    host = DynamicModelChoiceField( 
           label="VM Zabbix Config",      
           queryset=models.VMZabbixConfig.objects.all(),
           required=True,
       )
    
    interface = DynamicModelChoiceField( 
        label="VM Interface",
        queryset = models.AvailableVMInterface.objects.all(),
        query_params={"vitual_machine_id": "$host"},
        required=True,
    )
    
    ip_address = DynamicModelChoiceField(
        label="IP Address",
        queryset=IPAddress.objects.all(),
        query_params={ "vminterface_id": "$interface" },
        required=True,
    )
    
    dns_name = forms.CharField(
           label="DNS Name",
           max_length=255,
           required=False,
           disabled=True,
           widget=forms.TextInput(attrs={'data-field': 'dns_name'})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


        if self.initial.get('vm_zabbix_config_id'):
            specific_vm_zabbix_config_id = self.initial.get( 'vm_zabbix_config_id' )
            queryset = models.DeviceZabbixConfig.objects.filter( pk=specific_vm_zabbix_config_id )
            self.fields['host'].queryset = queryset
            self.initial['host'] = specific_vm_zabbix_config_id
            self.initial['name'] = f"{queryset[0].get_name()}-snmpv3"
        
        # Set the initial value of the calculated DNS name if editing an existing instance
        if self.instance.pk:
            self.fields['dns_name'].initial = self.instance.resolved_dns_name


# ------------------------------------------------------------------------------
# Tag Mapping
# ------------------------------------------------------------------------------

class TagMappingForm(NetBoxModelForm):
    object_type = forms.ChoiceField(choices=models.TagMapping.OBJECT_TYPE_CHOICES, initial='device')
    prefix = "gurka"

    class Meta:
        model = models.TagMapping
        fields = ['object_type']  # exclude 'field_selection' from raw rendering

    def __init__(self, *args, **kwargs):
        super().__init__(*args, prefix=self.prefix, **kwargs)

        object_type = (
            self.initial.get('object_type')
            or self.data.get('object_type')
            or getattr(self.instance, 'object_type', None)
            or 'device'
        )

        configured_fields = PLUGIN_SETTINGS.get('field_mappings', {}).get(object_type, [])

        # Prepare a lookup for existing enabled states from instance.field_selection
        existing_selection = {}
        if self.instance.pk and self.instance.field_selection:
            for entry in self.instance.field_selection:
                existing_selection[entry['value']] = entry.get('enabled', False)

        # Ensure these aren't in the rendered form
        self.fields.pop( 'tags', None )
        
        # Dynamically add BooleanFields for each field with initial enabled value
        for field_name, field_value in configured_fields:
            # Use a unique prefix for the form field key to avoid name
            # collisions with existing NetBox fields. 
            # This allows us to safely use common or duplicate display names in
            # 'field_mappings', such as "Tags".
            field_key = slugify( f"{self.prefix}_{field_name}" )
            self.fields[field_key] = forms.BooleanField(
                label=field_name,
                required=False,
                initial=existing_selection.get( field_value, False ),
            )


    def clean_object_type(self):
        object_type = self.cleaned_data['object_type']
        qs = models.TagMapping.objects.filter( object_type=object_type )
        if self.instance.pk:
            qs = qs.exclude( pk=self.instance.pk )
        if qs.exists():
            raise forms.ValidationError( f"A mapping for object type '{object_type}' already exists." )
        return object_type


    def save(self, commit=True):
        # Build list of dicts with name, value, and enabled
        object_type = self.cleaned_data['object_type']
        configured_fields = PLUGIN_SETTINGS.get( 'field_mappings', {} ).get( object_type, [] )
        
        field_selection = []
        for field_name, field_value in configured_fields:
            field_key = slugify( f"{self.prefix}_{field_name}"  )

            enabled = self.cleaned_data.get( field_key, False )
            field_selection.append({
                "name": field_name,
                "value": field_value,
                "enabled": enabled,
            })

        self.instance.field_selection = field_selection
        return super().save( commit=commit )


# ------------------------------------------------------------------------------
# Device Mapping
# ------------------------------------------------------------------------------

from django.core.exceptions import FieldDoesNotExist

class DeviceMappingForm(NetBoxModelForm):
    fieldsets = (
        FieldSet(  'name', 'description', 'default', name="General" ),
        FieldSet( 'host_groups', 'templates', 'proxy', 'proxy_group', 'interface_type', name="Settings" ),
        FieldSet( 'sites', 'roles', 'platforms', name="Filters")
    )
    
    class Meta:
        model = models.DeviceMapping
        fields = '__all__' 

    #def __init__(self, *args, **kwargs):
    #    super().__init__(*args, **kwargs)
    #
    #    if not self.instance.default or models.DeviceMapping.objects.exists():
    #        self.initial["default"] = False
    #        self.fields.pop( "default", None )
    #                    
    #    if self.instance.default or not models.DeviceMapping.objects.exists():
    #        self.initial["default"] = True
    #        self.fields["default"].disabled = True
    #        self.initial["interface_type"] = models.InterfaceTypeChoices.Any
    #        self.fields["interface_type"].disabled = True
    #        
    #        self.fields.pop( "sites", None )
    #        self.fields.pop( "roles", None )
    #        self.fields.pop( "platforms", None )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
       
        # Are we creating the very first/default mapping?
        fist_mapping = models.DeviceMapping.objects.filter( default=True ).exists()
        
        if not fist_mapping or self.instance.default:
            # First mapping ever: it must be default
            self.initial['default'] = True
            self.fields['default'].disabled = True 
    
            # force interface_type to Any
            self.initial['interface_type'] = models.InterfaceTypeChoices.Any
            self.fields['interface_type'].disabled = True
    
            # remove all filter controls
            for field in ('sites', 'roles', 'platforms'):
                self.fields.pop( field, None )
            
            # prune the empty "Filters" FieldSet so it won't render at all
            self.fieldsets = [
                fs for fs in self.fieldsets
                if fs.name != 'Filters'
            ]
        else:
            # A default exists already: drop the 'default' field entirely
            self.fields.pop( 'default', None )

        
    def clean(self):
        super().clean()

        default = self.cleaned_data.get( 'default' )
        interface_type = self.cleaned_data.get( 'interface_type' )
        
        sites = self.cleaned_data.get( 'sites' )
        roles = self.cleaned_data.get( 'roles' )
        platforms = self.cleaned_data.get( 'platforms' )
    
        if default:
            # The default entry must not restrict on site/role/platform
            if sites and sites.exists() or roles and roles.exists() or platforms and platforms.exists():
                raise forms.ValidationError( "Default mapping cannot define sites, roles, or platforms." )
            if interface_type != models.InterfaceTypeChoices.Any:
                raise forms.ValidationError( "Default mapping must use interface_type = 'any'." )
        else:
            # Non-default mappings must restrict on at least one of sites/roles/platforms
            if not (sites.exists() or roles.exists() or platforms.exists()):
                raise forms.ValidationError( "At least one of sites, roles, or platforms must be set for non-default mappings." )
    
        # Ensure there is exactly one default in the database (excluding current instance if updating)
        if default:
            qs = models.DeviceMapping.objects.filter( default=True )
            if self.instance.pk:
                qs = qs.exclude( pk=self.instance.pk )
            if qs.exists():
                raise forms.ValidationError( "There can only be one default mapping." )
            return

        # Check for conflicting filters
        # Fallback filter must have all filters blank
        if default:
            if sites.exists() or roles.exists() or platforms.exists():
                raise ValidationError("Fallback filter cannot have any filter fields set.")
        else:
            # Check for overlap with other filters (excluding fallback and self)
            others = models.DeviceMapping.objects.exclude( pk=self.instance.pk ).filter( default=False )
            for other in others:
                if self._overlaps_with( other ):
                    raise ValidationError( f"Filter overlaps with existing filter: {other.name}" )
        
    def _overlaps_with(self, other):
        """
        Returns True if this mapping and 'other' have the same specificity and overlap.
        Allows subset/superset relationships (i.e., more specific mappings are allowed).
        """
        # Count how many filter fields are set for each mapping
        def count_fields(mapping):
            return sum(
                1 for field in ['sites', 'roles', 'platforms']
                if (self.cleaned_data.get( field ) if mapping is self else getattr( mapping, field ).exists())
            )
    
        self_fields = count_fields( self )
        other_fields = count_fields( other )
    
        # Only check for overlap if specificity is the same
        if self_fields != other_fields:
            return False
    
        # Now check for actual overlap
        for field in ['sites', 'roles', 'platforms']:
            current = self.cleaned_data.get( field )
            other_qs = getattr( other, field ).all()
            current_ids = set( current.values_list( 'pk', flat=True ) ) if current else set()
            other_ids   = set( other_qs.values_list( 'pk', flat=True ) ) if other_qs else set()
            
            # If both are set and have no intersection, no overlap
            if current_ids and other_ids and not current_ids & other_ids:
                return False
            # If either is empty, that's "all", so always overlap for this field
        return True  # Overlaps in all applicable fields




    def delete(self, *args, **kwargs):
        if self.default:
            raise ValidationError( "The default device mapping cannot be deleted." )
        super().delete(*args, **kwargs)


# ------------------------------------------------------------------------------
# VM Mapping
# ------------------------------------------------------------------------------

class VMMappingForm(NetBoxModelForm):
    class Meta:
        model = models.VMMapping
        fields = [ 'name', 'description', 'default', 
                  'host_groups', 'templates', 'proxy', 'proxy_group', 'platforms', 'interface_type', 
                  'sites', 'roles', 'platforms' ]

    def clean(self):
        super().clean()
        sites = self.cleaned_data['sites']
        roles = self.cleaned_data['roles']
        platforms = self.cleaned_data['platforms']
            
        if not (sites or roles or platforms):
            raise forms.ValidationError( "At least one of sites, roles or platforms must be set for mapping." )
    

# end