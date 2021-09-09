#!/usr/bin/python3
# Copyright 2021 Northern.tech AS
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

import http.server
import socketserver
import threading
import os
import subprocess

import pytest
from fabric import Result as FabricResult

SCRIPT_SERVER_ADDR = "localhost"
SCRIPT_SERVER_PORT = 8000


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        sdir = os.path.join(os.path.dirname(__file__), "..", "scripts")
        super().__init__(*args, directory=sdir, **kwargs)


@pytest.fixture(scope="session")
def script_server():
    thread = None
    with socketserver.TCPServer(("0.0.0.0", SCRIPT_SERVER_PORT), Handler) as httpd:
        httpd.allow_reuse_address = True
        thread = threading.Thread(target=httpd.serve_forever)
        thread.daemon = False
        thread.start()
        yield
    httpd.shutdown()
    thread.join()
    print("cleaned up script server")


@pytest.fixture(scope="function")
def generic_debian_container(request):
    image = "debian:buster"
    cmd = "docker run --network host --rm -tid %s" % image
    output = subprocess.check_output(cmd, shell=True)

    global docker_container_id
    docker_container_id = output.decode("utf-8").split("\n")[0]

    def finalizer():
        cmd = "docker rm -f %s" % docker_container_id
        subprocess.check_output(cmd, shell=True)

    request.addfinalizer(finalizer)

    class GenericContainer:
        def __init__(self, container_id):
            self.container_id = container_id

        def run(self, command, warn=False):
            cmd = "docker exec %s /bin/bash -c '%s'" % (self.container_id, command)
            return subprocess.run(cmd, shell=True, capture_output=True, check=not warn)

    c = GenericContainer(docker_container_id)

    # Get install-mender.sh requirements
    c.run("apt update")
    c.run("apt install -y curl")

    return c


def check_installed(conn, pkg, installed=True):
    """Check whether the given package is installed on the device given by
    conn."""

    res = conn.run(f"dpkg --status {pkg}", warn=True)
    if isinstance(res, FabricResult):
        assert (res.return_code == 0) == installed
    else:
        assert (res.returncode == 0) == installed


@pytest.mark.usefixtures("script_server")
class TestInstallMenderScript:
    @pytest.mark.parametrize("channel", ["", "stable", "experimental"])
    def test_default(
        self, generic_debian_container, channel,
    ):
        """Default, no arg install installs mender-client and add-ons (stable)."""

        if channel != "":
            channel = "-c " + channel

        generic_debian_container.run(
            f"curl http://{SCRIPT_SERVER_ADDR}:{SCRIPT_SERVER_PORT}/install-mender.sh | bash -s -- {channel}"
        )

        for pkg in ["mender-client", "mender-configure", "mender-connect"]:
            check_installed(generic_debian_container, pkg)

        # piggyback misc cmdline tests to save an extra container run
        # help
        res = generic_debian_container.run(
            f"curl http://{SCRIPT_SERVER_ADDR}:{SCRIPT_SERVER_PORT}/install-mender.sh | bash -s -- -h"
        )
        assert "usage:" in res.stdout.decode()

        # invalid arg/module
        res = generic_debian_container.run(
            f"curl http://{SCRIPT_SERVER_ADDR}:{SCRIPT_SERVER_PORT}/install-mender.sh | bash -s -- unknown",
            warn=True,
        )

        assert res.returncode == 1
        assert "Unsupported argument: `unknown`" in res.stdout.decode()

    def test_client(
        self, generic_debian_container,
    ):
        generic_debian_container.run(
            f"curl http://{SCRIPT_SERVER_ADDR}:{SCRIPT_SERVER_PORT}/install-mender.sh | bash -s -- mender-client"
        )

        check_installed(generic_debian_container, "mender-client")
        check_installed(generic_debian_container, "mender-connect", installed=False)
        check_installed(generic_debian_container, "mender-configure", installed=False)

        res = generic_debian_container.run("dpkg --status mender-connect", warn=True)
        assert res.returncode == 1

    def test_connect(
        self, generic_debian_container,
    ):
        generic_debian_container.run(
            f"curl http://{SCRIPT_SERVER_ADDR}:{SCRIPT_SERVER_PORT}/install-mender.sh | bash -s -- mender-connect"
        )

        check_installed(generic_debian_container, "mender-client")
        check_installed(generic_debian_container, "mender-connect")
        check_installed(generic_debian_container, "mender-configure", installed=False)

    def test_configure(
        self, generic_debian_container,
    ):
        generic_debian_container.run(
            f"curl http://{SCRIPT_SERVER_ADDR}:{SCRIPT_SERVER_PORT}/install-mender.sh | bash -s -- mender-configure"
        )

        check_installed(generic_debian_container, "mender-client")
        check_installed(generic_debian_container, "mender-connect", installed=False)
        check_installed(generic_debian_container, "mender-configure")


@pytest.mark.usefixtures("script_server")
class TestInstallMenderScriptRaspberryOS:
    def test_raspbian_default(
        self, setup_tester_ssh_connection_f,
    ):
        # We need to access the toplevel host's port from QUEMU to curl the script.
        localhost = setup_tester_ssh_connection_f.run(
            "ip route | grep default | awk '{print $3}'"
        ).stdout.strip()

        # Explicitly accept suite change from "stable" to "oldstable"
        setup_tester_ssh_connection_f.run(
            "sudo apt-get update --allow-releaseinfo-change-suite"
        )

        setup_tester_ssh_connection_f.run(
            f"curl http://{localhost}:{SCRIPT_SERVER_PORT}/install-mender.sh | sudo bash -s"
        )
        for pkg in ["mender-client", "mender-configure", "mender-connect"]:
            check_installed(setup_tester_ssh_connection_f, pkg)
