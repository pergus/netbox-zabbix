
from encodings.punycode import T
from django.contrib.contenttypes.models import ContentType


interface = VMInterface(name=interface_name, virtual_machine=vm)
interface.full_clean()
interface.save()

assigned_object_type_id = ContentType.objects.get(app_label='virtualization', model='vminterface').pk
assigned_object_id = interface.id

mac_address = MACAddress(assigned_object_id=assigned_object_id, assigned_object_type_id=assigned_object_type_id, mac_address="00:50:56:8B:09:C4")

mac_address.full_clean()
mac_address.save()

interface.primary_mac_address = mac_address
interface.full_clean()
interface.save()



