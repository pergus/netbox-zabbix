"""
NetBox Zabbix Plugin — Template Processing and Validation

This module implements logic for working with Zabbix templates as imported
into NetBox. It includes functionality for:

- Computing required interface types for templates based on their Zabbix items
- Collecting full parent/ancestor template chains
- Resolving template dependencies through trigger inheritance
- Populating NetBox Template objects with:
    * Computed interface types
    * Dependency relationships
- Validating template selections for:
    * Dependency completeness
    * Inheritance conflicts
    * Interface compatibility (Agent, SNMP, Any)

These utilities support template import, validation, and host provisioning
operations across the plugin, ensuring template sets are internally consistent
and compatible with the host’s interface types.
"""

# NetBox Zabbix Imports
from netbox_zabbix import models
from netbox_zabbix.zabbix import api as zapi
from netbox_zabbix.logger import logger


# ------------------------------------------------------------------------------
# Internal Helper Functions
# ------------------------------------------------------------------------------


def compute_interface_type(items):
    """
    Determine the Zabbix interface type based on item types.
    
    Agent types (0) → Agent
    SNMPv3 types (20) → SNMP
    Mixed or empty → Any
    
    Args:
        items (list[dict]): List of Zabbix item dictionaries.
    
    Returns:
        InterfaceTypeChoices: Agent, SNMP, or Any
    """
    required = set()

    for item in items:
        item_type = int( item.get( "type", -1 ) )

        # Zabbix agent types
        if item_type == 0:
            required.add( models.InterfaceTypeChoices.Agent )

        # Simplified SNMPv3 detection since we treat all SNMP agents as SNMPv3
        elif item_type == 20:
            required.add( models.InterfaceTypeChoices.SNMP )

    if not required:
        return models.InterfaceTypeChoices.Any

    # If both types present, default to Any
    if len( required ) > 1:
        return models.InterfaceTypeChoices.Any

    return required.pop()


def collect_template_ids(template, visited=None):
    """
    Recursively collect template IDs including all parent templates.
    
    Args:
        template: Template instance.
        visited (set, optional): IDs already visited.
    
    Returns:
        set[int]: Set of template IDs including parents.
    """
    if visited is None:
        visited = set()
    if template.id in visited:
        return set()
    visited.add( template.id )

    ids = {template.templateid}
    for parent in template.parents.all():
        ids |= collect_template_ids( parent, visited )
    return ids


def get_template_dependencies(templateid):
    """
    Retrieve Zabbix template IDs that the given template depends on.
    
    Args:
        templateid (int): Zabbix template ID.
    
    Returns:
        list[int]: List of dependent template IDs, excluding the input template.
    """

    # Fetch triggers for the template, including their dependencies
    try:
        triggers = zapi.get_triggers( [ templateid ] )
    except:
        raise

    deps = []
    for trig in triggers:
        for dep in trig.get( "dependencies", [] ):
            dep_triggerid = dep["triggerid"]

            try:
                dep_trigger = zapi.get_trigger( dep_triggerid )[0]
            except:
                raise

            for host in dep_trigger.get("hosts", []):
                dep_templateid = host["hostid"]
                if int( dep_templateid ) != int( templateid ):  # exclude the original template
                    deps.append( int( dep_templateid ) )

    return deps


def populate_templates_with_interface_type():
    """
    Populate all Template objects with their computed interface type
    based on associated Zabbix items.
    """
    # This function is called by import template to add the interface type for
    # each template in the database.
    
    # Fetch ALL items for ALL templates in one call
    all_template_ids = list( models.Template.objects.values_list( "templateid", flat=True ) )

    try:
        all_items = zapi.get_item_types( all_template_ids )
    except:
        raise

    # Group items by templateid
    items_by_template = {}
    for item in all_items:
        tid = item["hostid"] # hostid is the templateid in our case.
        items_by_template.setdefault( tid, [] ).append( item )


    # Calculate and store the interface type for each template
    for template in models.Template.objects.all():
        all_ids = collect_template_ids( template )

        # Collect items for this template and all its parents
        items = []
        for tid in all_ids:
            items.extend( items_by_template.get( tid, [] ) )

        template.interface_type = compute_interface_type( items )
        template.save()


def populate_templates_with_dependencies():
    """
    Populate all Template objects with dependencies based on triggers
    retrieved from Zabbix.
    """
    # This function is called by import template to add dependencies for
    # each template in the database.
    
    for template in models.Template.objects.all():
        try:
            # Get dependent template IDs from triggers
            dependent_template_ids = get_template_dependencies(template.templateid)

            # Resolve Template objects (exclude missing templates)
            dependent_templates = models.Template.objects.filter(templateid__in=dependent_template_ids)

            # Set the dependencies for this template
            template.dependencies.set(dependent_templates)

        except Exception as e:
            logger.error(f"Failed to populate dependencies for template {template.name} ({template.templateid}): {e}")


# ------------------------------------------------------------------------------
# Interface Functions
# ------------------------------------------------------------------------------


def validate_templates(templateids: list):
    """
    Validate that selected templates can be combined without conflicts
    and all dependencies are included.
    
    Args:
        templateids (list[int]): List of template IDs to validate.
    
    Returns:
        bool: True if valid, raises Exception otherwise.
    """

    seen = {}
    template_objects = models.Template.objects.filter( templateid__in=templateids )

    def get_all_parents(template, visited=None):
        """Recursively collect all parents of a template."""
        if visited is None:
            visited = set()
        if template.id in visited:
            return set()
        visited.add( template.id )

        parents = set(template.parents.all())
        for parent in template.parents.all():
            parents |= get_all_parents( parent, visited )
        return parents

    def get_all_dependencies(template, visited=None):
        """Recursively collect all dependencies of a template."""
        if visited is None:
            visited = set()
        if template.id in visited:
            return set()
        visited.add( template.id )

        deps = set( template.dependencies.all() )
        for dep in template.dependencies.all():
            deps |= get_all_dependencies( dep, visited )
        return deps

    for template in template_objects:
        # Check for conflicts through parent inheritance
        inherited_templates = {template} | get_all_parents( template )
        for inherited_template in inherited_templates:
            if inherited_template.id in seen:
                raise Exception(
                    f"Conflict: '{template.name}' and "
                    f"'{seen[inherited_template.id].name}' both include "
                    f"'{inherited_template.name}'"
                )
            seen[inherited_template.id] = template

        # Check for missing dependencies (recursive)
        for dependent_template in get_all_dependencies( template ):
            if dependent_template.templateid not in templateids:
                raise Exception(
                    f"Missing dependency: '{template.name}' depends on "
                    f"'{dependent_template.name}', which is not included."
                )

    return True


def validate_template_interface(templateids: list, interface_type):
    """
    Validate that templates are compatible with a specified interface type.
    
    Args:
        templateids (list[int]): List of template IDs.
        interface_type (InterfaceTypeChoices): Interface type to validate.
    
    Returns:
        bool: True if all templates are compatible, raises Exception otherwise.
    """

    template_objects = models.Template.objects.filter( templateid__in=templateids )

    def get_all_parents(template, visited=None):
        """Recursively collect all parents of a template."""
        if visited is None:
            visited = set()
        if template.id in visited:
            return set()
        visited.add( template.id )

        parents = set( template.parents.all() )
        for parent in template.parents.all():
            parents |= get_all_parents( parent, visited )
        return parents

    def get_all_dependencies(template, visited=None):
        """Recursively collect all dependencies of a template."""
        
        if visited is None:
            visited = set()
        
        if template.id in visited:
            return set()
        
        visited.add( template.id )

        deps = set( template.dependencies.all() )
        for dep in template.dependencies.all():
            deps |= get_all_dependencies( dep, visited )
        
        return deps

    def is_interface_compatible(template_iftype, target_iftype):
        """Check if a template interface type is compatible with target type."""
        
        if target_iftype == models.InterfaceTypeChoices.Any:
            return True
        
        if template_iftype == models.InterfaceTypeChoices.Any:
            return True
        
        return template_iftype == target_iftype

    for template in template_objects:
        all_related = {template} | get_all_parents(template) | get_all_dependencies(template)
        for related_template in all_related:
            if not is_interface_compatible( related_template.interface_type, interface_type ):
                raise Exception(
                    f"Interface type mismatch: '{related_template.name}' "
                    f"requires {models.InterfaceTypeChoices(related_template.interface_type).label}, "
                    f"but target is {models.InterfaceTypeChoices(interface_type).label}."
                )

    return True


def validate_templates_and_interface(templateids: list, interface_type=models.InterfaceTypeChoices.Any):
    """
    Validate template combination and interface compatibility.
    
    Args:
        templateids (list[int]): Template IDs to validate.
        interface_type (InterfaceTypeChoices, optional): Target interface type.
    
    Returns:
        bool: True if valid, raises Exception otherwise.
    """
    validate_templates( templateids )
    validate_template_interface( templateids, interface_type )
    return True


def is_valid_interface(host_config, interface_type=models.InterfaceTypeChoices.Any):
    """
    Check if a host has a valid interface compatible with assigned templates.
    
    Args:
        host_config: HostConfig instance.
        interface_type (InterfaceTypeChoices, optional): Interface type to validate.
    
    Returns:
        bool: True if a valid interface exists.
    
    Raises:
        ValueError: If no templates are assigned.
    """
    if not host_config.templates.exists():
        raise ValueError( f"HostConfig '{host_config}' has no templates assigned." )

    template_ids = list( host_config.templates.values_list( "templateid", flat=True ) )

    # Validate templates and interface compatibility
    validate_templates_and_interface( template_ids, interface_type )
    
    return True
