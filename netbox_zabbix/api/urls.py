from rest_framework.routers import DefaultRouter
from netbox_zabbix.api import views

router = DefaultRouter()

router.register( 'config',                     views.ConfigViewSet )
router.register( 'templates',                  views.TemplateViewSet )

router.register( 'proxy',                      views.ProxyViewSet )

router.register( 'proxy-groups',                views.ProxyGroupViewSet )

router.register( 'host-groups',                 views.HostGroupViewSet )


# Rename devicezabbixconfig to device-zabbix-config
router.register( 'device-zabbix-config',         views.DeviceZabbixConfigViewSet )
# Rename vmzabbixconfig to vm-zabbix-config
router.register( 'vm-zabbix-config',             views.VMZabbixConfigViewSet )

router.register( 'available-device-interface', views.AvailableDeviceInterfaceViewSet, basename='availabledeviceinterface' )
router.register( 'available-vm-interface',     views.AvailableVMInterfaceViewSet, basename='availablevminterface' )

# Mappings
router.register( 'tag-mappings',       views.TagMappingViewSet )
router.register( 'inventory-mappings', views.InventoryMappingViewSet )
router.register( 'device-mappings',    views.DeviceMappingViewSet )
router.register( 'vm-mappings',        views.VMMappingViewSet )

# EventLog

router.register( 'event-log', views.EventLogViewSet )

urlpatterns = router.urls
