import ckan.plugins.toolkit as toolkit
from ckan.logic.action.update import package_update as ckan_package_update
from ckanext.coat.helpers import extras_dict, is_protected


@toolkit.side_effect_free
def package_update(context, data_dict):
    package = toolkit.get_action("package_show")(context, data_dict)

    # Draft datasets must always be private
    package_state = data_dict.get("state") or package.get("state")
    is_draft = package_state == "draft"
    if is_draft:
        data_dict["private"] = True

    # Protect public active packages from changes, except when switching to private
    # Convert to bool to handle string "True"/"False" from forms
    new_private = toolkit.asbool(data_dict.get("private", False))
    old_private = toolkit.asbool(package.get("private", False))
    is_staying_public = not new_private and not old_private
    if is_staying_public:
        is_protected(package)

    # ckanext-scheming workaround
    base_name = extras_dict(package).get('base_name')
    if base_name:
        data_dict.setdefault('extras', [])
        if 'base_name' not in extras_dict(data_dict):
            data_dict['extras'].append(
                {'key': 'base_name', 'value': base_name},
             )

    # This is required in ckanext-coatcustom, version was missing
    # in data_dict -> required for Datacite DOI metadata
    # see ckanext-coatcustom.plugin.py
    if 'version' in package.keys():
        data_dict['version'] = package['version']

    return ckan_package_update(context, data_dict)
