from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
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
