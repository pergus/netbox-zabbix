from netbox.forms import NetBoxModelForm
from .models import ZBXConfig, ZBXTemplate, ZBXVM

import logging
logger = logging.getLogger('netbox.plugins.netbox_zabbix')

class ZBXConfigForm(NetBoxModelForm):
    class Meta:
        model = ZBXConfig
        fields = ("name", "api_address", "web_address", "token", "active")


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Is the config entry being edited the "default" entry?
        if self.instance.name == 'default':
            self.fields['name'].widget.attrs['readonly'] = True
        
    
    def save(self, commit=True):

        # If this config is being activated, deactivate the others
        if self.cleaned_data.get('active'):
            ZBXConfig.objects.filter(active=True).update(active=False)
        
        # If the config is being deactivated, activate the default config.
        instance = super().save(commit=False)
        if instance.pk:
            if self.cleaned_data.get('active') == False:
                if self.instance._prechange_snapshot.get('active') == True:
                    ZBXConfig.objects.filter(name="default").update(active=True)
        
        return super().save(commit)


class ZBXTemplateForm(NetBoxModelForm):
    class Meta:
        model = ZBXTemplate
        fields = ("name", "templateid", "last_synced", "marked_for_deletion" )

import django_filters
from netbox.forms import NetBoxModelFilterSetForm
from .models import ZBXTemplate

class ZBXTemplateFilterForm(NetBoxModelFilterSetForm):
    model = ZBXTemplate

    name = django_filters.CharFilter(lookup_expr='icontains', label='Name')


class ZBXVMForm(NetBoxModelForm):
    class Meta:
        model = ZBXVM
        fields = ("vm", "zbx_host_id", "status", "interface", "templates")


#
# Combined
#
from django.contrib.contenttypes.models import ContentType
from dcim.models import Device
from virtualization.models import VirtualMachine
from .models import ZBXHost, ZBXInterface

from utilities.forms.fields import ContentTypeChoiceField
from utilities.forms.widgets import HTMXSelect
from utilities.forms.fields import DynamicModelChoiceField


class ZBXHostForm(NetBoxModelForm):

    content_type = ContentTypeChoiceField(
           queryset=ContentType.objects.filter(model__in=["device", "virtualmachine"]),
           widget=HTMXSelect(),
           required=True,
           label='Host Type'
       )
    
    # The selector is nice but I have to disable it since I cannot get it to 
    # exclude hosts that already have zabbix configuration
    content_object = DynamicModelChoiceField(
            label= 'Host',
            queryset=Device.objects.none(),  # Initial queryset
            query_params={"id": 2},
            required=True,
            selector=False
        )


    class Meta: 
        model = ZBXHost
        fields = ['content_type', 'zbx_host_id', 'status', 'interface', 'templates']
    

    def __init__(self, *args, **kwargs):
        # Ensure initial dictionary exists and set default content_type to Device if not bound
        kwargs.setdefault('initial', {})
        if 'content_type' not in kwargs['initial']:
            try:
                kwargs['initial']['content_type'] = ContentType.objects.get(app_label='dcim', model='device').pk
            except ContentType.DoesNotExist:
                pass
    
        super().__init__(*args, **kwargs)
    
        # Reorder fields to ensure correct order
        self.order_fields([
            'content_type',
            'content_object',
            'zbx_host_id',
            'status',
            'interface',
            'templates',
        ])
    
        # Handle editing an existing ZBXHost or adding a new one
        instance = kwargs.get("instance")
    
        if instance and instance.pk and instance.content_type:
            self._initialize_for_edit(instance)
        elif self.initial.get('host_id'):
            self._initialize_for_add_specific_host()
        else:
            self._initialize_for_add()
    
    def _initialize_for_edit(self, instance):
        # Initialize the form for editing an existing ZBXHost
        model_class = instance.content_type.model_class()
        queryset = model_class.objects.filter(pk=instance.content_object.pk)
    
        self.fields["content_type"].initial = instance.content_type.pk
        self.fields["content_object"].initial = instance.content_object
        self.fields["content_object"].queryset = queryset
    
        # Hide content_type and make content_object read-only
        self.fields.pop("content_type", None)
        self.fields["content_object"].disabled = True
    

    def _initialize_for_add_specific_host(self):
        # Add specific host

        print(f"ADD SPECIFIC ZBXHOST {self.is_bound=} {self.data.get('host_id')=} {self.initial.get('host_id')=}" )
        print(f"ADD SPECIFIC ZBXHOST {self.is_bound=} {self.data.get('content_type')=} {self.initial.get('content_type')=}" )
        
        if self.is_bound:
            content_type_id = self.data.get("content_type")  # from submitted form
        else:
            content_type_id = self.initial.get("content_type")
        
        selected_host_id = self.initial.get("host_id")
        
        if selected_host_id:
            print(f"{content_type_id=}")
                        
            content_type = ContentType.objects.get(pk=content_type_id)            
            model_class = content_type.model_class()
            
            queryset = model_class.objects.filter(pk=selected_host_id)
        
            self.fields['content_object'] = DynamicModelChoiceField(
                label='Host',
                initial=queryset[0],
                queryset=queryset,
                query_params={"id": selected_host_id},
                required=True,
                selector=False,
           )
           
        

    def _initialize_for_add(self):
        # Add a new ZBXHost
        print(f"ADD NEW ZBXHOST {self.is_bound=} {self.data.get('host_id')=} {self.initial.get('host_id')=}" )
        print(f"ADD NEW ZBXHOST {self.is_bound=} {self.data.get('content_type')=} {self.initial.get('content_type')=}" )
        
        if self.is_bound:
            content_type_id = self.data.get("content_type")  # from submitted form
        else:
            content_type_id = self.initial.get("content_type")
        

        print(f"{content_type_id=}")
        content_type = ContentType.objects.get(pk=content_type_id)
        model_class = content_type.model_class()
                
            
    
        # Get the ids of all devices or vms that has an object_id, i.e. a zabbix configuration        
        linked_object_ids = list(ZBXHost.objects.filter(content_type=content_type).values_list('object_id', flat=True))

         # Get all devices or vms that doesn't have an object_id, i.e. no zabbix configuration
        queryset = model_class.objects.exclude(id__in=linked_object_ids)

         # Get the ids of all devices or vms that doesn't have an object_id, i.e. no zabbix configuration
        available_object_ids = list(model_class.objects.exclude(id__in=linked_object_ids).values_list('id', flat=True))

        # For some reson the follwing doesn't work, instead we have to create
        # a new DynamicModelChoiceField instance and assign that to the content_object.
        # self.fields['content_object']._queryset = queryset
        # self.fields['content_object'].query_params = {"id": available_object_ids}
        self.fields['content_object'] = DynamicModelChoiceField(
             label='Host',
             queryset=queryset,
             query_params={"id": available_object_ids},
             required=True,
             selector=False
        )
        

    def save(self, commit=True):
        instance = super().save(commit=False)
    
        # content_object is selected by the user
        obj = self.cleaned_data['content_object']

        # store the pk of the content_object in object_id
        instance.object_id = obj.pk
        instance.content_type = ContentType.objects.get_for_model(obj)
    
        if commit:
            instance.save()
            self.save_m2m()
            
        return instance
    




#class ZBXInterfaceForm(NetBoxModelForm):
#    class Meta:
#        model = ZBXInterface
#        fields = (
#            'host', 'interfaceid', 'available', 'hostid', 'type',
#            'ip', 'dns', 'port', 'useip', 'main', 'details',
#        )
#    
#    def __init__(self, *args, **kwargs):
#        initial = kwargs.get('initial', {})
#        super().__init__(*args, **kwargs)
#    
#        if 'host' in self.fields and 'host' in initial:
#            self.fields['host'].initial = initial['host']

from django import forms
from utilities.forms.rendering import FieldSet, TabbedGroups, InlineFields
class ZBXInterfaceForm(NetBoxModelForm):

    TYPE_CHOICES = [
        (1, 'Agent'),
        (2, 'SNMP'),
    ]

    AVAILABLE_CHOICES = [
        (0, 'Unknown'),
        (1, 'Available'),
        (2, 'Unavailable'),
    ]

    USEIP_CHOICES = [
        (0, 'DNS'),
        (1, 'IP'),
    ]

    MAIN_CHOICES = [
        (0, 'No'),
        (1, 'Yes'),
    ]

    SNMP_BULK_CHOICES = [
        (0, 'No'),
        (1, 'Yes'),        
    ]

    SNMP_VERSION_CHOICES = [
        (1, 'SNMPv1'),
        (2, 'SNMPv2c'),
        (3, 'SNMPv3'),
    ]

    SNMP_SECURITY_LEVEL_CHOICES = [
        (0, 'noAuthNoPriv'),
        (1, 'authNoPriv'),
        (2, 'authPriv'),
    ]

    SNMP_AUTH_PROTOCOL_CHOICES = [
        (0, 'MD5'),
        (1, 'SHA1'),
        (2, 'SHA224'),
        (3, 'SHA256'),
        (4, 'SHA384'),
        (5, 'SHA512'),
    ]

    SNMP_PRIV_PROTOCOL_CHOICES = [
        (0, 'DES'),
        (1, 'AES128'),
        (2, 'AES192'),
        (3, 'AES256'),
        (4, 'AES192C'),
        (5, 'AES256C'),
    ]


    #
    interfaceid = forms.IntegerField(label="Interface ID", required=False)

    # Interface settings
    ip = forms.GenericIPAddressField(label="IP Address", required=False)
    dns = forms.CharField(label="DNS Name", required=False)
    port = forms.CharField(label="Port", required=False)

    useip = forms.ChoiceField(choices=USEIP_CHOICES, label="Connect using", required=False)
    main = forms.ChoiceField(choices=MAIN_CHOICES, label="Default Interface", required=False)
    type = forms.ChoiceField(choices=TYPE_CHOICES, label="Interface Type", required=False)


    # SNMP Common settings
    snmp_version = forms.ChoiceField(choices=SNMP_VERSION_CHOICES, label="Version", initial=3, required=False)
    snmp_community = forms.CharField(label="Community", initial="{$SNMP_COMMUNITY}", required=False)
    snmp_max_repetitions = forms.IntegerField(label="Max repetition count", initial=10, required=False)

    # SNMPv3 settings and default values
    snmp_contextname = forms.CharField(label="Context Name", required=False)
    snmp_securityname = forms.CharField(label="Security Name", initial="{$SNMPV3_USER}", required=False)
    snmp_securitylevel = forms.ChoiceField(label="Security Level", choices=SNMP_SECURITY_LEVEL_CHOICES, initial=2, required=False)
    snmp_authprotocol = forms.ChoiceField(label="Authentication Protocol", choices=SNMP_AUTH_PROTOCOL_CHOICES, initial=1, required=False)
    snmp_authpassphrase = forms.CharField(label="Authentication Passphrase", initial="{$SNMPV3_AUTHPASS}", required=False)
    snmp_privprotocol = forms.ChoiceField(label="Privacy Protocol", choices=SNMP_PRIV_PROTOCOL_CHOICES, initial=1, required=False)
    snmp_privpassphrase = forms.CharField(label="Privacy Passphrase", initial="{$SNMPV3_PRIVPASS}", required=False)

    # SNMP Bulk            
    snmp_bulk = forms.ChoiceField(choices=SNMP_BULK_CHOICES, initial=1, required=False)
    
    
    fieldsets = (
        FieldSet(InlineFields('ip', 'dns')), 
        FieldSet(InlineFields('useip', 'main')),        
    )
    
    class Meta:
        model = ZBXInterface
        fields = [
            'host', 'ip', 'dns', 'useip', 'main',
            'port',
            'snmp_version',
            'snmp_community',
            'snmp_max_repetitions',
            'snmp_contextname',
            'snmp_securityname',
            'snmp_securitylevel',
            'snmp_authprotocol',
            'snmp_authpassphrase',
            'snmp_privprotocol',            
            'snmp_privpassphrase',
            'snmp_bulk',            
        ]
        exclude = [ 'available', 'custom_field_data', 'tags', 'interfaceid', 'type' ]



class ZBXHostFilterForm(NetBoxModelFilterSetForm):
    model = ZBXHost

    zbx_host_id = forms.CharField(label="Zabbix Host ID",
        required=False
    )

    templates = forms.ModelMultipleChoiceField(
        label="Templates XXX",
        queryset=ZBXTemplate.objects.all(),
        required=False
    )

    #templates = forms.Mul