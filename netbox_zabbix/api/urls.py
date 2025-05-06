from rest_framework.routers import DefaultRouter
from netbox_zabbix.api import views

router = DefaultRouter()

router.register( 'config',    views.ConfigViewSet )
router.register( 'templates', views.TemplateViewSet )
router.register( 'hosts',     views.HostViewSet )

urlpatterns = router.urls