from django.db import models
from django.urls import reverse
from netbox.models import NetBoxModel
from utilities.choices import ChoiceSet

from .exceptions import ZBXConfigDeleteError

#import logging
#logger = logging.getLogger('netbox.plugins.netbox_zabbix')
#logger.info("netbox_zabbix models...")



#
# Zabbix Configuration
#
class ZBXConfig(NetBoxModel):
    name = models.CharField(max_length=100)
    api_address = models.CharField(max_length=100, default="http://localhost")
    web_address = models.CharField(max_length=100, default="http://localhost")
    version = models.CharField(max_length=100, null=True)
    connection = models.BooleanField(default=False)
    token = models.CharField(max_length=100, default="token")
    active = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Zabbix Configuration"
        ordering = ("name", "active")

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("plugins:netbox_zabbix:zbxconfig", args=[self.pk])


    def delete(self, *args, **kwargs):
        if self.active == True:
            raise ZBXConfigDeleteError("Cannot delete active config, deactivate it before deleting")
        if self.name == 'default':
            raise ZBXConfigDeleteError("Cannot delete default configuration")
        
        super().delete(*args, **kwargs)


#
# Zabbix Templates
#
class ZBXTemplate(NetBoxModel):
    name = models.CharField(max_length=100)
    templateid = models.CharField(max_length=100)
    last_synced = models.DateTimeField()
    marked_for_deletion = models.BooleanField(default=False) 
    
    class Meta:
        verbose_name = "Zabbix Templates"
        verbose_name_plural = "Zabbix Templates"
        ordering = ("name", )

    def __str__(self):
          return self.name
    


#
# Host Settings
#

class ZBXStatus(ChoiceSet):
    key = 'zbxStatus.host'
    
    CHOICES = [
        ('enabled', 'Enabled',   'green'),
        ('disabled', 'Disabled', 'red'),
    ]

class ZBXInterface(ChoiceSet):

    key = 'zbxInterface.host'

    CHOICES = [
        ('agent', 'Agent'),
        ('snmp', 'SNMP'),
    ]


class ZBXHostInterface(NetBoxModel):

    type = models.IntegerField(default=1)
#
# VMs
#

class ZBXVM(NetBoxModel):
    vm = models.ForeignKey(to='virtualization.VirtualMachine', on_delete=models.CASCADE, related_name='zbx')
    # Better name for zbx_host_id
    zbx_host_id = models.CharField(max_length=20, unique=True)
    status = models.CharField(max_length=30, choices=ZBXStatus)
    interface = models.CharField(max_length=30, choices=ZBXInterface) # Remove
    templates = models.ManyToManyField(ZBXTemplate)

    class Meta:
        verbose_name = "Zabbix VMs"
        verbose_name_plural = "Zabbix VMs"
        ordering = ('vm', 'zbx_host_id', 'status', 'interface')
    
    def __str__(self):
        return self.vm.name
    
    def get_absolute_url(self):
        return reverse("plugins:netbox_zabbix:zbxvm", args=[self.pk])

    def get_status_color(self):
        return ZBXStatus.colors.get(self.status)
    

#
# Combined
#

from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey


class ZBXHost(NetBoxModel):

    # Better names of content_type, object_id and content_object

    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        limit_choices_to=models.Q(app_label='dcim', model='device') | models.Q(app_label='virtualization', model='virtualmachine'),
        related_name='zabbix'
    )
    
    object_id = models.PositiveIntegerField(default=0) # default to zero otherwise it breaks the form

    # Device or VM object
    content_object = GenericForeignKey(ct_field='content_type', fk_field='object_id')

    # Better name for zbx_host_id
    zbx_host_id = models.CharField(max_length=20, unique=True)
    status = models.CharField(max_length=30, choices=ZBXStatus)
    interface = models.CharField(max_length=30, choices=ZBXInterface) # Delete!!!
    templates = models.ManyToManyField(ZBXTemplate, blank=True)

    class Meta:
        verbose_name = "Zabbix Host"
        verbose_name_plural = "Zabbix Hosts"

    def __str__(self):
        return f"ZBXHost {self.content_object}"

    def get_absolute_url(self):
        return reverse("plugins:netbox_zabbix:zbxhost", args=[self.pk])

    def get_status_color(self):
        return ZBXStatus.colors.get(self.status)

    #def delete(self, *args, **kwargs):
    #    create zabbix cleanup job
    #    super().delete(*args, **kwargs)


    
class ZBXInterface(NetBoxModel):
    # Should an interface have a name? If so what should it be?


    TYPE_CHOICES = [
        (1, 'Agent'),
        (2, 'SNMP'),
    ]
    
    AVAILABLE_CHOICES = [
        (0, 'Unknown'),
        (1, 'Available'),
        (2, 'Unavailable'),
    ]
    
    USEIP_CHOICES = [
        (0, 'DNS Name'),
        (1, 'IP Address'),
    ]
    
    MAIN_CHOICES = [
        (0, 'No'),
        (1, 'Yes'),
    ]
    
    SNMP_BULK_CHOICES = [
        (0, 'No'),
        (1, 'Yes'),        
    ]
    
    SNMP_VERSION_CHOICES = [
        (1, 'SNMPv1'),
        (2, 'SNMPv2c'),
        (3, 'SNMPv3'),
    ]
    
    SNMP_SECURITY_LEVEL_CHOICES = [
        (0, 'noAuthNoPriv'),
        (1, 'authNoPriv'),
        (2, 'authPriv'),
    ]
    
    SNMP_AUTH_PROTOCOL_CHOICES = [
        (0, 'MD5'),
        (1, 'SHA1'),
        (2, 'SHA224'),
        (3, 'SHA256'),
        (4, 'SHA384'),
        (5, 'SHA512'),
    ]
    
    SNMP_PRIV_PROTOCOL_CHOICES = [
        (0, 'DES'),
        (1, 'AES128'),
        (2, 'AES192'),
        (3, 'AES256'),
        (4, 'AES192C'),
        (5, 'AES256C'),
    ]

    

    # Rename host to zhost or zbxhost...
    host = models.ForeignKey(to=ZBXHost, on_delete=models.CASCADE, related_name='interfaces', blank=True, null=True)

    # ID of the interface in ZBX
    interfaceid = models.IntegerField(blank=True, null=True)
    
    # Availablility of host interface.
    # Possible values:
    #  0 - unknown 
    #  1 - available
    #  2 - unavailable
    available = models.IntegerField(default=1)
    
    # ZBX host id of the host that the interface belongs to
    hostid = models.IntegerField(blank=True, null=True)

    # Interface type
    # Possible values:
    #  1 - Agent
    #  2 - SNMP
    type = models.IntegerField(choices=TYPE_CHOICES, default=1)
    
    # IP address used by the interface. Can be empty if connection is made via DNS.
    ip = models.GenericIPAddressField(blank=True, null=True)

    # DNS name used by the interface. Can be empty if connection is made via IP.
    dns = models.CharField(max_length=256, blank=True, null=True)

    # Port number used by the interface.
    port = models.CharField(max_length=256, default=10050)

    # Whether a connection should be made via IP. 0 - connect using DNS, 1 - connect using IP.
    useip = models.IntegerField(choices=USEIP_CHOICES, default=1)

    # Whether the interface is used as default on the host.
    # Only one interface of some type can be set as default on a host.
    #
    # Possible values:
    #  0 - not default
    #  1 - default
    main = models.IntegerField(choices=MAIN_CHOICES, default=1)

    # SNMP interface version. 
    # Possible values:
    #  1 - SNMPv1 
    #  2 - SNMPv2c
    #  3 - SNMPv3
    snmp_version = models.IntegerField(choices=SNMP_VERSION_CHOICES, default=3, blank=True, null=True)

    # Whether to use bulk SNMP requests.
    # Possible values:
    #  0 - Don't use bulk
    #  1 - Use bulk
    snmp_bulk = models.IntegerField(choices=SNMP_BULK_CHOICES, default=1, blank=True, null=True)

    # SNMP community. Used only by SNMPv1 and SNMPv2 interfaces.
    snmp_community = models.CharField(max_length=256, blank=True, null=True)

    # Max repetition value for native SNMP bulk requests
    snmp_max_repetitions = models.IntegerField(default=10, blank=True, null=True)

    # SNMPv3 security name. Used only by SNMPv3 interfaces.
    snmp_securityname = models.CharField(choices=SNMP_SECURITY_LEVEL_CHOICES, max_length=256, blank=True, null=True)

    # SNMPv3 security level. Used only by SNMPv3 interfaces.
    # Possible values:
    #  0 - noAuthNoPriv
    #  1 - authNoPriv 
    #  2 - authPriv
    snmp_securitylevel = models.IntegerField(default=2, blank=True, null=True)

    # SNMPv3 authentication passphrase. Used only by SNMPv3 interfaces.
    snmp_authpassphrase = models.CharField(default="{$SNMPV3_AUTHPASS}", blank=True, null=True)

    # SNMPv3 privacy passphrase. Used only by SNMPv3 interfaces
    snmp_privpassphrase = models.CharField(default="{$SNMPV3_PRIVPASS}", blank=True, null=True)

    # SNMPv3 authentication protocol. Used only by SNMPv3 interfaces.
    # Possible values:
    #  0 - (default) - MD5;
    #  1 - SHA1;
    #  2 - SHA224;
    #  3 - SHA256;
    #  4 - SHA384;
    #  5 - SHA512.
    snmp_authprotocol = models.IntegerField(choices=SNMP_AUTH_PROTOCOL_CHOICES, default=1, blank=True, null=True)

    # SNMPv3 privacy protocol. Used only by SNMPv3 interfaces.
    # Possible values:
    #  0 - (default) - DES;
    #  1 - AES128;
    #  2 - AES192;
    #  3 - AES256;
    #  4 - AES192C;
    #  5 - AES256C.
    snmp_privprotocol = models.IntegerField(choices=SNMP_PRIV_PROTOCOL_CHOICES, default=1, blank=True, null=True)

    # SNMPv3 context name. Used only by SNMPv3 interfaces.
    snmp_contextname = models.CharField(max_length=256, blank=True, null=True)
    
    class Meta:
        verbose_name = "Zabbix Interface"
        verbose_name_plural = "Zabbix Interfaces"
    
    def __str__(self):
        return f"ZBXInterface {self.id} {self.host.content_object.name}"
