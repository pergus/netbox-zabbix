# api/urls.py

from rest_framework.routers import DefaultRouter
from netbox_zabbix.api import views

router = DefaultRouter()

router.register( 'setting',                    views.SettingViewSet )
router.register( 'templates',                  views.TemplateViewSet )
router.register( 'proxy',                      views.ProxyViewSet )
router.register( 'proxy-group',                views.ProxyGroupViewSet )
router.register( 'host-group',                 views.HostGroupViewSet )
router.register( 'tag-mapping',                views.TagMappingViewSet )
router.register( 'inventory-mapping',          views.InventoryMappingViewSet )
router.register( 'device-mapping',             views.DeviceMappingViewSet )
router.register( 'vm-mapping',                 views.VMMappingViewSet )
router.register( 'event-log',                  views.EventLogViewSet )


# Proxy Models
router.register( "unassigned-hosts",            views.UnAssignedHostsViewSet,           basename='unassignedhosts' )
router.register( "unassigned-agent-interfaces", views.UnAssignedAgentInterfacesViewSet, basename='unassignedagentinterfaces' )
router.register( "unassigned-snmp-interfaces",  views.UnAssignedSNMPInterfacesViewSet,  basename='unassignedsnmpinterfaces' )
router.register( "unassigned-host-interfaces",  views.UnAssignedHostInterfacesViewSet,  basename='unassignedhostinterfaces' )
router.register( "unassigned-host-ipaddresses", views.UnAssignedHostIPAddressesViewSet, basename='unassignedhostipaddresses' )


urlpatterns = router.urls
