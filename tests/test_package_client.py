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

from helpers import Helpers
from setup import setup_tester_raspbian_host
from setup import setup_tester_ssh_connection

class TestPackageMenderClientBasicUsage():

    expected_update_modules = ["deb", "directory", "rpm", "script", "single-file"]
    expected_inventory_files = ["mender-inventory-bootloader-integration",
                                "mender-inventory-hostinfo",
                                "mender-inventory-network",
                                "mender-inventory-os",
                                "mender-inventory-rootfs-type"]
    expected_indentity_files = ["mender-device-identity"]

    expected_copyright_md5sum = "269720c1a5608250abd54a7818f369f6"

    @pytest.mark.usefixtures("setup_tester_raspbian_host")
    def test_install_package(self, setup_tester_ssh_connection):
        result = setup_tester_ssh_connection.run('uname -a', hide=True)
        assert "raspberrypi" in result.stdout

        Helpers.upload_deb_package(setup_tester_ssh_connection)

        result = setup_tester_ssh_connection.run('sudo dpkg -i ' + Helpers.package_filename("mender-client"), hide=True)
        assert "Unpacking mender-client (" + Helpers.packages_version + ")" in result.stdout
        assert "Setting up mender-client (" + Helpers.packages_version + ")" in result.stdout

        result = setup_tester_ssh_connection.run('mender -version', hide=True)
        assert Helpers.mender_version in result.stdout

        # Check installed files
        setup_tester_ssh_connection.run('test -x /usr/bin/mender', hide=True)
        setup_tester_ssh_connection.run('test -d /usr/share/mender/modules/v3', hide=True)
        for module in self.expected_update_modules:
            module_path = os.path.join("/usr/share/mender/modules/v3", module)
            setup_tester_ssh_connection.run('test -x {mod}'.format(mod=module_path), hide=True)
        setup_tester_ssh_connection.run('test -d /usr/share/mender/modules/v3', hide=True)
        for inventory in self.expected_inventory_files:
            inventory_path = os.path.join("/usr/share/mender/inventory", inventory)
            setup_tester_ssh_connection.run('test -x {invent}'.format(invent=inventory_path), hide=True)
        for identity in self.expected_indentity_files:
            identity_path = os.path.join("/usr/share/mender/identity", identity)
            setup_tester_ssh_connection.run('test -x {ident}'.format(ident=identity_path), hide=True)
        setup_tester_ssh_connection.run('test -d /etc/mender', hide=True)
        setup_tester_ssh_connection.run('test -f /etc/mender/mender.conf', hide=True)
        setup_tester_ssh_connection.run('test -f /etc/mender/mender.conf.demo', hide=True)
        setup_tester_ssh_connection.run('test -f /etc/mender/mender.conf.production', hide=True)
        setup_tester_ssh_connection.run('cmp /etc/mender/mender.conf.production /etc/mender/mender.conf', hide=True)
        setup_tester_ssh_connection.run('test -f /lib/systemd/system/mender.service', hide=True)

        # Northern.tech copyright file
        setup_tester_ssh_connection.run('test -f /usr/share/doc/mender-client/copyright', hide=True)
        result = setup_tester_ssh_connection.run('md5sum /usr/share/doc/mender-client/copyright', hide=True)
        assert result.stdout.split(' ')[0] == self.expected_copyright_md5sum

    @pytest.mark.usefixtures("setup_tester_raspbian_host")
    def test_configure_client(self, setup_tester_ssh_connection):
        """Configures the client following the documented steps:
        https://docs.mender.io/2.0/client-configuration/installing
        """

        setup_tester_ssh_connection.run('sudo cp /etc/mender/mender.conf.demo /etc/mender/mender.conf', hide=True)
        setup_tester_ssh_connection.run('TENANT_TOKEN="dummy"; sudo sed -i "s/Paste your Hosted Mender token here/$TENANT_TOKEN/" /etc/mender/mender.conf', hide=True)
        setup_tester_ssh_connection.run('sudo mkdir -p /var/lib/mender', hide=True)
        setup_tester_ssh_connection.run('echo "device_type=raspberrypi3" | sudo tee /var/lib/mender/device_type', hide=True)

    @pytest.mark.usefixtures("setup_tester_raspbian_host")
    def test_start_client(self, setup_tester_ssh_connection):

        # Force key generation in advance, as this takes quite a while
        # It returns error because the Tenant Token is invalid, but we don't care
        setup_tester_ssh_connection.run('sudo mender -bootstrap || true', hide=True)

        # Start the service and give time to boot and go once over the full cycle
        #  (retry poll interval: 30s)
        setup_tester_ssh_connection.run('sudo systemctl enable mender && sudo systemctl start mender', hide=True)
        time.sleep(50)
        result = setup_tester_ssh_connection.run('sudo journalctl -u mender --no-pager', hide=True)

        # Check correct boot
        assert "Started Mender OTA update service." in result.stdout
        assert "Loaded configuration file" in result.stdout
        assert "No dual rootfs configuration present" in result.stdout

        # Check transition Sync to Idle (one full cycle)
        assert "authorize failed: transient error: authorization request failed" in result.stdout
        assert "State transition: authorize [Sync] -> authorize-wait [Idle]" in result.stdout

    @pytest.mark.usefixtures("setup_tester_raspbian_host")
    def test_stop_client(self, setup_tester_ssh_connection):
        setup_tester_ssh_connection.run('sudo systemctl stop mender', hide=True)
        time.sleep(1)
        result = setup_tester_ssh_connection.run('sudo journalctl -u mender --no-pager', hide=True)

        # Check authorization failure
        assert "Stopping Mender OTA update service..." in result.stdout
        assert "Stopped Mender OTA update service." in result.stdout

    @pytest.mark.usefixtures("setup_tester_raspbian_host")
    def test_remove_package(self, setup_tester_ssh_connection):
        result = setup_tester_ssh_connection.run('sudo dpkg -r mender-client', hide=True)
        assert "Removing mender-client (" + Helpers.packages_version + ")" in result.stdout

        # Check directories
        setup_tester_ssh_connection.run('test ! -f /usr/bin/mender', hide=True)
        setup_tester_ssh_connection.run('test ! -e /usr/share/mender', hide=True)
        setup_tester_ssh_connection.run('test -d /etc/mender', hide=True)
        setup_tester_ssh_connection.run('test -d /var/lib/mender/', hide=True)

    @pytest.mark.usefixtures("setup_tester_raspbian_host")
    def test_purge_package(self, setup_tester_ssh_connection):
        result = setup_tester_ssh_connection.run('sudo dpkg -P mender-client', hide=True)
        assert "Purging configuration files for mender-client (" + Helpers.packages_version + ")" in result.stdout

        # Check directories
        setup_tester_ssh_connection.run('test ! -f /usr/bin/mender', hide=True)
        setup_tester_ssh_connection.run('test ! -e /usr/share/mender', hide=True)
        setup_tester_ssh_connection.run('test ! -e /etc/mender', hide=True)
        setup_tester_ssh_connection.run('test -d /var/lib/mender/', hide=True)

        # In future releases, device_type shall be removed
        setup_tester_ssh_connection.run('test -f /var/lib/mender/device_type', hide=True)

        # Infuture releases, systemd shall be cleaned up
        setup_tester_ssh_connection.run('test -h /etc/systemd/system/multi-user.target.wants/mender.service', hide=True)

    @pytest.mark.usefixtures("setup_tester_raspbian_host")
    @pytest.mark.skip
    def test_reboot_device(self, setup_tester_ssh_connection):
        assert False, "TODO: Test not implemented"
