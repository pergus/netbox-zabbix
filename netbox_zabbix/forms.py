from netbox.forms import NetBoxModelForm, NetBoxModelFilterSetForm

from utilities.forms.fields import ContentTypeChoiceField
from utilities.forms.fields import DynamicModelChoiceField
from utilities.forms.widgets import HTMXSelect
#from utilities.forms import BOOLEAN_WITH_BLANK_CHOICES

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.utils.timezone import now
from django.conf import settings
from django import forms
import django_filters

from dcim.models import Device

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

    name = forms.ModelMultipleChoiceField(
            queryset=models.Template.objects.all(),
            to_field_name='name',  # match against `name`, not PK
            label="Name",
            required=False
        )
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

class HostForm(NetBoxModelForm):
    class Meta: 
         model = models.Host
         fields = [ 'content_type', 'status', 'templates' ]
    
    content_type = ContentTypeChoiceField(
           queryset=ContentType.objects.filter( model__in=["device", "virtualmachine"] ),
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
    

    def __init__(self, *args, **kwargs):
        # Ensure initial dictionary exists and set default content_type to Device if not bound
        kwargs.setdefault( 'initial', {} )
        if 'content_type' not in kwargs['initial']:
            try:
                kwargs['initial']['content_type'] = ContentType.objects.get( app_label='dcim', model='device' ).pk
            except ContentType.DoesNotExist:
                pass
    
        super().__init__(*args, **kwargs)
    
        # Reorder fields to ensure correct order
        self.order_fields( [
            'content_type',
            'content_object',
            'status',
            'templates' ])
    
        # Handle editing an existing Host or adding a new one
        instance = kwargs.get( "instance" )
    
        if instance and instance.pk and instance.content_type:
            self._initialize_for_edit( instance )
        elif self.initial.get( 'host_id' ):
            self._initialize_for_add_specific_host()
        else:
            self._initialize_for_add()
    
    def _initialize_for_edit(self, instance):
        # Initialize the form for editing an existing Host
        model_class = instance.content_type.model_class()
        queryset = model_class.objects.filter( pk=instance.content_object.pk )
    
        self.fields["content_type"].initial = instance.content_type.pk
        self.fields["content_object"].initial = instance.content_object
        self.fields["content_object"].queryset = queryset
    
        # Hide content_type and make content_object read-only
        self.fields.pop("content_type", None)
        self.fields["content_object"].disabled = True
    
    
    def _initialize_for_add_specific_host(self):
        # Add specific host
        if self.is_bound:
            content_type_id = self.data.get( "content_type" )  # from submitted form
        else:
            content_type_id = self.initial.get( "content_type" )
        
        selected_host_id = self.initial.get( "host_id" )
        
        if selected_host_id:
            print(f"{content_type_id=}")
                        
            content_type = ContentType.objects.get( pk=content_type_id )            
            model_class = content_type.model_class()
            
            queryset = model_class.objects.filter( pk=selected_host_id )
        
            self.fields['content_object'] = DynamicModelChoiceField(
                label='Host',
                initial=queryset[0],
                queryset=queryset,
                query_params={"id": selected_host_id},
                required=True,
                selector=False,
           )


    def _initialize_for_add(self):
        # Add a new Host
        if self.is_bound:
            content_type_id = self.data.get( "content_type" )  # from submitted form
        else:
            content_type_id = self.initial.get( "content_type" )
        
        content_type = ContentType.objects.get( pk=content_type_id )
        model_class = content_type.model_class()
                
        # Get the ids of all devices or vms that has an object_id, i.e. a zabbix configuration        
        linked_object_ids = list(models.Host.objects.filter( content_type=content_type).values_list( 'object_id', flat=True ) )
    
         # Get all devices or vms that doesn't have an object_id, i.e. no zabbix configuration
        queryset = model_class.objects.exclude( id__in=linked_object_ids )
    
         # Get the ids of all devices or vms that doesn't have an object_id, i.e. no zabbix configuration
        available_object_ids = list(model_class.objects.exclude( id__in=linked_object_ids).values_list( 'id', flat=True ) )
    
        # For some reson the follwing doesn't work, instead we have to create
        # a new DynamicModelChoiceField instance and assign that to the content_object.
        # self.fields['content_object']._queryset = queryset
        # self.fields['content_object'].query_params = {"id": available_object_ids}
        self.fields['content_object'] = DynamicModelChoiceField(
             label='Host',
             queryset=queryset,
             query_params={ "id": available_object_ids },
             required=True,
             selector=False
        )
        
    
    def save(self, commit=True):
        instance = super().save( commit=False )
    
        # content_object is selected by the user
        obj = self.cleaned_data['content_object']
    
        # store the pk of the content_object in object_id
        instance.object_id = obj.pk
        instance.content_type = ContentType.objects.get_for_model( obj )
    
        if commit:
            instance.save()
            self.save_m2m()
            
        return instance
    

class HostFilterForm(NetBoxModelFilterSetForm):
    model = models.Host

    status = forms.ChoiceField( label = "Status", choices = [ ("", "---------")] + models.StatusChoices.choices, required = False )
    templates = forms.ModelMultipleChoiceField( label = "Templates", queryset = models.Template.objects.all(), required = False )
    zabbix_host_id = forms.ChoiceField( label = "Zabbix Host ID", required = False )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

         # Set zabbix_host_id choices dynamically on instantiation
        zabbix_host_ids = models.Host.objects.order_by('zabbix_host_id').distinct('zabbix_host_id').values_list('zabbix_host_id', flat=True)
        choices = [("", "---------")] + [(zid, zid) for zid in zabbix_host_ids if zid is not None]
        self.fields["zabbix_host_id"].choices = choices
        