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

from helpers import Helpers
from setup import setup_tester_raspbian_host
from setup import setup_tester_ssh_connection

class TestPackageMenderClientBasicUsage():

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

        #TODO: check for inventory scripts, update modules, ...

    @pytest.mark.usefixtures("setup_tester_raspbian_host")
    def test_configure_client(self, setup_tester_ssh_connection):
        """Configures the client following the documented steps:
        https://docs.mender.io/2.0/client-configuration/installing
        """

        setup_tester_ssh_connection.run('sudo cp /etc/mender/mender.conf.demo /etc/mender/mender.conf', hide=True)
        setup_tester_ssh_connection.run('TENANT_TOKEN="dummy"; sudo sed -i "s/Paste your Hosted Mender token here/$TENANT_TOKEN/" /etc/mender/mender.conf', hide=True)
        setup_tester_ssh_connection.run('sudo mkdir -p /var/lib/mender', hide=True)
        setup_tester_ssh_connection.run('echo "device_type=raspberrypi3" | sudo tee /var/lib/mender/device_type', hide=True)

        #TODO: some checks??

    @pytest.mark.usefixtures("setup_tester_raspbian_host")
    def test_start_client(self, setup_tester_ssh_connection):
        result = setup_tester_ssh_connection.run('sudo systemctl enable mender && sudo systemctl start mender', hide=True)

        # Give enough time to boot and go once over the full cycle
        #  (generating device keys: ~20s + retry poll interval: 30s)
        time.sleep(120)
        result = setup_tester_ssh_connection.run('sudo journalctl -u mender --no-pager', hide=True)

        # TODO: Can we force the key generation earlier with mender -bootstrap?

        # Check correct boot
        assert "Started Mender OTA update service." in result.stdout
        assert "Loaded configuration file" in result.stdout
        assert "No dual rootfs configuration present" in result.stdout

        # Check authorization failure
        assert "authorize failed: transient error: authorization request failed" in result.stdout
        assert "State transition: authorize [Sync] -> authorize-wait [Idle]" in result.stdout

        #TODO: Parsing and proper checking of the state machine

    @pytest.mark.usefixtures("setup_tester_raspbian_host")
    def test_stop_client(self, setup_tester_ssh_connection):
        result = setup_tester_ssh_connection.run('sudo systemctl stop mender', hide=True)
        time.sleep(1)
        result = setup_tester_ssh_connection.run('sudo journalctl -u mender --no-pager', hide=True)

        # Check authorization failure
        assert "Stopping Mender OTA update service..." in result.stdout
        assert "Stopped Mender OTA update service." in result.stdout

        #TODO: Check nothing else betwwen stopping and stopped

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
