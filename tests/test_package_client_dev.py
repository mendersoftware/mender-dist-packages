#!/usr/bin/python3
# Copyright 2021 Northern.tech AS
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

from helpers import package_filename, upload_deb_package


@pytest.mark.usefixtures("setup_mender_configured")
class TestPackageDev:
    def test_mender_client_dev(
        self, setup_tester_ssh_connection, mender_dist_packages_versions
    ):
        # Upload
        upload_deb_package(
            setup_tester_ssh_connection,
            mender_dist_packages_versions["mender-client"],
            "mender-client",
        )
        upload_deb_package(
            setup_tester_ssh_connection,
            mender_dist_packages_versions["mender-client"],
            "mender-client-dev",
            package_arch="all",
        )

        # Install
        result = setup_tester_ssh_connection.run(
            "sudo DEBIAN_FRONTEND=noninteractive dpkg -i "
            + package_filename(
                mender_dist_packages_versions["mender-client"], "mender-client",
            )
            + " "
            + package_filename(
                mender_dist_packages_versions["mender-client"],
                "mender-client-dev",
                package_arch="all",
            )
        )
        assert (
            "Unpacking mender-client-dev ("
            + mender_dist_packages_versions["mender-client"]
            + ")"
            in result.stdout
        )
        assert (
            "Setting up mender-client-dev ("
            + mender_dist_packages_versions["mender-client"]
            + ")"
            in result.stdout
        )

        # Check mender-client-dev files
        setup_tester_ssh_connection.run(
            "test -f /usr/share/dbus-1/interfaces/io.mender.Authentication1.xml"
        )
