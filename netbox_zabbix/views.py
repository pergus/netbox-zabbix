from django.utils import timezone
from netbox.views import generic
from virtualization.models.virtualmachines import VirtualMachine
from . import forms, models, tables, filtersets

from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.db.models import Count

from pyzabbix import ZabbixAPI


from core.models import Job

import logging
logger = logging.getLogger('netbox.plugins.netbox_zabbix')

#
# Zabbix Configuration
#
class ZBXConfigView(generic.ObjectView):
    queryset = models.ZBXConfig.objects.all()


class ZBXConfigListView(generic.ObjectListView):
    queryset = models.ZBXConfig.objects.all()
    table = tables.ZBXConfigTable


class ZBXConfigEditView(generic.ObjectEditView):
    queryset = models.ZBXConfig.objects.all()
    form = forms.ZBXConfigForm


class ZBXConfigDeleteView(generic.ObjectDeleteView):
    queryset = models.ZBXConfig.objects.all()

from django.contrib import messages
def ZBXConfigCheckConnectionView(request):
    cfg = models.ZBXConfig.objects.first()
    if not cfg:
        error_message = "Missing Zabbbix Configuration"
        logger.error(error_message)
        messages.error(request, error_message)
        messages.error(request, "Missing Zabbbix Configuration")
        return redirect(request.META.get('HTTP_REFERER', '/'))
    
    try:
        z = ZabbixAPI(cfg.api_address)
        z.login(api_token=cfg.token)        
        cfg.version = z.apiinfo.version()
        cfg.connection = True
        cfg.save()
    except Exception as e:
        error_message = f"Failed to connecto to {cfg.api_address} failed: {e}"
        logger.error(error_message)
        messages.error(request, error_message)
        cfg.connection = False
        cfg.save()
        return redirect(request.META.get('HTTP_REFERER', '/'))

    messages.success(request, "Connection to Zabbbix Succeeded")
    return redirect(request.META.get('HTTP_REFERER', '/'))
    
    


#
# Zabbix Templates
#
class ZBXTemplateView(generic.ObjectView):
    queryset = models.ZBXTemplate.objects.all()

class ZBXTemplateListView(generic.ObjectListView):
    queryset = models.ZBXTemplate.objects.annotate(vm_count=Count('zbxvm'))
    table = tables.ZBXTemplateTable
    template_name = "netbox_zabbix/zbxtemplate_list.html"

class ZBXTemplateEditView(generic.ObjectEditView):
    queryset = models.ZBXTemplate.objects.all()
    form = forms.ZBXTemplateForm


class ZBXTemplateDeleteView(generic.ObjectDeleteView):
    queryset = models.ZBXTemplate.objects.all()


def zbx_templates_review_deletions(request):
    items = models.ZBXTemplate.objects.filter(marked_for_deletion=True)
    return render(request, 'netbox_zabbix/zbxtemplate_review_deletions.html', {'items': items})

@require_POST
def zbx_templates_confirm_deletions(request):
    selected_ids = request.POST.getlist('confirm_ids')
    models.ZBXTemplate.objects.filter(id__in=selected_ids).delete()
    return redirect('plugins:netbox_zabbix:zbx_templates_review_deletions')


def zbx_templates_sync(request):

    cfg = models.ZBXConfig.objects.filter(active=True).first()
    if not cfg:
        return redirect('plugins:netbox_zabbix:zbxtemplate_list')
    
    z = ZabbixAPI(cfg.api_address)
    z.login(api_token=cfg.token)
    
    # Add a try except here!
    tpls = z.template.get(output=["name"], limit=10000)
    tpls = sorted(tpls, key=lambda x: x["name"])

    templateids = set(item['templateid'] for item in tpls)
    current_tpls = models.ZBXTemplate.objects.all()
    current_ids = set(current_tpls.values_list('templateid', flat=True))

    ## Begin Debug
    #templateids.remove("10564")
    #templateids.remove("10846")
    ## End Debug

    now = timezone.now()

    for item in tpls:
        obj, created = models.ZBXTemplate.objects.update_or_create( 
            templateid = item['templateid'],
            defaults = { 
                "name": item['name'],
                "last_synced":  now,
                "marked_for_deletion":  False 
            }
        )
    
    # Mark templates for deletion that are no longer in zabbix
    to_flag_for_deletion = current_ids - templateids
    models.ZBXTemplate.objects.filter(templateid__in=to_flag_for_deletion).update(marked_for_deletion=True)
    
    return redirect('plugins:netbox_zabbix:zbxtemplate_list')


#
# VMs
#

class ZBXVMView(generic.ObjectView):
    queryset = models.ZBXVM.objects.all()


class ZBXVMListView(generic.ObjectListView):
    queryset = models.ZBXVM.objects.all()
    filterset = filtersets.ZBXVMFilterSet
    table = tables.ZBXVMTable
    template_name = "netbox_zabbix/zbxvm_list.html"


class ZBXVMEditView(generic.ObjectEditView):
    queryset = models.ZBXVM.objects.all()
    form = forms.ZBXVMForm

class ZBXVMDeleteView(generic.ObjectDeleteView):
    queryset = models.ZBXVM.objects.all()

from utilities.views import ViewTab, register_model_view
@register_model_view(VirtualMachine, name="Zabbix", path="zabbix")
class ZBXVMTabView(generic.ObjectView):
    queryset = models.ZBXVM.objects.all()
    tab = ViewTab(label="Zabbix")

    def get(self, request, pk):
        vm = get_object_or_404(VirtualMachine, pk=pk)
        zbxvms = models.ZBXVM.objects.filter(vm=vm)
    
        problems = []
        if zbxvms.exists():
            zbxvm = zbxvms.first()  # assume one-to-one, or loop if many
            hostid = zbxvm.zbx_host_id
    
            try:
                zbx_cfg = models.ZBXConfig.objects.filter(active=True).first()
                if zbx_cfg:
                    z = ZabbixAPI(zbx_cfg.api_address)
                    z.login(api_token=zbx_cfg.token)
    
                    problems = z.problem.get(
                        output=["eventid", "severity", "acknowledged", "name", "clock"],
                        #hostids=[hostid],
                        hostids=[10659],
                        sortfield=["eventid"],
                        sortorder="DESC",
                    )
            except Exception as e:
                logger.warning(f"Zabbix fetch failed for VM {vm.name}: {e}")
    
        return render(request, "netbox_zabbix/zbxvm_additional_tab.html", context={
            "tab": self.tab,
            "object": vm,
            "zbxvms": zbxvms,
            "problems": problems,
        })

#
# Move this code into its own file(s)
#
from core.models import Job
from django_rq import job
from django_rq import get_queue
from utilities.rqworker import get_workers_for_queue


from virtualization.models import VirtualMachine

def sync_vm_zb2nb(vm, zhost, template_map, status_map, interface_map):
    """
    Sync a single Zabbix host to the corresponding ZBXVM object.
    """
    # Get or create ZBXVM for this VM
    zbxvm, created = models.ZBXVM.objects.get_or_create(vm=vm)

    logger.info(f"syncing host {vm.name} from zabbix to netbox")
    
    zbxvm.zbx_host_id = zhost["hostid"]
    zbxvm.status = status_map.get(str(zhost.get("status")), "unknown")

    # Handle interfaces
    interfaces = zhost.get("interfaces", [])
    if interfaces:
        iface_type = str(interfaces[0].get("type"))
        zbxvm.interface = interface_map.get(iface_type, "unknown")
    else:
        zbxvm.interface = "unknown"

    zbxvm.save()

    # Set templates
    template_ids = [t["templateid"] for t in zhost.get("parentTemplates", [])]
    templates = [template_map[tid] for tid in template_ids if tid in template_map]
    zbxvm.templates.set(templates)

# Sync multiple hosts
def z_sync_hosts_zb2nb(request):
    cfg = models.ZBXConfig.objects.filter(active=True).first()
    if not cfg:
        return redirect('plugins:netbox_zabbix:zbxvms_list')

    z = ZabbixAPI(cfg.api_address)
    z.login(api_token=cfg.token)

    # Fetch Zabbix hosts
    zabbix_hosts = z.host.get(
        output=["hostid", "name", "status"],
        selectInterfaces=["type"],
        selectParentTemplates=["templateid", "name"],
    )

    # Map VM name to VirtualMachine
    vm_map = {
        vm.name: vm
        for vm in VirtualMachine.objects.all()
    }

    # Map templateid to ZBXTemplate
    template_map = {
        t.templateid: t
        for t in models.ZBXTemplate.objects.all()
    }

    # Map Zabbix status and interface types
    status_map = {
        "0": "enabled",
        "1": "disabled",
    }

    interface_map = {
        "1": "agent",
        "2": "SNMP",
        "3": "IPMI",
        "4": "JMX",
    }

    # Sync all hosts
    for zhost in zabbix_hosts:
        name = zhost["name"]
        vm = vm_map.get(name)
        if not vm:
            logger.info(f"not syncing host {name} since it not in present in netbox")                
            continue  # No matching VM in NetBox, skip

        # Call the shared helper function to sync the ZBXVM
        sync_vm_zb2nb(vm, zhost, template_map, status_map, interface_map)

    return redirect('plugins:netbox_zabbix:zbxvm_list')

# Sync one host
#
# When an error occures a job has to:
# a) Log the message.
# b) Mark the job status as errored.
# c) Raise an exception so that the background task fails.
#
from core.choices import JobStatusChoices
from pyzabbix import ZabbixAPIException

def z_sync_host_zbx2nb_job(*args, **kwargs):

    job = kwargs.get("job")

    logger.info(f"Starting job {job.job_id} with name {job.name}................")
    
    
    vm = kwargs.get("vm")
    if vm is None:
        error_message = f"expected argument 'vm' is missing or None." 
        logger.info( error_message )
        job.data = { "status": "failed", "error": error_message }
        job.terminate( status=JobStatusChoices.STATUS_ERRORED, error=error_message )
        raise Exception( error_message )
    
        
    cfg = models.ZBXConfig.objects.filter(active=True).first()
    if not cfg:
        error_message = "missing Zabbix configuration"
        logger.info( error_message )
        job.data = { "status": "failed", "error": error_message }
        job.terminate( status=JobStatusChoices.STATUS_ERRORED, error=error_message )
        raise Exception( error_message )
    
    
    z = ZabbixAPI(cfg.api_address)        
    z.login(api_token=cfg.token)

    try:            
        # Fetch the specific Zabbix host associated with this VM
        zabbix_host = z.host.get(
            output=["hostid", "name", "status"],
            filter={"host": vm.name},  # Filter by the VM's name
            selectInterfaces=["type"],
            selectParentTemplates=["templateid", "name"],
        )
    except ZabbixAPIException as e:
        error_message = f"Zabbix API error: {str(e)}"
        logger.info( error_message )
        job.data = { "status": "failed", "error": error_message }
        job.terminate( status=JobStatusChoices.STATUS_ERRORED, error=error_message )
        raise Exception( error_message )
            
    if zabbix_host:
        zhost = zabbix_host[0]  # Assuming there's only one host that matches the VM
        # Define the mappings just like in zbx_hosts_sync
        template_map = {
            t.templateid: t
            for t in models.ZBXTemplate.objects.all()
        }
        
        status_map = {
            "0": "enabled",
            "1": "disabled",
        }
        
        interface_map = {
            "1": "agent",
            "2": "SNMP",
            "3": "IPMI",
            "4": "JMX",
        }
        
        # Call the shared helper function to sync the ZBXVM
        sync_vm_zb2nb(vm, zhost, template_map, status_map, interface_map)

        msg = f"Sync host {vm.name} succeeded"
        logger.info(msg)
        job.data = { "status": "ok", "message": msg }
        job.terminate( status=JobStatusChoices.STATUS_COMPLETED)
    else:
        error_message = f"No host named {vm.name} found in Zabbix"
        logger.info( error_message )
        job.data = { "status": "failed", "error": error_message }
        job.terminate( status=JobStatusChoices.STATUS_ERRORED, error=error_message)
        raise Exception( error_message )


def z_sync_host_zbx2nb( request, vm_id ):

    if vm_id is None:
        logger.info( "missing vm_id in call to z_sync_host_zbx2nb" )
        return redirect(request.META.get('HTTP_REFERER', '/')) # Error page?

    try:
        vm = VirtualMachine.objects.get( id = vm_id )
    except Exception as e:
        logger.info( f"missing vm with id {vm_id} in call to z_sync_host_zbx2nb" )
        return redirect(request.META.get('HTTP_REFERER', '/')) # Error page?

    Job.enqueue( z_sync_host_zbx2nb_job, name=f"Sync host {vm.name} FZ", user=request.user, vm = vm )

    return redirect(request.META.get('HTTP_REFERER', '/'))



#
# Zabbix Problems
#
from django.http import Http404
def zabbix_host_problems(request, name):
    # Retrieve active Zabbix config
    cfg = models.ZBXConfig.objects.filter(active=True).first()
    if not cfg:
        raise Http404("Zabbix configuration not found")

    # Connect to Zabbix API
    z = ZabbixAPI(cfg.api_address)
    z.login(api_token=cfg.token)


    # Fetch the problems related to the host
    try:
        host = z.host.get(filter={"host": name})[0]
        hostid = host["hostid"]
        
        problems = z.problem.get(
            output=["eventid", "severity", "acknowledged", "name", "clock"],
            hostids=[hostid],
            sortfield="eventid",
            sortorder="DESC"
        )
    except Exception as e:
        raise Http404(f"Error fetching problems for host {hostid}: {str(e)}")

    # Render the problems to a template
    return render(request, "netbox_zabbix/host_problems.html", { "name": name, "problems": problems, "hostid": hostid})


#
# Combined
#

class ZBXHostListView(generic.ObjectListView):
    queryset = models.ZBXHost.objects.all()
    table = tables.ZBXHostTable
    filterset = filtersets.ZBXHostFilterSet
    filterset_form = forms.ZBXHostFilterForm

class ZBXHostView(generic.ObjectView):
    queryset = models.ZBXHost.objects.all()

class ZBXHostEditView(generic.ObjectEditView):
    queryset = models.ZBXHost.objects.all()
    form = forms.ZBXHostForm

class ZBXHostInterfacesView(generic.ObjectChildrenView):
    queryset = models.ZBXHost.objects.all()
    child_model = models.ZBXInterface
    table = tables.ZBXHostZBXInterfaceTable
    filterset = filtersets.ZBXInterfaceFilterSet
    #template_name = 'netbox_zabbix/zbxhost_interfaces.html'

    def get_children(self, request, parent):
        # This returns all interfaces related to this ZBXHost
        return parent.interfaces.all()


class ZBXHostDeleteView(generic.ObjectDeleteView):
    queryset = models.ZBXHost.objects.all()


from django.contrib.contenttypes.models import ContentType
from .models import ZBXHost
from dcim.models import Device
from virtualization.models import VirtualMachine

def unconfigured_hosts(request):
    # Get ContentType instances
    device_ct = ContentType.objects.get(app_label='dcim', model='device')
    vm_ct = ContentType.objects.get(app_label='virtualization', model='virtualmachine')
    
    # Get linked object IDs for both content types
    linked_device_ids = ZBXHost.objects.filter(content_type=device_ct).values_list('object_id', flat=True)
    linked_vm_ids = ZBXHost.objects.filter(content_type=vm_ct).values_list('object_id', flat=True)
    
    # Get devices and VMs without ZBXHost
    unconfigured_devices = Device.objects.exclude(id__in=linked_device_ids)
    unconfigured_vms = VirtualMachine.objects.exclude(id__in=linked_vm_ids)
    

    vm_ct = ContentType.objects.get(app_label="virtualization", model="virtualmachine")
    device_ct = ContentType.objects.get(app_label="dcim", model="device")
    
    context = {
        'unconfigured_devices': unconfigured_devices,
        'unconfigured_vms': unconfigured_vms,
        "vm_ct": vm_ct,
        "device_ct": device_ct,
    }
    
    return render(request, 'netbox_zabbix/unconfigured_hosts.html', context)


#from utilities.views import ViewTab, register_model_view

#@register_model_view(models.ZBXHost, name="interfaces", path="interfaces", detail=False)
#class ZBXInterfaceTabView(generic.ObjectView):
#    queryset = models.ZBXInterface.objects.all()
#    tab = ViewTab(label="Zabbix Interfaces")
#
#    def get(self, request, pk):
#        host = get_object_or_404(models.ZBXHost, pk=pk)
#        return render(request, "netbox_zabbix/zbxhost_interfaces_tab.html", context={
#            "tab": self.tab,
#            "object": host,
#        })
    
@register_model_view(models.ZBXHost, name="ziltoid", path="ziltoid")
class ZBXInterfaceTabView(generic.ObjectView):
    queryset = models.ZBXInterface.objects.all()
    tab = ViewTab(label="Zabbix Interfaces", badge=lambda obj: models.ZBXInterface.objects.filter(host_id=obj.pk).count(),)

    def get(self, request, pk):
        host = get_object_or_404(models.ZBXHost, pk=pk)
        return render(request, "netbox_zabbix/zbxhost_interfaces_tab.html", context={ "tab": self.tab, "object": host })

class ZBXInterfaceListView(generic.ObjectListView):
    queryset = models.ZBXInterface.objects.all()
    table = tables.ZBXInterfaceTable
    filterset = filtersets.ZBXInterfaceFilterSet

class ZBXInterfaceView(generic.ObjectView):
    queryset = models.ZBXInterface.objects.all()
    table = tables.ZBXInterfaceTable
    

class ZBXInterfaceEditView(generic.ObjectEditView):
    queryset = models.ZBXInterface.objects.all()
    form = forms.ZBXInterfaceForm
    template_name = 'netbox_zabbix/zbxinterface_edit_tst.html'

class ZBXInterfaceDeleteView(generic.ObjectDeleteView):
    queryset = models.ZBXInterface.objects.all()

class ZBXInterfaceBulkDeleteView(generic.BulkDeleteView):
    queryset = models.ZBXInterface.objects.all()
    table = tables.ZBXInterfaceTable





from django.views.generic import TemplateView
from .utils import get_zabbix_only_hostnames

class ZabbixOnlyHostnamesView(TemplateView):
    template_name = 'netbox_zabbix/zabbix_only_hostnames.html'
    #zabbix_url = https://se-zbxtestfe01x.se.axis.com/zabbix.php?action=host.edit&hostid={{ object.cf.zabbix_hostid }}
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['zabbix_only_hostnames'] = get_zabbix_only_hostnames()
        return context
    




from .forms import ZBXInterfaceForm
def interface_snmp_form_tst(request):
    interface_type = request.GET.get("type")

    match interface_type:
        case "Agent":
            port = 10050
        case _:
            port = 161
    

    form = ZBXInterfaceForm(initial={"port": port})
    
    fields_by_tab = {
        "Agent": ["port"],
        "SNMPv3": [
            "port", "snmp_contextname", "snmp_securityname", "snmp_securitylevel",
            "snmp_authprotocol", "snmp_authpassphrase", "snmp_privprotocol", "snmp_privpassphrase", "snmp_bulk"
        ],
        "SNMPv2c": ["port", "snmp_community", "snmp_max_repetitions", "snmp_bulk"],
        "SNMPv1":  ["port", "snmp_community", "snmp_bulk"],        
    }

    logger.info(f"{interface_type=}")


    context = {
        "form": form,
        "fields": [form[field] for field in fields_by_tab.get(interface_type, [])],
        "port": port
    }

    return render(request, "netbox_zabbix/snmp_tab_fields.html", context)
