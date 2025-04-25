""" pas.plugins.eea Installer
"""

import os
from os.path import join

from setuptools import find_packages
from setuptools import setup

NAME = "pas.plugins.eea"
PATH = ["src"] + NAME.split(".") + ["version.txt"]
VERSION = ""
with open(join(*PATH), "r", encoding="utf-8") as version_file:
    VERSION = version_file.read().strip()

LONG_DESCRIPTION = ""
with open("README.rst", "r", encoding="utf-8") as readme_file:
    LONG_DESCRIPTION = readme_file.read()

with open(os.path.join("docs", "HISTORY.txt"), "r", encoding="utf-8") as hfile:
    LONG_DESCRIPTION += "\n" + hfile.read()


setup(
    name=NAME,
    version=VERSION,
    description=(
        "Provides user and group enumeration"
        " on top of pas.plugins.authomatic"
    ),
    long_description_content_type="text/x-rst",
    long_description=LONG_DESCRIPTION,
    # Get more from https://pypi.org/classifiers/
    classifiers=[
        "Environment :: Web Environment",
        "Framework :: Plone",
        "Framework :: Plone :: Addon",
        "Framework :: Plone :: 5.2",
        "Framework :: Plone :: 6.0",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
        "License :: OSI Approved :: GNU General Public License v2 (GPLv2)",
    ],
    keywords="EEA Add-ons Plone Zope",
    author="European Environment Agency: IDM2 A-Team",
    author_email="eea-edw-a-team-alerts@googlegroups.com",
    url="https://github.com/collective/pas.plugins.eea",
    project_urls={
        "PyPI": "https://pypi.org/project/pas.plugins.eea/",
        "Source": "https://github.com/collective/pas.plugins.eea",
        "Tracker": "https://github.com/collective/pas.plugins.eea/issues",
        # 'Documentation': 'https://pas.plugins.eea.readthedocs.io/en/latest/',
    },
    license="GPL version 2",
    packages=find_packages("src", exclude=["ez_setup"]),
    namespace_packages=["pas", "pas.plugins"],
    package_dir={"": "src"},
    include_package_data=True,
    zip_safe=False,
    python_requires=">=3.7",
    install_requires=[
        "setuptools",
        "plone.api>=1.8.4",
        "plone.app.dexterity",
        "pas.plugins.authomatic",
        "requests",
        "requests_futures",
    ],
    extras_require={
        "test": [
            "plone.app.testing",
            # Plone KGS does not use this version, because it would break
            # Remove if your package shall be part of coredev.
            # plone_coredev tests as of 2016-04-01.
            "plone.testing>=5.0.0",
            "plone.app.contenttypes",
            "responses",
            "coverage",
        ],
    },
    entry_points="""
    [plone.autoinclude.plugin]
    target = plone
    module = pas.plugins.eea
    [console_scripts]
    update_locale = pas.plugins.eea.locales.update:update_locale
    sync_eea_entra = pas.plugins.eea.scripts.sync:run_standalone
    """,
)
