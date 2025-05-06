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

class Host(NetBoxModel):
    class Meta:
        verbose_name = "Zabbix Host"
        verbose_name_plural = "Zabbix Hosts"
    
    
    # A generic relation to either a Device or VirtualMachine object.
    # This ForeignKey stores which *type* of object is being referenced (Device or VM).
    # The limit_choices_to ensures only those models are valid targets.
    content_type = models.ForeignKey(
            ContentType,
            on_delete=models.CASCADE,
            limit_choices_to=models.Q(app_label='dcim', model='device') | models.Q(app_label='virtualization', model='virtualmachine'),
            related_name='zabbix'
    )
    
    # Stores the primary key of the referenced object (Device or VM).
    object_id = models.PositiveIntegerField( default=0 ) # default to zero otherwise it breaks the form
    
    # Combines content_type and object_id to form a generic relation to the actual object instance.
    # Example: content_object may resolve to a Device or VirtualMachine instance.
    content_object = GenericForeignKey( ct_field='content_type', fk_field='object_id' )
    
    
    zabbix_host_id = models.PositiveIntegerField(unique=True, blank=True, null=True)

    status = models.CharField( max_length=255, choices=StatusChoices.choices, default='enabled')
    
    templates = models.ManyToManyField( Template, blank=True )

    def __str__(self):
        return f"zbx-{self.content_object.name}"

    def get_name(self):
        return f"zbx-{self.content_object.name}"
    
    def get_absolute_url(self):
        return reverse("plugins:netbox_zabbix:host", args=[self.pk])
    
    def get_status_color(self):
        return self.Status.colors.get(self.status)

    def save(self, *args, **kwargs):
        if self.zabbix_host_id is None:
            last_id = Host.objects.aggregate(models.Max('zabbix_host_id'))['zabbix_host_id__max'] or 0
            self.zabbix_host_id = last_id + 1
        super().save(*args, **kwargs)