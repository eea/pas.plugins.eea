# -*- coding: utf-8 -*-
"""Setup tests for this package."""

import unittest

from plone import api
from plone.app.testing import TEST_USER_ID
from plone.app.testing import setRoles

from pas.plugins.eea.testing import (  # noqa: E501
    PAS_PLUGINS_EEA_INTEGRATION_TESTING,
)

try:
    from Products.CMFPlone.utils import get_installer
except ImportError:
    get_installer = None


class TestSetup(unittest.TestCase):
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

    def test_product_installed(self):
        """Test if pas.plugins.eea is installed."""
        self.assertTrue(self.installer.is_product_installed("pas.plugins.eea"))

    def test_browserlayer(self):
        """Test that IPasPluginsEeaLayer is registered."""
        from plone.browserlayer import utils

        from pas.plugins.eea.interfaces import IPasPluginsEeaLayer

        self.assertIn(IPasPluginsEeaLayer, utils.registered_layers())


class TestUninstall(unittest.TestCase):
    """Test uninstall."""

    layer = PAS_PLUGINS_EEA_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        if get_installer:
            self.installer = get_installer(self.portal, self.layer["request"])
        else:
            self.installer = api.portal.get_tool("portal_quickinstaller")
        roles_before = api.user.get_roles(TEST_USER_ID)
        setRoles(self.portal, TEST_USER_ID, ["Manager"])
        self.installer.uninstall_product("pas.plugins.eea")
        setRoles(self.portal, TEST_USER_ID, roles_before)

    def test_product_uninstalled(self):
        """Test if pas.plugins.eea is cleanly uninstalled."""
        self.assertFalse(self.installer.is_product_installed("pas.plugins.eea"))

    def test_browserlayer_removed(self):
        """Test that IPasPluginsEeaLayer is removed."""
        from plone.browserlayer import utils

        from pas.plugins.eea.interfaces import IPasPluginsEeaLayer

        self.assertNotIn(IPasPluginsEeaLayer, utils.registered_layers())
