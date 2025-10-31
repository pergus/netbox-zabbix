# forms.py
#
# Description:
#

import re

from django import forms
from django.core.exceptions import ValidationError
from django.utils.safestring import mark_safe
from django.utils.timezone import now
from django.conf import settings as plugin_settings
from django.utils.text import slugify
from django.forms import Select

from django.contrib.contenttypes.models import ContentType
from utilities.forms.fields import ContentTypeChoiceField

from netbox.forms import NetBoxModelFilterSetForm, NetBoxModelForm
from utilities.forms.fields import DynamicModelChoiceField
from utilities.forms.rendering import FieldSet

from netbox_zabbix.models import (
    Setting,
    Template,
    Proxy,
    ProxyGroup,
    HostGroup,
    TagMapping,
    InventoryMapping,
    DeviceMapping,
    VMMapping,
    HostConfig,
    AgentInterface,
    SNMPInterface,
    UnAssignedHosts,
    UnAssignedHostInterfaces,
    UnAssignedHostIPAddresses,

    MonitoredByChoices,
    InterfaceTypeChoices,
    TLSConnectChoices,
    DeleteSettingChoices,
    InterfaceTypeChoices,
)
from netbox_zabbix.utils import create_custom_field
from netbox_zabbix import zabbix as z
from netbox_zabbix.inventory_properties import inventory_properties


from netbox_zabbix.utils import (
    validate_templates,
    validate_templates_and_interface,
    is_valid_interface
)

from netbox_zabbix import settings
from netbox_zabbix.logger import logger


#
# Notes
#
# DynamicModelChoiceField expects a corresponding API endpoint to fetch and
# filter options dynamically as a single-select field. Since we need to support
# multiple selections without relying on a custom API endpoint, use
# ModelMultipleChoiceField instead.
#


PLUGIN_SETTINGS = plugin_settings.PLUGINS_CONFIG.get("netbox_zabbix", {})

# ------------------------------------------------------------------------------
# Setting
# ------------------------------------------------------------------------------

# Since only one instance of the setting is allowed there is no need for 
# a FilterForm.

class SettingForm(NetBoxModelForm):
    fieldsets = (
        FieldSet( 'name',
                  'ip_assignment_method',
                  'event_log_enabled',
                  'auto_validate_importables',
                  'auto_validate_quick_add',
                  name="General" ),
        FieldSet( 'max_deletions',
                  'max_success_notifications',
                  'zabbix_sync_interval',
                  name="Background Jobs" ),
        FieldSet( 'api_endpoint',
                  'web_address',
                  'token',
                  name="Zabbix Server" ),
        FieldSet( 'delete_setting',
                  'graveyard',
                  'graveyard_suffix',
                  name="Delete Setting" ),
        FieldSet( 'exclude_custom_field_name',
                  'exclude_custom_field_enabled',
                  name="Additional Settings" ),
        FieldSet( 'inventory_mode',
                  'monitored_by',
                  'tls_connect', 
                  'tls_accept', 
                  'tls_psk_identity', 
                  'tls_psk', 
                  'use_ip', 
                  name="Common Defaults" ),
        FieldSet( 'agent_port', 
                  name="Agent Specific Defaults"),
        FieldSet( 'snmp_port', 
                  'snmp_bulk',
                  'snmp_max_repetitions',
                  'snmp_contextname',
                  'snmp_securityname',
                  'snmp_securitylevel',
                  'snmp_authprotocol',
                  'snmp_authpassphrase',
                  'snmp_privprotocol',
                  'snmp_privpassphrase',
                  name="SNMP Specific Defaults"),
        FieldSet( 'default_tag', 
                  'tag_prefix', 
                  'tag_name_formatting',
                  name="Tags" ),
    )
    
    class Meta:
        model = Setting
        fields = '__all__'

    def __init__(self, *args, **kwargs):
            super().__init__( *args, **kwargs )
    
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
            # overwriting existing values when editing an existing instance.
            if not self.instance.pk:
                self.initial['name'] = "config"
                self.initial['api_endpoint'] = f"https://{zhost}/api_jsonrpc.php"
                self.initial['web_address'] = f"https://{zhost}"

            # Hide the 'tags' field on "add" and "edit" view
            self.fields.pop('tags', None)


    def clean(self):
        super().clean()

        if self.errors:
            logger.error( f"Edit setting form errors: {self.errors}" )
            raise ValidationError( f"{self.errors}" )
        
        if self.cleaned_data is None:
            logger.error( f"Edit setting form cleaned_data is None" )
            raise ValidationError( f"Edit setting form cleaned_data is None" )
        
        # Prevent second setting instance from being created
        if not self.instance.pk and Setting.objects.exists():
            raise ValidationError( "Only one Zabbix setting instance is allowed." )

        # Check max deletions
        max_deletions = self.cleaned_data.get( "max_deletions" )
        if max_deletions is not None and ( max_deletions <= 0 or max_deletions > 100 ):
            self.add_error( "max_deletions", "Max deletions must be in the range 1 - 100." )
    
        # Check max_success_notifications
        max_success_notifications = self.cleaned_data.get( "max_success_notifications" )
        if max_success_notifications is not None and ( max_success_notifications <= 0 or max_success_notifications > 5 ):
            self.add_error( "max_success_notifications", "Max deletions must be in the range 1 - 5." )
            
        # Check tls settings
        tls_connect = self.cleaned_data.get( 'tls_connect' )
        tls_psk = self.cleaned_data.get( 'tls_psk' )
        tls_psk_identity = self.cleaned_data.get( 'tls_psk_identity' )
    
        # Validate PSK requirements
        if tls_connect == TLSConnectChoices.PSK:
            if not tls_psk_identity:
                self.add_error( 'tls_psk_identity', "TLS PSK Identity is required when TLS Connect is set to PSK." )
            if not tls_psk or not re.fullmatch( r'[0-9a-fA-F]{32,}', tls_psk ):
                self.add_error( 'tls_psk', "TLS PSK must be at least 32 hexadecimal digits." )
    
        # Check connection/token
        try:
            z.validate_zabbix_credentials( self.cleaned_data['api_endpoint'], self.cleaned_data['token'] )
            self.instance.version = z.fetch_version_from_credentials( self.cleaned_data['api_endpoint'], self.cleaned_data['token'] )
            self.instance.connection = True
            self.instance.last_checked_at = now()
        except Exception:
            self.add_error( 'api_endpoint', mark_safe( "Failed to verify connection to Zabbix.<br>Please check the API address and token." ) )

        # If soft delete then gravyard has to have a value
        delete_setting = self.cleaned_data.get( "delete_setting" )
        if delete_setting == DeleteSettingChoices.SOFT:
            graveyard = self.cleaned_data.get( "graveyard" )
            if not graveyard:
                raise ValidationError( f"Soft delete require a host group" )
            graveyard_suffix = self.cleaned_data.get( "graveyard_suffix" )
            if not graveyard_suffix:
                raise ValidationError( f"Soft delete require a gravyard suffix" )
        
        # Custom field for excluding a device/vm from Zabbix
        exclude_custom_field_name = self.cleaned_data.get( "exclude_custom_field_name" )
        if exclude_custom_field_name:
            defaults = {
                "label": "Exclude from Zabbix",
                "type": "boolean",
                "default": False,
                "required": False,
                "description": "If set, this object will be ignored in Zabbix synchronization."
            }
            create_custom_field( exclude_custom_field_name, defaults )


# ------------------------------------------------------------------------------
# Templates
# ------------------------------------------------------------------------------


class TemplateForm(NetBoxModelForm):
    class Meta:
        model = Template
        fields = ( "name", "templateid", "tags" )


class TemplateFilterForm(NetBoxModelFilterSetForm):
    model = Template
    name  = forms.ModelMultipleChoiceField( queryset=Template.objects.all(), to_field_name='name', label="Name", required=False )
    templateid = forms.ChoiceField( label = "Template ID", required = False )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
         # Set templateid choices dynamically on instantiation
        templateids = Template.objects.order_by('templateid').distinct('templateid').values_list('templateid', flat=True)
        choices = [("", "---------")] + [(zid, zid) for zid in templateids if zid is not None]
        self.fields["templateid"].choices = choices


# ------------------------------------------------------------------------------
# Proxy
# ------------------------------------------------------------------------------


class ProxyForm(NetBoxModelForm):
    class Meta:
        model = Proxy
        fields = ( "name", "proxyid", "proxy_groupid" )


class ProxyFilterForm(NetBoxModelFilterSetForm):
    model = Proxy

    name = forms.ModelMultipleChoiceField( queryset=Proxy.objects.all(), to_field_name='name', label="Name", required=False )
    proxyid = forms.ChoiceField( label = "Proxy ID", required = False )
    proxy_groupid = forms.ChoiceField( label = "Proxy Group ID", required = False )


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
         # Set proxyid choices dynamically on instantiation
        proxyids = Proxy.objects.order_by('proxyid').distinct('proxyid').values_list('proxyid', flat=True)
        choices = [("", "---------")] + [(zid, zid) for zid in proxyids if zid is not None]
        self.fields["proxyid"].choices = choices


# ------------------------------------------------------------------------------
# Proxy Groups
# ------------------------------------------------------------------------------


class ProxyGroupForm(NetBoxModelForm):
    class Meta:
        model = ProxyGroup
        fields = ( "name", "proxy_groupid" )


class ProxyGroupFilterForm(NetBoxModelFilterSetForm):
    model = ProxyGroup

    name = forms.ModelMultipleChoiceField( queryset=ProxyGroup.objects.all(), to_field_name='name', label="Name", required=False )
    proxy_groupid = forms.ChoiceField( label = "Proxy Group ID", required = False )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

         # Set proxyid choices dynamically on instantiation
        proxy_groupids = ProxyGroup.objects.order_by('proxy_groupid').distinct('proxy_groupid').values_list('proxy_groupid', flat=True)
        choices = [("", "---------")] + [(zid, zid) for zid in proxy_groupids if zid is not None]
        self.fields["proxy_groupid"].choices = choices


# ------------------------------------------------------------------------------
# Host Groups
# ------------------------------------------------------------------------------


class HostGroupForm(NetBoxModelForm):
    class Meta:
        model = HostGroup
        fields = [ 'name', 'groupid' ]


# ------------------------------------------------------------------------------
# Tag Mapping
# ------------------------------------------------------------------------------


class TagMappingForm(NetBoxModelForm):
    object_type = forms.ChoiceField( choices=TagMapping.OBJECT_TYPE_CHOICES, initial='device' )
    prefix = "gurka"

    class Meta:
        model = TagMapping
        fields = [ "object_type", "tags" ]

    def __init__(self, *args, **kwargs):
        super().__init__( *args, prefix=self.prefix, **kwargs )

        object_type = (
            self.initial.get( 'object_type' )
            or self.data.get( 'object_type' )
            or getattr( self.instance, 'object_type', None )
            or 'device'
        )
        
        tag_mappings = PLUGIN_SETTINGS.get( 'tag_mappings', {} ).get( object_type, [] )

        # Prepare a lookup for existing enabled states from instance.selection
        existing_selection = {}
        if self.instance.pk and self.instance.selection:
            for entry in self.instance.selection:
                existing_selection[entry['value']] = entry.get( 'enabled', False )

        if self.instance.object_type:
            self.fields['object_type'].disabled = True

        # Dynamically add BooleanFields for each field with initial enabled value
        for tag_name, tag_value in tag_mappings:
            # Use a unique prefix for the form field key to avoid name
            # collisions with existing NetBox fields. 
            # This allows us to safely use common or duplicate display names in
            # 'tag_mappings', such as "Tags".
            field_key = slugify( f"{self.prefix}_{tag_name}" )
            self.fields[field_key] = forms.BooleanField(
                label=tag_name,
                required=False,
                initial=existing_selection.get( tag_value, False ),
            )


    def clean_object_type(self):
        object_type = self.cleaned_data['object_type']
        qs = TagMapping.objects.filter( object_type=object_type )
        if self.instance.pk:
            qs = qs.exclude( pk=self.instance.pk )
        if qs.exists():
            raise forms.ValidationError( f"A mapping for object type '{object_type}' already exists." )
        return object_type


    def save(self, commit=True):
        # Build list of dicts with name, value, and enabled
        object_type = self.cleaned_data['object_type']
        tag_mappings = PLUGIN_SETTINGS.get( 'tag_mappings', {} ).get( object_type, [] )
        
        selection = []
        for tag_name, tag_value in tag_mappings:
            field_key = slugify( f"{self.prefix}_{tag_name}"  )

            enabled = self.cleaned_data.get( field_key, False )
            selection.append({
                "name": tag_name,
                "value": tag_value,
                "enabled": enabled,
            })

        self.instance.selection = selection
        return super().save( commit=commit )


# ------------------------------------------------------------------------------
# Inventory Mapping
# ------------------------------------------------------------------------------


class InventoryMappingForm(NetBoxModelForm):
    object_type = forms.ChoiceField( choices=InventoryMapping.OBJECT_TYPE_CHOICES, initial='device' )
    prefix = "kullager"

    class Meta:
        model = InventoryMapping
        fields = ["object_type", "tags" ]  # exclude 'selection' from raw rendering

    def __init__(self, *args, **kwargs):
        super().__init__( *args, prefix=self.prefix, **kwargs )

        object_type = (
            self.initial.get( 'object_type' )
            or self.data.get( 'object_type' )
            or getattr( self.instance, 'object_type', None )
            or 'device'
        )
        
        inventory_mapping = PLUGIN_SETTINGS.get( 'inventory_mapping', {} ).get( object_type, [] )

        # Prepare a lookup for existing enabled states from instance.selection
        existing_selection = {}
        if self.instance.pk and self.instance.selection:
            for entry in self.instance.selection:
                existing_selection[entry['name']] = entry.get( 'enabled', False )

        if self.instance.object_type:
            self.fields['object_type'].disabled = True

        # Dynamically add BooleanFields for each field with initial enabled value
        for name, invkey, _ in inventory_mapping:
            if invkey in inventory_properties:
                # Use a unique prefix for the form field key to avoid name
                # collisions with existing NetBox fields. 
                # This allows us to safely use common or duplicate display names in
                # 'inventory_mapping', such as "Tags".
                field_key = slugify( f"{self.prefix}_{name}" )
                self.fields[field_key] = forms.BooleanField(
                    label=name,
                    required=False,
                    initial=existing_selection.get( name, False ),
                )
            else:
                logger.info( f"{invkey} is not a legal inventory property" )


    def clean_object_type(self):
        object_type = self.cleaned_data['object_type']
        qs = InventoryMapping.objects.filter( object_type=object_type )
        if self.instance.pk:
            qs = qs.exclude( pk=self.instance.pk )
        if qs.exists():
            raise forms.ValidationError( f"A mapping for object type '{object_type}' already exists." )
        return object_type


    def save(self, commit=True):
        # Build list of dicts with name, inkey, paths, and enabled
        object_type = self.cleaned_data['object_type']
        inventory_mapping = PLUGIN_SETTINGS.get( 'inventory_mapping', {} ).get( object_type, [] )
        
        selection = []
        for name, invkey, paths in inventory_mapping:
            field_key = slugify( f"{self.prefix}_{name}"  )

            enabled = self.cleaned_data.get( field_key, False )
            selection.append({
                "name":    name,
                "invkey":  invkey,
                "paths":   paths,
                "enabled": enabled,
            })

        self.instance.selection = selection
        return super().save( commit=commit )


# ------------------------------------------------------------------------------
# Device Mapping
# ------------------------------------------------------------------------------


class DeviceMappingForm(NetBoxModelForm):
    fieldsets = (
        FieldSet( 'name', 'description', 'default', name="General" ),
        FieldSet( 'host_groups', 'templates', 'proxy', 'proxy_group', 'interface_type', name="Settings" ),
        FieldSet( 'sites', 'roles', 'platforms', name="Filters")
    )
    
    class Meta:
        model = DeviceMapping
        fields = '__all__' 

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
       
        # Are we creating the very first/default mapping?
        fist_mapping = DeviceMapping.objects.filter( default=True ).exists()
        
        if not fist_mapping or self.instance.default:
            # First mapping ever: it must be default
            self.initial['default'] = True
            self.fields['default'].disabled = True 
    
            # force interface_type to Any
            self.initial['interface_type'] = InterfaceTypeChoices.Any
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
            if interface_type != InterfaceTypeChoices.Any:
                raise forms.ValidationError( "Default mapping must use interface_type = 'any'." )
        else:
            # Non-default mappings must restrict on at least one of sites/roles/platforms
            if not (sites.exists() or roles.exists() or platforms.exists()):
                raise forms.ValidationError( "At least one of sites, roles, or platforms must be set for non-default mappings." )

        # Validate templates
        templates = self.cleaned_data.get( "templates", [] )
        if not templates:
            raise ValidationError( "At least one template must be selected." )
        
        template_ids = [ t.templateid for t in templates ]
        
        try:
            validate_templates_and_interface( template_ids, interface_type )
        except Exception as e:
            raise ValidationError( str( e ) )
        
        # Ensure there is exactly one default in the database (excluding current instance if updating)
        if default:
            qs = DeviceMapping.objects.filter( default=True )
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
            others = DeviceMapping.objects.exclude( pk=self.instance.pk ).filter( default=False )
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

        # If the interface type differ, then there can not be any filter overlap
        self_interface_type = self.cleaned_data.get( 'interface_type' )
        other_interface_type = other.interface_type
        
        if self_interface_type != other_interface_type:
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
    fieldsets = (
        FieldSet( 'name', 'description', 'default', name="General" ),
        FieldSet( 'host_groups', 'templates', 'proxy', 'proxy_group', 'interface_type', name="Settings" ),
        FieldSet( 'sites', 'roles', 'platforms', name="Filters")
    )
    
    class Meta:
        model = VMMapping
        fields = '__all__' 

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
       
        # Are we creating the very first/default mapping?
        fist_mapping = VMMapping.objects.filter( default=True ).exists()
        
        if not fist_mapping or self.instance.default:
            # First mapping ever: it must be default
            self.initial['default'] = True
            self.fields['default'].disabled = True 
    
            # force interface_type to Any
            self.initial['interface_type'] = InterfaceTypeChoices.Any
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
            if interface_type != InterfaceTypeChoices.Any:
                raise forms.ValidationError( "Default mapping must use interface_type = 'any'." )
        else:
            # Non-default mappings must restrict on at least one of sites/roles/platforms
            if not (sites.exists() or roles.exists() or platforms.exists()):
                raise forms.ValidationError( "At least one of sites, roles, or platforms must be set for non-default mappings." )

        # Validate templates
        templates = self.cleaned_data.get( "templates", [] )
        if not templates:
            raise ValidationError( "At least one template must be selected." )
        
        template_ids = [ t.templateid for t in templates ]
        
        try:
            validate_templates_and_interface( template_ids, interface_type )
        except Exception as e:
            raise ValidationError( str( e ) )
        
        # Ensure there is exactly one default in the database (excluding current instance if updating)
        if default:
            qs = VMMapping.objects.filter( default=True )
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
            others = VMMapping.objects.exclude( pk=self.instance.pk ).filter( default=False )
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

        # If the interface type differ, then there can not be any filter overlap
        self_interface_type = self.cleaned_data.get( 'interface_type' )
        other_interface_type = other.interface_type
        
        if self_interface_type != other_interface_type:
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
# Host Config
# ------------------------------------------------------------------------------


class HostConfigForm(NetBoxModelForm):
    object_id = forms.IntegerField(widget=forms.HiddenInput(), required=False)

    class Meta:
        model  = HostConfig
        fields = (
            'name',
            'content_type',
            'object_id',
            'host',
            'status',
            'monitored_by',
            'templates',
            'proxy',
            'proxy_group',
            'host_groups',
            'description'
        )

    content_type = ContentTypeChoiceField(
        label="Host Type",
        queryset=ContentType.objects.filter( model__in=["device", "virtualmachine"] ),
        required=True,
    )

    host = DynamicModelChoiceField(
        label="Host",
        queryset=UnAssignedHosts.objects.all(),
        required=True,
        selector=False,
        query_params={"content_type": "$content_type"},
    )


    def __init__(self, *args, **kwargs):
        instance = kwargs.get( 'instance', None )
        super().__init__( *args, **kwargs )

        if instance and instance.pk and instance.content_type:
            assigned = instance.assigned_object
            if assigned:
                # When editing an existing HostConfig that already has an assigned object,
                # lock the "host" and "content_type" fields so the user cannot change them.
                # These fields are replaced with HiddenInputs to preserve their values in POST data
                # while keeping them invisible in the form. This ensures data integrity and prevents
                # accidental reassignment of hosts that are already linked to a HostConfig.
                self.fields['host'].queryset = assigned.__class__.objects.filter( pk=assigned.pk )
                self.fields['host'].initial  = assigned
                self.fields['host'].disabled = True
                self.fields['host'].widget   = forms.HiddenInput()

                self.fields['content_type'].disabled = True
                self.fields['content_type'].widget   = forms.HiddenInput()


    def clean(self):
        super().clean()

        host         = self.cleaned_data.get( "host" )
        templates    = self.cleaned_data.get( "templates", [] )
        monitored_by = self.cleaned_data.get( "monitored_by" )

        if host:
            self.cleaned_data["object_id"] = host.id

        config = self.instance
        template_ids = [t.templateid for t in templates]

        # Determine interface availability
        has_agent = has_snmp = False
        if config and config.pk:
            has_agent = config.has_agent_interface
            has_snmp  = config.has_snmp_interface

        #  Monitored-by validation
        if monitored_by == MonitoredByChoices.Proxy and not self.cleaned_data.get( "proxy" ):
            raise ValidationError( "A proxy name is required." )

        if monitored_by == MonitoredByChoices.ProxyGroup and not self.cleaned_data.get( "proxy_group" ):
            raise ValidationError( "A proxy group name is required." )

        # Interface and template validation
        if not (has_agent or has_snmp):
            # Case 1: No interfaces — validate templates only
            try:
                validate_templates( template_ids )
            except Exception as e:
                raise ValidationError( str( e) )
            return self.cleaned_data

        # Case 2: Determine interface type
        interface_type = (
            InterfaceTypeChoices.Any   if has_agent and has_snmp else
            InterfaceTypeChoices.Agent if has_agent else
            InterfaceTypeChoices.SNMP
        )

        # Validate templates for the detected interface type
        try:
            validate_templates_and_interface(template_ids, interface_type)
        except Exception as e:
            raise ValidationError( str( e ) )

        return self.cleaned_data



# ------------------------------------------------------------------------------
# Base Host Interface Form
# ------------------------------------------------------------------------------


class BaseHostInterfaceForm(NetBoxModelForm):
    interface_name = DynamicModelChoiceField(
        label="Interface Name",
        queryset=UnAssignedHostInterfaces.objects.all(),
        query_params={"config_pk": "$host_config"},
        required=True,
    )

    ip_address = DynamicModelChoiceField(
        label="IP Address",
        queryset=UnAssignedHostIPAddresses.objects.all(),
        query_params={"config_pk": "$host_config", "interface_pk": "$interface_name"},
        required=True,
    )

    dns_name = forms.CharField(
        label="DNS Name",
        max_length=255,
        required=False,
        disabled=True,
        widget=forms.TextInput(attrs={"data-field": "dns_name"}),
    )

    is_edit_field = forms.BooleanField( widget=forms.HiddenInput(), required=False )
    
    interface_type_choice = InterfaceTypeChoices.Any  # override in subclasses
    default_name_suffix = ""                          # override in subclasses
    snmp_defaults = {}                                # override in SNMP form if needed

    class Meta:
        fields = (
            "name",
            "host_config",
            "interface_name",
            "ip_address",
            "dns_name",
            "useip",
            "main",
            "port",
        )

    def __init__(self, *args, **kwargs):
        super().__init__( *args, **kwargs )

        # Hide host_config but still submit it so it can be saved to the DB.
        self.fields["host_config"].widget = forms.HiddenInput()
        
        # Set the is_edit_field, which is used in the template to prevent fetching primary ip when editing an interface.
        self.fields["is_edit_field"].initial = bool( self.instance and self.instance.pk )

        # Editing an existing interface
        if self.instance.pk:
            current_interface = self.instance.interface
            current_ip        = self.instance.ip_address

            if current_interface:
                # When editing an existing Agent or SNMP interface, this section ensures that the
                # currently selected interface is displayed in the form — even if it would
                # normally be excluded from the queryset of unassigned interfaces. It replaces the
                # field’s queryset and widget so that the selected interface appears as a single,
                # prepopulated, non-editable option instead of an empty dropdown.
                field = self.fields["interface_name"]
                field.queryset = current_interface.__class__.objects.filter( pk=current_interface.pk )
                field.label_from_instance = lambda obj: obj.name
                field.initial = current_interface
                field.empty_label = None
                field.disabled = True
                field.widget = Select( choices=[(current_interface.pk, current_interface.name)] )
    
            if current_ip:
                self.fields["ip_address"].initial = current_ip.address
                self.fields["ip_address"].disabled = True
                self.fields["dns_name"].initial = current_ip.dns_name or ""
                self.fields["dns_name"].disabled = True


        # Creating a new interface
        if not self.instance.pk:
            try:
                host_config = HostConfig.objects.get( id=self.initial["host_config"] )
                self.initial["name"] = f"{host_config.assigned_object.name}-{self.default_name_suffix}"
                # Apply SNMP defaults if any
                for field, value in self.snmp_defaults.items():
                    self.initial[field] = value
            except Exception:
                pass


    def clean(self):
        super().clean()

        # Validate DNS Name
        ip_address = self.cleaned_data.get( "ip_address" )
        if ip_address and not ip_address.dns_name:
            raise ValidationError( "Missing DNS name" )

        # Validate interface
        host_config = self.cleaned_data.get( "host_config" )
        try:
            is_valid_interface( host_config, self.interface_type_choice )
        except Exception as e:
            raise ValidationError( f"{str( e )}" )

    def save(self, commit=True):
        instance = super().save( commit=False )

        # Populate interface_type and interface_id from the form field
        selected_interface = self.cleaned_data.get( "interface_name" )
        if selected_interface:
            instance.interface_type = ContentType.objects.get_for_model( selected_interface )
            instance.interface_id = selected_interface.pk

        if commit:
            instance.save()
        return instance


# ------------------------------------------------------------------------------
# Agent Interface
# ------------------------------------------------------------------------------


class AgentInterfaceForm(BaseHostInterfaceForm):
    interface_type_choice = InterfaceTypeChoices.Agent
    default_name_suffix = "agent"

    class Meta(BaseHostInterfaceForm.Meta):
        model = AgentInterface


# ------------------------------------------------------------------------------
# SNMP Interface
# ------------------------------------------------------------------------------


class SNMPInterfaceForm(BaseHostInterfaceForm):
    interface_type_choice = InterfaceTypeChoices.SNMP
    default_name_suffix = "snmp"
    snmp_defaults = {
        "port": settings.get_snmp_port(),
        "bulk": settings.get_snmp_bulk(),
        "max_repetitions": settings.get_snmp_max_repetitions(),
        "contextname": settings.get_snmp_contextname(),
        "securityname": settings.get_snmp_securityname(),
        "securitylevel": settings.get_snmp_securitylevel(),
        "authprotocol": settings.get_snmp_authprotocol(),
        "authpassphrase": settings.get_snmp_authpassphrase(),
        "privprotocol": settings.get_snmp_privprotocol(),
        "privpassphrase": settings.get_snmp_privpassphrase(),
    }

    class Meta(BaseHostInterfaceForm.Meta):
        model = SNMPInterface
        fields = BaseHostInterfaceForm.Meta.fields + (
            "max_repetitions",
            "contextname",
            "securityname",
            "securitylevel",
            "authprotocol",
            "authpassphrase",
            "privprotocol",
            "privpassphrase",
            "bulk",
        )


# end