from parameterized import parameterized
from seleniumbase import BaseCase
from seleniumbase.config import settings

from functools import wraps
import os


BASE = os.environ.get("COAT_URL", "http://localhost:5000")


def sanity_check(method):
    @wraps(method)
    def _impl(self, *method_args, **method_kwargs):
        method(self, *method_args, **method_kwargs)
        self.assert_no_404_errors(multithreaded=False, timeout=settings.EXTREME_TIMEOUT)
        self.assert_no_js_errors()
    return _impl


class CKANTest(BaseCase):
    @sanity_check
    def test_homepage(self):
        self.open(BASE)

    @parameterized.expand(
        [
            ["Datasets"],
            ["State variables"],
            ["Protocols"],
        ]
    )
    @sanity_check
    def test_dataset_list(self, label):
        self.open(BASE)
        self.click_link(label)
