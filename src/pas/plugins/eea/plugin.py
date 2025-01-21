import logging
from pathlib import Path

from AccessControl import ClassSecurityInfo
from AccessControl.class_init import InitializeClass
from BTrees.OOBTree import OOBTree
from Products.PageTemplates.PageTemplateFile import PageTemplateFile
from Products.PlonePAS.interfaces.group import IGroupIntrospection
from Products.PlonePAS.interfaces.group import IGroupManagement
from Products.PlonePAS.plugins.autogroup import VirtualGroup
from Products.PluggableAuthService.interfaces import plugins as pas_interfaces
from Products.PluggableAuthService.plugins.BasePlugin import BasePlugin
from zope.interface import implementer

logger = logging.getLogger(__name__)
tpl_dir = Path(__file__).parent.resolve() / "browser"

_marker = {}



def manage_addEEAEntraPlugin(context, id, title="", RESPONSE=None, **kw):
    """Create an instance of an EEA Plugin."""
    plugin = EEAEntraPlugin(id, title, **kw)
    context._setObject(plugin.getId(), plugin)
    if RESPONSE is not None:
        RESPONSE.redirect("manage_workspace")


manage_addEEAEntraPluginForm = PageTemplateFile(
    tpl_dir / "add_plugin.pt",
    globals(),
    __name__="addEEAEntraPlugin",
)


@implementer(
    # pas_interfaces.IUserEnumerationPlugin,
    pas_interfaces.IGroupEnumerationPlugin,
    pas_interfaces.IGroupsPlugin,
    IGroupManagement,
    IGroupIntrospection,
)
class EEAEntraPlugin(BasePlugin):
    """EEA PAS Plugin"""

    security = ClassSecurityInfo()
    meta_type = "EEA Entra Plugin"
    manage_options = BasePlugin.manage_options

    _ad_groups: dict | None = None
    _ad_group_members: dict | None = None

    # Tell PAS not to swallow our exceptions
    _dont_swallow_my_exceptions = True

    def __init__(self, id, title=None, **kw):
        self._setId(id)
        self.title = title
        self.plugin_caching = True
        self._ad_groups = OOBTree()
        self._ad_group_members = OOBTree()
        self._ad_member_groups = OOBTree()

    @security.private
    def addGroup(self, *args, **kw):
        """Noop"""
        pass

    @security.private
    def addPrincipalToGroup(self, *args, **kwargs):
        """Noop"""
        pass

    @security.private
    def removeGroup(self, *args, **kwargs):
        """Noop"""
        pass

    @security.private
    def removePrincipalFromGroup(self, *args, **kwargs):
        """Noop"""
        pass

    @security.private
    def updateGroup(self, *args, **kw):
        """Noop"""
        pass

    @security.private
    def setRolesForGroup(self, group_id, roles=()):
        rmanagers = self._getPlugins().listPlugins(
            pas_interfaces.IRoleAssignerPlugin
        )
        if not (rmanagers):
            raise NotImplementedError(
                "There is no plugin that can assign roles to groups"
            )
        for rid, rmanager in rmanagers:
            rmanager.assignRolesToPrincipal(roles, group_id)

    @security.private
    def getGroupById(self, group_id):
        groups = self.savedGroups(group_id)
        group = groups[0] if len(groups) == 1 else None
        if group:
            return VirtualGroup(
                group["id"],
                title=group["title"],
                description=group["title"],
            )

    @security.private
    def getGroupIds(self):
        return [x for x in self._ad_groups.keys()]

    @security.private
    def getGroupsForPrincipal(self, principal, *args, **kwargs):
        principal_id = principal.getId()
        result = self._ad_member_groups.get(principal_id, [])
        return [x for x in result]

    @security.private
    def getGroupMembers(self, group_id):
        result = self._ad_group_members.get(group_id, [])
        return [x for x in result]

    @security.private
    def savedGroups(self, query=None):
        pluginid = self.getId()

        result = []

        if query:
            group_title = self._ad_groups.get(query, None)
            if group_title:
                result = [
                    {
                        "title": group_title,
                        "id": query,
                        "groupid": query,
                        "pluginid": pluginid,
                    }
                ]

        if not result:
            result = [
                {
                    "title": group_title,
                    "id": group_id,
                    "groupid": group_id,
                    "pluginid": pluginid,
                }
                for group_id, group_title in self._ad_groups.items()
            ]

        return result

    @security.private
    def enumerateGroups(
        self, id=None, exact_match=False, sort_by=None, max_results=None, **kw
    ):
        result = []
        if not id:
            result = self.savedGroups()

        elif id and exact_match:
            result = self.savedGroups(id)

        if not result:
            query = id.lower()
            result = [g for g in self.savedGroups() if query in g["title"].lower()]

        return result


InitializeClass(EEAEntraPlugin)
