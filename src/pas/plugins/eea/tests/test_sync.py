# -*- coding: utf-8 -*-
""" Setup tests for this package. """

# pylint: disable=anomalous-backslash-in-string,unspecified-encoding,protected-access,import-error,no-name-in-module,import-outside-toplevel


import os
import re
import unittest

import responses

from zope.component import getUtility

from plone import api
from plone.registry.interfaces import IRegistry

from pas.plugins.eea.query import ENDPOINT_ENTRA
from pas.plugins.eea.query import ENDPOINT_GRAPH_API
from pas.plugins.eea.sync import SyncEntra
from pas.plugins.eea.testing import (  # noqa: E501
    PAS_PLUGINS_EEA_INTEGRATION_TESTING,
)
from pas.plugins.eea.utils import get_authomatic_plugin
from pas.plugins.eea.utils import get_plugin

try:
    from Products.CMFPlone.utils import get_installer
except ImportError:
    get_installer = None

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "authomatic_config.json")

TOKEN_RESPONSE = {
    "url": f"{ENDPOINT_ENTRA}/mock.entra.domain.local/oauth2/v2.0/token",
    "body": {
        "token_type": "Bearer",
        "expires_in": 3599,
        "ext_expires_in": 3599,
        "access_token": "mock-token.mock.token",
    },
}

USER_RESPONSE = {
    "url": f"{ENDPOINT_GRAPH_API}/users/mock-user-uuid",
    "body": {
        "value": {
            "businessPhones": [],
            "displayName": "Mock User",
            "givenName": "User",
            "jobTitle": None,
            "mail": "mock.user@mock.entra.domain.local",
            "mobilePhone": None,
            "officeLocation": None,
            "preferredLanguage": None,
            "surname": "Mock",
            "userPrincipalName": "mock.user@mock.entra.domain.local",
            "country": None,
            "userType": "Member",
            "id": "mock-user-uuid",
        },
    },
}

ENDPOINT_GRAPH_API_FOR_RE = ENDPOINT_GRAPH_API.replace(".", "\.")
ENDPOINT_GRAPH_API_USERS_RE = "users\?\$top=999.*"
USERS_RESPONSE = {
    "url": re.compile(
        rf"{ENDPOINT_GRAPH_API_FOR_RE}/{ENDPOINT_GRAPH_API_USERS_RE}"
    ),
    "body": {"value": [USER_RESPONSE["body"]["value"]]},
}


class TestSync(unittest.TestCase):
    """Test that pas.plugins.eea is properly installed."""

    layer = PAS_PLUGINS_EEA_INTEGRATION_TESTING

    def setUp(self):
        """Custom shared utility setup for tests."""
        self.portal = self.layer["portal"]
        if get_installer:
            self.installer = get_installer(self.portal, self.layer["request"])
        else:
            self.installer = api.portal.get_tool("portal_quickinstaller")
        self.installer.install_product("pas.plugins.authomatic")
        self.installer.install_product("pas.plugins.eea")

        self.eea_plugin = get_plugin()
        self.authomatic_plugin = get_authomatic_plugin()

        registry = getUtility(IRegistry)

        with open(CONFIG_PATH, "r") as authomatic_config:
            registry[
                "pas.plugins.authomatic.interfaces.IPasPluginsAuthomaticSettings.json_config"
            ] = authomatic_config.read()

    @responses.activate
    def test_sync_new_users(self):
        """Test syncing the users."""
        responses.add(
            responses.POST,
            TOKEN_RESPONSE["url"],
            json=TOKEN_RESPONSE["body"],
            status=200,
        )
        responses.add(
            responses.GET,
            USERS_RESPONSE["url"],
            json=USERS_RESPONSE["body"],
            status=200,
        )
        responses.add(
            responses.GET,
            USER_RESPONSE["url"],
            json=USER_RESPONSE["body"],
            status=200,
        )

        syncer = SyncEntra()
        syncer.add_new_users()

        assert len(self.eea_plugin._user_types) == 1

        service_uuid = USER_RESPONSE["body"]["value"]["id"]
        plone_uuid = syncer.get_plone_uuid(service_uuid)

        assert service_uuid == syncer.get_service_uuid(plone_uuid)
        assert self.eea_plugin._user_types[plone_uuid] == "Member"

        assert len(self.authomatic_plugin._userid_by_identityinfo) == 1
        assert (
            self.authomatic_plugin._userid_by_identityinfo.get(
                ("microsoft", service_uuid)
            )
            is not None
        )
        assert len(self.authomatic_plugin._useridentities_by_userid) == 1

        uis = list(
            self.authomatic_plugin._useridentities_by_userid.itervalues()
        )[-1]
        assert (
            uis._sheet.getProperty("email")
            == USER_RESPONSE["body"]["value"]["mail"]
        )
