#!/usr/bin/python3
# Copyright 2020 Northern.tech AS
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
    @pytest.mark.skip(
        reason="no mender-shell in 'stable'; in 'experimental' depends on client 2.5.0 which is not there yet"
    )
    def test_default(
        self,
        script_server,
        setup_tester_ssh_connection_f,
        mender_dist_packages_versions,
        mender_version,
        channel,
    ):
        """Default, no arg install installs mender-client and mender-shell (stable)."""
        localhost = self._get_localhost_ip(setup_tester_ssh_connection_f)

        if channel != "":
            channel = "-c " + channel

        setup_tester_ssh_connection_f.run(
            "curl http://{}:{}/install-mender.sh | sudo bash -s -- {}".format(
                localhost, SCRIPT_SERVER_PORT, channel
            )
        )

        setup_tester_ssh_connection_f.run("dpkg --status mender-client")
        setup_tester_ssh_connection_f.run("dpkg --status mender-shell")

    @pytest.mark.usefixtures("setup_test_container_f")
    @pytest.mark.parametrize("channel", ["", "stable", "experimental"])
    def test_client(
        self,
        script_server,
        setup_tester_ssh_connection_f,
        mender_dist_packages_versions,
        mender_version,
        channel,
    ):
        localhost = self._get_localhost_ip(setup_tester_ssh_connection_f)

        if channel != "":
            channel = "-c " + channel

        setup_tester_ssh_connection_f.run(
            "curl http://{}:{}/install-mender.sh | sudo bash -s -- {} mender-client".format(
                localhost, SCRIPT_SERVER_PORT, channel
            )
        )

        setup_tester_ssh_connection_f.run("dpkg --status mender-client")

        res = setup_tester_ssh_connection_f.run("dpkg --status mender-shell", warn=True)
        assert res.exited == 1

        # piggyback misc cmdline tests to save an extra container run
        # TODO: best place for these bits is the 'default' test case - move when it's unskipped

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
    @pytest.mark.parametrize("channel", ["", "stable", "experimental"])
    @pytest.mark.skip(
        reason="no mender-shell in 'stable'; in 'experimental' depends on client 2.5.0 which is not there yet"
    )
    def test_shell(
        self,
        script_server,
        setup_tester_ssh_connection_f,
        mender_dist_packages_versions,
        mender_version,
        channel,
    ):
        localhost = self._get_localhost_ip(setup_tester_ssh_connection_f)

        if channel != "":
            channel = "-c " + channel

        setup_tester_ssh_connection_f.run(
            "curl http://{}:{}/install-mender.sh | sudo bash -s -- {} mender-shell".format(
                localhost, SCRIPT_SERVER_PORT, channel
            )
        )

        setup_tester_ssh_connection_f.run("dpkg --status mender-client")
        setup_tester_ssh_connection_f.run("dpkg --status mender-shell")
