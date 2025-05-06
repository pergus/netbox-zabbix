import django_tables2 as tables
from netbox.tables import NetBoxTable, columns

from .models import ZBXConfig, ZBXTemplate, ZBXVM, ZBXHost, ZBXInterface


#
# Zabbix Configuration
#
EXTRA_BUTTONS = """
<span class="dropdown">
    <button id="actions" type="button" class="btn btn-sm btn-primary dropdown-toggle" data-bs-toggle="dropdown" aria-expanded="false">
        <i class="mdi mdi-plus-thick" aria-hidden="true"></i> Actions
    </button>

    <ul class="dropdown-menu" aria-labeled-by="actions">
        <li>
            <a class="dropdown-item"
                href="{% url 'plugins:netbox_zabbix:zbx_check_connection' %}">
                Check Connection
            </a>
        </li>
        <li>
            <a class="dropdown-item"
                href="{% url 'plugins:netbox_zabbix:zbx_templates_sync' %}">
                Sync Templates
            </a>
        </li>
    </ul>
</span>
"""


class ZBXConfigTable(NetBoxTable):
    name = tables.Column(linkify=True)
    actions = columns.ActionsColumn(extra_buttons=EXTRA_BUTTONS)

    class Meta(NetBoxTable.Meta):
        model = ZBXConfig
        fields = ("pk", "id", "name", "api_address", "web_address", "version", "connection", "token", "active", "actions")
        default_columns = ("name", "api_address", "web_address", "version", "connection", "active")


#
# Templates
#
class ZBXTemplateTable(NetBoxTable):
    name = tables.Column(linkify=True)
    vm_count = columns.LinkedCountColumn(
         viewname='plugins:netbox_zabbix:zbxvm_list',
         url_params={'templates': 'pk'},
         verbose_name="Virtual Machines"
     )
    
    class Meta(NetBoxTable.Meta):
        model = ZBXTemplate
        fields = ("name", "templateid", "last_synced", "vm_count", "marked_for_deletion" )
        default_columns = ("name", "templateid", "last_synced", "vm_count", "marked_for_deletion" )


#
# VMs
#

class ZBXTemplateColumn(tables.TemplateColumn):
    template_code = """
    {% load helpers %}
    {% for tpl in value.all %}
        {% badge tpl  %}
    {% empty %}
        <span class="text-muted">&mdash;</span>
    {% endfor %}
    """

    def __init__(self, url_name=None):
        super().__init__(
            orderable=False,
            template_code=self.template_code,
            extra_context={'url_name': url_name},
            verbose_name='Templates',
        )

    def value(self, value):
        return ",".join([tpl.name for tpl in value.all()])


from django_tables2.utils import A 

class ZBXVMTable(NetBoxTable):
    vm = tables.Column(linkify=True)
    status = columns.ChoiceFieldColumn(verbose_name='Status')
    templates = ZBXTemplateColumn()
    
    # Zabbix problems
    problems_url = tables.LinkColumn(
        'plugins:netbox_zabbix:zabbix_host_problems',
        args=[tables.A('vm.name')],
        verbose_name="Problems",
        orderable=False,
        empty_values=(),
        text="View Problems",
        attrs={"a": {"class": "btn btn-sm btn-normal"}}
    )
    
    # Sync button column using LinkColumn
    sync_button = tables.LinkColumn(
         'plugins:netbox_zabbix:zbx_host_sync',  # URL name
         args=[tables.A('vm.id')],               # Pass the VM id as the argument
         verbose_name="Action",                  # Display name of the column
         orderable=False,                        # Optional: Set to False to prevent sorting on this column
         empty_values=(),                        # Handle empty values if necessary
         text="Sync FZ",                         # Link text
         attrs={ "a": {"class": "btn btn-sm btn-primary"} }
    )
    
    class Meta(NetBoxTable.Meta):
        model = ZBXVM
        fields = ("vm", "zbx_host_id", "status", "interface", "templates", "problems_url", "sync_button")
        default_columns = ("status", "interface", "templates", "problems_url", "sync_button")



#
# Combined
#

class ZBXHostTable(NetBoxTable):
    object = tables.Column(accessor='content_object', verbose_name='Host', linkify=True)
    status = tables.Column()
    interface = tables.Column()
    zbx_host_id = tables.Column(verbose_name='Zabbix Host ID')

    class Meta(NetBoxTable.Meta):
        model = ZBXHost
        fields = ('object', 'zbx_host_id', 'status', 'interface')



class ZBXInterfaceTable(NetBoxTable):
    host = tables.Column(linkify=True, verbose_name='Host')
#    id = tables.Column()
#    interfaceid = tables.Column()
#    hostid = tables.Column() 
#    type = tables.Column()
#    ip = tables.Column()
#    dns = tables.Column()
#    port = tables.Column()
#    useip = tables.Column()
#    available = tables.Column()
#    main = tables.Column()

#    type = tables.Column(accessor="get_type_display")

    class Meta(NetBoxTable.Meta):
        model = ZBXInterface
        fields = (
            'id', 'host', 'interfaceid', 'hostid', 
            'ip', 'dns', 'port', 'useip', 'main', 'type',
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
            'snmp_bulk'
        )
        default_columns = (
            'host', 'id', 'ip', 'port', 'dns', 'type',
        )


class ZBXHostZBXInterfaceTable(ZBXInterfaceTable):
    class Meta(NetBoxTable.Meta):
        model = ZBXInterface
        fields = (
                  'id', 'interfaceid', 'hostid', 'type',
                  'ip', 'dns', 'port', 'useip', 'available', 'main',
              )
        default_columns = (
                  'id', 'ip', 'port', 'type', 'main',
              )