# filterset.py

import django_filters
from django.db.models import Q
from django.contrib.contenttypes.models import ContentType

from dcim.models import Device
from dcim.filtersets import DeviceFilterSet

from virtualization.models import VirtualMachine
from virtualization.filtersets import VirtualMachineFilterSet
from netbox.filtersets import NetBoxModelFilterSet

from netbox_zabbix.models import (
    InterfaceTypeChoices,
    Template,
    Proxy,
    ProxyGroup,
    HostGroup,
    TagMapping,
    InventoryMapping,
    HostConfig,
    AgentInterface,
    SNMPInterface,
    EventLog
)


# ------------------------------------------------------------------------------
# Templates
# ------------------------------------------------------------------------------


class TemplateFilterSet(NetBoxModelFilterSet):
    class Meta:
        model = Template
        fields = [ 'name', 'templateid' ]

    name = django_filters.ModelMultipleChoiceFilter(
            field_name='name',
            to_field_name='name',
            queryset=Template.objects.all(),
            label="Name"
        )

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(
            Q(name__icontains=value) |
            Q(interface_type__icontains=value)
        )


# ------------------------------------------------------------------------------
# Proxy
# ------------------------------------------------------------------------------


class ProxyFilterSet(NetBoxModelFilterSet):
    class Meta:
        model = Proxy
        fields = [ 'name', 'proxyid', 'proxy_groupid']

    name = django_filters.ModelMultipleChoiceFilter(
            field_name='name',
            to_field_name='name',
            queryset=Proxy.objects.all(),
            label="Name"
        )

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(
            Q(name__icontains=value) 
        )


# ------------------------------------------------------------------------------
# Proxy Groups
# ------------------------------------------------------------------------------


class ProxyGroupFilterSet(NetBoxModelFilterSet):
    class Meta:
        model = ProxyGroup
        fields = [ 'name', 'proxy_groupid' ]

    name = django_filters.ModelMultipleChoiceFilter(
            field_name='name',
            to_field_name='name',
            queryset=ProxyGroup.objects.all(),
            label="Name"
        )

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(
            Q(name__icontains=value) 
        )


# ------------------------------------------------------------------------------
# Host Groups
# ------------------------------------------------------------------------------


class HostGroupFilterSet(NetBoxModelFilterSet):
    class Meta:
        model = HostGroup
        fields = [ 'name' ]

    name = django_filters.ModelMultipleChoiceFilter(
            field_name='name',
            to_field_name='name',
            queryset=HostGroup.objects.all(),
            label="Name"
        )

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(
            Q(name__icontains=value)
        )


# ------------------------------------------------------------------------------
# Tag Mapping
# ------------------------------------------------------------------------------


class TagMappingFilterSet(NetBoxModelFilterSet):
    class Meta:
        model = TagMapping
        fields = [ 'object_type' ]

    object_type = django_filters.ModelMultipleChoiceFilter(
            field_name='object_type',
            to_field_name='object_type',
            queryset=TagMapping.objects.all(),
            label="Object type"
        )

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(
            Q(object_type__icontains=value) 
        )


# ------------------------------------------------------------------------------
# Inventory Mapping
# ------------------------------------------------------------------------------


class InventoryMappingFilterSet(NetBoxModelFilterSet):
    class Meta:
        model = InventoryMapping
        fields = [ 'object_type' ]

    object_type = django_filters.ModelMultipleChoiceFilter(
            field_name='object_type',
            to_field_name='object_type',
            queryset=InventoryMapping.objects.all(),
            label="Object type"
        )

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(
            Q(object_type__icontains=value) 
        )



# ------------------------------------------------------------------------------
# Device Mapping
# ------------------------------------------------------------------------------


class DeviceMappingFilterSet(DeviceFilterSet):
    class Meta(DeviceFilterSet.Meta):
        model  = Device
        fields = DeviceFilterSet.Meta.fields

    def search(self, queryset, name, value):
        value = value.strip().lower()
        if not value:
            return queryset
    
        # Match the search value against the human-readable interface type names.
        # Django stores 'interface_type' as an integer in the database, but users search
        # using the display labels (like "Agent" or "SNMP"). Build a map from label -> integer
        # and find all interface_type values whose label contains the search string.
        label_to_value = {label.lower(): v for v, label in InterfaceTypeChoices.choices}
        matched_interface_types = [v for label, v in label_to_value.items() if value in label]
    
        q = Q( name__icontains=value )
    
        if matched_interface_types:
            q |= Q( interface_type__in=matched_interface_types )
    
        q |= Q( templates__name__icontains=value )
        q |= Q( host_groups__name__icontains=value )
        q |= Q( proxy__name__icontains=value )
        q |= Q( proxy_group__name__icontains=value )
    
        return queryset.filter( q ).distinct()


# ------------------------------------------------------------------------------
# VM Mapping
# ------------------------------------------------------------------------------

class VMMappingFilterSet(VirtualMachineFilterSet):
    class Meta(VirtualMachineFilterSet.Meta):
        model  = VirtualMachine
        fields = VirtualMachineFilterSet.Meta.fields

    def search(self, queryset, name, value):
        value = value.strip().lower()
        if not value:
            return queryset
    
        # Match the search value against the human-readable interface type names.
        # Django stores 'interface_type' as an integer in the database, but users search
        # using the display labels (like "Agent" or "SNMP"). Build a map from label -> integer
        # and find all interface_type values whose label contains the search string.
        label_to_value = {label.lower(): v for v, label in InterfaceTypeChoices.choices}
        matched_interface_types = [v for label, v in label_to_value.items() if value in label]
    
        q = Q( name__icontains=value )
    
        if matched_interface_types:
            q |= Q( interface_type__in=matched_interface_types )
    
        q |= Q( templates__name__icontains=value )
        q |= Q( host_groups__name__icontains=value )
        q |= Q( proxy__name__icontains=value )
        q |= Q( proxy_group__name__icontains=value )
    
        return queryset.filter( q ).distinct()


# ------------------------------------------------------------------------------
# Host Configuration
# ------------------------------------------------------------------------------


class HostConfigFilterSet(NetBoxModelFilterSet):
    class Meta:
        model = HostConfig
        fields = (
            'name', 'content_type', 'description',
        )

    def search(self, queryset, name, value):
        value = value.strip()
        if not value:
            return queryset
    
        # Find matching content types by display name (app_label/model name)
        matching_cts = ContentType.objects.filter(
            Q(model__icontains=value)
        ).values_list('id', flat=True)
    
        return queryset.filter(
            Q(name__icontains=value)
            | Q(description__icontains=value)
            | Q(content_type_id__in=matching_cts)
        )


# ------------------------------------------------------------------------------
# Agent Interface
# ------------------------------------------------------------------------------


class AgentInterfaceFilterSet(NetBoxModelFilterSet):
    host_config_id = django_filters.NumberFilter( field_name='host_config__id' )

    class Meta:
        model = AgentInterface
        fields = ['host_config_id']

    def search(self, queryset, name, value):
        value = value.strip().lower()
        if not value:
            return queryset
    
        filtered = [
            obj for obj in queryset
            if (
                value in (obj.name or '').lower()
                or value in (obj.resolved_dns_name or '').lower()
                or value in (obj.interface.name or '').lower()
            )
        ]
        return queryset.model.objects.filter(pk__in=[obj.pk for obj in filtered])

# ------------------------------------------------------------------------------
# SNMP Interface
# ------------------------------------------------------------------------------


class SNMPInterfaceFilterSet(NetBoxModelFilterSet):
    host_config_id = django_filters.NumberFilter( field_name='host_config__id' )

    class Meta:
        model = SNMPInterface
        fields = ['host_config_id']
    
    def search(self, queryset, name, value):
        value = value.strip().lower()
        if not value:
            return queryset
    
        filtered = [
            obj for obj in queryset
            if (
                value in (obj.name or '').lower()
                or value in (obj.resolved_dns_name or '').lower()
                or value in (obj.interface.name or '').lower()
            )
        ]
        return queryset.model.objects.filter(pk__in=[obj.pk for obj in filtered])


# ------------------------------------------------------------------------------
# Event Log
# ------------------------------------------------------------------------------

from django.db.models import CharField
from django.db.models.functions import Cast

class EventLogFilterSet(NetBoxModelFilterSet):
    class Meta:
        model = EventLog
        fields = [ 'name' ]

    name = django_filters.ModelMultipleChoiceFilter(
            field_name='name',
            to_field_name='name',
            queryset=EventLog.objects.all(),
            label="Name"
        )

#    def search(self, queryset, name, value):
#        if not value.strip():
#            return queryset
#        return queryset.filter(
#            Q(name__icontains=value) |
#            Q(job__job_id=value)
#        )
    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
    
        # Annotate job_id as a string so we can search by partial UUID
        queryset = queryset.annotate(
            job_uuid_str=Cast('job__job_id', CharField())
        )
    
        return queryset.filter(
            Q( name__icontains=value ) |
            Q( job__name__icontains=value ) |
            Q( job_uuid_str__icontains=value ) |
            Q( message__icontains=value )
        )

# end

