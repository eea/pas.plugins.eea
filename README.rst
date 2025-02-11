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

Contribute
==========

-  Issue Tracker: https://github.com/eea/pas.plugins.eea/issues
-  Source Code: https://github.com/eea/pas.plugins.eea

License
=======

The project is licensed under the GPLv2.
