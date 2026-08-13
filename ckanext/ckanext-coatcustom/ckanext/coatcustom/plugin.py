import json

import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
from ckan.common import config

import ckanext.coat.logic.action.create
import ckanext.coat.logic.action.update
import ckanext.coatcustom.helpers as helpers
import ckanext.coatcustom.logic.action.create
import ckanext.coatcustom.logic.action.update
import ckanext.coatcustom.validators as validators
from ckanext.coat.helpers import extras_dict
from ckanext.coatcustom.views import scheming
from ckanext.doi.interfaces import IDoi


class CoatcustomPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IBlueprint)
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IPackageController, inherit=True)
    plugins.implements(plugins.IActions)
    plugins.implements(plugins.IFacets, inherit=True)
    plugins.implements(plugins.ITemplateHelpers)
    plugins.implements(plugins.IValidators)
    plugins.implements(IDoi, inherit=True)

    # IBlueprint
    def get_blueprint(self):
        return [scheming]

    # IConfigurer

    def update_config(self, config_):
        toolkit.add_template_directory(config_, "templates")
        toolkit.add_public_directory(config_, "public")
        toolkit.add_resource("assets", "coatcustom")

    # IPackageController

    _CITATION_TYPES = {"dataset", "state-variable", "protocol"}

    def after_dataset_show(self, context, pkg_dict):
        if pkg_dict.get("type") not in self._CITATION_TYPES:
            return
        url = config["ckan.site_url"] + "/dataset/" + pkg_dict["name"]
        created = pkg_dict.get("metadata_created", "")
        year = created[:4] if created else ""
        authors = helpers.coatcustom_get_authors_display(pkg_dict)
        pkg_dict["resource_citations"] = (
            authors + ", " if authors else ""
        ) + f"{year}, {pkg_dict['name']}: COAT project data. Available online: {url}"

        # author_email is derived from author: the author select stores the
        # user's email, so show it directly instead of a separately entered value.
        pkg_dict["author_email"] = pkg_dict.get("author", "")

    # IValidators

    def get_validators(self):
        return {name: getattr(validators, name) for name in dir(validators)}

    # IActions

    def get_actions(self):
        return {
            "coat_package_create": ckanext.coat.logic.action.create.package_create,
            "package_create": ckanext.coatcustom.logic.action.create.package_create,
            "coat_package_update": ckanext.coat.logic.action.update.package_update,
            "package_update": ckanext.coatcustom.logic.action.update.package_update,
        }

    # IFacets

    def _facets(self, facets_dict):
        if "groups" in facets_dict:
            del facets_dict["groups"]
        facets_dict["locations"] = toolkit._("Locations")
        facets_dict["scientific_names"] = toolkit._("Scientific names")
        facets_dict["organization"] = toolkit._("Modules")
        facets_dict["topic_category"] = toolkit._("Topic Category")
        return facets_dict

    def dataset_facets(self, facets_dict, package_type):
        return self._facets(facets_dict)

    # ITemplateHelpers

    def get_helpers(self):
        return {name: getattr(helpers, name) for name in dir(helpers)}

    # IDoi

    def build_metadata_dict(self, pkg_dict, metadata_dict, errors):
        # add COAT topic_category as Datacite subject
        topic = pkg_dict.get("topic_category", None)
        if topic:
            metadata_dict["subject"] = topic

        # add dataset version
        metadata_dict["version"] = pkg_dict["version"]

        # modify publisher (defaults to NINA, as the Datacite customer)
        if "publisher" in pkg_dict:
            metadata_dict["publisher"] = pkg_dict["publisher"]

        # bbox coordinates in COAT spatial are 5 lon-lat couples: NW - NE - SE - SW - NW
        # converted to Datacite bbox format, 2 lat-lon couples white space separated: SW - NE
        if "spatial" in extras_dict(pkg_dict):
            coordinates = json.loads(extras_dict(pkg_dict)["spatial"])["coordinates"][0]
            north = coordinates[0][1]
            east = coordinates[2][0]
            south = coordinates[2][1]
            west = coordinates[0][0]
            bbox_datacite = f"{south} {west} {north} {east}"
            metadata_dict["geo_box"] = bbox_datacite

        return metadata_dict, errors

    @staticmethod
    def metadata_to_xml(xml_dict, metadata):
        """
        ..seealso:: ckanext.doi.interfaces.IDoi.metadata_to_xml
        """

        return xml_dict
