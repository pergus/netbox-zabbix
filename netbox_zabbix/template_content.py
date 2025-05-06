#from netbox.plugins import PluginTemplateExtension
#from .models import ZBXVM
#from django.urls import reverse
#
#import logging
#
#class ZBXVMSettings(PluginTemplateExtension):
#    model = 'virtualization.virtualmachine'
#
#    logger = logging.getLogger('netbox.plugins.netbox_zabbix')
#    
#    def buttons(self):
#        vm = self.context['object']
#        
#        # Check if ZBXVM exists for this VM
#        zbxvm = ZBXVM.objects.filter(vm=vm).first()
#        
#        if zbxvm:
#            # Display the Edit button if ZBXVM exists
#            self.logger.info("EDIT ZABBIX BUTTON")
#            return self.render("netbox_zabbix/edit_zabbix_button.html", extra_context = { "zbxvm": zbxvm } )
#        else:
#            # Display the Add button if no ZBXVM exists
#            self.logger.info("ADD ZABBIX BUTTON")
#            return self.render("netbox_zabbix/add_zabbix_button.html")
#        
#
#    def left_page(self):
#        self.logger.info("zbx plugin left_page...")
#        z_set = ZBXVM.objects.filter(vm=self.context['object'])
#        if z_set.exists():
#            return self.render('netbox_zabbix/zbxvm_settings.html', extra_context={
#                           'object': self.context['object'],  # The current VirtualMachine object
#                           'zbxvms': z_set                    # Pass the related ZBXVM objects
#                       })
#        else:
#            return ""
#
#    def right_page(self):
#        self.logger.info("zbx plugin right_page...")
#        return ""
#
#    def full_width_page(self):
#        self.logger.info("zbx plugin full_width_page...")
#        z_set = ZBXVM.objects.filter(vm=self.context['object'])
#        if z_set.exists():
#            return self.render('netbox_zabbix/zbxvm_settings.html', extra_context={
#                           'object': self.context['object'],  # The current VirtualMachine object
#                           'zbxvms': z_set                    # Pass the related ZBXVM objects
#                       })
#        return ""
#    
#template_extensions = [ZBXVMSettings]


from netbox.plugins import PluginTemplateExtension
from .models import ZBXHost  # adjust if you renamed

class DeviceZabbixConfig(PluginTemplateExtension):
    model = 'dcim.device'

    def right_page(self):
        zbxhost = ZBXHost.objects.filter(
            content_type__model='device',
            object_id=self.context['object'].id
        ).first()

        if not zbxhost:
            return ''

        return self.render('netbox_zabbix/inc/zabbix_config.html', {
            'zbxhost': zbxhost
        })

class VMZabbixConfig(PluginTemplateExtension):
    model = 'virtualization.virtual-machine'
    
    def right_page(self):
        zbxhost = ZBXHost.objects.filter(
            content_type__model='virtualmachine',
            object_id=self.context['object'].id
        ).first()

        if not zbxhost:
            return ''

        return self.render('netbox_zabbix/inc/zabbix_config.html', {
            'zbxhost': zbxhost
        })


template_extensions = [DeviceZabbixConfig, VMZabbixConfig]