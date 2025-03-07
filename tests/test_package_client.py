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
import time
import os.path

from helpers import package_filename, upload_deb_package, check_installed
from mender_test_containers.helpers import *


@pytest.mark.golangclient
@pytest.mark.mender_client
class PackageMenderClientChecker:

    expected_update_modules = ["deb", "directory", "rpm", "script", "single-file"]
    expected_inventory_files = [
        "mender-inventory-bootloader-integration",
        "mender-inventory-hostinfo",
        "mender-inventory-network",
        "mender-inventory-os",
        "mender-inventory-rootfs-type",
    ]
    expected_indentity_files = ["mender-device-identity"]

    expected_copyright_from_l2_md5sum = "39a30292da940b7ce011150e8c8d5e4f"

    def check_mender_client_version(self, ssh_connection, mender_version):
        if mender_version != "master":
            result = ssh_connection.run("mender -version")
            assert mender_version in result.stdout

    def check_installed_files(self, ssh_connection):
        ssh_connection.run("test -x /usr/bin/mender")
        ssh_connection.run("test -d /usr/share/mender/modules/v3")
        for module in self.expected_update_modules:
            module_path = os.path.join("/usr/share/mender/modules/v3", module)
            ssh_connection.run("test -x {mod}".format(mod=module_path))
        ssh_connection.run("test -d /usr/share/mender/modules/v3")
        for inventory in self.expected_inventory_files:
            inventory_path = os.path.join("/usr/share/mender/inventory", inventory)
            ssh_connection.run("test -x {invent}".format(invent=inventory_path))
        for identity in self.expected_indentity_files:
            identity_path = os.path.join("/usr/share/mender/identity", identity)
            ssh_connection.run("test -x {ident}".format(ident=identity_path))
        ssh_connection.run("test -d /etc/mender")
        ssh_connection.run("test -f /etc/mender/scripts/version")
        result = ssh_connection.run("cat /etc/mender/scripts/version")
        assert "3" == result.stdout
        ssh_connection.run("test -f /lib/systemd/system/mender-client.service")
        ssh_connection.run(
            "test -f /etc/systemd/system/multi-user.target.wants/mender-client.service"
        )
        ssh_connection.run("test -f /usr/share/doc/mender-client/examples/demo.crt")

        # Northern.tech copyright file
        ssh_connection.run("test -f /usr/share/doc/mender-client/copyright")
        result = ssh_connection.run(
            "tail -n +2 /usr/share/doc/mender-client/copyright | md5sum"
        )
        assert result.stdout.split(" ")[0] == self.expected_copyright_from_l2_md5sum

    def configure_mender_client(self, ssh_connection):
        """
        Manually configures the mender-client for the rest of the test. Before mender-client 4.0
        this was done by mender setup command and now it is handled by the mender-setup tool.
        """

        default_configuration = """
{
    "HttpsClient": {},
    "Security": {},
    "Connectivity": {},
    "DeviceTypeFile": "/var/lib/mender/device_type",
    "DBus": {
        "Enabled": true
    },
    "UpdatePollIntervalSeconds": 1800,
    "InventoryPollIntervalSeconds": 28800,
    "RetryPollIntervalSeconds": 300,
    "TenantToken": "Paste your Hosted Mender token here",
    "Servers": [
        {
            "ServerURL": "https://hosted.mender.io"
        }
    ]
}
"""
        ssh_connection.run(
            "echo '" + default_configuration + "' | sudo tee /etc/mender/mender.conf"
        )
        ssh_connection.run("sudo mkdir -p /var/lib/mender/")
        ssh_connection.run(
            "echo device_type=raspberrypi | sudo tee /var/lib/mender/device_type"
        )
        ssh_connection.run("sudo systemctl restart mender-client")

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
        result = ssh_connection.run("pgrep mender")
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

    def check_removed_files(self, ssh_connection, purge):
        # Check first that mender process has been stopped
        result = ssh_connection.run("pgrep mender", warn=True)
        assert result.exited == 1

        ssh_connection.run("test ! -f /usr/bin/mender")
        ssh_connection.run("test ! -e /usr/share/mender")
        ssh_connection.run("test ! -f /lib/systemd/system/mender-client.service")
        ssh_connection.run(
            "test ! -f /etc/systemd/system/multi-user.target.wants/mender-client.service"
        )
        ssh_connection.run("test ! -f /usr/share/doc/mender-client/examples/demo.crt")
        ssh_connection.run("test -d /var/lib/mender/")
        if purge:
            ssh_connection.run("test ! -f /etc/mender/scripts/version")
        else:
            ssh_connection.run("test -f /etc/mender/scripts/version")
            # Purging mender-client removes the configuration, even if it was created externally
            ssh_connection.run("test -f /etc/mender/mender.conf")
            ssh_connection.run("test -f /var/lib/mender/device_type")

        result = ssh_connection.run("sudo journalctl -u mender-client --no-pager")
        assert "Stopping Mender OTA update service..." in result.stdout
        assert "Stopped Mender OTA update service." in result.stdout


@pytest.mark.golangclient
class TestPackageMenderClientDefaults(PackageMenderClientChecker):
    """Tests installation, setup, start, removal and purge of mender-client deb package with
    in non-interactive method (i.e. default configuration).
    """

    @pytest.mark.usefixtures("setup_test_container")
    def test_install_configure_start(
        self, setup_tester_ssh_connection, mender_dist_packages_versions, mender_version
    ):
        result = setup_tester_ssh_connection.run("uname -a")
        assert "raspberrypi" in result.stdout

        upload_deb_package(
            setup_tester_ssh_connection,
            mender_dist_packages_versions["mender-client"],
            package_name="mender-client",
        )

        # Install the deb package. On failure, install the missing dependencies.
        setup_tester_ssh_connection.run(
            "sudo DEBIAN_FRONTEND=noninteractive dpkg --install "
            + package_filename(
                mender_dist_packages_versions["mender-client"],
                package_name="mender-client",
            )
            + "|| sudo apt-get --fix-broken --assume-yes install"
        )
        check_installed(setup_tester_ssh_connection, "mender-client")

        self.check_mender_client_version(setup_tester_ssh_connection, mender_version)

        self.check_installed_files(setup_tester_ssh_connection)

        self.configure_mender_client(setup_tester_ssh_connection)

        self.check_systemd_start_full_cycle(setup_tester_ssh_connection)

    def test_service_starts_after_reboot(
        self, setup_test_container, setup_tester_ssh_connection,
    ):
        # Reboot in the background, so that SSH can exit properly
        setup_tester_ssh_connection.run("sleep 1 && sudo reboot &")

        # Wait for the reboot to actually start before calling wait_for_container_boot
        time.sleep(10)
        wait_for_container_boot(setup_test_container.container_id)

        # Check first that mender process is running
        result = setup_tester_ssh_connection.run("pgrep mender")
        assert result.exited == 0

        result = setup_tester_ssh_connection.run(
            "sudo journalctl -u mender-client --no-pager"
        )

        # Check Mender service start after device reboot
        assert "Started Mender OTA update service." in result.stdout
        assert "Loaded configuration file" in result.stdout
        assert "No dual rootfs configuration present" in result.stdout

    @pytest.mark.usefixtures("setup_test_container")
    def test_remove_stop(self, setup_tester_ssh_connection):
        setup_tester_ssh_connection.run("sudo dpkg --remove mender-client")

        self.check_removed_files(setup_tester_ssh_connection, purge=False)

    @pytest.mark.usefixtures("setup_test_container")
    def test_purge(self, setup_tester_ssh_connection):
        setup_tester_ssh_connection.run("sudo dpkg --purge mender-client")
        check_installed(setup_tester_ssh_connection, "mender-client", installed=False)

        self.check_removed_files(setup_tester_ssh_connection, purge=True)
