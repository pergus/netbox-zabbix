"""
NetBox Zabbix Plugin — NetBox changelog and audit trail management.

Implements manual logging mechanisms for tracking changes made to integrated objects,
ensuring proper audit trails are maintained for compliance and troubleshooting.
"""

# NetBox imports
from core.choices import ObjectChangeActionChoices

# NetBox Zabbix Imports
from netbox_zabbix import models

def changelog_create( obj, user, request_id ):
    """
    Manually log an ObjectChange entry for an object creation in a background job.

    Normally, when objects are created via the NetBox UI, the change log
    (ObjectChange) is automatically created by signals that have access to
    the current HTTP request. However, this code runs in a background job,
    which does not have a live request object, so the signals will not fire.
    To ensure the creation is logged, we manually create an ObjectChange.

    Args:
        obj (models.Model): Object that was created.
        user (User): NetBox user performing the operation.
        request_id (str): Request ID for tracking.
    """

    if user and request_id:
        obj_change = obj.to_objectchange( action=ObjectChangeActionChoices.ACTION_CREATE )
        obj_change.user = user
        obj_change.request_id = request_id
        obj_change.save()


def changelog_update( obj, user, request_id ):
    """
    Manually log an ObjectChange entry for an object update in a background job.

    Normally, when objects are created via the NetBox UI, the change log
    (ObjectChange) is automatically created by signals that have access to
    the current HTTP request. However, this code runs in a background job,
    which does not have a live request object, so the signals will not fire.
    To ensure the creation is logged, we manually create an ObjectChange.

    Args:
        obj (models.Model): Object that was updated.
        user (User): NetBox user performing the operation.
        request_id (str): Request ID for tracking.
    """

    if user and request_id:
        obj_change = obj.to_objectchange( action=ObjectChangeActionChoices.ACTION_UPDATE )
        obj_change.user = user
        obj_change.request_id = request_id
        obj_change.save()

