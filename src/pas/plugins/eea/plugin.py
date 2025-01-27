import logging
from operator import attrgetter
from pathlib import Path

from AccessControl import ClassSecurityInfo
from AccessControl.class_init import InitializeClass

from BTrees.OOBTree import OOBTree  # noqa
from zope.interface import implementer

from Products.PageTemplates.PageTemplateFile import PageTemplateFile
from Products.PlonePAS.interfaces.group import IGroupData
from Products.PlonePAS.interfaces.group import IGroupIntrospection
from Products.PlonePAS.interfaces.group import IGroupManagement
from Products.PlonePAS.plugins.autogroup import VirtualGroup
from Products.PlonePAS.tools.groupdata import GroupData
from Products.PlonePAS.tools.memberdata import MemberData
from Products.PluggableAuthService.interfaces import plugins as pas_interfaces
from Products.PluggableAuthService.plugins.BasePlugin import BasePlugin

from plone import api

from pas.plugins.eea.utils import get_authomatic_plugin
from pas.plugins.eea.utils import get_plugin

logger = logging.getLogger(__name__)
tpl_dir = Path(__file__).parent.resolve() / "browser"

_marker = {}


@implementer(IGroupData)
class EEAEntraGroupData(VirtualGroup):
    """Wrapper in order to satisfy plone.restapi serializer."""

    canAddToGroup = MemberData.canAddToGroup
    canRemoveFromGroup = MemberData.canRemoveFromGroup
    canAssignRole = MemberData.canAssignRole
    canDelete = GroupData.canDelete
    canPasswordSet = GroupData.canPasswordSet
    passwordInClear = GroupData.passwordInClear

    def __str__(self):
        return self.id

    def getMemberId(self):
        """
        This method added to satisfy check in
        PlonePAS.tools.groups.GroupTool.wrapGroup
        """
        return self.id

    def getGroupName(self):
        return self.title

    def getProperty(self, name, default=None):
        result = default
        if name in ["id", "title", "description"]:
            result = attrgetter(name)(self) or default
        return result

    def getProperties(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
        }

    def getRoles(self):
        return []

    def getGroupMemberIds(self):
        plugin = get_plugin()
        return plugin.getGroupMembers(self.id)

    def _getPlugins(self):
        portal = api.portal.get()
        return portal.acl_users.plugins

    def canWriteProperty(self, name):
        return False

    def getGroupTitleOrName(self):
        return self.title or self.id


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
    pas_interfaces.IUserEnumerationPlugin,
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
            return EEAEntraGroupData(
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

    def getGroups(self):
        return [self.getGroupById(group_id) for group_id in self.getGroupIds()]

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

        else:
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
        if not id and kw:
            for group in self.savedGroups():
                for key, value in kw.items():
                    if value.lower() in group.get(key).lower():
                        result.append(group)

        elif not id:
            result = self.savedGroups()

        elif id and exact_match:
            result = self.savedGroups(id)

        elif id:
            query = id.lower()
            result = [
                g for g in self.savedGroups() if query in g["title"].lower()
            ]

        return result

    @security.private
    def enumerateUsers(
        self,
        id=None,
        login=None,
        *args,
        **kw,
    ):
        plugin = get_authomatic_plugin()

        if isinstance(id, list):
            # handle plone.restapi
            id = "".join(id)

        if isinstance(login, list):
            # handle plone.restapi
            login = "".join(login)

        if id and login and id != login:
            existing = plugin._useridentities_by_userid[id]
            if (
                existing
                and existing.propertysheet.getProperty("email", "").lower()
                == login.lower()
            ):
                login = id

        found = plugin.enumerateUsers(id, login, *args, **kw)

        for user in found:
            identity = plugin._useridentities_by_userid[user["id"]]
            user["login"] = identity.propertysheet.getProperty("email", "")

        return found


InitializeClass(EEAEntraPlugin)
