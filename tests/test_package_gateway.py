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

from helpers import package_filename, upload_deb_package, check_installed

pytestmark = pytest.mark.requires_option("--mender-gateway-deb-version")


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
        setup_tester_ssh_connection.run(
            "sudo dpkg --install "
            + package_filename(
                mender_dist_packages_versions["mender-gateway"],
                "mender-gateway",
            )
        )
        check_installed(setup_tester_ssh_connection, "mender-gateway")

        # Check mender-gateway files
        setup_tester_ssh_connection.run("test -x /usr/bin/mender-gateway")
        try:
            setup_tester_ssh_connection.run("test -f /etc/mender/mender-gateway.conf")
        except Exception:
            # This test can fail as on Ubuntu the /etc/mender/mender-gateway.conf is a symlink
            # to /usr/share/doc/mender-gateway/examples/mender-gateway.conf - which is not being
            # deployed due to mask in /etc/dpkg/dpkg.cfg.d
            # TODO: Enable this test again on Ubuntu after MEN-9952 is done
            if os.getenv("OS_FAMILY", "") == "ubuntu":
                return
            raise

        setup_tester_ssh_connection.run(
            "test -f /lib/systemd/system/mender-gateway.service"
        )
