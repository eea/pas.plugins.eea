pas.plugins.eea
===============

Provides user and group enumeration on top of pas.plugins.authomatic

Features

-  user enumeration
-  groups enumeration
-  group member enumeration
-  user group enumeration

Documentation
=============

This addon depends on
`pas.plugins.authomatic <https://github.com/collective/pas.plugins.authomatic>`__.
Upon installation, it will automatically run the setup step for
``pas.plugins.authomatic``.

In order for this plugin to function correctly, the Entra ID application
should be granted the following **API permissions** in the
``Microsoft.Graph`` scope via the Azure Portal:

-  ``Group.Read.All``
-  ``GroupMember.Read.All``
-  ``User.Read.All``

The type for all the permissions is ``Application`` and *“Admin
consent”* must be granted.

Installation
============

Install pas.plugins.eea by adding it to your buildout::

::

   [buildout]

   ...

   eggs =
       pas.plugins.eea

and then running ``bin/buildout``

After enabling the product in Site Setup -> Add-ons, make sure to:

-  go into Site Setup -> Authomatic (OAuth2/OpenID) and make sure that
   *“Generator for Plone User IDs.”* is set to UUID as User ID**.

-  update the JSON configuration

-  make sure to add the following to the JSON configuration (for working
   sync)

   ::

            "sync_propertymap": {
              "id": "id",
              "mail": "email",
              "country": "location",
              "displayName": "fullname",
              "userPrincipalName": "email",
              "userType": null
            },

-  | From control panel run sync users

-  Disable the following functionalities in ``acl_users``:

   -  ``authomatic``:

      -  User_Enumeration (this is handled by ``eea_entra`` - the
         ``login`` property is set to the user email)
      -  User_Management (to disable the remove checkboxes, as Entra
         users cannot be deleted from Plone)
      -  Properties (to add “External” emoji)

   -  ``mutable_properties``:

      -  User_Enumeration (this is handled by ``eea_entra`` - the
         ``login`` property is set to the user email)

-  In acl_users -> plugins -> Properties Plugins make sure that
   ``eea_entra`` is at the top of the list of “Active Plugins”.

CRON
====

A script is provided to sync users and groups from Entra ID.
The script is located in ``pas/plugins/eea/scripts/sync.py`` and
registered in setup.py as a console script.

It can be called from the command line like this::

    sync_eea_entra --portal PLONE_PORTAL_ID --zope-conf /path/to/zope.conf

The script initializes itself the same way ``zconsole run`` would.
It cannot be called with ``zconsole run`` as that command does not pass on script arguments,
so there is no way to specify the portal id.

EEA specifics
=============

- https://taskman.eionet.europa.eu/projects/infrastructure/wiki/Authentication_with_Entra_ID_in_Plone

Contribute
==========

-  Issue Tracker: https://github.com/eea/pas.plugins.eea/issues
-  Source Code: https://github.com/eea/pas.plugins.eea

License
=======

The project is licensed under the GPLv2.
