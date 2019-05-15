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
import os.path

from fabric import Connection
from fabric import Config
from paramiko import SSHException

docker_container_id = None


@pytest.fixture(scope="class")
def setup_tester_raspbian_host():
    output = subprocess.check_output("docker run --rm --network host -d mender-dist-packages-tester", shell=True)
    global docker_container_id
    docker_container_id = output.decode("utf-8").split("\n")[0]

    ready = wait_for_raspbian_boot()

    assert ready, "Raspbian QEMU image did not boot. Aborting"
    yield
    subprocess.check_output("docker stop {}".format(docker_container_id), shell=True)

@pytest.fixture(scope="class")
def setup_tester_ssh_connection():
    yield new_tester_ssh_connection()

def new_tester_ssh_connection():
    key_filename = os.path.join(os.path.dirname(os.path.realpath(__file__)), "docker-files/ssh-keys/key")
    config_hide = Config()
    config_hide.run.hide = True
    with Connection(host="localhost",
                user="pi",
                port=5555,
                config=config_hide,
                connect_timeout=30,
                connect_kwargs={
                    "key_filename": key_filename,
                } ) as conn:

        ready = _probe_ssh_connection(conn)

        assert ready, "SSH connection can not be established. Aborting"
        return conn

def wait_for_raspbian_boot():
    global docker_container_id
    assert docker_container_id is not None
    ready = False
    timeout = time.time() + 60*3
    while not ready and time.time() < timeout:
        time.sleep(5)
        output = subprocess.check_output("docker logs {} 2>&1".format(docker_container_id), shell=True)

        # Check on the last 100 chars only, so that we can detect reboots
        if "Raspbian GNU/Linux 9 raspberrypi ttyAMA0" in output.decode("utf-8")[-100:]:
            ready = True

    return ready

def _probe_ssh_connection(conn):
    ready = False
    timeout = time.time() + 60
    while not ready and time.time() < timeout:
        try:
            result = conn.run('true', hide=True)
            if result.exited == 0:
                ready = True

        except SSHException as e:
            if not (str(e).endswith("Connection reset by peer") or str(e).endswith("Error reading SSH protocol banner")):
                raise e
            time.sleep(5)

    return ready