#!/usr/bin/python3
# Copyright 2022 Northern.tech AS
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


class TestPackageGateway:
    @pytest.mark.commercial
    def test_mender_gateway(
        self, setup_tester_ssh_connection, mender_dist_packages_versions
    ):
        # Upload
        upload_deb_package(
            setup_tester_ssh_connection,
            mender_dist_packages_versions["mender-gateway"],
            "mender-gateway",
        )

        # Install
        result = setup_tester_ssh_connection.run(
            "sudo dpkg -i"
            + package_filename(
                mender_dist_packages_versions["mender-gateway"], "mender-gateway",
            )
        )
        assert (
            "Unpacking mender-gateway ("
            + mender_dist_packages_versions["mender-gateway"]
            + ")"
            in result.stdout
        )
        assert (
            "Setting up mender-gateway ("
            + mender_dist_packages_versions["mender-gateway"]
            + ")"
            in result.stdout
        )

        # Check mender-gateway files
        setup_tester_ssh_connection.run("test -x /usr/bin/mender-gateway")
        setup_tester_ssh_connection.run("test -f /etc/mender/mender-gateway.conf")
        setup_tester_ssh_connection.run(
            "test -f /lib/systemd/system/mender-gateway.service"
        )
