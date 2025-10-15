#!/usr/bin/python3
# Copyright 2025 Northern.tech AS
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


@pytest.mark.usefixtures("setup_mender_configured")
class TestPackageUpdateModules:
    def test_mender_container_modules(
        self, setup_tester_ssh_connection, mender_dist_packages_versions
    ):
        # Upload
        upload_deb_package(
            setup_tester_ssh_connection,
            mender_dist_packages_versions["mender-container-modules"],
            "mender-docker-compose",
            "all",
        )

        # Install
        setup_tester_ssh_connection.run(
            "sudo apt --assume-yes install --fix-broken ./"
            + package_filename(
                mender_dist_packages_versions["mender-container-modules"],
                "mender-docker-compose",
                "all",
            )
        )
        check_installed(setup_tester_ssh_connection, "mender-docker-compose")

        # Check mender-configure files
        setup_tester_ssh_connection.run(
            "test -x /usr/share/mender/modules/v3/docker-compose"
        )
