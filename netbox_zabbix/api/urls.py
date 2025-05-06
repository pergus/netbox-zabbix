from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()

router.register('zbxtemplates', views.ZBXTemplateViewSet)
router.register('zbxinterfaces', views.ZBXInterfaceViewSet)

urlpatterns = router.urls