# Utility Functions

import logging

from .models import ZBXConfig
from pyzabbix import ZabbixAPI
from dcim.models import Device
from virtualization.models import VirtualMachine

logger = logging.getLogger('netbox.plugins.netbox_zabbix')
#logger.info("netbox_zabbix signals...")



# Get all Zabbix Hostnames
def get_zabbix_hostnames():
    cfg = ZBXConfig.objects.filter(active=True).first()
    
    if not cfg:
        return []
    
    z = ZabbixAPI(cfg.api_address)
    z.login(api_token=cfg.token)

    try:
        hostnames = z.host.get(output=["name"])        
    except Exception as e:
        logger.error(f"Get Zabbix hostnames from {cfg.api_address} failed: {e}")
        return []

    return hostnames


def get_zabbix_only_hostnames():
    zabbix_hostnames = get_zabbix_hostnames()
    netbox_hostnames = set( Device.objects.values_list('name', flat=True) ).union( VirtualMachine.objects.values_list('name', flat=True) )

    return [h for h in zabbix_hostnames if h["name"] not in netbox_hostnames]
