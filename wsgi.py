import os

from ckan.cli import CKANConfigLoader
from ckan.config.middleware import make_app

config_path = os.environ[u'CKAN_INI']
config = CKANConfigLoader(config_path).get_config()

application = make_app(config)
