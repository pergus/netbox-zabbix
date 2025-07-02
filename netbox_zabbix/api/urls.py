from rest_framework.routers import DefaultRouter
from netbox_zabbix.api import views

router = DefaultRouter()

router.register( 'config',                     views.ConfigViewSet )
router.register( 'templates',                  views.TemplateViewSet )

router.register( 'proxy',                      views.ProxyViewSet )

router.register( 'proxygroups',                views.ProxyGroupViewSet )

router.register( 'hostgroups',                 views.HostGroupViewSet )


# Rename devicezabbixconfig to device-zabbix-config
router.register( 'devicezabbixconfig',         views.DeviceZabbixConfigViewSet )
# Rename vmzabbixconfig to vm-zabbix-config
router.register( 'vmzabbixconfig',             views.VMZabbixConfigViewSet )

router.register( 'available-device-interface', views.AvailableDeviceInterfaceViewSet, basename='availabledeviceinterface' )
router.register( 'available-vm-interface',     views.AvailableVMInterfaceViewSet, basename='availablevminterface' )

# Mappings
router.register( 'tag-mappings',       views.TagMappingViewSet )
router.register( 'inventory-mappings', views.InventoryMappingViewSet )
router.register( 'device-mappings',    views.DeviceMappingViewSet )
router.register( 'vm-mappings',        views.VMMappingViewSet )

# JobLog

router.register( 'joblog',        views.JobLogViewSet )

urlpatterns = router.urls
