from rest_framework.routers import DefaultRouter
from netbox_zabbix.api import views

router = DefaultRouter()

router.register( 'config',                     views.ConfigViewSet )
router.register( 'templates',                  views.TemplateViewSet )
router.register( 'template-mappings',          views.TemplateMappingViewSet )

router.register( 'proxy',                      views.ProxyViewSet )
router.register( 'proxy-mappings',             views.ProxyMappingViewSet )

router.register( 'proxygroups',                views.ProxyGroupViewSet )
router.register( 'proxygroup-mappings',        views.ProxyGroupMappingViewSet )

router.register( 'hostgroups',                 views.HostGroupViewSet )
router.register( 'hostgroup-mappings',         views.HostGroupMappingViewSet )

router.register( 'devicezabbixconfig',         views.DeviceZabbixConfigViewSet )
router.register( 'vmzabbixconfig',             views.VMZabbixConfigViewSet )
router.register( 'available-device-interface', views.AvailableDeviceInterfaceViewSet, basename='availabledeviceinterface' )
router.register( 'available-vm-interface',     views.AvailableVMInterfaceViewSet, basename='availablevminterface' )

urlpatterns = router.urls
