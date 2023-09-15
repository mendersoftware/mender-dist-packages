#!/usr/bin/python3
# Copyright 2023 Northern.tech AS
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

import pytest
import time
import os.path
import re

from helpers import package_filename, upload_deb_package
from mender_test_containers.helpers import *


class PackageMenderAppUpdateModuleChecker:

    expected_update_modules = ["app"]
    expected_update_app_modules = ["k8s", "docker-compose"]

    def check_installed_files(self, ssh_connection, device_type="unknown"):
        ssh_connection.run("test -d /usr/share/mender/modules/v3")
        ssh_connection.run("test -d /usr/share/mender/app-modules/v1")
        for module in self.expected_update_modules:
            module_path = os.path.join("/usr/share/mender/modules/v3", module)
            ssh_connection.run("test -x {mod}".format(mod=module_path))
        for module in self.expected_update_app_modules:
            module_path = os.path.join("/usr/share/mender/app-modules/v1", module)
            ssh_connection.run("test -x {mod}".format(mod=module_path))

    def check_removed_files(self, ssh_connection, purge):
        for module in self.expected_update_modules:
            module_path = os.path.join("/usr/share/mender/modules/v3", module)
            ssh_connection.run("test ! -x {mod}".format(mod=module_path))
        for module in self.expected_update_app_modules:
            module_path = os.path.join("/usr/share/mender/app-modules/v1", module)
            ssh_connection.run("test ! -x {mod}".format(mod=module_path))


class TestPackageMenderAppUpdateModule(PackageMenderAppUpdateModuleChecker):
    """Tests instalation, setup, start, removal and purge of mender-app-update-module deb package with
    in non-interactive method (i.e. default configuration).
    """

    @pytest.mark.usefixtures("setup_test_container")
    def test_install(
        self, setup_tester_ssh_connection, mender_dist_packages_versions, mender_version
    ):
        result = setup_tester_ssh_connection.run("uname -a")
        assert "raspberrypi" in result.stdout

        upload_deb_package(
            setup_tester_ssh_connection, mender_dist_packages_versions["mender-client"]
        )

        # Install the deb package. On failure, install the missing dependencies.
        result = setup_tester_ssh_connection.run(
            "sudo DEBIAN_FRONTEND=noninteractive dpkg -i "
            + package_filename(mender_dist_packages_versions["mender-client"])
            + "|| sudo apt-get -f -y install"
        )

        upload_deb_package(
            setup_tester_ssh_connection,
            mender_dist_packages_versions["mender-app-update-module"],
            package_name="mender-app-update-module",
            package_arch="all",
        )

        result = setup_tester_ssh_connection.run(
            "sudo DEBIAN_FRONTEND=noninteractive dpkg -i "
            + package_filename(
                mender_dist_packages_versions["mender-app-update-module"],
                package_name="mender-app-update-module",
                package_arch="all",
            ),
        )
        assert (
            "Unpacking mender-app-update-module ("
            + mender_dist_packages_versions["mender-app-update-module"]
            + ")"
            in result.stdout
        )
        assert (
            "Setting up mender-app-update-module ("
            + mender_dist_packages_versions["mender-app-update-module"]
            + ")"
            in result.stdout
        )

        self.check_installed_files(setup_tester_ssh_connection, "raspberrypi")

    @pytest.mark.usefixtures("setup_test_container")
    def test_remove(self, setup_tester_ssh_connection, mender_dist_packages_versions):
        result = setup_tester_ssh_connection.run(
            "sudo dpkg -r mender-app-update-module"
        )
        assert (
            "Removing mender-app-update-module ("
            + mender_dist_packages_versions["mender-app-update-module"]
            + ")"
            in result.stdout
        )

        self.check_removed_files(setup_tester_ssh_connection, purge=False)
