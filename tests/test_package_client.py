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
import subprocess
import time
from fabric import Connection

def wait_for_raspbian_boot(docker_container_id):
    ready = False
    timeout = time.time() + 60*3
    while not ready and time.time() < timeout:
        time.sleep(5)
        output = subprocess.check_output("docker logs {} 2>&1".format(docker_container_id), shell=True)

        if "Raspbian GNU/Linux 9 raspberrypi ttyAMA0" in output.decode("utf-8"):
            ready = True
            time.sleep(5)

    return ready

@pytest.fixture(scope="class")
def standard_setup():
    output = subprocess.check_output("docker run --rm --network host -d mender-dist-packages-testing", shell=True)
    docker_container_id = output.decode("utf-8").split("\n")[0]

    ready = wait_for_raspbian_boot(docker_container_id)

    assert ready, "Raspbian QEMU image did not boot. Aborting"
    yield
    subprocess.check_output("docker stop {}".format(docker_container_id), shell=True)

conn = None
@pytest.fixture(scope="class")
def ssh_connection():
    with Connection(host="localhost",
                user="pi",
                port=5555,
                connect_timeout=30,
                connect_kwargs={
                    "key_filename": "docker-files/ssh-keys/key",
                } ) as conn:
        yield conn

# TODO: globaly define version, pakcage names, etc
def upload_package(ssh_connection, package_name = "mender"):
    ssh_connection.put("../output/mender_2.0.0b1-1_armhf.deb")

class TestPackageClientInstallConfigureStart():

    @pytest.mark.usefixtures("standard_setup")
    def test_install_package(self, ssh_connection):
        result = ssh_connection.run('uname -a', hide=True)
        assert "raspberrypi" in result.stdout

        upload_package(ssh_connection)

        result = ssh_connection.run('sudo dpkg -i mender_2.0.0b1-1_armhf.deb', hide=True)
        assert "Unpacking mender (2.0.0b1-1)" in result.stdout
        assert "Setting up mender (2.0.0b1-1)" in result.stdout

        result = ssh_connection.run('mender -version', hide=True)
        assert "2.0.0b1" in result.stdout

        #TODO: check for inventory scripts, update modules, ...

    @pytest.mark.usefixtures("standard_setup")
    def test_configure_client(self, ssh_connection):
        """Configures the client following the documented steps:
        https://docs.mender.io/2.0/client-configuration/installing
        """

        ssh_connection.run('sudo cp /etc/mender/mender.conf.demo /etc/mender/mender.conf', hide=True)
        ssh_connection.run('TENANT_TOKEN="dummy"; sudo sed -i "s/Paste your Hosted Mender token here/$TENANT_TOKEN/" /etc/mender/mender.conf', hide=True)
        ssh_connection.run('sudo mkdir -p /var/lib/mender', hide=True)
        ssh_connection.run('echo "device_type=raspberrypi3" | sudo tee /var/lib/mender/device_type', hide=True)

        #TODO: some checks??

    @pytest.mark.usefixtures("standard_setup")
    def test_start_client(self, ssh_connection):
        result = ssh_connection.run('sudo systemctl enable mender && sudo systemctl start mender', hide=True)

        # Give enough time to boot and go once over the full cycle
        #  (generating device keys: ~20s + retry poll interval: 30s)
        time.sleep(120)
        result = ssh_connection.run('sudo journalctl -u mender --no-pager', hide=True)

        # TODO: Can we force the key generation earlier with mender -bootstrap?

        # Check correct boot
        assert "Started Mender OTA update service." in result.stdout
        assert "Loaded configuration file" in result.stdout
        assert "No dual rootfs configuration present" in result.stdout

        # Check authorization failure
        assert "authorize failed: transient error: authorization request failed" in result.stdout
        assert "State transition: authorize [Sync] -> authorize-wait [Idle]" in result.stdout

        #TODO: Parsing and proper checking of the state machine

    @pytest.mark.usefixtures("standard_setup")
    def test_stop_client(self, ssh_connection):
        result = ssh_connection.run('sudo systemctl stop mender', hide=True)
        time.sleep(1)
        result = ssh_connection.run('sudo journalctl -u mender --no-pager', hide=True)

        # Check authorization failure
        assert "Stopping Mender OTA update service..." in result.stdout
        assert "Stopped Mender OTA update service." in result.stdout

        #TODO: Check nothing else betwwen stopping and stopped

    @pytest.mark.usefixtures("standard_setup")
    def test_remove_package(self, ssh_connection):
        result = ssh_connection.run('sudo dpkg -r mender', hide=True)
        assert "Removing mender (2.0.0b1-1)" in result.stdout

        # Check directories
        ssh_connection.run('test ! -f /usr/bin/mender', hide=True)
        ssh_connection.run('test ! -e /usr/share/mender', hide=True)
        ssh_connection.run('test -d /etc/mender', hide=True)
        ssh_connection.run('test -d /var/lib/mender/', hide=True)

    @pytest.mark.usefixtures("standard_setup")
    def test_purge_package(self, ssh_connection):
        result = ssh_connection.run('sudo dpkg -P mender', hide=True)
        assert "Purging configuration files for mender (2.0.0b1-1)" in result.stdout

        # Check directories
        ssh_connection.run('test ! -f /usr/bin/mender', hide=True)
        ssh_connection.run('test ! -e /usr/share/mender', hide=True)
        ssh_connection.run('test ! -e /etc/mender', hide=True)
        ssh_connection.run('test -d /var/lib/mender/', hide=True)

        # In future releases, device_type shall be removed
        ssh_connection.run('test -f /var/lib/mender/device_type', hide=True)

        # Infuture releases, systemd shall be cleaned up
        ssh_connection.run('test -h /etc/systemd/system/multi-user.target.wants/mender.service', hide=True)

    @pytest.mark.usefixtures("standard_setup")
    @pytest.mark.skip
    def test_reboot_device(self, ssh_connection):
        assert False, "TODO: Test not implemented"
