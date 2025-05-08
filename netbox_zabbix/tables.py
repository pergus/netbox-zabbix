import django_tables2 as tables
from netbox.tables import NetBoxTable, columns
from netbox_zabbix import models
from django_tables2 import TemplateColumn
from dcim.models import Device
from virtualization.models import VirtualMachine


# ------------------------------------------------------------------------------
# Configuration
#

EXTRA_BUTTONS = """
<span class="dropdown">
    <button id="actions" type="button" class="btn btn-sm btn-primary dropdown-toggle" data-bs-toggle="dropdown" aria-expanded="false">
        <i class="mdi mdi-plus-thick" aria-hidden="true"></i> Actions
    </button>

    <ul class="dropdown-menu" aria-labeled-by="actions">
        <li>
            <a class="dropdown-item"
                href="{% url 'plugins:netbox_zabbix:config_check_connection' %}">
                Check Connection
            </a>
        </li>
    </ul>
</span>
"""

class ConfigTable(NetBoxTable):
    class Meta(NetBoxTable.Meta):
        model = models.Config
        fields = ('name', 'api_endpoint', 'web_address', 'version', 'connection', 'last_checked_at')
        default_columns = ('name', 'api_endpoint', 'version', 'connection', 'last_checked_at')

    name = tables.Column( linkify=True )
    actions = columns.ActionsColumn( extra_buttons=EXTRA_BUTTONS )


# ------------------------------------------------------------------------------
# Templates
#

class TemplateTable(NetBoxTable):
    name = tables.Column( linkify=True )
    host_count = columns.LinkedCountColumn( 
         viewname='plugins:netbox_zabbix:host_list',
         url_params={'templates': 'pk'},
         verbose_name="Hosts" )
    
    class Meta(NetBoxTable.Meta):
        model = models.Template
        fields = ("name", "templateid", "host_count", "last_synced", "marked_for_deletion" )
        default_columns = ("name", "templateid", "host_count", "last_synced", "marked_for_deletion" )


# ------------------------------------------------------------------------------
# Hosts
#

class HostTable(NetBoxTable):
    name = tables.Column( accessor='get_name', verbose_name='Name', linkify=True )
    object = tables.Column( accessor='content_object', verbose_name='Host', linkify=True )
    status = tables.Column()
    zabbix_host_id = tables.Column( verbose_name='Zabbix Host ID' )
    templates = tables.ManyToManyColumn(linkify_item=True)
    
    class Meta(NetBoxTable.Meta):
        model = models.Host
        fields = ('object', 'name', 'zabbix_host_id', 'status', 'templates')


class UnsyncedDeviceTable(NetBoxTable):
    name = tables.Column( linkify=True )
    actions = TemplateColumn(
        template_code='''
        <a href="{% url 'plugins:netbox_zabbix:host_add' %}?content_type={{ device_ct.pk }}&host_id={{ record.id }}"
           class="btn btn-sm btn-primary">Add Host</a>
        ''',
        orderable=False,
        verbose_name="Actions"
    )

    class Meta(NetBoxTable.Meta):
        model = Device
        fields = ("name",)

class UnsyncedVMTable(NetBoxTable):
    name = tables.Column( linkify=True )
    actions = TemplateColumn(
        template_code='''
        <a href="{% url 'plugins:netbox_zabbix:host_add' %}?content_type={{ vm_ct.pk }}&host_id={{ record.id }}"
           class="btn btn-sm btn-primary">Add Host</a>
        ''',
        orderable=False,
        verbose_name="Actions"
    )

    class Meta(NetBoxTable.Meta):
        model = VirtualMachine
        fields = ("name",)


class NetBoxOnlyHostnameTable(tables.Table):
    name = TemplateColumn(
        template_code='''
        {% if record.url %}
            <a href="{{ record.url }}">{{ record.name }}</a>
        {% else %}
            {{ record.name }}
        {% endif %}
        ''',
        verbose_name="Name"
    )

    class Meta:
        attrs = {"class": "table table-hover"}
        default_columns = ("name")

class ZabbixOnlyHostnameTable(tables.Table):
    name = TemplateColumn(
            template_code='''
            <a href="{{ zabbix_web_address }}/zabbix.php?action=host.edit&hostid={{ record.hostid }}">
                {{ record.name }}
            </a>
            ''',
            verbose_name="Name"
        )
    
    #hostid = tables.Column(linkify=False, verbose_name="Host ID")

    class Meta:
        attrs = {"class": "table table-hover"}
        default_columns = ("name")
