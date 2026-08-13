import os

import sentry_sdk

from ckan.cli import CKANConfigLoader
from ckan.config.middleware import make_app

config_path = os.environ["CKAN_INI"]
config = CKANConfigLoader(config_path).get_config()

if os.environ.get("SENTRY_DSN"):
    sentry_sdk.init(
        dsn=os.environ["SENTRY_DSN"],
        send_default_pii=True,
        enable_logs=True,
        traces_sample_rate=0.05,
    )

application = make_app(config)

