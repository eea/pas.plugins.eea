# -*- coding: utf-8 -*-
"""Init and utils."""
from AccessControl.Permissions import add_user_folders

from zope.i18nmessageid import MessageFactory

from Products.PluggableAuthService import registerMultiPlugin

from pas.plugins.eea.plugin import EEAEntraPlugin
from pas.plugins.eea.plugin import manage_addEEAEntraPlugin
from pas.plugins.eea.plugin import manage_addEEAEntraPluginForm
from pas.plugins.eea.plugin import tpl_dir

_ = MessageFactory("pas.plugins.eea")


def initialize(context):
    """Initializer called when used as a Zope 2 product.

    This is referenced from configure.zcml. Regstrations as a "Zope 2 product"
    is necessary for GenericSetup profiles to work, for example.

    Here, we call the Archetypes machinery to register our content types
    with Zope and the CMF.
    """
    registerMultiPlugin(EEAEntraPlugin.meta_type)
    context.registerClass(
        EEAEntraPlugin,
        permission=add_user_folders,
        constructors=(
            manage_addEEAEntraPluginForm,
            manage_addEEAEntraPlugin,
        ),
        visibility=None,
    )
