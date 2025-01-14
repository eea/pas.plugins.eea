from datetime import datetime
from logging import getLogger

from pas.plugins.authomatic.interfaces import DEFAULT_ID as DEFAULT_AUTHOMATIC_ID
from plone import api
from plone import schema
from plone.autoform.form import AutoExtensibleForm
from z3c.form import button
from z3c.form import form
from zope.interface import Interface

from pas.plugins.eea.utils import get_plugin

logger = getLogger(__name__)


class IUserSyncForm(Interface):
    start_sync = schema.Bool(title="Start sync?", default=False)

class UserSyncForm(AutoExtensibleForm, form.EditForm):
    schema = IUserSyncForm
    ignoreContext = True

    label = "Sync users with Entra ID"

    @button.buttonAndHandler("Ok")
    def handleApply(self, action):
        data, errors = self.extractData()
        if errors:
            self.status = self.formErrorsMessage
            return

        count, done = self.do_sync()
        self.status = f"Synced {count} users ({done})"

    @button.buttonAndHandler("Cancel")
    def handleCancel(self, action):
        """User cancelled. Redirect back to the front page.
        """
        return self.request.response.redirect(api.portal.get().absolute_url())

    def do_sync(self):
        portal = api.portal.get()

        plugin = get_plugin()
        authomatic_plugin = portal.acl_users[DEFAULT_AUTHOMATIC_ID]

        count = 0

        # User properties are kept in authomatic, not in portal_memberdata, that is what we need to update.
        for user_id, identities in authomatic_plugin._useridentities_by_userid.items():
            log_message = "Fetching updated data for %s... %s"
            response = plugin.queryApiEndpoint(f"https://graph.microsoft.com/v1.0/users/{user_id}")
            if response.status_code == 200:
                info = response.json()
                sheet = identities.propertysheet
                sheet._properties["fullname"] = info["displayName"]
                sheet._properties["email"] = info["userPrincipalName"]
                identities._p_changed = 1
                count += 1
                logger.info(log_message, user_id, "Success.")
            else:
                logger.warning(log_message, user_id, "Fail!")

        return count, datetime.isoformat(datetime.now())
