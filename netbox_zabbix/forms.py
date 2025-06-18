
import re


from netbox.forms import NetBoxModelForm, NetBoxModelFilterSetForm

from utilities.forms.fields import DynamicModelChoiceField
from ipam.models import IPAddress

from django.utils.safestring import mark_safe
from django.core.exceptions import ValidationError
from django.utils.timezone import now
from django.conf import settings
from django import forms

from dcim.models import Device
from virtualization.models import VirtualMachine
from utilities.forms.rendering import FieldSet

from netbox_zabbix import models
from netbox_zabbix import zabbix as z

#from netbox_zabbix.logger import logger


#
# Notes
#
# DynamicModelChoiceField expects a corresponding API endpoint to fetch and
# filter options dynamically as a single-select field. Since we need to support
# multiple selections without relying on a custom API endpoint, use
# ModelMultipleChoiceField instead.
#


# ------------------------------------------------------------------------------
# Settings
#

# Since only one configuration is allowed there is no need for a FilterForm.
from django.forms import NumberInput

class ConfigForm(NetBoxModelForm):

    fieldsets = (
        FieldSet( 'name', 'ip_assignment_method', 'auto_validate_importables', 'max_deletions', 'max_success_notifications', name="General"),
        FieldSet( 'api_endpoint', 'web_address', 'token', 
                 'default_cidr', 'monitored_by', 
                 'tls_connect', 'tls_accept', 'tls_psk_identity', 'tls_psk', name="Zabbix" )
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

            # Set min/max on max_deletions field
            self.fields['max_deletions'].min_value = 1
            self.fields['max_deletions'].max_value = 100
            self.fields['max_deletions'].widget = NumberInput(attrs={
                'min': 1,
                'max': 100,
                'step': 1
            })

            # Set min/max on max_success_notifications field
            self.fields['max_success_notifications'].min_value = 0
            self.fields['max_success_notifications'].max_value = 5
            self.fields['max_success_notifications'].widget = NumberInput(attrs={
                'min': 0,
                'max': 5,
                'step': 1
            })
            

    def clean(self):
        super().clean()
    
        # Prevent second config
        if not self.instance.pk and models.Config.objects.exists():
            raise ValidationError( "Only one Zabbix configuration is allowed." )
    
        # Check max deletions
        max_deletions = self.cleaned_data.get( "max_deletions" )
        if max_deletions < 0 or max_deletions > 100:
            raise ValidationError( "Max deletions must be in the range 1 - 100." )
                    
        # Check tls settings
        tls_connect = self.cleaned_data.get( 'tls_connect' )
        tls_psk = self.cleaned_data.get( 'tls_psk' )
        tls_psk_identity = self.cleaned_data.get(  'tls_psk_identity' )
        
        # Validate PSK requirements
        if tls_connect == models.TLSConnectChoices.PSK:
            if not tls_psk_identity:
                raise ValidationError( "TLS PSK Identity is required when TLS Connect is set to PSK." )
        
            if not tls_psk or not re.fullmatch(r'[0-9a-fA-F]{32,}', tls_psk):
                raise ValidationError( "TLS PSK must be at least 32 hexadecimal digits." )
        

        # Check connection/token
        try:
            z.validate_zabbix_credentials(self.cleaned_data['api_endpoint'], self.cleaned_data['token'])
            self.instance.version = z.fetch_version_from_credentials(self.cleaned_data['api_endpoint'], self.cleaned_data['token'])
            self.instance.connection = True
            self.instance.last_checked_at = now()
        except Exception:
            raise ValidationError( mark_safe("Failed to verify connection to Zabbix.<br>Please check the API address and token.") )

# ------------------------------------------------------------------------------
# Templates
#

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
#

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
# Proxy
#

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
#

class ProxyMappingForm(NetBoxModelForm):
        class Meta:
            model = models.ProxyMapping
            fields = [ 'name', 'proxies', 'sites', 'roles', 'platforms', 'tags' ]

        
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
# Proxy Groups
#

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
#

class ProxyGroupMappingForm(NetBoxModelForm):
        class Meta:
            model = models.ProxyGroupMapping
            fields = [ 'name', 'proxygroups', 'sites', 'roles', 'platforms', 'tags' ]

        
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
# Hostgroups
#

class HostGroupForm(NetBoxModelForm):
    class Meta:
        model = models.HostGroup
        fields = [
            'name',
            'groupid',
        ]

# ------------------------------------------------------------------------------
# Hostgroup Mappings
#

class HostGroupMappingForm(NetBoxModelForm):
        class Meta:
            model = models.HostGroupMapping
            fields = [ 'name','hostgroups','sites','roles','platforms','tags' ]

        
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
# Device Host Groups
#
from dcim.forms import DeviceFilterForm
class DeviceHostGroupFilterForm(DeviceFilterForm):
    hostgroups = forms.ModelMultipleChoiceField( queryset=models.HostGroupMapping.objects.all(), required=False, label="Host Groups" )
    
    fieldsets = DeviceFilterForm.fieldsets + ( FieldSet( 'hostgroups', name='Zabbix' ), )

    

# ------------------------------------------------------------------------------
# Zabbix Configurations
#

class DeviceZabbixConfigForm(NetBoxModelForm):
    device = forms.ModelChoiceField( queryset=Device.objects.all(), label='Device', help_text='Select the NetBox Device to link this Zabbix host to.' )

    class Meta:
        model = models.DeviceZabbixConfig
        fields = ('device', 'status', 'templates')

    def __init__(self, *args, **kwargs):
        instance = kwargs.get('instance', None)
    
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

    status    = forms.ChoiceField( label = "Status", choices = [ ("", "---------")] + models.StatusChoices.choices, required = False )
    templates = forms.ModelMultipleChoiceField( label = "Templates", queryset = models.Template.objects.all(), required = False )
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
        fields = ('virtual_machine', 'status', 'templates')

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

    status         = forms.ChoiceField( label = "Status", choices = [ ("", "---------")] + models.StatusChoices.choices, required = False )
    templates      = forms.ModelMultipleChoiceField( label = "Templates", queryset = models.Template.objects.all(), required = False )
    hostid = forms.ChoiceField( label = "Zabbix Host ID", required = False )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

         # Set hostid choices dynamically on instantiation
        hostids = models.VMZabbixConfig.objects.order_by( 'hostid' ).distinct( 'hostid' ).values_list( 'hostid', flat=True )
        choices = [("", "---------")] + [(zid, zid) for zid in hostids if zid is not None]
        self.fields["hostid"].choices = choices


# ------------------------------------------------------------------------------
# Interface
#


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