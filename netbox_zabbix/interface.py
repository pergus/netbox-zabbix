import uuid

from django import forms
from django.http import HttpResponse, Http404
from django.shortcuts import render, reverse, redirect
from django.urls import reverse_lazy
from django.utils.functional import lazy
from django.utils.translation import gettext as _
from django.views.generic import View

from netbox.registry import Registry

from .host import host_json


"""
------------------------------------------------------------------------------
Interface Widget System Overview
------------------------------------------------------------------------------

This module implements a dynamic interface widget system that supports 
custom per-interface configuration forms using Django forms, a registry, and 
HTMX for asynchronous UI updates.

Key Concepts:
-------------

1. Registration via `@register_interface`:
   - Interface classes (e.g. `ZabbixAgentInterface`, `ZabbixSNMPv3Interface`) are 
     registered via the `@register_interface` decorator.
   - The decorator stores each interface class in the global registry 
     `netbox_zabbix_registry['interfaces']` using its full dotted Python path 
     as the key (e.g. `'netbox_zabbix.interface.ZabbixAgentInterface'`).
   - Each interface is assigned a numeric `interface_type_id` used for mapping.

2. Mapping Between Interface Type and Widget Class:
   - `INTERFACE_TYPE_TO_WIDGET` maps a numeric `interface_type_id` (like `'1'`, `'2'`) 
     to the full class name string.
   - `WIDGET_TO_INTERFACE_TYPE` is the inverse, mapping the class name string back to 
     the numeric ID.
   - These mappings allow translation between user selection (via widget_class) 
     and backend logic.

3. `widget_class` Form Field:
   - The `InterfaceAddForm` and `InterfaceEditView` use a `ChoiceField` named 
     `widget_class` to let the user select an interface type.
   - The field is populated dynamically via `get_interface_choices()`, which 
     enumerates the registered interfaces.
   - HTMX attributes (`hx-get`, `hx-trigger`, etc.) are added to the widget for 
     dynamic loading of the interface-specific config form when the selection changes.

4. Using `widget_class` in Views:
   - On GET: The selected `widget_class` name (a string key) is looked up via 
     `get_widget_class(name)` to retrieve the actual class object from the registry.
   - This class's `ConfigForm` inner class is then instantiated to render the 
     correct config form for the selected interface type.
   - On POST: The `widget_class` value from the form is used again to load and 
     validate the correct `ConfigForm` with the submitted data.

5. Why `widget_class` Doesn't Include a File Name:
   - The value of `widget_class` in the form is a string like 
     `'netbox_zabbix.interface.ZabbixAgentInterface'`, which is the fully qualified 
     class name, *not* a physical file path. 
   - This value is a registry key and serves as an identifier for lookup and 
     form reconstruction, making the interface pluggable and not tied to specific 
     files or file system paths.
"""


# ------------------------------------------------------------------------------
# Registry and Registration Utilities
# ------------------------------------------------------------------------------

netbox_zabbix_registry = Registry( {'interfaces': dict()} )
INTERFACE_TYPE_TO_WIDGET = {}
WIDGET_TO_INTERFACE_TYPE = {}

# A simple auto-increment type ID generator
_next_interface_type_id = [1]

def register_interface(cls):
    """
    Register a new interface class into the global registry.
    
    Args:
        cls (type): The interface class to register.
    
    Returns:
        type: The original class, unmodified.
    
    Side Effects:
        - Adds the class to `netbox_zabbix_registry['interfaces']` keyed by 
          fully qualified class name.
        - Assigns a unique numeric string ID to `cls.interface_type_id` if not set.
        - Updates the mappings `INTERFACE_TYPE_TO_WIDGET` and `WIDGET_TO_INTERFACE_TYPE`.
    """
    label = f'{cls.__module__}.{cls.__name__}'
    netbox_zabbix_registry['interfaces'][label] = cls

    # Assign next numeric type if not manually set
    if not hasattr( cls, 'interface_type_id' ):
        cls.interface_type_id = str( _next_interface_type_id[0] )
        _next_interface_type_id[0] += 1
    
    INTERFACE_TYPE_TO_WIDGET[cls.interface_type_id] = label
    WIDGET_TO_INTERFACE_TYPE[label] = cls.interface_type_id
    
    return cls


def get_interface_choices():
    """
    Retrieve registered interface classes as choices for a Django ChoiceField.
    
    Returns:
        Iterable[Tuple[str, type]]: An iterable of (fully qualified class name, class).
    """
    return netbox_zabbix_registry['interfaces'].items()


def get_widget_class(name):
    """
    Lookup the interface class by its fully qualified name.
    
    Args:
        name (str): The fully qualified interface class name.
    
    Returns:
        type: The interface class corresponding to the given name.
    
    Raises:
        ValueError: If the interface class name is not registered.
    """
    try:
        return netbox_zabbix_registry['interfaces'][name]
    except KeyError:
        raise ValueError(_("Unregistered interface class: {name}").format(name=name))


def get_field_value(form, field_name):
    """
    Helper to get a form field's value, considering bound data or initial.
    
    Args:
        form (forms.Form): The form instance.
        field_name (str): The name of the field.
    
    Returns:
        Any: The current value for the field.
    """    
    field = form.fields[field_name]
    prefixed_name = form.add_prefix(field_name)

    if form.is_bound and prefixed_name in form.data:
        value = form.data[prefixed_name]
        if value is not None and (not hasattr(field, 'valid_value') or field.valid_value(value)):
            return value
        
    return form.get_initial_for_field(field, field_name)


# ------------------------------------------------------------------------------
# Forms
# ------------------------------------------------------------------------------

class InterfaceConfigForm(forms.Form):
    """
    Base class for per-interface configuration forms.
    
    Intended to be subclassed by each interface type to define interface-specific
    configuration fields.
    """
    pass


class InterfaceForm(forms.Form):
    """
    Base form for interface data.
    
    Attributes:
        title (CharField): Optional title for the interface.
    """    
    title = forms.CharField(required=False)


class InterfaceAddForm(InterfaceForm):
    """
    Form for adding a new interface, including selection of the interface type.
    
    Fields:
        widget_class (ChoiceField): Choice of interface type, dynamically populated.
    
    HTMX integration:
        Adds attributes for asynchronous loading of interface-specific config form
        when the widget_class selection changes.
    
    Args:
        host_id (int, optional): The host ID to use in HTMX GET URL for form reloading.
    """    
    widget_class = forms.ChoiceField(
            choices=lazy(get_interface_choices, list)(),
            widget=forms.Select(
                       attrs={
                           'hx-get': reverse_lazy('plugins:netbox_zabbix:interface_add', kwargs={'pk': 0}), # Dummy value seeems to work...s
                           'hx-target': '#add_interface',
                       }
                   ),
            label=_('Interface type'),
        )
    field_order = ('widget_class', 'title')


    def __init__(self, *args, host_id=None, editable_widget_class=True, **kwargs):
        """
        Initialize InterfaceAddForm.
        
        Args:
            *args: Variable length argument list.
            host_id (int, optional): Host ID to build hx-get URL.
            **kwargs: Arbitrary keyword arguments.
        """
        super().__init__(*args, **kwargs)
        if not editable_widget_class:
            self.fields['widget_class'].widget.attrs['readonly'] = True
            #self.fields['widget_class'].widget.attrs['disabled'] = True
            
        if host_id is not None:
            self.fields['widget_class'].widget.attrs.update({
                'hx-get': reverse('plugins:netbox_zabbix:interface_add', kwargs={'pk': host_id}),
                'hx-target': '#add_interface',
                'hx-trigger': 'change',
                'hx-include': 'closest form',  # ensures all form data is sent
            })

# ------------------------------------------------------------------------------
# Views
# ------------------------------------------------------------------------------


# Not used!
class InterfaceView(View):
    """
    A placeholder view for interfaces.
    
    GET requests render the base interface template.
    """
    template_name = 'netbox_zabbix/interface.html'

    def get(self, request):
        """
        Handle GET request.
        
        Args:
            request (HttpRequest): The HTTP request object.
        
        Returns:
            HttpResponse: Rendered template response.
        """
        return render(request, self.template_name)


def extract_details(config):
    """
    Extract non-core fields from interface config for storage in 'details'.
    
    Args:
        config (dict): The full config dictionary.
    
    Returns:
        dict: Key-value pairs excluding core fields.
    """
    core_fields = { 'ip', 'dns', 'port', 'useip', 'main' }
    return { k: str(v) for k, v in config.items() if k not in core_fields }


class InterfaceAddView(View):
    """
    View to handle adding new interfaces.
    
    GET:
        Renders the add interface form and loads the config form for the selected interface type.
    
    POST:
        Validates and processes the submitted interface data and config, adding the new interface.
    """

    template_name = 'netbox_zabbix/interface_add.html'


    def get(self, request, pk, *args, **kwargs):
        """
        Handle GET request to render interface add form and config form.
        
        Args:
            request (HttpRequest): The HTTP request object.
            pk (int): The host ID.
        
        Returns:
            HttpResponse: Rendered template response with forms.
        """
        initial = {
            'widget_class': request.GET.get('widget_class') or 'netbox_zabbix.interface.ZabbixAgentInterface'
        }

        print("HTMX POST data:", request.POST)

        interface_form = InterfaceAddForm( initial=initial )
        interface_name = get_field_value( interface_form, 'widget_class' )
        widget_class = get_widget_class( interface_name )
        
        config_form = widget_class.ConfigForm(
            initial=widget_class.default_config,
            prefix='config'
        )

        return render(request, self.template_name, {
            'host_id': pk,
            'widget_class': widget_class,
            'interface_form': interface_form,
            'config_form': config_form,
        })


    def post(self, request, pk):
        """
        Handle POST request to add a new interface.
        
        Args:
            request (HttpRequest): The HTTP request object.
            pk (int): The host ID.
        
        Returns:
            HttpResponse: Redirect response on success or rendered form on failure.
        """
        form = InterfaceAddForm( request.POST )
        widget_class = None
        config_form = None

        if form.is_valid():
            interface_name = form.cleaned_data['widget_class']
            widget_class = get_widget_class( interface_name )
            config_form = widget_class.ConfigForm( request.POST, prefix='config' )
            
            if config_form.is_valid():
                config = config_form.cleaned_data
                interfaces = host_json.setdefault( 'interfaces', [] )

                # Determine the interface type from widget class name
                widget_class_name = f"{widget_class.__module__}.{widget_class.__name__}"
                interface_type = WIDGET_TO_INTERFACE_TYPE.get(widget_class_name)
                
                # Determine if this new interface should be main
                is_main = config.get('main', False)

                if config.get('main'):
                    for iface in interfaces:
                        if iface['type'] == interface_type and iface['main'] == '1':
                            iface['main'] = '0'  # demote existing main of same type


                # Add new interface
                new_interface = {
                    "interfaceid": str( uuid.uuid4().int % 1000000 ),
                    "hostid": str( pk ),
                    "main": "0", # Will be updated below
                    "type": interface_type,
                    "useip": "1" if config.get('useip') else "0",
                    "ip": config.get('ip', ''),
                    "dns": config.get('dns', ''),
                    "port": str(config.get('port', '10050')),
                    "available": "0",
                    "error": "",
                    "errors_from": "0",
                    "disable_until": "0",
                    "details": extract_details(config),
                }

                # If this interface should be main, unset main on others of same type
                if is_main:
                    for iface in interfaces:
                        if iface.get('type') == interface_type:
                            iface['main'] = "0"
                    new_interface['main'] = "1"
                else:
                    new_interface['main'] = "0"
                

                interfaces.append(new_interface)
                return HttpResponse(headers={ 'HX-Redirect': reverse('plugins:netbox_zabbix:host'), })

        return render(request, self.template_name, {
                    'host_id': pk,
                    'interface_form': form,
                    'config_form': config_form,
                    'widget_class': widget_class,
                })    
        

class InterfaceEditView(View):
    """
    View to edit existing interfaces.
    
    GET:
        Renders the interface edit form with current configuration.
    
    POST:
        Validates and updates the interface data.
    """
    template_name = 'netbox_zabbix/interface_edit.html'

    def get_interface(self, host_data, interfaceid):
        for iface in host_data.get('interfaces', []):
            if iface.get('interfaceid') == interfaceid:
                return iface
        return None

    def get(self, request, pk, interfaceid):
        """
        Handle GET request to render edit form for the interface.
        
        Args:
            request (HttpRequest): The HTTP request object.
            pk (int): Host ID.
            interface_id (int): Interface ID to edit.
        
        Returns:
            HttpResponse: Rendered template response with forms.
        """

        # Load interface data from JSON - N.B. interfaceid has to be a string.
        iface = self.get_interface( host_json, str( interfaceid ))
        if not iface:
            return HttpResponse( "Interface not found", status=404 )

        # Map Zabbix type number to widget class name or get default 
        widget_class_name = INTERFACE_TYPE_TO_WIDGET.get(iface['type'], 'netbox_zabbix.interface.ZabbixAgentInterface')
        widget_class = get_widget_class(widget_class_name)

        # Compose initial data for InterfaceForm
        interface_initial = {
            'widget_class': widget_class_name,
            'title': iface.get('dns', '') or iface.get('ip', ''),
        }
        interface_form = InterfaceAddForm( initial=interface_initial, editable_widget_class=False )

        # Compose initial data for config form from interface fields
        # For example, use keys that widget_class.ConfigForm expects
        config_initial = {
            'ip': iface.get( 'ip', '' ),
            'dns': iface.get( 'dns', '' ),
            'port': int(iface.get( 'port', 10050 ) ),
            'useip': iface.get( 'useip', '0' ) == '1',
            'main': iface.get( 'main', '0' ) == '1',
        }
        config_form = widget_class.ConfigForm( initial=config_initial, prefix='config' )

        return render(request, self.template_name, {
            'host_id': pk,
            'interfaceid': interfaceid,
            'interface_form': interface_form,
            'config_form': config_form,
            'widget_class': widget_class,
        })

    def post(self, request, pk, interfaceid):
        """
        Handle POST request to update interface data.
        
        Args:
            request (HttpRequest): The HTTP request object.
            pk (int): Host ID.
            interface_id (int): Interface ID.
        
        Returns:
            HttpResponse: Redirect response on success or rendered form on failure.
        """

        iface = self.get_interface( host_json, str( interfaceid ) )
        if not iface:
            return HttpResponse( "Interface not found", status=404 )

        interface_form = InterfaceAddForm( request.POST )
        widget_class = None
        config_form = None

        if interface_form.is_valid():
            interface_name = interface_form.cleaned_data['widget_class']
            widget_class = get_widget_class( interface_name )

            config_form = widget_class.ConfigForm( request.POST, prefix='config' )

            if config_form.is_valid():
                # Update the interface data in the JSON (in memory)
                config_data = config_form.cleaned_data

                iface['ip'] = config_data.get( 'ip', '' )
                iface['dns'] = config_data.get( 'dns', '' )
                iface['port'] = str(config_data.get( 'port', 10050) )
                iface['useip'] = '1' if config_data.get( 'useip' ) else '0'                

                # Determine if this interface should be main
                is_main = config_data.get('main', False)
                current_type = iface.get('type')
                
                if is_main:
                    # Unset 'main' on all other interfaces of the same type
                    for other_iface in host_json.get('interfaces', []):
                        if (
                            other_iface.get('interfaceid') != iface.get('interfaceid') and
                            other_iface.get('type') == current_type
                        ):
                            other_iface['main'] = "0"
                    iface['main'] = "1"
                else:
                    iface['main'] = "0"
                

                existing_details = iface.get('details')
                if not isinstance(existing_details, dict):
                    existing_details = {}
                new_details = {**existing_details, **extract_details(config_data)}
                iface['details'] = new_details

                return HttpResponse(headers={ 'HX-Redirect': reverse('plugins:netbox_zabbix:host'), })

        return render(request, self.template_name, {
            'host_id': pk,
            'interfaceid': interfaceid,
            'interface_form': interface_form,
            'config_form': config_form,
            'widget_class': widget_class,
        })




class InterfaceDeleteView(View):
    template_name = 'netbox_zabbix/interface_delete_confirmation.html'


    def get(self, request, pk, interfaceid):
        interface_type_labels = {
            "1": "Agent",
            "2": "SNMPv3",
        }
        

        interfaces = host_json.get('interfaces', [])
        iface = next( (i for i in interfaces if str( i.get( 'interfaceid' ) ) == str( interfaceid )), None )
        if not iface:
            raise Http404(_("Interface not found"))

        interface_type_id = str(iface.get("type"))
        interface_label = interface_type_labels.get(interface_type_id, _("Unknown"))

        return render(request, self.template_name, {
            'object': iface,
            'interface_type': interface_label,
            'return_url': reverse('plugins:netbox_zabbix:host'),
        })

    def post(self, request, pk, interfaceid):
        interfaces = host_json.get('interfaces', [])
        interfaceid = str(interfaceid)
        
        # Find and remove the interface
        removed_interface = None
        updated_interfaces = []
        for iface in interfaces:
            if iface.get('interfaceid') == interfaceid:
                removed_interface = iface
                continue
            updated_interfaces.append(iface)
        
        if not removed_interface:
            return HttpResponse("Interface not found", status=404)
        
        host_json['interfaces'] = updated_interfaces
        
        # Promote another interface of same type if removed one was main
        if removed_interface.get('main') == '1':
            removed_type = removed_interface.get('type')
            for iface in updated_interfaces:
                if iface.get('type') == removed_type:
                    iface['main'] = '1'
                    break
        
        return redirect(reverse('plugins:netbox_zabbix:host'))

#    def post(self, request, pk, interfaceid):
#        interfaces = host_json.get('interfaces', [])
#        index_to_delete = next( (i for i, iface in enumerate( interfaces )
#                                if iface.get( 'interfaceid') == str( interfaceid ) ), None )
#
#        if index_to_delete is not None:
#            del interfaces[index_to_delete]
#            return redirect(reverse('plugins:netbox_zabbix:host'))
#
#        raise Http404(_("Interface not found"))      


# ------------------------------------------------------------------------------
# Interface Base Class
# ------------------------------------------------------------------------------

class Interface:
    """
    Base class for all interface implementations.
    
    Attributes:
        description (str): Description of the interface.
        default_title (str): Default title to use if none provided.
        default_config (dict): Default configuration dictionary.
    
    Instance Attributes:
        title (str): Title of the interface instance.
        config (dict): Configuration dictionary for this instance.
        width (int, optional): Width for UI rendering (if applicable).
        height (int, optional): Height for UI rendering.
        x (int, optional): X coordinate in UI.
        y (int, optional): Y coordinate in UI.
    """
    

    description = None
    default_title = None
    default_config = {}

    def __init__(self, title=None, config=None, width=None, height=None, x=None, y=None):
        """
        Initialize an Interface instance.
        
        Args:
            title (str, optional): Custom title.
            config (dict, optional): Custom config dictionary.
            width (int, optional): UI width.
            height (int, optional): UI height.
            x (int, optional): UI x-coordinate.
            y (int, optional): UI y-coordinate.
        """

        self.title = title or self.default_title or self.__class__.title
        self.config = config or self.default_config
        self.width = width
        self.height = height
        self.x = x
        self.y = y

    def __str__(self):
        """
        String representation.
        
        Returns:
            str: Title or class name.
        """
        return self.title or self.__class__.__name__

    def render(self, request):
        """
        Render method to be implemented by subclasses.
        
        Args:
            request (HttpRequest): The Django HTTP request.
        
        Raises:
            NotImplementedError: Must be implemented in subclasses.
        """
        raise NotImplementedError(_("{class_name} must define a render() method.").format(
            class_name=self.__class__
        ))

    @property
    def name(self):
        """
        Get the fully qualified interface class name.
        
        Returns:
            str: Module name + class name.
        """
        return f'{self.__class__.__module__.split(".")[0]}.{self.__class__.__name__}'

    @property
    def form_data(self):
        """
        Prepare form data dictionary.
        
        Returns:
            dict: Data for populating forms.
        """
        return {
            'title': self.title,
            'config': self.config,
        }


# ------------------------------------------------------------------------------
# Interface Implementations
# ------------------------------------------------------------------------------

@register_interface
class ZabbixAgentInterface(Interface):
    """
    Interface implementation for the Zabbix Agent.
    
    Attributes:
        title (str): Interface display title.
        interface_type_id (str): Numeric type ID.
        description (str): Description of this interface.
        default_config (dict): Default configuration values.
    """

    title = 'Zabbix Agent'
    interface_type_id = "1"
    description = 'Standard Zabbix agent interface'
    default_config = {
        'ip': '',
        'dns': '',
        'port': 10050,
        'useip': True,
        'main': True,
    }

    class ConfigForm(InterfaceConfigForm):
        """
        Configuration form for Zabbix Agent interface.
        """
        ip = forms.GenericIPAddressField(label=_('IP address'), required=False)
        dns = forms.CharField(label=_('DNS name'), required=False)
        port = forms.IntegerField(label=_('Port'), initial=10050, min_value=1, max_value=65535)
        useip = forms.BooleanField(label=_('Use IP'), required=False)
        main = forms.BooleanField(label=_('Default interface'), required=False)



@register_interface
class ZabbixSNMPv3Interface(Interface):
    """
    Interface implementation for Zabbix SNMPv3.
    
    Attributes:
        title (str): Interface display title.
        interface_type_id (str): Numeric type ID.
        description (str): Description of this interface.
        default_config (dict): Default configuration values.
    """

    title = 'Zabbix SNMPv3'
    interface_type_id = "2"
    description = 'SNMPv3-capable Zabbix interface'
    default_config = {
        'ip': '',
        'dns': '',
        'port': 1611,
        'useip': True,
        'main': False,
        'version': 3,
        'bulk': 1,
        'max_repetitions': 11,
        'contextname': '',
        'security_level': 'authPriv',
        'securityname': '',
        'auth_protocol': 'SHA1',
        'auth_passphrase': '{$SNMPV3_AUTHPASS}',
        'priv_protocol': 'AES128',
        'priv_passphrase': '{$SNMPV3_PRIVPASS}',
    }

    class ConfigForm(InterfaceConfigForm):
        """
        Configuration form for Zabbix SNMPv3 interface.
        """
        ip = forms.GenericIPAddressField(label=_('IP address'), required=False)
        dns = forms.CharField(label=_('DNS name'), required=False)
        port = forms.IntegerField(label=_('Port'), initial=161, min_value=1, max_value=65535)
        useip = forms.BooleanField(label=_('Use IP'), required=False)
        main = forms.BooleanField(label=_('Default interface'), required=False)
        
        version = forms.IntegerField(
            label=_('SNMP version'),
            initial=3,
            widget=forms.HiddenInput()
        )

        bulk = forms.BooleanField(label=_('Use bulk requests'), required=False, initial=True)
        max_repetitions = forms.IntegerField( label=_('Max repetition count'), initial=10, min_value=1, max_value=65535 )
        contextname = forms.CharField( label=_('Context name'), required=False )
        securityname = forms.CharField(label=_('Security name'), required=False )
        security_level = forms.ChoiceField(label=_('Security level'), choices=[
            ('noAuthNoPriv','noAuthNoPriv'),
            ('authNoPriv','authNoPriv'),
            ('authPriv','authPriv')
        ])

        auth_protocol = forms.ChoiceField(label=_('Auth protocol'), choices=[('MD5','MD5'),('SHA1','SHA1'), ('SHA224', 'SHA224'), ('SHA256', 'SHA256'), ('SHA384', 'SHA384'), ('SHA512', 'SHA512')], required=False)
        auth_passphrase = forms.CharField(label=_('Auth passphrase'), required=False, widget=forms.PasswordInput(render_value=True))
        priv_protocol = forms.ChoiceField(label=_('Privacy protocol'), choices=[('DES','DES'),('AES128','AES128'), ('AES192', 'AES192'), ('AES256', 'AES256'), ('AES192C', 'AES192C'), ('AES256C', 'AES256C')], required=False)
        priv_passphrase = forms.CharField(label=_('Privacy passphrase'), required=False, widget=forms.PasswordInput(render_value=True))


