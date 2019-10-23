#!/usr/bin/python3
# Copyright 2019 Northern.tech AS
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        https://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

import pytest
import time
import os.path

from helpers import package_filename, upload_deb_package
from mender_test_containers.helpers import *

class TestPackageMenderClientBasicUsage():

    expected_update_modules = ["deb", "directory", "rpm", "script", "single-file"]
    expected_inventory_files = ["mender-inventory-bootloader-integration",
                                "mender-inventory-hostinfo",
                                "mender-inventory-network",
                                "mender-inventory-os",
                                "mender-inventory-rootfs-type"]
    expected_indentity_files = ["mender-device-identity"]

    expected_copyright_md5sum = "269720c1a5608250abd54a7818f369f6"

    @pytest.mark.usefixtures("setup_test_container")
    def test_install_package(self, setup_tester_ssh_connection, mender_dist_packages_versions, mender_version):
        result = setup_tester_ssh_connection.run('uname -a')
        assert "raspberrypi" in result.stdout

        upload_deb_package(setup_tester_ssh_connection, mender_dist_packages_versions["mender-client"])

        result = setup_tester_ssh_connection.run('sudo dpkg -i ' + package_filename(mender_dist_packages_versions["mender-client"]))
        assert "Unpacking mender-client (" + mender_dist_packages_versions["mender-client"] + ")" in result.stdout
        assert "Setting up mender-client (" + mender_dist_packages_versions["mender-client"] + ")" in result.stdout

        result = setup_tester_ssh_connection.run('mender -version')
        assert mender_version in result.stdout

        # Check installed files
        setup_tester_ssh_connection.run('test -x /usr/bin/mender')
        setup_tester_ssh_connection.run('test -d /usr/share/mender/modules/v3')
        for module in self.expected_update_modules:
            module_path = os.path.join("/usr/share/mender/modules/v3", module)
            setup_tester_ssh_connection.run('test -x {mod}'.format(mod=module_path))
        setup_tester_ssh_connection.run('test -d /usr/share/mender/modules/v3')
        for inventory in self.expected_inventory_files:
            inventory_path = os.path.join("/usr/share/mender/inventory", inventory)
            setup_tester_ssh_connection.run('test -x {invent}'.format(invent=inventory_path))
        for identity in self.expected_indentity_files:
            identity_path = os.path.join("/usr/share/mender/identity", identity)
            setup_tester_ssh_connection.run('test -x {ident}'.format(ident=identity_path))
        setup_tester_ssh_connection.run('test -d /etc/mender')
        setup_tester_ssh_connection.run('test -f /etc/mender/mender.conf')
        setup_tester_ssh_connection.run('test -f /etc/mender/mender.conf.demo')
        setup_tester_ssh_connection.run('test -f /etc/mender/mender.conf.production')
        setup_tester_ssh_connection.run('cmp /etc/mender/mender.conf.production /etc/mender/mender.conf')
        setup_tester_ssh_connection.run('test -f /lib/systemd/system/mender.service')

        # Northern.tech copyright file
        setup_tester_ssh_connection.run('test -f /usr/share/doc/mender-client/copyright')
        result = setup_tester_ssh_connection.run('md5sum /usr/share/doc/mender-client/copyright')
        assert result.stdout.split(' ')[0] == self.expected_copyright_md5sum

    @pytest.mark.usefixtures("setup_test_container")
    def test_configure_client(self, setup_tester_ssh_connection):
        """Configures the client following the documented steps:
        https://docs.mender.io/2.0/client-configuration/installing
        """

        setup_tester_ssh_connection.run('sudo cp /etc/mender/mender.conf.demo /etc/mender/mender.conf')
        setup_tester_ssh_connection.run('TENANT_TOKEN="dummy"; sudo sed -i "s/Paste your Hosted Mender token here/$TENANT_TOKEN/" /etc/mender/mender.conf')
        setup_tester_ssh_connection.run('sudo mkdir -p /var/lib/mender')
        setup_tester_ssh_connection.run('echo "device_type=raspberrypi3" | sudo tee /var/lib/mender/device_type')

    @pytest.mark.usefixtures("setup_test_container")
    def test_start_client(self, setup_tester_ssh_connection):

        # Force key generation in advance, as this takes quite a while
        # It returns error because the Tenant Token is invalid, but we don't care
        setup_tester_ssh_connection.run('sudo mender -bootstrap || true')

        # Start the service and give time to boot and go once over the full cycle
        #  (retry poll interval: 30s)
        setup_tester_ssh_connection.run('sudo systemctl enable mender && sudo systemctl start mender')
        time.sleep(50)
        result = setup_tester_ssh_connection.run('sudo journalctl -u mender --no-pager')

        # Check correct boot
        assert "Started Mender OTA update service." in result.stdout
        assert "Loaded configuration file" in result.stdout
        assert "No dual rootfs configuration present" in result.stdout

        # Check transition Sync to Idle (one full cycle)
        assert "authorize failed: transient error: authorization request failed" in result.stdout
        assert "State transition: authorize [Sync] -> authorize-wait [Idle]" in result.stdout

    @pytest.mark.usefixtures("setup_test_container")
    def test_stop_client(self, setup_tester_ssh_connection):
        setup_tester_ssh_connection.run('sudo systemctl stop mender')
        time.sleep(1)
        result = setup_tester_ssh_connection.run('sudo journalctl -u mender --no-pager')

        # Check authorization failure
        assert "Stopping Mender OTA update service..." in result.stdout
        assert "Stopped Mender OTA update service." in result.stdout

    @pytest.mark.usefixtures("setup_test_container")
    def test_remove_package(self, setup_tester_ssh_connection, mender_dist_packages_versions):
        result = setup_tester_ssh_connection.run('sudo dpkg -r mender-client')
        assert "Removing mender-client (" + mender_dist_packages_versions["mender-client"] + ")" in result.stdout

        # Check directories
        setup_tester_ssh_connection.run('test ! -f /usr/bin/mender')
        setup_tester_ssh_connection.run('test ! -e /usr/share/mender')
        setup_tester_ssh_connection.run('test -d /etc/mender')
        setup_tester_ssh_connection.run('test -d /var/lib/mender/')

    @pytest.mark.usefixtures("setup_test_container")
    def test_purge_package(self, setup_tester_ssh_connection, mender_dist_packages_versions):
        result = setup_tester_ssh_connection.run('sudo dpkg -P mender-client')
        assert "Purging configuration files for mender-client (" + mender_dist_packages_versions["mender-client"] + ")" in result.stdout

        # Check directories
        setup_tester_ssh_connection.run('test ! -f /usr/bin/mender')
        setup_tester_ssh_connection.run('test ! -e /usr/share/mender')
        setup_tester_ssh_connection.run('test ! -e /etc/mender')
        setup_tester_ssh_connection.run('test -d /var/lib/mender/')

        # In future releases, device_type shall be removed
        setup_tester_ssh_connection.run('test -f /var/lib/mender/device_type')

        # Infuture releases, systemd shall be cleaned up
        setup_tester_ssh_connection.run('test -h /etc/systemd/system/multi-user.target.wants/mender.service')

class TestPackageMenderClientSystemd():

    def test_mender_service_starts_after_reboot(self, setup_test_container, setup_tester_ssh_connection, mender_dist_packages_versions):
        conn = setup_tester_ssh_connection
        upload_deb_package(conn, mender_dist_packages_versions["mender-client"])

        conn.run('sudo dpkg -i ' + package_filename(mender_dist_packages_versions["mender-client"]))
        conn.run('sudo cp /etc/mender/mender.conf.demo /etc/mender/mender.conf')
        conn.run('TENANT_TOKEN="dummy"; sudo sed -i "s/Paste your Hosted Mender token here/$TENANT_TOKEN/" /etc/mender/mender.conf')
        conn.run('sudo mkdir -p /var/lib/mender')
        conn.run('echo "device_type=raspberrypi3" | sudo tee /var/lib/mender/device_type')

        conn.run('sudo systemctl enable mender')

        # Reboot in the background, so that SSH can exit properly
        conn.run('sleep 1 && sudo reboot &')

        # Wait for the reboot to actually start before calling wait_for_container_boot
        time.sleep(10)
        wait_for_container_boot(setup_test_container.container_id)

        result = conn.run('sudo journalctl -u mender --no-pager')

        # Check Mender service start after device reboot
        assert "Started Mender OTA update service." in result.stdout
        assert "Loaded configuration file" in result.stdout
        assert "No dual rootfs configuration present" in result.stdout
