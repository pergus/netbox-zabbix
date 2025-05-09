from django.urls import reverse
from django.db import models

from netbox.models import NetBoxModel


# ------------------------------------------------------------------------------
# Configuration
#

class Config(NetBoxModel):
    class Meta:
        verbose_name = "Zabbix Configuration"
        verbose_name_plural = "Zabbix Configurations"
    
    name             = models.CharField( max_length=255 )
    api_endpoint     = models.CharField( max_length=255 )
    web_address      = models.CharField( max_length=255 )
    token            = models.CharField( max_length=255 )    
    connection       = models.BooleanField( default=False )
    last_checked_at  = models.DateTimeField( null=True, blank=True )
    version          = models.CharField( max_length=255, blank=True, null=True )
    

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("plugins:netbox_zabbix:config", args=[self.pk])

# ------------------------------------------------------------------------------
# Templates
#

class Template(NetBoxModel):
    class Meta:
        verbose_name = "Zabbix Template"
        verbose_name_plural = "Zabbix Templates"
    
    name = models.CharField( max_length=255 )
    templateid = models.CharField( max_length=255 )
    last_synced = models.DateTimeField( blank=True, null=True )
    marked_for_deletion = models.BooleanField( default=False )
     
    def __str__(self):
        return self.name
    
# ------------------------------------------------------------------------------
# Host
#

class StatusChoices(models.TextChoices):
    ENABLED = 'enabled', 'Enabled'
    DISABLEd = 'disabled', 'Disabled'

class BaseHost(NetBoxModel):
    class Meta:
        abstract = True

    zabbix_host_id = models.PositiveIntegerField( unique=True, blank=True, null=True )
    status = models.CharField( max_length=255, choices=StatusChoices.choices, default='enabled' )
    templates = models.ManyToManyField( Template, blank=True )

    
class DeviceHost(BaseHost):
    device = models.OneToOneField( to='dcim.Device', on_delete=models.CASCADE, related_name='zabbix_device_host' )

    def __str__(self):
        return f"zbx-{self.device.name}"

    def get_name(self):
        return f"zbx-{self.device.name}"

    def get_absolute_url(self):
        return reverse( "plugins:netbox_zabbix:devicehost", args=[self.pk] )


class VMHost(BaseHost):
    virtual_machine = models.OneToOneField( to='virtualization.VirtualMachine', on_delete=models.CASCADE, related_name='zabbix_vm_host' )

    def __str__(self):
        return f"zbx-{self.virtual_machine.name}"

    def get_name(self):
        return f"zbx-{self.virtual_machine.name}"

    def get_absolute_url(self):
        return reverse( "plugins:netbox_zabbix:vmhost", args=[self.pk] )


# ------------------------------------------------------------------------------
# Interface
#

class UseIPChoices(models.IntegerChoices):
    DNS = (0, 'DNS Name')
    IP = (1, 'IP Address')

class MainChoices(models.IntegerChoices):
    NO = (0, 'No')
    YES = (1, 'Yes')


class HostInterface(NetBoxModel):
    class Meta:
        abstract = True
    
    name = models.CharField( max_length=255, blank=False, null=False )
    zabbix_host_id = models.IntegerField( blank=True, null=True )
    zabbix_interface_id = models.IntegerField( blank=True, null=True )
    available = models.IntegerField( default=1 )
    useip = models.IntegerField( choices=UseIPChoices, default=UseIPChoices.IP )
    main = models.IntegerField( choices=MainChoices, default=MainChoices.YES )


class DeviceAgentInterface(HostInterface):
    class Meta:
        verbose_name = "Device Agent Interface"
        verbose_name_plural = "Device Agent Interfaces"
    
    port = models.IntegerField( default=10050 )
    host = models.ForeignKey( to="DeviceHost", on_delete=models.CASCADE, related_name="agent_interfaces" )
    interface = models.OneToOneField( to="dcim.Interface", on_delete=models.CASCADE, related_name="device_interface" )

#class DeviceSNMPv1(HostInterface):
#    class Meta:
#        verbose_name = "Device SNMPv1 Interface"
#        verbose_name_plural = "Device SNMPv1 Interfaces"
#    
#    port = models.IntegerField( default=161 )
#    host = models.OneToOneField( to='DeviceHost', on_delete=models.CASCADE, related_name='snmpv1_interfaces' )
#
#
#class VMAgentInterface(HostInterface):
#    class Meta:
#        verbose_name = "VM Agent Interface"
#        verbose_name_plural = "VM Agent Interfaces"
#
#    port = models.IntegerField( default=10050 )
#    host = models.OneToOneField( to='VMHost', on_delete=models.CASCADE, related_name='agent_interfaces' )
#
#
#class VMSNMPv1(HostInterface):
#    class Meta:
#        verbose_name = "VM SNMPv1 Interface"
#        verbose_name_plural = "VM SNMPv1 Interfaces"
#        
#    port = models.IntegerField( default=161 )
#    host = models.OneToOneField( to='VMHost', on_delete=models.CASCADE, related_name='snmpv1_interfaces' )


from dcim.models import Interface
class AvailableDeviceInterface(Interface):
    class Meta:
        proxy = True