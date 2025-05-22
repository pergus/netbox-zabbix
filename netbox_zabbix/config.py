
from netbox_zabbix.models import Config
from netbox_zabbix.logger import logger

class ZabbixConfigNotFound(Exception):
    """Raised when the required Zabbix configuration is not present."""
    pass

def get_config():
    cfg = Config.objects.first()
    if not cfg:
        msg = "Missing Zabbix Configuration"
        logger.error( msg )
        raise ZabbixConfigNotFound( msg )
    return cfg

def get_zabbix_api_endpoint():
    cfg = get_config()
    return cfg.api_endpoint

def get_zabbix_web_address():
    cfg = get_config()
    return cfg.web_address
    
def set_version( version ):
    cfg = get_config()
    cfg.version = version
    cfg.save()

def set_connection( status ):
    cfg = get_config()
    cfg.connection = status
    cfg.save()

def set_last_checked( timestamp ):
    cfg = get_config()
    cfg.last_checked_at = timestamp
    cfg.save()