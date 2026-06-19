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

pytestmark = pytest.mark.requires_option("--mender-monitor-deb-version")


@pytest.mark.usefixtures("setup_mender_configured")
class TestPackageMonitor:
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
