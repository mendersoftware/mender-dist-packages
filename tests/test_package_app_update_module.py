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
import os.path

from helpers import package_filename, upload_deb_package, check_installed
from mender_test_containers.helpers import *


class PackageMenderAppUpdateModuleChecker:

    expected_update_modules = ["app"]
    expected_update_app_modules = ["k8s", "docker-compose"]

    def check_installed_files(self, ssh_connection):
        ssh_connection.run("test -d /usr/share/mender/modules/v3")
        ssh_connection.run("test -d /usr/share/mender/app-modules/v1")
        for module in self.expected_update_modules:
            module_path = os.path.join("/usr/share/mender/modules/v3", module)
            ssh_connection.run("test -x {mod}".format(mod=module_path))
        for module in self.expected_update_app_modules:
            module_path = os.path.join("/usr/share/mender/app-modules/v1", module)
            ssh_connection.run("test -x {mod}".format(mod=module_path))

    def check_removed_files(self, ssh_connection):
        for module in self.expected_update_modules:
            module_path = os.path.join("/usr/share/mender/modules/v3", module)
            ssh_connection.run("test ! -x {mod}".format(mod=module_path))
        for module in self.expected_update_app_modules:
            module_path = os.path.join("/usr/share/mender/app-modules/v1", module)
            ssh_connection.run("test ! -x {mod}".format(mod=module_path))


class TestPackageMenderAppUpdateModule(PackageMenderAppUpdateModuleChecker):
    """Tests installation, and removal of mender-app-update-module deb package.
    """

    @pytest.mark.usefixtures("setup_test_container")
    def test_install(self, setup_tester_ssh_connection, mender_dist_packages_versions):
        upload_deb_package(
            setup_tester_ssh_connection,
            mender_dist_packages_versions["mender-app-update-module"],
            package_name="mender-app-update-module",
            package_arch="all",
        )

        setup_tester_ssh_connection.run(
            "sudo dpkg --ignore-depends=mender-client --install "
            + package_filename(
                mender_dist_packages_versions["mender-app-update-module"],
                package_name="mender-app-update-module",
                package_arch="all",
            ),
        )
        check_installed(setup_tester_ssh_connection, "mender-app-update-module")

        self.check_installed_files(setup_tester_ssh_connection)

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

        self.check_removed_files(setup_tester_ssh_connection)
