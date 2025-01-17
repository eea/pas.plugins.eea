from datetime import datetime
from logging import getLogger

import requests
from pas.plugins.authomatic.interfaces import \
    DEFAULT_ID as DEFAULT_AUTHOMATIC_ID
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

        t0 = datetime.now()
        count, done = self.do_sync()
        seconds = (datetime.now() - t0).total_seconds()

        self.status = f"Synced {count} users in {seconds} seconds ({done})"

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

        user_mapping = authomatic_plugin._userid_by_identityinfo.items()
        identities_mapping = authomatic_plugin._useridentities_by_userid

        session = requests.Session()

        for (_, provider_uuid), user_id in user_mapping:
            # User properties are kept in authomatic, not in portal_memberdata,
            # that is what we need to update.
            identities = identities_mapping.get(user_id)
            log_message = "Fetching updated data for %s... %s"

            response = plugin.queryApiEndpoint(
                f"https://graph.microsoft.com/v1.0/users/{provider_uuid}",
                session=session)

            if response.status_code == 200:
                info = response.json()
                sheet = identities.propertysheet
                sheet._properties["fullname"] = info["displayName"]
                sheet._properties["email"] = info.get(
                    "email", info["userPrincipalName"]
                )
                identities._p_changed = 1
                count += 1
                logger.info(log_message, user_id, "Success.")
            else:
                logger.warning(log_message, user_id, "Fail!")

        return count, datetime.isoformat(datetime.now())
