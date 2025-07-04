from django.db.models.signals import post_delete, pre_delete
from django.dispatch import receiver

from netbox_zabbix.models import DeviceAgentInterface, DeviceSNMPv3Interface, DeviceZabbixConfig, MainChoices

import logging
from netbox_zabbix.jobs import DeleteZabbixHost


logger = logging.getLogger('netbox.plugins.netbox_zabbix')

#
# Add singal handler for rename & delete...
#


@receiver(post_delete, sender=DeviceAgentInterface)
def promot_agent_interface_to_main(sender, instance, **kwargs):
    # If the deleted instance was main, promote another interface
    if instance.main == MainChoices.YES:
        remaining = instance.host.agent_interfaces.exclude( pk=instance.pk )
        fallback = remaining.first()
        if fallback:
            fallback.main = MainChoices.YES
            fallback.save()
            logger.info( f"Promoted interface {fallback.name} to main interface for {fallback.host.get_name()}" )


@receiver(post_delete, sender=DeviceSNMPv3Interface)
def promot_snmpv3_interface_to_main(sender, instance, **kwargs):
    # If the deleted instance was main, promote another interface
    if instance.main == MainChoices.YES:
        remaining = instance.host.snmpv3_interfaces.exclude( pk=instance.pk )
        fallback = remaining.first()
        if fallback:
            fallback.main = MainChoices.YES
            fallback.save()
            logger.info( f"Promoted interface {fallback.name} to main interface for {fallback.host.get_name()}" )


@receiver(pre_delete, sender=DeviceZabbixConfig)
def delete_zabbix_device_host(sender, instance, **kwargs):
    logger.info( f"delete zabbix host {instance.device.name}" )

    try:
        DeleteZabbixHost.run_job( hostid=instance.hostid )
    except Exception as e:
        raise e
    
    
