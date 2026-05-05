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

pytestmark = pytest.mark.requires_option("--mender-connect-deb-version")


@pytest.mark.usefixtures("setup_mender_configured")
class TestPackageConnect:
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
            "sudo apt -y install --fix-broken ./"
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
