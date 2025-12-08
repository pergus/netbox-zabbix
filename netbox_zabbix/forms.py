"""
NetBox Zabbix Plugin — Forms

This module defines the Django forms used by the NetBox Zabbix plugin. These
forms handle validation, rendering, and data processing for Zabbix settings,
templates, proxies, host groups, and other related models.

Custom validation and helper functions are provided to ensure that Zabbix
configuration and mappings are consistent and correctly formatted.
"""


# Standard library imports
import re

# Django imports
from django import forms
from django.contrib import messages
from django.conf import settings as plugin_settings
from django.core.exceptions import ValidationError
from django.forms import Select
from django.utils.safestring import mark_safe
from django.utils.text import slugify
from django.utils.timezone import now
from django.contrib.contenttypes.models import ContentType

# NetBox imports
from utilities.forms.fields import (
    ContentTypeChoiceField, 
    DynamicModelChoiceField,
)
from utilities.forms.widgets import DateTimePicker
from utilities.forms.rendering import FieldSet
from netbox.forms import NetBoxModelFilterSetForm, NetBoxModelForm
from virtualization.models import VirtualMachine

# NetBox Zabbix plugin imports
from netbox_zabbix.models import (
    # Choices
    ProxyModeChoices,
    MonitoredByChoices,
    InterfaceTypeChoices,
    TLSAcceptChoices,
    TLSConnectChoices,
    DeleteSettingChoices,
    InterfaceTypeChoices,
    # Models
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
    Maintenance,
    UnAssignedHosts,
    UnAssignedHostInterfaces,
    UnAssignedHostIPAddresses,
)
from netbox_zabbix.netbox.custom_fields import create_netbox_custom_field
from netbox_zabbix.zabbix.templates import (
    validate_templates, 
    validate_templates_and_interface, 
    is_valid_interface 
)
from netbox_zabbix.zabbix.inventory_properties import inventory_properties
from netbox_zabbix.zabbix import api as zapi
from netbox_zabbix import settings
from netbox_zabbix.netbox.permissions import has_any_model_permission
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


class SettingForm(NetBoxModelForm):
    """
    Form for editing Zabbix plugin settings.
    
    Ensures only one instance exists, validates TLS/PSK, API connection, deletion settings,
    and handles creation of a custom exclusion field.
    """
    fieldsets = (
        FieldSet( 'name',
                  'ip_assignment_method',
                  'event_log_enabled',
                  'auto_validate_importables',
                  'auto_validate_quick_add',
                  name="General" ),
        FieldSet( 'max_deletions',
                  'max_success_notifications',
                  name="Background Jobs" ),
        FieldSet( 'zabbix_import_interval',
                  'host_config_sync_interval',
                  'cutoff_host_config_sync',
                  'maintenance_cleanup_interval',
                  name="System Jobs" ),
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
                  'useip',
                  'tls_connect', 
                  'tls_accept', 
                  'tls_psk_identity', 
                  'tls_psk', 
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
    
    # Hide the token
    token = forms.CharField( widget=forms.PasswordInput( render_value=True ), help_text="Zabbix API token (hidden input)" )

    class Meta:
        model = Setting
        fields = '__all__'

    def __init__(self, *args, **kwargs):
            """
            Initialize form with default initial values for new instance.
            
            Hides 'tags' field and sets default API/web endpoints if creating a new setting.
            """
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
        """
        Validate form fields and enforce plugin constraints.
        
        Checks max deletions, TLS PSK requirements, API connection,
        soft delete settings, and uniqueness of the setting instance.
        
        Raises:
            ValidationError: If any validation fails.
        """
        super().clean()

        if self.errors:
            raise ValidationError( f"{self.errors}" )
        
        if self.cleaned_data is None:
            raise ValidationError( f"Internal Error: Edit setting form cleaned_data is None" )
        
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
        tls_accept = self.cleaned_data.get( 'tls_accept' )
        tls_psk = self.cleaned_data.get( 'tls_psk' )
        tls_psk_identity = self.cleaned_data.get( 'tls_psk_identity' )
    
        # Validate PSK requirements
        if tls_connect == TLSConnectChoices.PSK or tls_accept == TLSAcceptChoices.PSK:
            if not tls_psk_identity:
                self.add_error( 'tls_psk_identity', "TLS PSK Identity is required when TLS Connect/Accept is set to PSK." )
            if not tls_psk or not re.fullmatch( r'[0-9a-fA-F]{32,}', tls_psk ):
                self.add_error( 'tls_psk', "TLS PSK must be at least 32 hexadecimal digits." )
    
        # Check connection/token
        try:
            zapi.validate_zabbix_credentials( self.cleaned_data['api_endpoint'], self.cleaned_data['token'] )
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
            create_netbox_custom_field( exclude_custom_field_name, defaults )


    def save(self, commit=True):
        instance = super().save(commit=False)
    
        # Update connection fields after validation
        try:
            zapi.validate_zabbix_credentials(instance.api_endpoint, instance.token)
            instance.version = zapi.fetch_version_from_credentials(instance.api_endpoint, instance.token)
            instance.connection = True
            instance.last_checked_at = now()
        except Exception:
            instance.connection = False
            instance.last_checked_at = None
    
        if commit:
            instance.save()
        return instance


# ------------------------------------------------------------------------------
# Templates
# ------------------------------------------------------------------------------


class TemplateForm(NetBoxModelForm):
    """
    Form for creating or editing Zabbix Templates.
    """
    class Meta:
        model = Template
        fields = ( "name", "templateid", "tags" )

    def __init__(self, *args, **kwargs):
        """
        Initialize form with default initial values for new instance.
        
        Hides 'tags' field.
        """
        super().__init__( *args, **kwargs )
    
        # Hide the 'tags' field on "add" and "edit" view
        self.fields.pop('tags', None)


class TemplateFilterForm(NetBoxModelFilterSetForm):
    """
    Filter form for Templates by name or template ID.
    Dynamically populates templateid choices on initialization.
    """
    model      = Template
    name       = forms.ModelMultipleChoiceField( queryset=Template.objects.all(), to_field_name='name', label="Name", required=False )
    templateid = forms.ChoiceField( label = "Template ID", required = False )

    def __init__(self, *args, **kwargs):
        """
        Initialize filter choices for template IDs dynamically.
        """
        super().__init__(*args, **kwargs)
    
         # Set templateid choices dynamically on instantiation
        templateids = Template.objects.order_by('templateid').distinct('templateid').values_list('templateid', flat=True)
        choices = [("", "---------")] + [(zid, zid) for zid in templateids if zid is not None]
        self.fields["templateid"].choices = choices


# ------------------------------------------------------------------------------
# Proxy
# ------------------------------------------------------------------------------


class ProxyForm(NetBoxModelForm):
    """
    Form for creating or editing Zabbix Proxies.
    """
    fieldsets = ( 
        FieldSet(
            "name",
            "proxyid", 
            "proxy_groupid",
            "proxy_group",
            "operating_mode",
            "local_address",
            "local_port",
            "address",
            "port",
            "allowed_addresses",
            "description",
            name="Main"),
        FieldSet( 
            "tls_connect",
            "tls_accept",
            "tls_issuer",
            "tls_subject",
            "tls_psk_identity",
            "tls_psk",
            name="Encryption"
        ),
        FieldSet( 
            "custom_timeouts", 
            "timeout_zabbix_agent", 
            "timeout_simple_check", 
            "timeout_snmp_agent", 
            "timeout_external_check", 
            "timeout_db_monitor", 
            "timeout_http_agent", 
            "timeout_ssh_agent", 
            "timeout_telnet_agent", 
            "timeout_script", 
            "timeout_browser", 
            name="Timeouts"
        )
    )

    class Meta:
        model = Proxy
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        """
        Initialize form with default initial values for new instance.
        
        Hides 'tags' field.
        """

        instance = kwargs.get( 'instance', None )
        
        super().__init__( *args, **kwargs )
    
        # Hide the 'tags' field on "add" and "edit" view
        self.fields.pop('tags', None)


        if instance and instance.pk:
            # Edit existing proxy
            self.fields.pop('proxyid', None)
            self.fields.pop('proxy_groupid', None)
        else:
            # New proxy
            self.fields.pop('proxyid', None)
            self.fields.pop('proxy_groupid', None)

        # Main
        self.fields['local_address'].widget.attrs['class'] = 'conditional-field local-field'
        self.fields['local_port'].widget.attrs['class'] = 'conditional-field local-field'
        self.fields['address'].widget.attrs['class'] = 'conditional-field remote-field'
        self.fields['port'].widget.attrs['class'] = 'conditional-field remote-field'
        self.fields['allowed_addresses'].widget.attrs['class'] = 'conditional-field active-field'

        # Encryption
        self.fields['tls_psk'].widget.attrs['class'] = 'conditional-field psk-field'
        self.fields['tls_psk_identity'].widget.attrs['class'] = 'conditional-field psk-field'
        self.fields['tls_issuer'].widget.attrs['class'] = 'conditional-field cert-field'
        self.fields['tls_subject'].widget.attrs['class'] = 'conditional-field cert-field'



class ProxyFilterForm(NetBoxModelFilterSetForm):
    """
    Filter form for Proxies by name, proxy ID, or proxy group ID.
    
    Dynamically populates proxyid choices on initialization.
    """
    model         = Proxy
    name          = forms.ModelMultipleChoiceField( queryset=Proxy.objects.all(), to_field_name='name', label="Name", required=False )
    proxyid       = forms.ChoiceField( label = "Proxy ID", required = False )
    proxy_groupid = forms.ChoiceField( label = "Proxy Group ID", required = False )


    def __init__(self, *args, **kwargs):
        """
        Initialize filter choices for proxy IDs dynamically.
        """
        super().__init__(*args, **kwargs)
    
         # Set proxyid choices dynamically on instantiation
        proxyids = Proxy.objects.order_by( 'proxyid' ).distinct( 'proxyid' ).values_list( 'proxyid', flat=True )
        choices = [("", "---------")] + [(zid, zid) for zid in proxyids if zid is not None]
        self.fields["proxyid"].choices = choices


# ------------------------------------------------------------------------------
# Proxy Groups
# ------------------------------------------------------------------------------


class ProxyGroupForm(NetBoxModelForm):
    """
    Form for creating or editing Proxy Groups.
    """
    class Meta:
        model = ProxyGroup
        fields = ( "name", "proxy_groupid", "failover_delay", "min_online", "description" )


    def __init__(self, *args, **kwargs):
        """
        Initialize form with default initial values for new instance.
        
        Hides 'tags' field.
        """
        super().__init__( *args, **kwargs )
    
        # Hide the 'tags' field on "add" and "edit" view
        self.fields.pop( 'tags', None )


class ProxyGroupFilterForm(NetBoxModelFilterSetForm):
    """
    Filter form for Proxy Groups by name or group ID.
    Dynamically populates proxy_groupid choices on initialization.
    """
    model         = ProxyGroup
    name          = forms.ModelMultipleChoiceField( queryset=ProxyGroup.objects.all(), to_field_name='name', label="Name", required=False )
    proxy_groupid = forms.ChoiceField( label = "Proxy Group ID", required = False )

    def __init__(self, *args, **kwargs):
        """
        Initialize filter choices for proxy group IDs dynamically.
        """
        super().__init__(*args, **kwargs)

         # Set proxyid choices dynamically on instantiation
        proxy_groupids = ProxyGroup.objects.order_by( 'proxy_groupid' ).distinct( 'proxy_groupid' ).values_list( 'proxy_groupid', flat=True )
        choices = [("", "---------")] + [(zid, zid) for zid in proxy_groupids if zid is not None]
        self.fields["proxy_groupid"].choices = choices


# ------------------------------------------------------------------------------
# Host Groups
# ------------------------------------------------------------------------------


class HostGroupForm(NetBoxModelForm):
    """
    Form for creating or editing Host Groups.
    """
    class Meta:
        model = HostGroup
        fields = [ 'name' ]


    def __init__(self, *args, **kwargs):
        """
        Initialize form with default initial values for new instance.
        
        Hides 'tags' field.
        """
        super().__init__( *args, **kwargs )
    
        # Hide the 'tags' field on "add" and "edit" view
        self.fields.pop('tags', None)

    def clean_name(self):
        """
        Validate that no duplicate host group names exists.
        
        Returns:
            str: The cleaned name.
        
        Raises:
            ValidationError: If a host group name already exists.
        """
        name = self.cleaned_data['name']
        qs = HostGroup.objects.filter( name=name )
        if self.instance.pk:
            qs = qs.exclude( pk=self.instance.pk )
        if qs.exists():
            raise forms.ValidationError( f"A host group named '{name}' already exists." )
        return name


# ------------------------------------------------------------------------------
# Tag Mapping
# ------------------------------------------------------------------------------


class TagMappingForm(NetBoxModelForm):
    """
    Form for creating or editing tag mappings for devices or VMs.
    Dynamically generates BooleanFields for each tag and prevents duplicate object_type mappings.
    """
    object_type = forms.ChoiceField( choices=TagMapping.OBJECT_TYPE_CHOICES, initial='device' )
    prefix = "gurka"

    class Meta:
        model = TagMapping
        fields = [ "object_type", "tags" ]

    def __init__(self, *args, **kwargs):
        """
        Initialize form with dynamic BooleanFields based on object_type and plugin settings.
        Locks object_type if editing existing instance and prepares initial enabled states.
        """
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
        # Hide the 'tags' field on "add" and "edit" view
        self.fields.pop('tags', None)


    def clean_object_type(self):
        """
        Validate that no duplicate tag mapping exists for the same object_type.
        
        Returns:
            str: The cleaned object_type.
        
        Raises:
            ValidationError: If a mapping for the object_type already exists.
        """
        object_type = self.cleaned_data['object_type']
        qs = TagMapping.objects.filter( object_type=object_type )
        if self.instance.pk:
            qs = qs.exclude( pk=self.instance.pk )
        if qs.exists():
            raise forms.ValidationError( f"A mapping for object type '{object_type}' already exists." )
        return object_type


    def save(self, commit=True):
        """
        Save the tag mapping selection based on user input.
        
        Args:
            commit (bool): Whether to commit to the database immediately.
        
        Returns:
            TagMapping: The saved instance.
        """
        # Build list of dicts with name, value, and enabled
        object_type = self.cleaned_data['object_type']
        tag_mappings = PLUGIN_SETTINGS.get( 'tag_mappings', {} ).get( object_type, [] )
        
        selection = []
        for tag_name, tag_value in tag_mappings:
            field_key = slugify( f"{self.prefix}_{tag_name}"  )

            enabled = self.cleaned_data.get( field_key, False )
            selection.append({
                "name":    tag_name,
                "value":   tag_value,
                "enabled": enabled,
            })

        self.instance.selection = selection
        return super().save( commit=commit )


# ------------------------------------------------------------------------------
# Inventory Mapping
# ------------------------------------------------------------------------------


class InventoryMappingForm(NetBoxModelForm):
    """
    Form for creating or editing inventory mappings for devices or VMs.
    Dynamically generates BooleanFields for each inventory property.
    """
    object_type = forms.ChoiceField( choices=InventoryMapping.OBJECT_TYPE_CHOICES, initial='device' )
    prefix = "kullager"

    class Meta:
        model = InventoryMapping
        fields = ["object_type", "tags" ]  # exclude 'selection' from raw rendering


    def __init__(self, *args, **kwargs):
        """
        Initialize form with dynamic BooleanFields based on object_type and plugin settings.
        Locks object_type if editing existing instance and prepares initial enabled states.
        """
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
                logger.error( f"{invkey} is not a legal inventory property" )

        # Hide the 'tags' field on "add" and "edit" view
        self.fields.pop('tags', None)


    def clean_object_type(self):
        """
        Validate that no duplicate inventory mapping exists for the same object_type.
        
        Returns:
            str: The cleaned object_type.
        
        Raises:
            ValidationError: If a mapping for the object_type already exists.
        """
        object_type = self.cleaned_data['object_type']
        qs = InventoryMapping.objects.filter( object_type=object_type )
        if self.instance.pk:
            qs = qs.exclude( pk=self.instance.pk )
        if qs.exists():
            raise forms.ValidationError( f"A mapping for object type '{object_type}' already exists." )
        return object_type

    def save(self, commit=True):
        """
        Save the inventory mapping selection based on user input.
        
        Args:
            commit (bool): Whether to commit to the database immediately.
        
        Returns:
            InventoryMapping: The saved instance.
        """
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
    """
    Form for creating or editing device mappings.
    Handles default mapping rules, filter restrictions, template validation,
    and prevents deletion of the default mapping.
    """
    fieldsets = (
        FieldSet( 'name', 'default', name="General" ),
        FieldSet( 'host_groups', 'templates', 'proxy', 'proxy_group', 'interface_type', name="Settings" ),
        FieldSet( 'sites', 'roles', 'platforms', name="Filters" ),
        FieldSet( 'description', name="Optional" )
    )
    
    class Meta:
        model = DeviceMapping
        fields = '__all__' 

    def __init__(self, *args, **kwargs):
        """
        Initialize the form for a new or existing device mapping.
        
        Sets the first mapping as default and disables fields as appropriate.
        Removes filter fields for default mapping and prunes empty FieldSets.
        """
        
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

        # Hide the 'tags' field on "add" and "edit" view
        self.fields.pop('tags', None)


    def clean(self):
        """
        Validate mapping filters, templates, and ensure only one default mapping exists.
        
        Raises:
            ValidationError: If filters overlap, templates are missing, or default rules are violated.
        """
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
        Check if this mapping overlaps with another mapping.
        
        Returns:
            bool: True if filters overlap and specificity is the same, otherwise False.
        """
        # Count how many filter fields are set for each mapping
        def count_fields(mapping):
            """
            Count how many filter fields (sites, roles, platforms) are set for a mapping.
            
            For the form instance (`self`), checks `cleaned_data`; for other mappings,
            checks the related fields in the database.
            
            Args:
                mapping (DeviceMappingForm or DeviceMapping): The mapping to evaluate.
            
            Returns:
                int: The number of filter fields that are set (0–3).
            
            Notes:
                - This is used to determine the "specificity" of a mapping for overlap checks.
                - A field counts as "set" if it contains at least one value.
            """
            return sum(
                1 for field in ['sites', 'roles', 'platforms']
                if (self.cleaned_data.get( field ) if mapping is self else getattr( mapping, field ).exists())
            )
    
        self_fields  = count_fields( self )
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
        """
        Prevent deletion of the default device mapping.
        
        Raises:
            ValidationError: If attempting to delete the default mapping.
        """
        if self.default:
            raise ValidationError( "The default device mapping cannot be deleted." )
        super().delete(*args, **kwargs)


# ------------------------------------------------------------------------------
# VM Mapping
# ------------------------------------------------------------------------------


class VMMappingForm(NetBoxModelForm):
    """
    Form for creating or editing VM mappings.
    Similar to DeviceMappingForm, but specifically for virtual machines.
    """
    fieldsets = (
        FieldSet( 'name', 'default', name="General" ),
        FieldSet( 'host_groups', 'templates', 'proxy', 'proxy_group', 'interface_type', name="Settings" ),
        FieldSet( 'sites', 'roles', 'platforms', name="Filters"),
        FieldSet( 'description', name="Optional" )
    )
    
    class Meta:
        model = VMMapping
        fields = '__all__' 

    def __init__(self, *args, **kwargs):
        """
        Initialize the form for a new or existing VM mapping.
        
        Sets the first mapping as default and disables fields as appropriate.
        Removes filter fields for default mapping and prunes empty FieldSets.
        """
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

        # Hide the 'tags' field on "add" and "edit" view
        self.fields.pop('tags', None)


    def clean(self):
        """
        Validate mapping filters, templates, and ensure only one default mapping exists.
        
        Raises:
            ValidationError: If filters overlap, templates are missing, or default rules are violated.
        """
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
        Check if this VM mapping overlaps with another mapping.
        
        Returns:
            bool: True if filters overlap and specificity is the same, otherwise False.
        """
        # Count how many filter fields are set for each mapping
        def count_fields(mapping):
            """
            Count how many filter fields (sites, roles, platforms) are set for a mapping.
            
            For the form instance (`self`), checks `cleaned_data`; for other mappings,
            checks the related fields in the database.
            
            Args:
                mapping (DeviceMappingForm or DeviceMapping): The mapping to evaluate.
            
            Returns:
                int: The number of filter fields that are set (0–3).
            
            Notes:
                - This is used to determine the "specificity" of a mapping for overlap checks.
                - A field counts as "set" if it contains at least one value.
            """
            return sum(
                1 for field in ['sites', 'roles', 'platforms']
                if (self.cleaned_data.get( field ) if mapping is self else getattr( mapping, field ).exists())
            )
    
        self_fields  = count_fields( self )
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
        """
        Prevent deletion of the default VM mapping.
        
        Raises:
            ValidationError: If attempting to delete the default mapping.
        """
        if self.default:
            raise ValidationError( "The default device mapping cannot be deleted." )
        super().delete(*args, **kwargs)


# ------------------------------------------------------------------------------
# Host Config
# ------------------------------------------------------------------------------


class HostConfigForm(NetBoxModelForm):
    """
    Form for configuring hosts in Zabbix.
    Supports devices or VMs, validates monitored_by, templates, and interface availability.
    """
    object_id = forms.IntegerField( widget=forms.HiddenInput(), required=False )

    # Dummy
    DefaultContentType = ContentType.objects.get_for_model( VirtualMachine )

    interface_type = forms.ChoiceField( label="Interface Type", help_text="Select the interface Zabbix should use to monitor this host: Agent, SNMP, or Any.", choices=InterfaceTypeChoices, initial=InterfaceTypeChoices.Agent )

    class Meta:
        model  = HostConfig
        fields = (
            'name',
            'content_type',
            'object_id',
            'host',
            'interface_type',
            'status',
            'monitored_by',
            'host_groups',
            'templates',
            'proxy',
            'proxy_group',
            'description'
        )

    content_type = ContentTypeChoiceField(
        label="Host Type",
        help_text="Associated Host Type.",
        queryset=ContentType.objects.filter( model__in=["virtualmachine", "device" ] ),

        # NOTE: Setting initial here has no effect on pre-selecting the model 
        # in the form. However, the field must have a value; otherwise, it 
        # defaults to empty, forcing the user to select both the Content Type 
        # and Host before the Host Mappings can be prepopulated.
        initial=DefaultContentType, 
        required=True,
    )

    host = DynamicModelChoiceField(
        label="Host",
        help_text="Associated Device or Virtual Machine.",
        queryset=UnAssignedHosts.objects.all(),
        required=True,
        selector=False,
        query_params={"content_type": "$content_type"},
    )

    is_edit_field = forms.BooleanField( widget=forms.HiddenInput(), required=False )

    def __init__(self, *args, **kwargs):
        """
        Lock host and content_type fields when editing an existing instance.
        
        Pre-populates fields with assigned object to prevent reassignment.
        """

        instance = kwargs.get( 'instance', None )
        super().__init__( *args, **kwargs )

        self.fields["is_edit_field"].initial = bool( self.instance and self.instance.pk )

        # Hide the 'tags' field on "add" and "edit" view
        self.fields.pop( 'tags', None )
        
        # Editing existing HostConfig
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
            return



    def clean_host(self):
        """
        Validate the selected host before saving the form.
    
        Ensures that the underlying Device or VirtualMachine has a primary IPv4 address.
        """
        host = self.cleaned_data.get( "host" )
        if host is None:
            return host
    
        # Check if the host has a primary IPv4
        if not getattr(host, "primary_ip4", None):
            raise ValidationError( f"The selected host '{host}' has no primary IPv4 address and cannot be used to create a HostConfig." )

        return host
    

    def clean(self):
        """
        Validate monitored_by settings, interface type, and template compatibility.
        
        Raises:
            ValidationError: If monitored_by is incomplete or templates/interfaces are invalid.
        """
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



#    def save(self, *args, **kwargs):
#
#        from netbox_zabbix.jobs.provision import ProvisionAgent, ProvisionSNMP
#
#        # Save the HostConfig instance normally
#        instance = super().save( *args, **kwargs )
#
#        # Retrieve the interface_type from cleaned_data
#        interface_type = self.cleaned_data.get( "interface_type", None )
#
#        # Get the request which was added in alter_object() in the view.
#        request = getattr( instance, "_request", None )
#        
#        if int( interface_type ) == int( InterfaceTypeChoices.Agent ):
#            job = ProvisionAgent.run_job( instance=instance.assigned_object, request=request )
#            message = mark_safe( f'Queued job <a href=/core/jobs/{job.id}/>#{job.id}</a> ' f'to create host in Zabbix' )
#            messages.success( request, message )
#
#        elif int( interface_type) == int( InterfaceTypeChoices.SNMP ):
#            job = ProvisionSNMP.run_job( instance=instance.assigned_object, request=request )
#            message = mark_safe( f'Queued job <a href=/core/jobs/{job.id}/>#{job.id}</a> ' f'to create host in Zabbix' )
#            messages.success( request, message )
#
#        else:
#            messages.error( request, "Did not provision host in Zabbix" )
#       
#        return instance

    def save(self, *args, **kwargs):
        from netbox_zabbix.jobs.provision import ProvisionAgent, ProvisionSNMP
    
        # Determine if this is a new host or editing an existing one
        is_new = self.instance.pk is None  # True if adding, False if editing
    
        # Save the HostConfig instance normally
        instance = super().save( *args, **kwargs )

        if is_new:
            # Only run provisioning jobs if this is a new host
            interface_type = self.cleaned_data.get( "interface_type" )
            request = getattr( instance, "_request", None )
            
            
            if int(interface_type) == int(InterfaceTypeChoices.Agent):
                job = ProvisionAgent.run_job(instance=instance.assigned_object, request=request)
                message = mark_safe(f'Queued job <a href=/core/jobs/{job.id}/>#{job.id}</a> to create host in Zabbix')
                messages.success(request, message)
    
            elif int(interface_type) == int(InterfaceTypeChoices.SNMP):
                job = ProvisionSNMP.run_job(instance=instance.assigned_object, request=request)
                message = mark_safe(f'Queued job <a href=/core/jobs/{job.id}/>#{job.id}</a> to create host in Zabbix')
                messages.success(request, message)
    
            else:
                messages.error(request, "Did not provision host in Zabbix")
            
        return instance


# ------------------------------------------------------------------------------
# Base Host Interface Form
# ------------------------------------------------------------------------------


class BaseHostInterfaceForm(NetBoxModelForm):
    """
    Base form for host interfaces (Agent or SNMP).
    Handles dynamic selection of interface and IP, DNS validation, and interface assignment.
    """
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
    agent_defaults = {}                               # override in Agent form
    snmp_defaults  = {}                               # override in SNMP form

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
        """
        Initialize form for creating or editing an interface.
        
        Pre-populates fields for existing instances, applies agent/SNMP defaults,
        and sets is_edit_field for template usage.
        """
        super().__init__( *args, **kwargs )

        # Hide host_config but still submit it so it can be saved to the DB.
        self.fields["host_config"].widget = forms.HiddenInput()
        
        # Set the is_edit_field, which is used in the template to prevent fetching primary ip when editing an interface.
        self.fields["is_edit_field"].initial = bool( self.instance and self.instance.pk )

        # Editing an existing interface
        if self.instance and self.instance.pk:
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
            return

        # Creating new interface
        host_config = None
        if "host_config" in self.initial:
            host_config = HostConfig.objects.filter(id=self.initial["host_config"]).first()
        elif getattr(self.instance, "host_config_id", None):
            host_config = self.instance.host_config
        
        if host_config:
            self.initial["name"] = f"{host_config.assigned_object.name}-{self.default_name_suffix}"
            
            # Apply common defaults
            for field, value in self.agent_defaults.items():
                self.initial[field] = value
        
            # Apply SNMP defaults
            for field, value in self.snmp_defaults.items():
                self.initial[field] = value
        else:
            logger.error( "HostConfig is Not defined" )


    def clean(self):
        """
        Validate DNS and interface constraints for host configuration.
        
        Raises:
            ValidationError: If DNS is missing or interface is invalid.
        """
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
        """
        Save the interface instance, populating interface type and ID.
        
        Args:
            commit (bool): Whether to commit to the database immediately.
        
        Returns:
            BaseHostInterface: Saved instance.
        """
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
    """
    Form for creating/editing Agent interfaces.
    Sets interface_type_choice and default port for Agent interfaces.
    """
    interface_type_choice = InterfaceTypeChoices.Agent
    default_name_suffix = "agent"

    class Meta(BaseHostInterfaceForm.Meta):
        model = AgentInterface

    def __init__(self, *args, **kwargs):
        """
        Initialize AgentInterfaceForm and apply default port from settings.
        """

        # The order is important agent defaults has to be set before the __init__ call.
        self.agent_defaults = {
            "useip": settings.get_useip(),
            "port":  settings.get_agent_port()
        }
        super().__init__( *args, **kwargs )


# ------------------------------------------------------------------------------
# SNMP Interface
# ------------------------------------------------------------------------------


class SNMPInterfaceForm(BaseHostInterfaceForm):
    """
    Form for creating/editing SNMP interfaces.
    Sets interface_type_choice and default SNMP parameters (port, bulk, security, auth).
    """
    interface_type_choice = InterfaceTypeChoices.SNMP
    default_name_suffix = "snmp"
    
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

    def __init__(self, *args, **kwargs):
        """
        Initialize SNMPInterfaceForm and apply default SNMP settings from plugin configuration.
        """
        # The order is important snmp defaults has to be set before the __init__ call.
        self.snmp_defaults = {
            "useip":           settings.get_useip(),
            "port":            settings.get_snmp_port(),
            "bulk":            settings.get_snmp_bulk(),
            "max_repetitions": settings.get_snmp_max_repetitions(),
            "contextname":     settings.get_snmp_contextname(),
            "securityname":    settings.get_snmp_securityname(),
            "securitylevel":   settings.get_snmp_securitylevel(),
            "authprotocol":    settings.get_snmp_authprotocol(),
            "authpassphrase":  settings.get_snmp_authpassphrase(),
            "privprotocol":    settings.get_snmp_privprotocol(),
            "privpassphrase":  settings.get_snmp_privpassphrase(),
        }
        super().__init__( *args, **kwargs )


# ------------------------------------------------------------------------------
# Maintenance
# ------------------------------------------------------------------------------


class MaintenanceForm(NetBoxModelForm):
    """
    Form for creating or updating a Zabbix maintenance window.
    """
    
    start_time = forms.DateTimeField( 
        required=True,
        widget=DateTimePicker(),
        label="Start at",
        help_text="Maintenence start time." 
    )
    
    end_time = forms.DateTimeField( 
        required=True,
        widget=DateTimePicker(),
        label="End at",
        help_text="Maintenence end time." 
    )

    class Meta:
        model = Maintenance
        fields = (
            'name', 'start_time', 'end_time',
            'disable_data_collection', 
            'host_configs', 'sites', 'host_groups',
            'proxies', 'proxy_groups', 'clusters', 
            'description'
        )

    def __init__(self, *args, **kwargs):
        """
        Initialize form with default initial values for new instance.

        Hides 'tags' field.
        """

        super().__init__( *args, **kwargs )

        # Hide the 'tags' field on "add" and "edit" view
        self.fields.pop( 'tags', None )

        user = getattr( self.instance, "_current_user", None )
        if not has_any_model_permission( user, "netbox_zabbix", "zabbixadminpermission" ):
            self.fields.pop( 'proxies', None )
            self.fields.pop( 'proxy_groups', None )


# end
