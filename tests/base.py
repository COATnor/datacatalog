import os
from functools import wraps

from parameterized import parameterized
from seleniumbase import BaseCase
from seleniumbase.config import settings

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

    @sanity_check
    def test_search_map(self):
        self.open(BASE + "/dataset/")
        self.assert_element(".leaflet-container")


class PyCSW(BaseCase):
    def test_homepage(self):
        self.open(BASE + "/pycsw/csw.py")
        self.assert_element_present("*")  # XML page loaded


class OAuth2Login(BaseCase):
    def test_feide_login(self):
        self.open(BASE + "/user/login")
        self.click("a.section-list")  # "Feide test users"
        # https://docs.feide.no/reference/testusers.html
        self.type("#username", "emma123elev")
        self.type("#password", "098asd")
        self.click("button[type=submit].button-primary")
        self.assert_element(".account .username", timeout=15)
