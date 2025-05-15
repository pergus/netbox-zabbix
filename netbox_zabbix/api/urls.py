from rest_framework.routers import DefaultRouter
from netbox_zabbix.api import views

router = DefaultRouter()

router.register( 'config',                   views.ConfigViewSet )
router.register( 'templates',                views.TemplateViewSet )
router.register( 'devicehost',               views.DeviceHostViewSet )
router.register( 'vmhost',                   views.VMHostViewSet )
router.register( 'availabledeviceinterface', views.AvailableDeviceInterfaceViewSet, basename='availabledeviceinterface' )

urlpatterns = router.urls
