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
import pytest

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


def check_installed(conn, pkg, installed=True):
    """Check whether the given package is installed on the device given by
    conn."""

    res = conn.run(f"dpkg --status {pkg}", warn=True)
    assert (res.return_code == 0) == installed


class TestInstallMenderScript:
    def _get_localhost_ip(self, setup_tester_ssh_connection):
        """We need to access the toplevel host's port to curl the script.
        'localhost' of course doesn't work, but qemu runs on docker in 'net=host' mode,
        so the host's address is simply the default route.
        """
        result = setup_tester_ssh_connection.run(
            "ip route | grep default | awk '{print $3}'"
        )
        return result.stdout.strip()

    @pytest.mark.usefixtures("setup_test_container_f")
    @pytest.mark.parametrize("channel", ["", "stable", "experimental"])
    def test_default(
        self, script_server, setup_tester_ssh_connection_f, channel,
    ):
        """Default, no arg install installs mender-client and mender-connect (stable)."""
        localhost = self._get_localhost_ip(setup_tester_ssh_connection_f)

        if channel != "":
            channel = "-c " + channel

        setup_tester_ssh_connection_f.run(
            "curl http://{}:{}/install-mender.sh | sudo bash -s -- {}".format(
                localhost, SCRIPT_SERVER_PORT, channel
            )
        )

        for pkg in ["mender-client", "mender-configure", "mender-connect"]:
            check_installed(setup_tester_ssh_connection_f, pkg)

        # piggyback misc cmdline tests to save an extra container run
        # help
        res = setup_tester_ssh_connection_f.run(
            "curl http://{}:{}/install-mender.sh | bash -s -- -h".format(
                localhost, SCRIPT_SERVER_PORT
            )
        )
        assert "usage:" in res.stdout

        # invalid arg/module
        res = setup_tester_ssh_connection_f.run(
            "curl http://{}:{}/install-mender.sh | bash -s -- unknown".format(
                localhost, SCRIPT_SERVER_PORT
            ),
            warn=True,
        )

        assert res.exited == 1
        assert "Unsupported argument: `unknown`" in res.stdout

    @pytest.mark.usefixtures("setup_test_container_f")
    def test_client(
        self, script_server, setup_tester_ssh_connection_f,
    ):
        localhost = self._get_localhost_ip(setup_tester_ssh_connection_f)

        setup_tester_ssh_connection_f.run(
            f"curl http://{localhost}:{SCRIPT_SERVER_PORT}/install-mender.sh | sudo bash -s -- mender-client"
        )

        check_installed(setup_tester_ssh_connection_f, "mender-client")
        check_installed(
            setup_tester_ssh_connection_f, "mender-connect", installed=False
        )
        check_installed(
            setup_tester_ssh_connection_f, "mender-configure", installed=False
        )

        res = setup_tester_ssh_connection_f.run(
            "dpkg --status mender-connect", warn=True
        )
        assert res.exited == 1

    @pytest.mark.usefixtures("setup_test_container_f")
    def test_connect(
        self, script_server, setup_tester_ssh_connection_f,
    ):
        localhost = self._get_localhost_ip(setup_tester_ssh_connection_f)

        setup_tester_ssh_connection_f.run(
            f"curl http://{localhost}:{SCRIPT_SERVER_PORT}/install-mender.sh | sudo bash -s -- mender-connect"
        )

        check_installed(setup_tester_ssh_connection_f, "mender-client")
        check_installed(setup_tester_ssh_connection_f, "mender-connect")
        check_installed(
            setup_tester_ssh_connection_f, "mender-configure", installed=False
        )

    @pytest.mark.usefixtures("setup_test_container_f")
    def test_configure(
        self, script_server, setup_tester_ssh_connection_f,
    ):
        localhost = self._get_localhost_ip(setup_tester_ssh_connection_f)

        setup_tester_ssh_connection_f.run(
            f"curl http://{localhost}:{SCRIPT_SERVER_PORT}/install-mender.sh | sudo bash -s -- mender-configure"
        )

        check_installed(setup_tester_ssh_connection_f, "mender-client")
        check_installed(
            setup_tester_ssh_connection_f, "mender-connect", installed=False
        )
        check_installed(setup_tester_ssh_connection_f, "mender-configure")
