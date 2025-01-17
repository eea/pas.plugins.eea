# -*- coding: utf-8 -*-
from zope.interface import implementer

from plone.base.interfaces import INonInstallable

from .interfaces import DEFAULT_ID
from .plugin import EEAEntraPlugin

TITLE = "EEA Entra plugin (pas.plugins.eea)"


@implementer(INonInstallable)
class HiddenProfiles(object):
    def getNonInstallableProfiles(self):
        """Hide uninstall profile from site-creation and quickinstaller."""
        return [
            "pas.plugins.eea:uninstall",
        ]

    def getNonInstallableProducts(self):
        """Hide the upgrades package from site-creation and quickinstaller."""
        return ["pas.plugins.eea.upgrades"]


def _add_plugin(pas, pluginid=DEFAULT_ID):
    if pluginid in pas.objectIds():
        return f"{TITLE} already installed."
    if pluginid != DEFAULT_ID:
        return f"ID of plugin must be {DEFAULT_ID}"
    plugin = EEAEntraPlugin(pluginid, title=TITLE)
    pas._setObject(pluginid, plugin)
    plugin = pas[plugin.getId()]  # get plugin acquisition wrapped!
    for info in pas.plugins.listPluginTypeInfo():
        interface = info["interface"]
        if not interface.providedBy(plugin):
            continue
        pas.plugins.activatePlugin(interface, plugin.getId())
        pas.plugins.movePluginsDown(
            interface,
            [x[0] for x in pas.plugins.listPlugins(interface)[:-1]],
        )


def _remove_plugin(pas, pluginid=DEFAULT_ID):
    if pluginid in pas.objectIds():
        pas.manage_delObjects([pluginid])


def post_install(context):
    """Post install script"""
    _add_plugin(context.aq_parent.acl_users)


def uninstall(context):
    """Uninstall script"""
    _remove_plugin(context.aq_parent.acl_users)
