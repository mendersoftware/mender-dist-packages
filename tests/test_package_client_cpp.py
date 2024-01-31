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

expected_copyright_from_l2_md5sum = "39a30292da940b7ce011150e8c8d5e4f"


def verify_file_exists(ssh_conn, files):
    for file in files:
        file_name = file["name"]
        if file["type"] == "executable":
            ssh_conn.run(f"test -x {file_name}")
        elif file["type"] == "directory":
            ssh_conn.run(f"test -d {file_name}")
        elif file["type"] == "file":
            ssh_conn.run(f"test -f {file_name}")
        elif file.get("contents", False):
            result = ssh_conn.run(f"cat {file_name}")
            assert file["contents"] == result.stdout
        else:
            raise Exception("Unknown file type check")


all_files = [
    {"name": "/usr/bin/mender-update", "type": "executable",},
    {"name": "/usr/bin/mender-auth", "type": "executable",},
    {"name": "/usr/share/mender/modules/v3/", "type": "directory",},
    #
    # Inventory scripts symlinked to /etc/ as conf files
    #
    {"name": "/usr/share/mender/inventory", "type": "directory",},
    {
        "name": "/usr/share/mender/inventory/mender-inventory-bootloader-integration",
        "type": "file",
    },
    {"name": "/usr/share/mender/inventory/mender-inventory-hostinfo", "type": "file",},
    {"name": "/usr/share/mender/inventory/mender-inventory-network", "type": "file",},
    {"name": "/usr/share/mender/inventory/mender-inventory-os", "type": "file",},
    {"name": "/usr/share/mender/inventory/mender-inventory-provides", "type": "file",},
    {
        "name": "/usr/share/mender/inventory/mender-inventory-rootfs-type",
        "type": "file",
    },
    {
        "name": "/usr/share/mender/inventory/mender-inventory-update-modules",
        "type": "file",
    },
    {"name": "/etc/mender/inventory", "type": "directory",},
    {
        "name": "/etc/mender/inventory/mender-inventory-bootloader-integration",
        "type": "file",
    },
    {"name": "/etc/mender/inventory/mender-inventory-hostinfo", "type": "executable",},
    {"name": "/etc/mender/inventory/mender-inventory-network", "type": "executable",},
    {"name": "/etc/mender/inventory/mender-inventory-os", "type": "executable",},
    {"name": "/etc/mender/inventory/mender-inventory-provides", "type": "file",},
    {
        "name": "/etc/mender/inventory/mender-inventory-rootfs-type",
        "type": "executable",
    },
    {"name": "/etc/mender/inventory/mender-inventory-update-modules", "type": "file",},
    #
    # Update modules
    #
    {"name": "/usr/share/mender/modules/v3/", "type": "directory",},
    {"name": "/usr/share/mender/modules/v3/deb", "type": "executable",},
    {"name": "/usr/share/mender/modules/v3/directory", "type": "executable",},
    {"name": "/usr/share/mender/modules/v3/docker", "type": "executable",},
    {"name": "/usr/share/mender/modules/v3/rootfs-image", "type": "executable",},
    {"name": "/usr/share/mender/modules/v3/rpm", "type": "executable",},
    {"name": "/usr/share/mender/modules/v3/script", "type": "executable",},
    {"name": "/usr/share/mender/modules/v3/single-file", "type": "executable",},
    #
    # device identity files
    #
    {"name": "/usr/share/mender/identity", "type": "directory",},
    {
        "name": "/usr/share/mender/identity/mender-device-identity",
        "type": "executable",
    },
    #
    # Configuration files
    # Installed by mender-setup
    #
    # {
    #     "name": "/etc/mender/",
    #     "type": "directory",
    # },
    # {
    #     "name": "/etc/mender/mender.conf",
    #     "type": "file",
    # },
    {"name": "/etc/mender/scripts", "type": "directory",},
    {"name": "/etc/mender/scripts/version", "type": "file", "contents": "3",},
    #
    # Systemd services
    #
    {"name": "/lib/systemd/system/mender-updated.service", "type": "file",},
    {"name": "/lib/systemd/system/mender-authd.service", "type": "file",},
    #
    # D-Bus policy files
    #
    {
        "name": "/usr/share/dbus-1/system.d/io.mender.AuthenticationManager.conf",
        "type": "file",
    },
    #
    # Demo certificate
    #
    {"name": "/usr/share/doc/mender-auth/examples/demo.crt", "type": "file",},
    #
    # Device type file
    # Installed by mender-setup
    #
    # {
    #     "name": "/var/lib/mender/device_type",
    #     "type": "file",
    #     "contents": "device_type=unknown",
    # },
]


class PackageMenderClientChecker:
    def check_mender_client_version(self, ssh_connection, mender_version):
        result = ssh_connection.run("mender-auth --version")
        if mender_version != "master":
            assert mender_version in result.stdout

        result = ssh_connection.run("mender-update --version")
        if mender_version != "master":
            assert mender_version in result.stdout

    def check_installed_files(self, ssh_connection):
        verify_file_exists(ssh_connection, all_files)
        # Northern.tech copyright file
        ssh_connection.run("test -f /usr/share/doc/mender-client4/copyright")
        result = ssh_connection.run(
            "tail -n +2 /usr/share/doc/mender-client4/copyright | md5sum"
        )
        assert result.stdout.split(" ")[0] == expected_copyright_from_l2_md5sum

    def check_systemd_service(self, ssh_connection):
        result = ssh_connection.run("systemctl is-enabled mender-authd")
        assert result.stdout.strip() == "enabled"

        result = ssh_connection.run("systemctl is-enabled mender-updated")
        assert result.stdout.strip() == "enabled"


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
        # Explicitly accept suite change from "stable" to "oldstable"
        setup_tester_ssh_connection.run(
            "sudo apt-get update --allow-releaseinfo-change-suite"
        )

        # Client meta package
        upload_deb_package(
            setup_tester_ssh_connection,
            mender_dist_packages_versions["mender-client4"],
            package_name="mender-client4",
        )
        # Upload mender-auth
        upload_deb_package(
            setup_tester_ssh_connection,
            mender_dist_packages_versions["mender-client4"],
            package_name="mender-auth",
        )
        # Upload mender-update
        upload_deb_package(
            setup_tester_ssh_connection,
            mender_dist_packages_versions["mender-client4"],
            package_name="mender-update",
        )

        # Install the deb packages. On failure, install the missing dependencies.
        setup_tester_ssh_connection.run(
            "sudo apt install --yes ./"
            + package_filename(
                mender_dist_packages_versions["mender-client"],
                package_name="mender-client",
            ).replace("client", "update")
        )
        check_installed(setup_tester_ssh_connection, "mender-update")

        setup_tester_ssh_connection.run(
            "sudo apt install --yes ./"
            + package_filename(
                mender_dist_packages_versions["mender-client"],
                package_name="mender-client",
            ).replace("client", "auth")
        )
        check_installed(setup_tester_ssh_connection, "mender-auth")

        # Install the client meta-package also
        setup_tester_ssh_connection.run(
            "sudo apt install --yes ./"
            + package_filename(
                mender_dist_packages_versions["mender-client4"],
                package_name="mender-client4",
            )
        )
        check_installed(setup_tester_ssh_connection, "mender-client4")

        self.check_installed_files(setup_tester_ssh_connection)

        self.check_mender_client_version(setup_tester_ssh_connection, mender_version)

        self.check_systemd_service(setup_tester_ssh_connection)

    @pytest.mark.usefixtures("setup_test_container")
    def test_remove_stop(self, setup_tester_ssh_connection):
        setup_tester_ssh_connection.run("sudo dpkg --remove mender-client4")

    @pytest.mark.usefixtures("setup_test_container")
    def test_purge(self, setup_tester_ssh_connection):
        # Dummy configuration
        setup_tester_ssh_connection.run("sudo mkdir --parents /etc/mender/")
        setup_tester_ssh_connection.run(
            "echo 'config' | sudo tee /etc/mender/mender.conf"
        )
        setup_tester_ssh_connection.run("sudo mkdir --parents /var/lib/mender/")
        setup_tester_ssh_connection.run(
            "echo 'device' | sudo tee /var/lib/mender/device_type"
        )

        # Purging mender-client removes the configuration
        result = setup_tester_ssh_connection.run("sudo dpkg --purge mender-client4")
        assert result.return_code == 0
        check_installed(setup_tester_ssh_connection, "mender-client4", installed=False)
        setup_tester_ssh_connection.run("test ! -f /etc/mender/mender.conf")
        setup_tester_ssh_connection.run("test ! -f /var/lib/mender/device_type")
