from rest_framework.routers import DefaultRouter
from netbox_zabbix.api import views

router = DefaultRouter()

router.register( 'config',                     views.ConfigViewSet )
router.register( 'templates',                  views.TemplateViewSet )
router.register( 'devicezabbixconfig',         views.DeviceZabbixConfigViewSet )
router.register( 'vmzabbixconfig',             views.VMZabbixConfigViewSet )
router.register( 'available-device-interface', views.AvailableDeviceInterfaceViewSet, basename='availabledeviceinterface' )

urlpatterns = router.urls
