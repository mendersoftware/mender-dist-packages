#!/usr/bin/python3
# Copyright 2026 Northern.tech AS
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

from helpers import package_filename, upload_deb_package, check_installed

pytestmark = pytest.mark.requires_option("--mender-configure-deb-version")


@pytest.mark.usefixtures("setup_mender_configured")
class TestPackageConfigure:
    def test_mender_configure(
        self, setup_tester_ssh_connection, mender_dist_packages_versions
    ):
        # Upload
        upload_deb_package(
            setup_tester_ssh_connection,
            mender_dist_packages_versions["mender-configure"],
            "mender-configure",
            "all",
        )

        # Install
        setup_tester_ssh_connection.run(
            "sudo apt -y install --fix-broken ./"
            + package_filename(
                mender_dist_packages_versions["mender-configure"],
                "mender-configure",
                "all",
            )
        )
        check_installed(setup_tester_ssh_connection, "mender-configure")

        # Check mender-configure files
        setup_tester_ssh_connection.run(
            "test -x /usr/share/mender/modules/v3/mender-configure"
        )
        setup_tester_ssh_connection.run(
            "test -x /usr/share/mender/inventory/mender-inventory-mender-configure"
        )
