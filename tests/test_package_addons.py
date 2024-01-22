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
import re

from helpers import package_filename, upload_deb_package, check_installed


@pytest.mark.usefixtures("setup_mender_configured")
class TestPackageAddons:
    def test_mender_connect(
        self,
        setup_tester_ssh_connection,
        mender_dist_packages_versions,
        mender_connect_version,
    ):
        # Upload
        upload_deb_package(
            setup_tester_ssh_connection,
            mender_dist_packages_versions["mender-connect"],
            "mender-connect",
        )

        # Install
        setup_tester_ssh_connection.run(
            "sudo dpkg --install "
            + package_filename(
                mender_dist_packages_versions["mender-connect"], "mender-connect"
            )
        )
        check_installed(setup_tester_ssh_connection, "mender-connect")

        # Check mender-connect files
        setup_tester_ssh_connection.run("test -x /usr/bin/mender-connect")
        setup_tester_ssh_connection.run("test -f /etc/mender/mender-connect.conf")
        setup_tester_ssh_connection.run(
            "test -f /lib/systemd/system/mender-connect.service"
        )

        # Check mender-configure version
        if mender_connect_version == "master":
            # For master it will print the short git hash. We can obtain this from the deb
            # package version, which is something like: "0.0~git20191022.dade697-1"
            m = re.match(
                r"[0-9]+\.[0-9]+\.[0-9]+~git[0-9]+\.([a-z0-9]+)-1",
                mender_dist_packages_versions["mender-connect"],
            )
            assert m is not None
        else:
            result = setup_tester_ssh_connection.run("mender-connect version")
            assert mender_connect_version in result.stdout

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
            "sudo dpkg --install "
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

    @pytest.mark.commercial
    def test_mender_monitor(
        self, setup_tester_ssh_connection, mender_dist_packages_versions
    ):
        # Upload
        upload_deb_package(
            setup_tester_ssh_connection,
            mender_dist_packages_versions["mender-monitor"],
            "mender-monitor",
            "all",
        )

        # Install the lmdb-utils
        result = setup_tester_ssh_connection.run(
            "sudo apt-get install -f -y " + "lmdb-utils"
        )

        assert result.exited == 0

        # Install
        setup_tester_ssh_connection.run(
            "sudo dpkg --install "
            + package_filename(
                mender_dist_packages_versions["mender-monitor"],
                "mender-monitor",
                "all",
            )
        )
        check_installed(setup_tester_ssh_connection, "mender-monitor")

        # Check mender-monitor files
        setup_tester_ssh_connection.run(
            "test -x /usr/share/mender-monitor/mender-monitord"
        )
        setup_tester_ssh_connection.run("test -x /etc/mender-monitor/monitor.d/log.sh")
        setup_tester_ssh_connection.run("test -d /etc/mender-monitor/monitor.d/enabled")
        setup_tester_ssh_connection.run(
            "test -d /etc/mender-monitor/monitor.d/available"
        )
