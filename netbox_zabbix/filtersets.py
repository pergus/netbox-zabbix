from netbox.filtersets import NetBoxModelFilterSet
import django_filters
from .models import ZBXVM, ZBXTemplate, ZBXHost, ZBXInterface


class ZBXVMFilterSet(NetBoxModelFilterSet):
    # Filter by the related VirtualMachine's ID (not ZBXVM.pk)
    vm_id = django_filters.NumberFilter(field_name='vm__id')
    templates = django_filters.ModelMultipleChoiceFilter(queryset=ZBXTemplate.objects.all())
    
    class Meta:
        model = ZBXVM
        fields = ['vm_id', 'templates']





#
# Combined
#


class ZBXHostFilterSet(NetBoxModelFilterSet):
    class Meta:
        model = ZBXHost
        fields = ['zbx_host_id', 'status', 'interface', 'templates' ]


class ZBXInterfaceFilterSet(NetBoxModelFilterSet):
    host = django_filters.ModelChoiceFilter(queryset=ZBXHost.objects.all())

    class Meta:
        model = ZBXInterface
        fields = [
            'host', 'interfaceid', 'hostid', 'type',
            'ip', 'dns', 'port', 'useip', 'available', 'main',
        ]



class ZBXTemplateFilterSet(NetBoxModelFilterSet):
    q = django_filters.CharFilter(field_name='name', lookup_expr='icontains', label='Search Templates')
    class Meta:
        model = ZBXTemplate
        fields = ['name']