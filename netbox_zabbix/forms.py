from netbox.forms import NetBoxModelForm, NetBoxModelFilterSetForm

from django.core.exceptions import ValidationError
from django.utils.timezone import now
from django.conf import settings
from django import forms

from dcim.models import Device, Interface
from virtualization.models import VirtualMachine

from netbox_zabbix import models
from netbox_zabbix import zabbix as z

import logging
logger = logging.getLogger('netbox.plugins.netbox_zabbix')


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

class ConfigForm(NetBoxModelForm):
    class Meta:
        model = models.Config
        fields = ('name', 'api_endpoint', 'web_address', 'token')

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
        logger.info("CLEAN")
        super().clean()
    
        # Prevent second config
        if not self.instance.pk and models.Config.objects.exists():
            raise ValidationError("Only one Zabbix configuration is allowed.")
    
        # Check connection/token
        try:
            z.verify_token(self.cleaned_data['api_endpoint'], self.cleaned_data['token'])
            self.instance.version = z.get_version(self.cleaned_data['api_endpoint'], self.cleaned_data['token'])
            self.instance.connection = True
            self.instance.last_checked_at = now()
        except Exception:
            raise ValidationError("Failed to verify connection to Zabbix. Please check the API address and token.")

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

    status         = forms.ChoiceField( label = "Status", choices = [ ("", "---------")] + models.StatusChoices.choices, required = False )
    templates      = forms.ModelMultipleChoiceField( label = "Templates", queryset = models.Template.objects.all(), required = False )
    zabbix_host_id = forms.ChoiceField( label = "Zabbix Host ID", required = False )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

         # Set zabbix_host_id choices dynamically on instantiation
        zabbix_host_ids = models.DeviceHost.objects.order_by( 'zabbix_host_id' ).distinct( 'zabbix_host_id' ).values_list( 'zabbix_host_id', flat=True )
        choices = [("", "---------")] + [(zid, zid) for zid in zabbix_host_ids if zid is not None]
        self.fields["zabbix_host_id"].choices = choices


class VMHostForm(NetBoxModelForm):
    virtual_machine = forms.ModelChoiceField( queryset=VirtualMachine.objects.all(), label='Virtual Machine', help_text='Select the NetBox Virtual Machine to link this Zabbix host to.' )

    class Meta:
        model = models.VMHost
        fields = ('virtual_machine', 'status', 'templates')

    def __init__(self, *args, **kwargs):
        instance = kwargs.get('instance', None)
    
        super().__init__(*args, **kwargs)
    
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
    zabbix_host_id = forms.ChoiceField( label = "Zabbix Host ID", required = False )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

         # Set zabbix_host_id choices dynamically on instantiation
        zabbix_host_ids = models.VMHost.objects.order_by( 'zabbix_host_id' ).distinct( 'zabbix_host_id' ).values_list( 'zabbix_host_id', flat=True )
        choices = [("", "---------")] + [(zid, zid) for zid in zabbix_host_ids if zid is not None]
        self.fields["zabbix_host_id"].choices = choices


# ------------------------------------------------------------------------------
# Interface
#
from utilities.forms.fields import DynamicModelChoiceField

class DeviceAgentInterfaceForm(NetBoxModelForm):
    class Meta:
        model = models.DeviceAgentInterface
        fields = ( 'host', 'interface', 'name', 'available', 'useip', 'useip', 'main', 'port', 'interface' )

    name = forms.CharField( max_length=255, required=True )
    available = forms.ChoiceField( choices=models.AvailableChoices )
    useip = forms.ChoiceField( label="Connect using", choices=models.UseIPChoices )
    main = forms.ChoiceField( choices=models.MainChoices )
    port = forms.IntegerField( required=True )
    host = forms.ModelChoiceField( queryset=models.DeviceHost.objects.all(), required=True )
    interface = DynamicModelChoiceField( 
        label="Device Interface",
        queryset = models.AvailableDeviceInterface.objects.all(),
        query_params={"device_id": "$host"},
        null_option="---------"
    )


class DeviceSNMPv3InterfaceForm(NetBoxModelForm):
    class Meta:
        model = models.DeviceAgentInterface
        fields = ( 'host', 'interface', 'name', 'available', 'useip', 'useip', 'main', 'port', 'interface' )

    name = forms.CharField( max_length=255, required=True )
    available = forms.ChoiceField( choices=models.AvailableChoices )
    useip = forms.ChoiceField( label="Connect using", choices=models.UseIPChoices )
    main = forms.ChoiceField( choices=models.MainChoices )
    port = forms.IntegerField( required=True )
    host = forms.ModelChoiceField( queryset=models.DeviceHost.objects.all(), required=True )
    interface = DynamicModelChoiceField( 
        label="Device Interface",
        queryset = models.AvailableDeviceInterface.objects.all(),
        query_params={"device_id": "$host"},
        null_option="---------"
    )
