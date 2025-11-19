 Suggested New Names for Functions and Methods

  core/integration.py

  | Old Name                                          | New Name                                |
  |---------------------------------------------------|-----------------------------------------|
X  | get_zabbix_inventory_for_object(obj)              | generate_zabbix_inventory(obj)          |
X  | get_zabbix_tags_for_object(obj)                   | generate_zabbix_tags(obj)               |
X  | compare_host_config_with_zabbix_host(host_config) | compare_host_configuration(host_config) |

  zabbix/api.py

  | Old Name                   | New Name                          |
  |----------------------------|-----------------------------------|
  | normalize_interface(iface) | normalize_zabbix_interface(iface) |

  zabbix/hosts.py

  | Old Name                                             | New Name                                          |
  |------------------------------------------------------|---------------------------------------------------|
 X | create_host_in_zabbix(host_config)                   | create_zabbix_host(host_config)                   |
 X | update_host_in_zabbix(host_config, user, request_id) | update_zabbix_host(host_config, user, request_id) |
 X | hard_delete_zabbix_host(host_config)                 | delete_zabbix_host_permanently(host_config)       |
 X | soft_delete_zabbix_host(host_config)                 | delete_zabbix_host_softly(host_config)            |

  zabbix/interfaces.py

  | Old Name                                            | New Name|
  |-----------------------------------------------------|------------------------------------------------------------|
  | link_interface_in_zabbix(interface_config)          | link_zabbix_interface(interface_config)|
  | link_missing_interface(host_config, interface_data) | link_missing_zabbix_interface(host_config,interface_data) |

  zabbix/validation.py

  | Old Name                                                                | New Name |
  |-------------------------------------------------------------------------|----------------------------------------------------------------------|
  | validate_template_compatibility(template, interface_type)               | check_template_compatibility(template, interface_type)               |
  | validate_interface_template_compatibility(interface_type, template_ids) | check_interface_template_compatibility(interface_type, template_ids) |
  | validate_zabbix_host(zabbix_host, host)                                 | validate_zabbix_host_data(zabbix_host, host)                         |

  netbox/models.py

  | Old Name                            | New Name                                   |
  |-------------------------------------|--------------------------------------------|
X  | create_custom_field(name, defaults) | create_netbox_custom_field(name, defaults) |
X  | find_ip_address(address)            | lookup_ip_address(address)                 |

  netbox/changelog.py

  | Old Name                                           | New Name
  |
  |----------------------------------------------------|------------------------------------------------------
  |
X  | changelog_create(instance, user, request_id, data) | log_creation_event(instance, user, request_id, data) |
X  | changelog_update(instance, user, request_id, data) | log_update_event(instance, user, request_id, data) |

  netbox/jobs.py

  | Old Name                                   | New Name                                |
  |--------------------------------------------|-----------------------------------------|
  | associate_instance_with_job(job, instance) | associate_model_with_job(job, instance) |

  mapping/resolver.py

  | Old Name                                                           | New Name
                                       |
  |--------------------------------------------------------------------|---------------------------------------------------------------------------|
  | resolve_mapping(obj, interface_model, mapping_model, mapping_name) | resolve_device_mapping(obj,interface_model, mapping_model, mapping_name) |
  | resolve_device_mapping(obj, interface_model)                       | resolve_device_to_zabbix_mapping(obj,interface_model)                    |
  | resolve_vm_mapping(obj, interface_model)                           | resolve_vm_to_zabbix_mapping(obj,interface_model)                        |

  mapping/application.py

  | Old Name                                                    | New Name |
  |-------------------------------------------------------------|------------------------------------------------------------------|
X  | apply_mapping_to_config(host_config, mapping, monitored_by) | apply_mapping_to_host_config(host_config mapping, monitored_by) |

  provisioning/handler.py

  | Old Name                   | New Name                       |
  |----------------------------|--------------------------------|
  | provision_zabbix_host(ctx) | provision_new_zabbix_host(ctx) |

  importing/handler.py

  | Old Name                 | New Name                         |
  |--------------------------|----------------------------------|
  | import_zabbix_host(ctx)  | import_existing_zabbix_host(ctx) |
  | import_zabbix_settings() | import_zabbix_configuration()    |

  helpers.py

  | Old Name                                                              | New Name |
  |-----------------------------------------------------------------------|---------------------------------------------------------------------------|
  | resolve_field_path(obj, path)                                         | resolve_nested_attribute(obj,path)                                       |
x  | compute_interface_type(items)                                         | determine_interface_type(items) |
  | collect_template_ids(template, visited=None)                          | gather_template_hierarchy(template, visited=None)                         |
  | get_template_dependencies(templateid)                                 |fetch_template_dependencies(templateid)                                   |
  | populate_templates_with_interface_type()                              |enrich_templates_with_interface_types()                                   |
  | populate_templates_with_dependencies()                                |enrich_templates_with_dependencies()                                      |
  | compare_json(obj_a, obj_b, mode="overwrite")                          | compare_json_structures(obj_a,obj_b, mode="overwrite")                   |
  | normalize_host(zabbix_host, payload_template)                         | normalize_zabbix_host(zabbix_host,payload_template)                      |
  | preprocess_host(host, template)                                       | prepare_host_for_comparison(host,template)                               |
  | create_host_config(obj)                                               | initialize_host_config(obj)
                                          |
  | create_zabbix_interface(host_config, interface_data, interface_model) | initialize_zabbix_interface(host_config, interface_data, interface_model) |
  | save_host_config(host_config)                                         | persist_host_config(host_config)
                                          |
  | get_tags(obj, existing_tags=None)                                     | generate_object_tags(obj,existing_tags=None)                             |
  | payload(host_config, for_update=False, pre_data=None)                 | build_zabbix_payload(host_config,for_update=False, pre_data=None)        |
