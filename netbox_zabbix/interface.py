from django import forms
from django.urls import reverse_lazy
from django.shortcuts import render, reverse
from django.views.generic import View
from django.utils.translation import gettext as _
from django.template.loader import render_to_string
from django.http import HttpResponse

from utilities.templatetags.builtins.filters import render_markdown
from netbox.registry import Registry
from netbox_zabbix.logger import logger


# ------------------------------------------------------------------------------
# Registry and Registration Utilities
# ------------------------------------------------------------------------------

netbox_zabbix_registry = Registry({'interfaces': dict()})


def register_interface(cls):
    """Register a new interface class into the global registry."""
    app_label = cls.__module__.split('.', maxsplit=1)[0]
    label = f'{app_label}.{cls.__name__}'
    netbox_zabbix_registry['interfaces'][label] = cls
    return cls


def get_interface_choices():
    return netbox_zabbix_registry['interfaces'].items()


def get_widget_class(name):
    try:
        return netbox_zabbix_registry['interfaces'][name]
    except KeyError:
        raise ValueError(_("Unregistered interface class: {name}").format(name=name))


def get_field_value(form, field_name):
    """Return the pre-clean value for a field from form data or initial."""
    field = form.fields[field_name]
    if form.is_bound and field_name in form.data:
        value = form.data[field_name]
        if value is not None and (not hasattr(field, 'valid_value') or field.valid_value(value)):
            return value
    return form.get_initial_for_field(field, field_name)


# ------------------------------------------------------------------------------
# Forms
# ------------------------------------------------------------------------------

class InterfaceConfigForm(forms.Form):
    """Base class for per-interface config forms."""


class InterfaceForm(forms.Form):
    title = forms.CharField(required=False)


class InterfaceAddForm(InterfaceForm):
    widget_class = forms.ChoiceField(
        choices=get_interface_choices,
        widget=forms.Select(
            attrs={
                'hx-get': reverse_lazy('plugins:netbox_zabbix:interface_add'),
                'hx-target': '#add_interface',
            }
        ),
        label=_('Interface type'),
    )
    field_order = ('widget_class', 'title')


# ------------------------------------------------------------------------------
# Views
# ------------------------------------------------------------------------------

class InterfaceView(View):
    template_name = 'netbox_zabbix/interface.html'

    def get(self, request):
        return render(request, self.template_name)


class InterfaceAddView(View):
    template_name = 'netbox_zabbix/interface_add.html'

    def get(self, request):
        initial = {
            'widget_class': request.GET.get('widget_class') or 'netbox_zabbix.ZabbixAgentInterface'
        }
        interface_form = InterfaceAddForm(initial=initial)
        interface_name = get_field_value(interface_form, 'widget_class')
        widget_class = get_widget_class(interface_name)

        config_form = widget_class.ConfigForm(
            initial=widget_class.default_config,
            prefix='config'
        )

        return render(request, self.template_name, {
            'widget_class': widget_class,
            'interface_form': interface_form,
            'config_form': config_form,
        })

    def post(self, request):
        interface_form = InterfaceAddForm(request.POST)
        config_form = None
        widget_class = None

        if interface_form.is_valid():
            interface_name = interface_form.cleaned_data['widget_class']
            widget_class = get_widget_class(interface_name)

            config_form = widget_class.ConfigForm(data=request.POST, prefix='config')

            if config_form.is_valid():
                full_data = {
                    'interface': interface_form.cleaned_data,
                    'config': config_form.cleaned_data,
                }
                logger.info(f"{full_data=}")
                return HttpResponse(headers={
                    'HX-Redirect': reverse('plugins:netbox_zabbix:interface'),
                })

        return render(request, self.template_name, {
            'widget_class': widget_class,
            'interface_form': interface_form,
            'config_form': config_form,
        })


# ------------------------------------------------------------------------------
# Interface Base Class
# ------------------------------------------------------------------------------

class Interface:
    description = None
    default_title = None
    default_config = {}

    def __init__(self, title=None, config=None, width=None, height=None, x=None, y=None):
        self.title = title or self.default_title or self.__class__.title
        self.config = config or self.default_config
        self.width = width
        self.height = height
        self.x = x
        self.y = y

    def __str__(self):
        return self.title or self.__class__.__name__

    def render(self, request):
        raise NotImplementedError(_("{class_name} must define a render() method.").format(
            class_name=self.__class__
        ))

    @property
    def name(self):
        return f'{self.__class__.__module__.split(".")[0]}.{self.__class__.__name__}'

    @property
    def form_data(self):
        return {
            'title': self.title,
            'config': self.config,
        }


# ------------------------------------------------------------------------------
# Interface Implementations
# ------------------------------------------------------------------------------

# Interfaces

@register_interface
class ZabbixAgentInterface(Interface):
    title = 'Zabbix Agent'
    description = 'Standard Zabbix agent interface'
    default_config = {
        'ip': '',
        'dns': '',
        'port': 10050,
        'useip': True,
        'main': True,
    }

    class ConfigForm(InterfaceConfigForm):
        ip = forms.GenericIPAddressField(label=_('IP address'), required=False)
        dns = forms.CharField(label=_('DNS name'), required=False)
        port = forms.IntegerField(label=_('Port'), initial=10050, min_value=1, max_value=65535)
        useip = forms.BooleanField(label=_('Use IP'), required=False)
        main = forms.BooleanField(label=_('Default interface'), required=False)

    def render(self, request):
        return render_to_string('netbox_zabbix/interface_agent.html', {
            **self.config
        })


@register_interface
class ZabbixSNMPv3Interface(Interface):
    title = 'Zabbix SNMPv3'
    description = 'SNMPv3-capable Zabbix interface'
    default_config = {
        'ip': '',
        'dns': '',
        'port': 1611,
        'useip': True,
        'main': False,
#        'details': {
            'version': 3,
            'bulk': 1,
            'max_repetitions': 11,
            'security_level': 'authPriv',
            'securityname': '',
            'auth_protocol': 'SHA1',
            'auth_passphrase': '{$SNMPV3_AUTHPASS}',
            'priv_protocol': 'AES128',
            'priv_passphrase': '{$SNMPV3_PRIVPASS}',
 #       }
    }

    class ConfigForm(InterfaceConfigForm):
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


    def render(self, request):
        data = {**self.config}
        data.update(data.pop('details'))
        return render_to_string('netbox_zabbix/interface_snmpv3.html', data)
