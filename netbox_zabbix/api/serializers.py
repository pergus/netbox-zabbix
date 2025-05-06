from rest_framework import serializers
from netbox.api.serializers import NetBoxModelSerializer


from ..models import ZBXConfig, ZBXTemplate, ZBXVM, ZBXInterface

class ZBXConfigSerializer(NetBoxModelSerializer):
    class Meta:
        model = ZBXConfig
        fields = ( "name", "api_address", "web_address", "version", "connection", "token", "active" )


class ZBXTemplateSerializer(NetBoxModelSerializer):
    class Meta:
        model = ZBXTemplate
        fields = ("name", "display", "id", "templateid", "last_synced", "marked_for_deletion" )
    
    def get_display(self, obj):
        return str(obj.name) 
    

class ZBXVMSerializer(NetBoxModelSerializer):
    class Meta:
        model = ZBXVM
        fields = ('vm', 'zbx_host_id', 'status', 'interface', 'templates')


#
# Combined
#

from django.contrib.contenttypes.models import ContentType
from ..models import ZBXHost


class ZBXHostSerializer(NetBoxModelSerializer):
    content_type = serializers.SlugRelatedField(
        slug_field='model',
        queryset=ContentType.objects.all()
    )
    templates = ZBXTemplateSerializer(many=True, read_only=True)
    associated_object = serializers.SerializerMethodField()

    class Meta:
        model = ZBXHost
        fields = (
            'id',
            'content_type',
            'object_id',
            'associated_object',
            'zbx_host_id',
            'status',
            'interface',
            'templates',
        )

    def get_associated_object(self, obj):
        try:
            return str(obj.associated_object)
        except Exception:
            return None
        


class ZBXInterfaceSerializer(NetBoxModelSerializer):
    class Meta:
        model = ZBXInterface
        fields = '__all__'
#        fields = ('ip', 'dns', 'port', 'useip', 'main', 'type',
#                  'snmp_version',
#                  'snmp_community',
#                  'snmp_max_repetitions',
#                  'snmp_contextname',
#                  'snmp_securityname',
#                  'snmp_securitylevel',
#                  'snmp_authprotocol',
#                  'snmp_authpassphrase',
#                  'snmp_privprotocol',            
#                  'snmp_privpassphrase',
#                  'snmp_bulk')
