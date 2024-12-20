# -*- coding: utf-8 -*-
from plone.app.robotframework.testing import REMOTE_LIBRARY_BUNDLE_FIXTURE
from plone.app.testing import applyProfile
from plone.app.testing import FunctionalTesting
from plone.app.testing import IntegrationTesting
from plone.app.testing import PLONE_FIXTURE
from plone.app.testing import PloneSandboxLayer
from plone.testing import z2

import pas.plugins.eea


class PasPluginsEeaLayer(PloneSandboxLayer):

    defaultBases = (PLONE_FIXTURE,)

    def setUpZope(self, app, configurationContext):
        # Load any other ZCML that is required for your tests.
        # The z3c.autoinclude feature is disabled in the Plone fixture base
        # layer.
        import plone.app.dexterity
        self.loadZCML(package=plone.app.dexterity)
        import plone.restapi
        self.loadZCML(package=plone.restapi)
        self.loadZCML(package=pas.plugins.eea)

    def setUpPloneSite(self, portal):
        applyProfile(portal, 'pas.plugins.eea:default')


PAS_PLUGINS_EEA_FIXTURE = PasPluginsEeaLayer()


PAS_PLUGINS_EEA_INTEGRATION_TESTING = IntegrationTesting(
    bases=(PAS_PLUGINS_EEA_FIXTURE,),
    name='PasPluginsEeaLayer:IntegrationTesting',
)


PAS_PLUGINS_EEA_FUNCTIONAL_TESTING = FunctionalTesting(
    bases=(PAS_PLUGINS_EEA_FIXTURE,),
    name='PasPluginsEeaLayer:FunctionalTesting',
)


PAS_PLUGINS_EEA_ACCEPTANCE_TESTING = FunctionalTesting(
    bases=(
        PAS_PLUGINS_EEA_FIXTURE,
        REMOTE_LIBRARY_BUNDLE_FIXTURE,
        z2.ZSERVER_FIXTURE,
    ),
    name='PasPluginsEeaLayer:AcceptanceTesting',
)
