import ckan.plugins.toolkit as toolkit
from ckan.logic.action.delete import package_delete as ckan_package_delete
from ckanext.coat import helpers


@toolkit.side_effect_free
def package_delete(context, data_dict):
    package = toolkit.get_action('package_show')(context, data_dict)
    helpers.is_protected(package)
    return ckan_package_delete(context, data_dict)

