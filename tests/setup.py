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
from paramiko import SSHException

@pytest.fixture(scope="class")
def setup_tester_raspbian_host():
    output = subprocess.check_output("docker run --rm --network host -d mender-dist-packages-tester", shell=True)
    docker_container_id = output.decode("utf-8").split("\n")[0]

    ready = _wait_for_raspbian_boot(docker_container_id)

    assert ready, "Raspbian QEMU image did not boot. Aborting"
    yield
    subprocess.check_output("docker stop {}".format(docker_container_id), shell=True)

@pytest.fixture(scope="class")
def setup_tester_ssh_connection():
    with Connection(host="localhost",
                user="pi",
                port=5555,
                connect_timeout=30,
                connect_kwargs={
                    "key_filename": "docker-files/ssh-keys/key",
                } ) as conn:

        ready = _probe_ssh_connection(conn)

        assert ready, "SSH connection can not be established. Aborting"
        yield conn

def _wait_for_raspbian_boot(docker_container_id):
    ready = False
    timeout = time.time() + 60*3
    while not ready and time.time() < timeout:
        time.sleep(5)
        output = subprocess.check_output("docker logs {} 2>&1".format(docker_container_id), shell=True)

        if "Raspbian GNU/Linux 9 raspberrypi ttyAMA0" in output.decode("utf-8"):
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
            if not str(e).endswith("Connection reset by peer"):
                raise e
            time.sleep(5)

    return ready