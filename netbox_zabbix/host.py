
from django.views.generic import View
from django.shortcuts import render

from django import forms

host_json = {
  "hostid": "10830",
  "proxyid": "0",
  "host": "se-perguslab01x",
  "status": "0",
  "ipmi_authtype": "-1",
  "ipmi_privilege": "2",
  "ipmi_username": "",
  "ipmi_password": "",
  "maintenanceid": "0",
  "maintenance_status": "0",
  "maintenance_type": "0",
  "maintenance_from": "0",
  "name": "se-perguslab01x",
  "flags": "0",
  "templateid": "0",
  "description": "",
  "tls_connect": "2",
  "tls_accept": "2",
  "tls_issuer": "",
  "tls_subject": "",
  "custom_interfaces": "0",
  "uuid": "",
  "vendor_name": "",
  "vendor_version": "",
  "proxy_groupid": "2",
  "monitored_by": "2",
  "inventory_mode": "0",
  "active_available": "0",
  "assigned_proxyid": "4",
  "parentTemplates": [
    {
      "proxyid": "0",
      "host": "AXIS Ubuntu",
      "status": "3",
      "ipmi_authtype": "-1",
      "ipmi_privilege": "2",
      "ipmi_username": "",
      "ipmi_password": "",
      "maintenanceid": "0",
      "maintenance_status": "0",
      "maintenance_type": "0",
      "maintenance_from": "0",
      "name": "AXIS Ubuntu",
      "flags": "0",
      "templateid": "10633",
      "description": "AXIS standard template for a Ubuntu system.",
      "tls_connect": "1",
      "tls_accept": "1",
      "tls_issuer": "",
      "tls_subject": "",
      "tls_psk_identity": "",
      "tls_psk": "",
      "custom_interfaces": "0",
      "uuid": "03dbf335156e4ca1a55b1dbf3c3adf6f",
      "vendor_name": "",
      "vendor_version": "",
      "proxy_groupid": "0",
      "monitored_by": "0",
      "link_type": "0"
    }
  ],
  "groups": [
    {
      "groupid": "83",
      "name": "IT/Server",
      "flags": "0",
      "uuid": "de248845b45f4d279ac362a124e9e442"
    }
  ],
  "inventory": {
    "type": "",
    "type_full": "",
    "name": "se-perguslab01x",
    "alias": "",
    "os": "Ubuntu Linux (64-bit)",
    "os_full": "",
    "os_short": "",
    "serialno_a": "",
    "serialno_b": "",
    "tag": "",
    "asset_tag": "",
    "macaddress_a": "",
    "macaddress_b": "",
    "hardware": "",
    "hardware_full": "",
    "software": "",
    "software_full": "",
    "software_app_a": "",
    "software_app_b": "",
    "software_app_c": "",
    "software_app_d": "",
    "software_app_e": "",
    "contact": "",
    "location": "Lund HQ",
    "location_lat": "55.718460",
    "location_lon": "13.220390",
    "notes": "",
    "chassis": "",
    "model": "",
    "hw_arch": "",
    "vendor": "",
    "contract_number": "",
    "installer_name": "",
    "deployment_status": "",
    "url_a": "",
    "url_b": "",
    "url_c": "",
    "host_networks": "",
    "host_netmask": "",
    "host_router": "",
    "oob_ip": "",
    "oob_netmask": "",
    "oob_router": "",
    "date_hw_purchase": "",
    "date_hw_install": "",
    "date_hw_expiry": "",
    "date_hw_decomm": "",
    "site_address_a": "",
    "site_address_b": "",
    "site_address_c": "",
    "site_city": "",
    "site_state": "",
    "site_country": "",
    "site_zip": "",
    "site_rack": "",
    "site_notes": "",
    "poc_1_name": "",
    "poc_1_email": "",
    "poc_1_phone_a": "",
    "poc_1_phone_b": "",
    "poc_1_cell": "",
    "poc_1_screen": "",
    "poc_1_notes": "",
    "poc_2_name": "",
    "poc_2_email": "",
    "poc_2_phone_a": "",
    "poc_2_phone_b": "",
    "poc_2_cell": "",
    "poc_2_screen": "",
    "poc_2_notes": ""
  },
  "interfaces": [
    {
      "interfaceid": "177",
      "hostid": "10830",
      "main": "1",
      "type": "1",
      "useip": "0",
      "ip": "10.0.2.215",
      "dns": "se-perguslab01x.se.axis.com",
      "port": "10050",
      "available": "0",
      "error": "",
      "errors_from": "0",
      "disable_until": "0",
      "details": []
    },
    {
      "interfaceid": "178",
      "hostid": "10830",
      "main": "1",
      "type": "2",
      "useip": "1",
      "ip": "10.0.2.215",
      "dns": "",
      "port": "161",
      "available": "0",
      "error": "",
      "errors_from": "0",
      "disable_until": "0",
      "details": {
        "version": "3",
        "bulk": "1",
        "max_repetitions": "10",
        "security_level": "authPriv",
        "securityname": "my-snmp-user",
        "auth_protocol": "SHA1",
        "auth_passphrase": "{$SNMPV3_AUTHPASS}",
        "priv_protocol": "AES128",
        "priv_passphrase": "{$SNMPV3_PRIVPASS}"
      }
    }
  ],
  "tags": [
    {
      "tag": "netbox",
      "value": "true",
      "automatic": "0"
    },
    {
      "tag": "site",
      "value": "Lund HQ",
      "automatic": "0"
    }
  ]
}



#class ZabbixHostForm(forms.Form):
#    host = forms.CharField(label='Host', required=True)
#    name = forms.CharField(label='Name', required=False)
#    proxyid = forms.IntegerField(label='Proxy ID', required=False)
#    tls_connect = forms.ChoiceField(choices=[(1, 'PSK'), (2, 'Certificate')], required=False)
#    tls_accept = forms.ChoiceField(choices=[(1, 'PSK'), (2, 'Certificate')], required=False)
#    description = forms.CharField(widget=forms.Textarea, required=False)


def create_dynamic_form(data):
    class DynamicZabbixHostForm(forms.Form):
        pass

    for key, value in data.items():
        if isinstance(value, list) or isinstance(value, dict):
            continue  # skip nested structures

        if key in {"tls_connect", "tls_accept"}:
            field = forms.ChoiceField(
                choices=[(1, 'PSK'), (2, 'Certificate')],
                required=False,
                label=key.replace('_', ' ').capitalize()
            )
        elif key.endswith("id") or value.isdigit():
            field = forms.IntegerField(required=False, label=key.replace('_', ' ').capitalize())
        else:
            field = forms.CharField(required=False, label=key.replace('_', ' ').capitalize())

        DynamicZabbixHostForm.base_fields[key] = field

    return DynamicZabbixHostForm


class HostView(View):
    template_name = 'netbox_zabbix/host.html'

    def get(self, request):
        DynamicForm = create_dynamic_form( host_json )
        form = DynamicForm( initial=host_json )

        return render(request, self.template_name, {
                    'form': form,
                    'host': host_json,
                    'interfaces': host_json.get('interfaces', []),
                })


    def post(self, request):
        DynamicForm = create_dynamic_form(host_json)
        form = DynamicForm(request.POST)
        if form.is_valid():
            # Update host_json in-place
            for field, value in form.cleaned_data.items():
                if field in host_json:
                    host_json[field] = str(value) if value is not None else ""
    
            return render(request, self.template_name, {
                'form': form,
                'host': host_json,
                'interfaces': host_json.get('interfaces', []),
                'message': 'Host data updated successfully.',
            })
    
        return render(request, self.template_name, {
            'form': form,
            'host': host_json,
            'interfaces': host_json.get('interfaces', []),
            'message': 'Invalid data submitted.',
        })