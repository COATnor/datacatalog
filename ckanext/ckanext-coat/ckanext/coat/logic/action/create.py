import re
import string

import ckan.plugins.toolkit as toolkit
from ckan.logic.action.create import package_create as ckan_package_create

from ckanext.coat.helpers import extras_dict, is_sysadmin

allowed_characters = string.ascii_lowercase + string.digits + "-_"


@toolkit.side_effect_free
def package_create(context, data_dict):
    # parent dataset
    # https://github.com/aptivate/ckanext-datasetversions/issues/10
    if data_dict.get("__parent", False):
        return ckan_package_create(context, data_dict)

    # Identity is managed internally (sysadmins may override); divergence is rejected, not adjusted.
    sysadmin = is_sysadmin(context)

    # set base_name extra field, by mimicking slug-field
    submitted_base = extras_dict(data_dict).get("base_name")
    if sysadmin and submitted_base:
        base_name = submitted_base
    else:
        slug = "".join(
            character if character in allowed_characters else "-"
            for character in data_dict.get("title", "").lower()
        )
        base_name = re.sub(r"-+", "-", slug).strip("-")

    data_dict["extras"] = [e for e in data_dict.get("extras") or [] if e.get("key") != "base_name"]
    data_dict["extras"].append({"key": "base_name", "value": base_name})

    # set version. Must stay numeric for everyone: Solr indexes it as a
    # number and rejects anything else at index time.
    version = data_dict.get("version", "")
    if not version:
        version = "1"
    elif not str(version).isdigit():
        raise toolkit.ValidationError({"version": ["Version must be a number"]})
    data_dict["version"] = str(version)

    # the name always follows base_name and version
    expected_name = base_name + "_v" + data_dict["version"]
    submitted_name = data_dict.get("name")
    if submitted_name and submitted_name != expected_name and not sysadmin:
        raise toolkit.ValidationError(
            {"name": ["Dataset name is managed internally and must match base name and version"]}
        )
    if not sysadmin or not submitted_name:
        data_dict["name"] = expected_name

    # create package and version
    package = ckan_package_create(context, data_dict)
    toolkit.get_action("dataset_version_create")(
        context,
        {
            "id": package["id"],
            "base_name": base_name,
            "owner_org": data_dict["owner_org"],
            "type": data_dict["type"],
        },
    )

    return package
