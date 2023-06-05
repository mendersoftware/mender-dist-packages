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
import time
import os.path
import re

from helpers import package_filename, upload_deb_package
from mender_test_containers.helpers import *

expected_copyright_from_l2_md5sum = "39a30292da940b7ce011150e8c8d5e4f"


def verify_file_exists(ssh_conn, files):
    for file in files:
        if file["type"] == "executable":
            ssh_conn.run(f"test -x {file}")
        elif file["type"] == "directory":
            ssh_conn.run(f"test -d {file}")
        elif file["type"] == "file":
            ssh_conn.run(f"test -f {file}")
        else:
            raise Exception("Unknown file type check")
        if file["contents"]:
            fname = file["name"]
            result = ssh_conn.run(f"cat {fname}")
            assert file["contents"] == result.stdout


all_files = [
    {
        "name": "/usr/bin/mender-update",
        "type": "executable",
    },
    {
        "name": "/usr/bin/mender-auth",
        "type": "executable",
    },
    {
        "name": "/usr/share/mender/modules/v3/",
        "type": "directory",
    },
    #
    # Update modules
    #
    {
        "name": "/usr/share/mender/modules/v3/",
        "type": "directory",
    },
    {
        "name": "mender-inventory-bootloader-integration",
        "type": "executable",
    },
    {
        "name": "mender-inventory-hostinfo",
        "type": "executable",
    },
    {
        "name": "mender-inventory-network",
        "type": "executable",
    },
    {
        "name": "mender-inventory-os",
        "type": "executable",
    },
    {
        "name": "mender-inventory-rootfs-type",
        "type": "executable",
    },
    #
    # Update modules
    #
    {
        "name": "/usr/share/mender/modules/deb",
        "type": "executable",
    },
    {
        "name": "/usr/share/mender/modules/directory",
        "type": "executable",
    },
    {
        "name": "/usr/share/mender/modules/rpm",
        "type": "executable",
    },
    {
        "name": "/usr/share/mender/modules/script",
        "type": "executable",
    },
    {
        "name": "/usr/share/mender/modules/single-file",
        "type": "executable",
    },
    #
    # device identity files
    #
    {
        "name": "/usr/share/mender/inventory",
        "type": "directory",
    },
    {
        "name": "/usr/share/mender/inventory/mender-device-identity",
        "type": "executable",
    },
    #
    # Configuration files
    #
    {
        "name": "/etc/mender/",
        "type": "directory",
    },
    {
        "name": "/etc/mender/mender.conf",
        "type": "file",
    },
    {
        "name": "/etc/mender/scripts",
        "type": "directory",
    },
    {
        "name": "/etc/mender/scripts/version",
        "type": "executable",
        "contents": "3",
    },
    #
    # Systemd services
    #
    {
        "name": "/lib/systemd/system/mender-udpated.service",
        "type": "file",
    },
    {
        "name": "/etc/systemd/multi-user.target.wants/mender-updated.service",
        "type": "file",
    },

    {
        "name": "/lib/systemd/system/mender-authd.service",
        "type": "file",
    },
    {
        "name": "/etc/systemd/multi-user.target.wants/mender-authd.service",
        "type": "file",
    },
    #
    # Demo certificate
    #

    {
        "name": "/usr/share/doc/mender/examples/demo.crt",
        "type": "file",
    },
    #
    # Device type file
    #
    {
        "name": "/var/lib/mender/device_type",
        "type": "file",
        "contents": "device_type=unknown",
    },
]


class PackageMenderClientChecker:

    def check_mender_client_version(self, ssh_connection, mender_version):
        if mender_version != "master":
            result = ssh_connection.run("mender --version")
            assert mender_version in result.stdout

    def check_installed_files(self, ssh_connection, device_type="unknown"):
        verify_file_exists(ssh_connection, all_files)
        # Northern.tech copyright file
        ssh_connection.run("test -f /usr/share/doc/mender-client/copyright")
        result = ssh_connection.run(
            "tail -n +2 /usr/share/doc/mender-client/copyright | md5sum"
        )
        assert result.stdout.split(" ")[0] == self.expected_copyright_from_l2_md5sum

    def check_systemd_start_full_cycle(self, ssh_connection):
        """
        Verifies that the Mender state machine starts, and reports the expected
        output as it's transitioning through a full cycle.

        There is three possible outputs to expect here. One for the older clients, and one for
        3.2.x, which has the Authorization states removed and authorizes upon requests to the
        backend if it finds it is unauthorized upon a request, and one for 3.3.x and newer for which
        the client may attempt inventory-update before update-check.
        """
        # Check first that mender process is running
        result = ssh_connection.run("pgrep mender-update")
        assert result.exited == 0

        # Detect of a full cycle in 4 min timeout (~2 min to generate device keys + 30 secs full cycle)
        start_time = time.time()
        timeout = 4 * 60
        while time.time() - start_time < timeout:
            result = ssh_connection.run("sudo journalctl -u mender-client --no-pager")
            if any(
                [
                    expected_output in result.stdout
                    for expected_output in [
                        "State transition: authorize [Sync] -> authorize-wait [Idle]",
                        "State transition: check-wait [Idle] -> update-check [Sync]",
                        "State transition: check-wait [Idle] -> inventory-update [Sync]",
                    ]
                ]
            ):
                break
            time.sleep(10)
        else:
            pytest.fail(
                "Did not detect a full cycle in %d seconds. Output follows:\n%s"
                % (timeout, result.stdout)
            )

        # Check correct boot
        assert "Started Mender OTA update service." in result.stdout, result.stdout
        assert "Loaded configuration file" in result.stdout, result.stdout
        assert "No dual rootfs configuration present" in result.stdout, result.stdout

        while time.time() - start_time < timeout:
            result = ssh_connection.run("sudo journalctl -u mender-client --no-pager")
            if any(
                [
                    expected_output in result.stdout
                    for expected_output in [
                        "Reauthorization failed with error: transient error: authorization request failed",
                        "Authorize failed: transient error: authorization request failed",
                    ]
                ]
            ):
                break
        else:
            pytest.fail(
                "Did not detect a full cycle in %d seconds. Output follows:\n%s"
                % (timeout, result.stdout)
            )


@pytest.mark.cppclient
class TestPackageMenderClientDefaults(PackageMenderClientChecker):
    """Tests installation, setup, start, removal and purge of mender-client deb
    package with the non-interactive method (i.e. default configuration).

    """

    @pytest.mark.usefixtures("setup_test_container")
    def test_install_configure_start(
        self, setup_tester_ssh_connection, mender_dist_packages_versions, mender_version
    ):
        result = setup_tester_ssh_connection.run("uname -a")
        assert "raspberrypi" in result.stdout

        # First things first
        setup_tester_ssh_connection.run(
            "sudo apt-get update"
        )

        # Client meta package
        upload_deb_package(
            setup_tester_ssh_connection, mender_dist_packages_versions["mender-client"]
        )
        # Upload mender-auth
        upload_deb_package(
            setup_tester_ssh_connection, mender_dist_packages_versions["mender-client"], package_name="mender-auth"
        )
        # Upload mender-update
        upload_deb_package(
            setup_tester_ssh_connection, mender_dist_packages_versions["mender-client"], package_name="mender-update",
        )

        # Install the deb packages. On failure, install the missing dependencies.
        result = setup_tester_ssh_connection.run(
            "sudo DEBIAN_FRONTEND=noninteractive apt install --yes ./"
            + package_filename(mender_dist_packages_versions["mender-client"]).replace("client", "update")
        )
        assert (
            "Unpacking mender-update ("
            + mender_dist_packages_versions["mender-client"]
            + ")"
            in result.stdout
        )
        assert (
            "Setting up mender-update ("
            + mender_dist_packages_versions["mender-client"]
            + ")"
            in result.stdout
        )

        result = setup_tester_ssh_connection.run(
            "sudo DEBIAN_FRONTEND=noninteractive apt install --yes ./"
            + package_filename(mender_dist_packages_versions["mender-client"]).replace("client", "auth")
        )
        assert (
            "Unpacking mender-auth ("
            + mender_dist_packages_versions["mender-client"]
            + ")"
            in result.stdout
        )
        assert (
            "Setting up mender-auth ("
            + mender_dist_packages_versions["mender-client"]
            + ")"
            in result.stdout
        )

        # Install the client meta-package also
        result = setup_tester_ssh_connection.run(
            "sudo DEBIAN_FRONTEND=noninteractive apt install --yes ./"
            + package_filename(mender_dist_packages_versions["mender-client"])
        )

        self.check_mender_client_version(setup_tester_ssh_connection, mender_version)

        self.check_installed_files(setup_tester_ssh_connection, "raspberrypi")

        # Default setup expects ServerURL hosted.mender.io
        result = setup_tester_ssh_connection.sudo("cat /etc/mender/mender.conf")
        assert '"ServerURL": "https://hosted.mender.io"' in result.stdout

        # self.check_systemd_start_full_cycle(setup_tester_ssh_connection)

    @pytest.mark.usefixtures("setup_test_container")
    def test_remove_stop(
        self, setup_tester_ssh_connection, mender_dist_packages_versions
    ):
        result = setup_tester_ssh_connection.run("sudo dpkg --remove mender-client")
        assert (
            "Removing mender-client ("
            + mender_dist_packages_versions["mender-client"]
            + ")"
            in result.stdout
        )

    @pytest.mark.usefixtures("setup_test_container")
    def test_purge(self, setup_tester_ssh_connection, mender_dist_packages_versions):
        result = setup_tester_ssh_connection.run("sudo dpkg --purge mender-client")
        assert (
            "Purging configuration files for mender-client ("
            + mender_dist_packages_versions["mender-client"]
            + ")"
            in result.stdout
        )

        self.check_removed_files(setup_tester_ssh_connection, purge=True)

