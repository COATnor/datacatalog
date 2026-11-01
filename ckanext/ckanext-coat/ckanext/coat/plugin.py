import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
from ckan.common import config, g, login_user, request
from ckan.config.declaration import Declaration, Key
from ckan.lib.api_token import get_user_from_token

import ckanext.coat.logic.action.create
import ckanext.coat.logic.action.delete
import ckanext.coat.logic.action.get
import ckanext.coat.logic.action.update
import ckanext.coat.logic.validators as validators
from ckanext.coat import blueprint, helpers


class CoatPlugin(plugins.SingletonPlugin, toolkit.DefaultDatasetForm):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IActions)
    plugins.implements(plugins.IResourceController, inherit=True)
    plugins.implements(plugins.IBlueprint, inherit=True)
    plugins.implements(plugins.ITemplateHelpers)
    plugins.implements(plugins.IDatasetForm)
    plugins.implements(plugins.IValidators)
    # https://github.com/NaturalHistoryMuseum/ckanext-doi/issues/126
    plugins.implements(plugins.IConfigDeclaration, inherit=True)
    plugins.implements(plugins.IAuthenticator)

    # IConfigurer

    def update_config(self, config_):
        toolkit.add_template_directory(config_, "templates")
        toolkit.add_public_directory(config_, "public")
        toolkit.add_resource("fanstatic", "coat")

    # IConfigDeclaration

    def declare_config_options(self, declaration: Declaration, key: Key):
        # https://github.com/NaturalHistoryMuseum/ckanext-doi/issues/126
        group = key.ckanext.doi
        declaration.declare(group.account_name)
        declaration.declare(group.account_password)
        declaration.declare(group.prefix)
        declaration.declare(group.publisher)
        declaration.declare(group.site_title)
        declaration.declare(group.test_mode)
        # ckanext.doi.site_url is intentionally not declared: ckanext-doi
        # reads it with a fallback to ckan.site_url, and declaring it would
        # inject None and break that fallback.

    # IAuthenticator

    def _user_from_legacy_api_token_header(self):
        """User for the API token sent in the legacy ``X-CKAN-API-Key``
        header, or None.

        CKAN < 2.11 read the API token from ``apikey_header_name`` (default
        ``X-CKAN-API-KEY``); since 2.11 the token is only read from the header
        named by ``apitoken_header_name`` (default ``Authorization``), so
        tokens sent in the legacy header are otherwise silently ignored,
        leaving older clients (e.g. ckanr < 2025-11) anonymous and without
        access to private datasets.
        """
        token = request.headers.get("X-CKAN-API-KEY")
        if not token:
            return None
        return get_user_from_token(token)

    def identify_user(self, user_id=None):
        """New-style IAuthenticator hook, used by CKAN's Flask-Login request
        loader.

        Note: ckanext-oauth2 replaces that loader with its own on the first
        request, so after that only ``identify`` (below) runs.
        """
        user = self._user_from_legacy_api_token_header()
        if user is not None:
            # same effect as CKAN's own header-based login: disable CSRF
            # protection for this request
            g.login_via_auth_header = True
        return user

    def identify(self):
        """Deprecated side-effect hook, still invoked by CKAN 2.12 for every
        IAuthenticator plugin on every request.

        ckanext-oauth2 replaces CKAN's Flask-Login request loader with its
        own (which only checks the ``Authorization``/``X-Tapis-Token``
        headers), so the legacy header can only be honoured here, by logging
        the user in directly.
        """
        user = self._user_from_legacy_api_token_header()
        if user is None:
            return None
        g.login_via_auth_header = True
        login_user(user)
        return None

    # IActions

    def get_actions(self):
        return {
            "ckan_package_create": ckanext.coat.logic.action.create.package_create,
            "package_create": ckanext.coat.logic.action.create.package_create,
            "ckan_package_search": ckanext.coat.logic.action.get.ckan_package_search,
            "package_search": ckanext.coat.logic.action.get.package_search,
            "ckan_package_update": ckanext.coat.logic.action.update.package_update,
            "package_show": ckanext.coat.logic.action.get.package_show,
            "package_update": ckanext.coat.logic.action.update.package_update,
            "ckan_package_delete": ckanext.coat.logic.action.delete.package_delete,
            "package_delete": ckanext.coat.logic.action.delete.package_delete,
            "ckan_resource_show": ckanext.coat.logic.action.get.ckan_resource_show,
            "resource_show": ckanext.coat.logic.action.get.resource_show,
        }

    # IResourceController

    def before_resource_update(self, context, obj, *args, **kwargs):
        resource = toolkit.get_action("resource_show")(context, obj)
        helpers.is_protected(resource, context, action="update")

    def before_resource_delete(self, context, obj, *args, **kwargs):
        resource = toolkit.get_action("resource_show")(context, obj)
        helpers.is_protected(resource, context, action="delete")

    # IBlueprint

    def get_blueprint(self):
        return blueprint.coat

    # ITemplateHelpers

    def get_helpers(self):
        return {
            "coat_is_under_embargo": helpers.is_under_embargo,
            "coat_has_active_embargo": helpers.has_active_embargo,
        }

    # IDatasetForm

    def _custom_package_schema(self, schema):
        validators = schema["resources"]["name"]
        for validator in ("lowercase_extension", "resource_name_conflict"):
            validators.append(toolkit.get_validator(validator))
        schema["resources"]["name"] = validators
        return schema

    def create_package_schema(self):
        schema = super().create_package_schema()
        schema["private"].append(toolkit.get_validator("private_on_creation"))
        return self._custom_package_schema(schema)

    def update_package_schema(self):
        schema = super().update_package_schema()
        return self._custom_package_schema(schema)

    def show_package_schema(self):
        schema = super().show_package_schema()
        return schema

    def is_fallback(self):
        return False

    def package_types(self):
        if config.get("ckanext.coat.custom_form", "true").lower() == "false":
            return []
        else:
            return ["dataset"]

    # IValidators

    def get_validators(self):
        return {
            "lowercase_extension": validators.lowercase_extension,
            "resource_name_conflict": validators.resource_name_conflict,
            "private_on_creation": validators.private_on_creation,
        }
