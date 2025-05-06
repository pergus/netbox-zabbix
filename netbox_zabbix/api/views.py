
from netbox.api.viewsets import NetBoxModelViewSet
from netbox_zabbix.models import ZBXTemplate, ZBXInterface
from netbox_zabbix.api.serializers import ZBXTemplateSerializer, ZBXInterfaceSerializer

class ZBXTemplateViewSet(NetBoxModelViewSet):
    queryset = ZBXTemplate.objects.all()
    serializer_class = ZBXTemplateSerializer

class ZBXInterfaceViewSet(NetBoxModelViewSet):
    queryset = ZBXInterface.objects.all()
    serializer_class = ZBXInterfaceSerializer