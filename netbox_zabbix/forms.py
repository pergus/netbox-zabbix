from netbox.forms import NetBoxModelForm, NetBoxModelFilterSetForm

from utilities.forms.fields import DynamicModelChoiceField
from ipam.models import IPAddress

from django.core.exceptions import ValidationError
from django.utils.timezone import now
from django.conf import settings
from django import forms

from dcim.models import Device
from virtualization.models import VirtualMachine

from netbox_zabbix import models
from netbox_zabbix import zabbix as z


PLUGIN_SETTINGS = settings.PLUGINS_CONFIG.get("netbox_zabbix", {})


#
# Notes
#
# DynamicModelChoiceField expects a corresponding API endpoint to fetch and
# filter options dynamically as a single-select field. Since we need to support
# multiple selections without relying on a custom API endpoint, use
# ModelMultipleChoiceField instead.
#


# ------------------------------------------------------------------------------
# Configuration
#

# Since only one configuration is allowed there is no need for a FilterForm.
from django.utils.safestring import mark_safe

class ConfigForm(NetBoxModelForm):
    class Meta:
        model = models.Config
        fields = ( 'name', 'api_endpoint', 'web_address', 'token', 'ip_assignment_method' )

    def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
    
            zhost = PLUGIN_SETTINGS.get("zabbix_host", "localhost")
    
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
    
        # Prevent second config
        if not self.instance.pk and models.Config.objects.exists():
            raise ValidationError("Only one Zabbix configuration is allowed.")
    
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
# Hosts
#

class DeviceHostForm(NetBoxModelForm):
    device = forms.ModelChoiceField( queryset=Device.objects.all(), label='Device', help_text='Select the NetBox Device to link this Zabbix host to.' )

    class Meta:
        model = models.DeviceHost
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
            # Creating a new DeviceHost
            used_device_ids = models.DeviceHost.objects.values_list( 'device_id', flat=True )
            self.fields['device'].queryset = Device.objects.exclude( id__in=used_device_ids )
        else:  
            # Editing an existing DeviceHost
            used_device_ids = models.DeviceHost.objects.exclude( id=instance.id ).values_list( 'device_id', flat=True )
            self.fields['device'].queryset = Device.objects.exclude( id__in=used_device_ids )


class DeviceHostFilterForm(NetBoxModelFilterSetForm):
    model = models.DeviceHost

    status    = forms.ChoiceField( label = "Status", choices = [ ("", "---------")] + models.StatusChoices.choices, required = False )
    templates = forms.ModelMultipleChoiceField( label = "Templates", queryset = models.Template.objects.all(), required = False )
    hostid    = forms.ChoiceField( label = "Zabbix Host ID", required = False )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

         # Set hostid choices dynamically on instantiation
        hostids = models.DeviceHost.objects.order_by( 'hostid' ).distinct( 'hostid' ).values_list( 'hostid', flat=True )
        choices = [("", "---------")] + [(zid, zid) for zid in hostids if zid is not None]
        self.fields["hostid"].choices = choices


class VMHostForm(NetBoxModelForm):
    virtual_machine = forms.ModelChoiceField( queryset=VirtualMachine.objects.all(), label='Virtual Machine', help_text='Select the NetBox Virtual Machine to link this Zabbix host to.' )

    class Meta:
        model = models.VMHost
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
            # Creating a new VMHost
            used_vms_ids = models.VMHost.objects.values_list( 'virtual_machine_id', flat=True )
            self.fields['virtual_machine'].queryset = VirtualMachine.objects.exclude( id__in=used_vms_ids )
        else:  
            # Editing an existing VMHost
            used_vms_ids = models.VMHost.objects.exclude( id=instance.id ).values_list( 'virtual_machine_id', flat=True )
            self.fields['virtual_machine'].queryset = VirtualMachine.objects.exclude( id__in=used_vms_ids )


class VMHostFilterForm(NetBoxModelFilterSetForm):
    model = models.DeviceHost

    status         = forms.ChoiceField( label = "Status", choices = [ ("", "---------")] + models.StatusChoices.choices, required = False )
    templates      = forms.ModelMultipleChoiceField( label = "Templates", queryset = models.Template.objects.all(), required = False )
    hostid = forms.ChoiceField( label = "Zabbix Host ID", required = False )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

         # Set hostid choices dynamically on instantiation
        hostids = models.VMHost.objects.order_by( 'hostid' ).distinct( 'hostid' ).values_list( 'hostid', flat=True )
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
        label="Zabbix Host",      
        queryset=models.DeviceHost.objects.all(),
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
           label="Zabbix Host",      
           queryset=models.DeviceHost.objects.all(),
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
      
            # Set the initial value of the calculated DNS name if editing an existing instance
            if self.instance.pk:
                self.fields['dns_name'].initial = self.instance.resolved_dns_name