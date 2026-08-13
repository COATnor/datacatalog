import ckan.plugins.toolkit as toolkit

import ckanext.coatcustom.helpers as helpers


@toolkit.chained_action
def package_update(coat_package_update, context, data_dict):
    if data_dict.get("__parent", False):
        return coat_package_update(context, data_dict)

    old_location = None
    if data_dict.get("id"):
        try:
            old = toolkit.get_action("package_show")(
                {**context, "ignore_auth": True, "for_update": True},
                {"id": data_dict["id"]},
            )
            old_location = old.get("location")
        except toolkit.ObjectNotFound:
            pass

    data_dict = helpers.data_dict_with_spatial(context, data_dict, old_location)

    # Remove extra DOI keys
    data_dict = {k: v for k, v in data_dict.items() if not k.startswith("doi")}

    return coat_package_update(context, data_dict)
