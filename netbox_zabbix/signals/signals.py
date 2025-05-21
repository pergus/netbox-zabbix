from django.db.models.signals import post_delete
from django.dispatch import receiver

from netbox_zabbix.models import DeviceAgentInterface, DeviceSNMPv3Interface, MainChoices

import logging

logger = logging.getLogger('netbox.plugins.netbox_zabbix')


@receiver(post_delete, sender=DeviceAgentInterface)
def ensure_main_exists(sender, instance, **kwargs):
    # If the deleted instance was main, promote another interface
    if instance.main == MainChoices.YES:
        remaining = instance.host.agent_interfaces.exclude( pk=instance.pk )
        fallback = remaining.first()
        if fallback:
            fallback.main = MainChoices.YES
            fallback.save()
            logger.info( f"Promoted interface {fallback.name} to main interface for {fallback.host.get_name()}" )


@receiver(post_delete, sender=DeviceSNMPv3Interface)
def ensure_main_exists(sender, instance, **kwargs):
    # If the deleted instance was main, promote another interface
    if instance.main == MainChoices.YES:
        remaining = instance.host.snmpv3_interfaces.exclude( pk=instance.pk )
        fallback = remaining.first()
        if fallback:
            fallback.main = MainChoices.YES
            fallback.save()
            logger.info( f"Promoted interface {fallback.name} to main interface for {fallback.host.get_name()}" )