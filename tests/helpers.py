#!/usr/bin/python3
# Copyright 2019 Northern.tech AS
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        https://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

import os.path

tests_path = os.path.dirname(os.path.realpath(__file__))

# Defaults
packages_path_default = os.path.normpath(os.path.join(tests_path, "..", "output"))
mender_version_default = "2.1.0"
packages_version_default = mender_version_default + "-1"

class Helpers:

    mender_version = mender_version_default
    packages_version = packages_version_default
    packages_path = packages_path_default

    # List of all deb packages
    VALID_PACKAGE_NAMES = ["mender-client"]

    @staticmethod
    def package_filename(package_name):
        return "{name}_{version}_armhf.deb".format(name=package_name, version=__class__.packages_version)

    @staticmethod
    def upload_deb_package(ssh_connection, package_name="mender-client"):
        assert package_name in __class__.VALID_PACKAGE_NAMES
        ssh_connection.put(__class__._package_filename_path(package_name))

    @staticmethod
    def _package_filename_path(package_name):
        filename = "{name}_{version}_armhf.deb".format(name=package_name, version=__class__.packages_version)
        return os.path.join(__class__.packages_path, filename)
