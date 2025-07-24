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

from helpers import package_filename, upload_deb_package, check_installed
from mender_test_containers.helpers import *


class TestPackageSnapshot:
    """Tests installation of mender-snapshot deb package.
    """

    @pytest.mark.usefixtures("setup_test_container")
    def test_install(self, setup_tester_ssh_connection, mender_dist_packages_versions):
        upload_deb_package(
            setup_tester_ssh_connection,
            mender_dist_packages_versions["mender-snapshot"],
            package_name="mender-snapshot",
        )

        setup_tester_ssh_connection.run(
            "sudo dpkg --install "
            + package_filename(
                mender_dist_packages_versions["mender-snapshot"],
                package_name="mender-snapshot",
            ),
        )
        check_installed(setup_tester_ssh_connection, "mender-snapshot")

        setup_tester_ssh_connection.run("test -x /usr/bin/mender-snapshot")
