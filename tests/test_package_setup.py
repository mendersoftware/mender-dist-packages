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


@pytest.mark.mender_setup
class TestPackageSetup:
    """Tests installation mender-setup deb package.
    """

    @pytest.mark.usefixtures("setup_test_container")
    def test_install(self, setup_tester_ssh_connection, mender_dist_packages_versions):
        result = setup_tester_ssh_connection.run("uname -a")
        assert "raspberrypi" in result.stdout

        upload_deb_package(
            setup_tester_ssh_connection,
            mender_dist_packages_versions["mender-setup"],
            package_name="mender-setup",
        )

        setup_tester_ssh_connection.run(
            "sudo DEBIAN_FRONTEND=noninteractive dpkg --install "
            + package_filename(
                mender_dist_packages_versions["mender-setup"],
                package_name="mender-setup",
            ),
        )
        check_installed(setup_tester_ssh_connection, "mender-setup")
        setup_tester_ssh_connection.run("test -x /usr/bin/mender-setup")
        setup_tester_ssh_connection.run("test -f /etc/mender/mender.conf")
        setup_tester_ssh_connection.run("test -f /var/lib/mender/device_type")

        # Default setup expects ServerURL hosted.mender.io
        result = setup_tester_ssh_connection.sudo("cat /etc/mender/mender.conf")
        assert '"ServerURL": "https://hosted.mender.io"' in result.stdout

        # Device type
        setup_tester_ssh_connection.run("test -f /var/lib/mender/device_type")
        result = setup_tester_ssh_connection.run("cat /var/lib/mender/device_type")
        assert "device_type=raspberrypi" in result.stdout

        result = setup_tester_ssh_connection.run("sudo dpkg --remove mender-setup")
        assert (
            "Removing mender-setup ("
            + mender_dist_packages_versions["mender-setup"]
            + ")"
            in result.stdout
        )
        setup_tester_ssh_connection.run("test ! -x /usr/bin/mender-setup")
        setup_tester_ssh_connection.run("test -f /etc/mender/mender.conf")
        setup_tester_ssh_connection.run("test -f /var/lib/mender/device_type")

        # Purging mender-setup does not remove the configuration
        setup_tester_ssh_connection.run("sudo dpkg --purge mender-setup")
        setup_tester_ssh_connection.run("test -f /etc/mender/mender.conf")
        setup_tester_ssh_connection.run("test -f /var/lib/mender/device_type")

        # Re-install the package using the following flow for the setup wizard:
        # ...
        # Enter a name for the device type (e.g. raspberrypi3): [raspberrypi] raspberrytest
        # Are you connecting this device to hosted.mender.io? [Y/n] n
        # Do you want to run the client in demo mode? [Y/n] y
        # Set the IP of the Mender Server: [127.0.0.1] 1.2.3.4
        # Mender setup successfully.
        # ...
        setup_tester_ssh_connection.run("sudo rm /etc/mender/mender.conf")
        setup_tester_ssh_connection.run("sudo rm /var/lib/mender/device_type")
        setup_tester_ssh_connection.run(
            "sudo dpkg --install "
            + package_filename(
                mender_dist_packages_versions["mender-setup"], "mender-setup"
            )
            + """ <<STDIN
raspberrytest
n
y
1.2.3.4
y
STDIN"""
        )

        result = setup_tester_ssh_connection.run("cat /var/lib/mender/device_type")
        assert "device_type=raspberrytest" in result.stdout
        # Demo setup expects ServerURL docker.mender.io with IP address in /etc/hosts
        result = setup_tester_ssh_connection.sudo("cat /etc/mender/mender.conf")
        assert '"ServerURL": "https://docker.mender.io"' in result.stdout
        result = setup_tester_ssh_connection.run("cat /etc/hosts")
        assert (
            re.match(r".*1\.2\.3\.4\s*docker\.mender\.io.*", result.stdout, re.DOTALL)
            is not None
        )
