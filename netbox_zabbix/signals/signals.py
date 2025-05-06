import logging

from django.dispatch import receiver
from django.db.models.signals import pre_save, post_save, pre_delete


from dcim.models import Device
from virtualization.models import VirtualMachine
from django.contrib.contenttypes.models import ContentType
from ..models import ZBXHost

logger = logging.getLogger('netbox.plugins.netbox_zabbix')


#@receiver(pre_save, sender=ZBXConfig)
#def pre_save_zbx_config(instance, **kwargs):
#    logger.info("post_save_zbx_config()...")
#
#@receiver(post_save, sender=ZBXConfig)
#def post_save_zbx_config(instance, **kwargs):
#    pass
#
#@receiver(pre_delete, sender=ZBXConfig)
#def pre_delete_zbx_config(instance, **kwargs):
#    pass



# Signal handler to delete associated ZBXHost instances when a Device or VirtualMachine is deleted.
#
# The ZBXHost model uses a GenericForeignKey to reference either a Device or VirtualMachine.
# Since Django does not cascade deletions across GenericForeignKeys, this signal ensures that
# related ZBXHost records are explicitly removed when their referenced object is deleted.
#
@receiver(pre_delete, sender=Device)
@receiver(pre_delete, sender=VirtualMachine)
def delete_zbxhost(sender, instance, **kwargs):
    content_type = ContentType.objects.get_for_model(instance)
    ZBXHost.objects.filter(content_type=content_type, object_id=instance.pk).delete()


@receiver(pre_delete, sender=ZBXHost)
def zbxhost_pre_delete_cleanup(sender, instance, **kwargs):
    """
    Perform cleanup before a ZBXHost is deleted.
    """
    logger.info(f"Don't forget to create a job that remove the host {instance.content_object.name} in Zabbix")
