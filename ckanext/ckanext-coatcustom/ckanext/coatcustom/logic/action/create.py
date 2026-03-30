import ckan.plugins.toolkit as toolkit
import ckanext.coatcustom.helpers as helpers


@toolkit.chained_action
def package_create(coat_package_create, context, data_dict):
    if data_dict.get("__parent", False):
        return coat_package_create(context, data_dict)

    data_dict = helpers.data_dict_with_spatial(context, data_dict)
    return coat_package_create(context, data_dict)
