"""
NetBox Zabbix Plugin — API URL Router

This module defines REST API endpoints for the NetBox Zabbix plugin.
It uses Django REST Framework's DefaultRouter to register viewsets
for Zabbix settings, templates, proxies, host groups, mappings,
interfaces, and event logs. Additional endpoints provide access to
unassigned objects for administrative tasks.
"""

# Third-party imports
from rest_framework.routers import DefaultRouter

# NetBox Zabbix imports
from netbox_zabbix.api import views

# Initialize DRF router
router = DefaultRouter()

# NetBox Zabbix models
router.register( 'setting',           views.SettingViewSet )
router.register( 'templates',         views.TemplateViewSet )
router.register( 'proxy',             views.ProxyViewSet )
router.register( 'proxy-group',       views.ProxyGroupViewSet )
router.register( 'host-group',        views.HostGroupViewSet )
router.register( 'tag-mapping',       views.TagMappingViewSet )
router.register( 'inventory-mapping', views.InventoryMappingViewSet )
router.register( 'device-mapping',    views.DeviceMappingViewSet )
router.register( 'vm-mapping',        views.VMMappingViewSet )
router.register( 'host-config',       views.HostConfigViewSet )
router.register( 'agent-interface',   views.AgentInterfaceViewSet )
router.register( 'snmp-interface',    views.SNMPInterfaceViewSet )
router.register( 'event-log',         views.EventLogViewSet )
router.register( 'maintenance',       views.MaintenanceViewSet )


router.register("host-mapping",       views.HostMappingViewSet, basename='host-mapping' )


# Proxy Models
router.register( "unassigned-hosts",            views.UnAssignedHostsViewSet,           basename='unassignedhosts' )
router.register( "unassigned-agent-interfaces", views.UnAssignedAgentInterfacesViewSet, basename='unassignedagentinterfaces' )
router.register( "unassigned-snmp-interfaces",  views.UnAssignedSNMPInterfacesViewSet,  basename='unassignedsnmpinterfaces' )
router.register( "unassigned-host-interfaces",  views.UnAssignedHostInterfacesViewSet,  basename='unassignedhostinterfaces' )
router.register( "unassigned-host-ipaddresses", views.UnAssignedHostIPAddressesViewSet, basename='unassignedhostipaddresses' )


# Expose router URLs
urlpatterns = router.urls
