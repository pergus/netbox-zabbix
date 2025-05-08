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

# If I have a Host object (e.g., host = Host.objects.first()), I can access the
# related Device or VirtualMachine instance directly via the 'content_object' field:
#
# device_or_vm = host.content_object
#
# To do the reverse — that is, get the Host object given a Device or VirtualMachine — 
# I can query the Host model using the content type and object ID like this:
#
# vm = VirtualMachine.objects.first()
# host = Host.objects.get(content_type__model='virtualmachine', object_id=vm.id)
#
# Additionally, the 'zabbix_hosts' related_name allows listing all Host objects 
# associated with a specific ContentType. For example, to get all Host objects 
# with the same content type as the first Host:
#
# host = Host.objects.first()
# host.content_type.zabbix_hosts.all()


class StatusChoices(models.TextChoices):
    ENABLED = 'enabled', 'Enabled'
    DISABLEd = 'disabled', 'Disabled'

class Host(NetBoxModel):
    class Meta:
        verbose_name = "Zabbix Host"
        verbose_name_plural = "Zabbix Hosts"
    
    
    # A generic relation to either a Device or VirtualMachine object.
    # This ForeignKey stores which *type* of object is being referenced (Device or VM).
    # The limit_choices_to ensures only Device and VirtualMachine models are valid targets.
    content_type = models.ForeignKey(
            ContentType,
            on_delete=models.CASCADE,
            limit_choices_to=models.Q( app_label='dcim', model='device') | models.Q(app_label='virtualization', model='virtualmachine') ,
            related_name='zabbix_hosts' # 
    )
    
    # Stores the primary key of the referenced object (Device or VM).
    # default to zero otherwise it breaks the form
    object_id = models.PositiveIntegerField( default=0 )
    
    # Combines content_type and object_id to form a generic relation to the actual object instance.
    # Example: content_object may resolve to a Device or VirtualMachine instance.
    content_object = GenericForeignKey( ct_field='content_type', fk_field='object_id' )
    
    
    zabbix_host_id = models.PositiveIntegerField(unique=True, blank=True, null=True )

    status = models.CharField( max_length=255, choices=StatusChoices.choices, default='enabled' )
    
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

# ------------------------------------------------------------------------------
# Interface
#
"""
USEIP_CHOICES = [
    (0, 'DNS Name'),
    (1, 'IP Address'),
]

MAIN_CHOICES = [
    (0, 'No'),
    (1, 'Yes'),
]


class Interface(NetBoxModel):
    class meta:
        verbose_name = "Host Interface"
        verbose_name_plural = "Hosts Interfaces"

    name = models.CharField( max_length=255 )

    # Reference to the Host
    host = models.ForeignKey( to=Host, on_delete=models.CASCADE, related_name='%(class)s_interfaces' )

    zbx_interface_id = models.IntegerField( blank=True, null=True )
#    zbx_host_id      = models.IntegerField( blank=True, null=True )
    available        = models.IntegerField( default=1 )
    useip            = models.IntegerField( choices=USEIP_CHOICES, default=1 )
    main             = models.IntegerField( choices=MAIN_CHOICES, default=1 )


    content_type = models.ForeignKey(
            ContentType,
            on_delete=models.CASCADE,
            limit_choices_to=models.Q(app_label='dcim', model='interface') | models.Q(app_label='virtualization', model='interface'),
            related_name='zabbix_interfaces'
    )
    object_id = models.PositiveIntegerField( default=0 )
    content_object = GenericForeignKey( ct_field='content_type', fk_field='object_id' )
    

class AgentInterface(Interface):
    class meta:
        verbose_name = "Agent Interface"
        verbose_name_plural = "Agent Interfaces"

    port = models.IntegerField( default=10050 )
"""
"""
host = Host.objects.first()
agent_iface = AgentInterface.objects.create(
    host=host,
    name="eth0-agent",
    useip=1,
    main=1,
    content_type=ContentType.objects.get_for_model(VMInterface), # Use Interface for dcim.
    object_id=netbox_iface.id,
    port=10050
)


# AgentInterface.objects.create( host=h, name="eth0-agent", useip=1, main=1, content_type=ContentType.objects.get_for_model(VMInterface), object_id=vnic.id )

ip = agent_iface.get_ip()
dns = agent_iface.get_dns_name()
"""

USEIP_CHOICES = [
    (0, 'DNS Name'),
    (1, 'IP Address'),
]

MAIN_CHOICES = [
    (0, 'No'),
    (1, 'Yes'),
]


class Interface(NetBoxModel):
    """Abstract base class for Host interfaces linked to NetBox interfaces."""

    class Meta:
        abstract = True

#    host = models.ForeignKey(
#        to='Host',
#        on_delete=models.CASCADE,
#        related_name='%(class)s_interfaces'
#    )

    name = models.CharField( max_length=255 )

    # Whether Zabbix should use IP or DNS for this interface
    useip = models.IntegerField( choices=USEIP_CHOICES, default=1 )
    main = models.IntegerField( choices=MAIN_CHOICES, default=1 )
    available = models.IntegerField( default=1)

    # Link to NetBox Interface (dcim.Interface or virtualization.Interface)
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        limit_choices_to=models.Q( app_label='dcim', model='interface') | models.Q(app_label='virtualization', model='interface' ),
        related_name='%(class)s_linked_interfaces'
    )
    object_id = models.PositiveIntegerField()
    netbox_interface = GenericForeignKey( 'content_type', 'object_id' )

    def get_ip(self):
        return self.netbox_interface.ip_addresses.first()

#    def get_dns_name(self):
#        return self.netbox_interface.dns_name if hasattr( self.netbox_interface, 'dns_name' ) else None
    def get_dns_name(self):
        # Check if the related netbox_interface has a dns_name field
        if hasattr(self.netbox_interface, 'dns_name') and self.netbox_interface.dns_name:
            return self.netbox_interface.dns_name
        
        # If the DNS name is not directly available, try to get it from the primary IP address
        try:
            # Assuming the Host is linked to Device or VM and has a primary IP address
            host = self.host  # The Host instance associated with this interface
            device_or_vm = host.content_object
    
            if device_or_vm:
                # Get the primary IP address (adjust the IP field name as needed)
                primary_ip = device_or_vm.primary_ip if hasattr(device_or_vm, 'primary_ip') else None
                if primary_ip and hasattr(primary_ip, 'dns_name'):
                    return primary_ip.dns_name
        except Exception as e:
            # Log the exception if necessary
            print(f"Error getting DNS name: {e}")
    
        return None
    

class AgentInterface(Interface):
    port = models.IntegerField( default=10050 )
    host = models.ForeignKey(
           to='Host',
           on_delete=models.CASCADE,
           related_name='agent_interfaces'  # Use a specific shorter name
       )
    

class SNMPv1Interface(Interface):
    port = models.IntegerField( default=161 )
    host = models.ForeignKey(
           to='Host',
           on_delete=models.CASCADE,
           related_name='snmpv1_interfaces'  # Use a specific shorter name
       )

class SNMPv2CInterface(Interface):
    port = models.IntegerField( default=161 )
    host = models.ForeignKey(
           to='Host',
           on_delete=models.CASCADE,
           related_name='snmpv2c_interfaces'  # Use a specific shorter name
       )

class SNMPv3Interface(Interface):
    port = models.IntegerField( default=161 )
    security_name = models.CharField( max_length=255 )
    auth_protocol = models.CharField( max_length=255 )
    priv_protocol = models.CharField( max_length=255 )
    host = models.ForeignKey(
           to='Host',
           on_delete=models.CASCADE,
           related_name='snmpv3_interfaces'  # Use a specific shorter name
       )