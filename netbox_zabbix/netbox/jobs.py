"""
NetBox Zabbix Plugin — Job Association Utilities

This module provides utilities for linking Django model instances to
NetBox background jobs, enabling proper tracking and monitoring of
long-running operations.

Main functionality:

- `associate_instance_with_job(job, instance)`: Associates a NetBox job
  with a specific Django model instance, setting the job's content type
  and object ID fields for changelog and audit purposes.

Intended for use with background jobs that create, update, or synchronize
objects between NetBox and Zabbix.
"""


# Django imports
from django.contrib.contenttypes.models import ContentType

def associate_instance_with_job(job, instance):
    """
    Link a Django model instance to a NetBox Job record.
    This sets the job's ``object_type_id`` and ``object_id`` fields to
    reference the given model instance, effectively linking the job to the
    instance in a way compatible with NetBox's changelog and object tracking.
    
    Args:
        job (JobResult): Job record to associate.
        instance (models.Model): Django model instance to link.
    
    Notes:
        - Useful for background jobs creating or updating objects.
    """
    job.object_type_id = ContentType.objects.get_for_model( instance ).pk
    job.object_id = instance.pk


