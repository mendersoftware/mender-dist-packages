#!/usr/bin/python3
# Copyright 2024 Northern.tech AS
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

import glob
import http.server
import os
import socketserver
import subprocess
import threading

import pytest
from helpers import packages_path, check_installed

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
            try:
                return subprocess.run(
                    cmd, shell=True, capture_output=True, check=not warn
                )
            except subprocess.CalledProcessError as e:
                print(e.output.decode())
                raise

        def put(self, source, dest):
            subprocess.check_call(
                ["docker", "cp", source, f"{self.container_id}:{dest}"]
            )

    c = GenericContainer(docker_container_id)

    # Get install-mender.sh requirements
    c.run("apt update")
    c.run("apt install -y curl")

    return c


def put_all_built_packages(container, dest):
    container.run(f"mkdir -p {dest}")
    for package in glob.glob(packages_path("mender-client", "amd64") + "/*.deb"):
        container.put(package, dest)


def prepare_local_apt_repo(container, packages_path):
    # Configure a local APT repo with dpkg-dev. See:
    # https://askubuntu.com/questions/458748/is-it-possible-to-add-a-location-folder-on-my-hard-disk-to-sources-list
    container.run("apt install -y dpkg-dev")
    container.run(
        f"cd {packages_path} && dpkg-scanpackages . /dev/null | gzip -9c > Packages.gz"
    )
    sources_list_file = (
        f"/etc/apt/sources.list.d/{os.path.basename(packages_path)}.list"
    )
    container.run(
        f"echo deb [trusted=yes] file:{packages_path} ./ > {sources_list_file}"
    )
    container.run("apt update")


def local_apt_repo_from_built_packages(container):
    put_all_built_packages(container, "/packages")
    prepare_local_apt_repo(container, "/packages")


def local_apt_repo_from_upstream_packages(container, pool_paths, dest):
    container.run(f"mkdir {dest}")
    for path in pool_paths:
        url = f"https://downloads.mender.io/repos/debian/pool/main/{path}"
        container.run(f"cd {dest} && curl --remote-name {url}")

    prepare_local_apt_repo(container, dest)


def local_apt_repo_from_test_packages(container, pool_paths, dest):
    container.run(f"mkdir {dest}")
    for path in pool_paths:
        url = f"https://downloads.mender.io/repos/debian/pool/test-packages/{path}"
        container.run(f"cd {dest} && curl --remote-name {url}")

    prepare_local_apt_repo(container, dest)


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

    def test_default_setup_mender(
        self, generic_debian_container,
    ):
        """Pass mender setup args, should be propagated"""

        generic_debian_container.run(
            f"curl http://{SCRIPT_SERVER_ADDR}:{SCRIPT_SERVER_PORT}/install-mender.sh | bash -s -- -- --demo --device-type cool-device --hosted-mender --tenant-token my-secret-token"
        )

        result = generic_debian_container.run("cat /etc/mender/mender.conf")
        assert '"ServerURL": "https://hosted.mender.io"' in result.stdout.decode()

        result = generic_debian_container.run("cat /var/lib/mender/device_type")
        assert result.stdout.decode().strip() == "device_type=cool-device"

        result = generic_debian_container.run("cat /etc/mender/mender-connect.conf")
        assert '"User": "nobody"' in result.stdout.decode()

    def test_default_setup_addons(
        self, generic_debian_container,
    ):
        """Setup for add-ons (passing --demo)"""

        generic_debian_container.run(
            f"curl http://{SCRIPT_SERVER_ADDR}:{SCRIPT_SERVER_PORT}/install-mender.sh | bash -s -- --demo"
        )

        result = generic_debian_container.run("cat /etc/mender/mender-connect.conf")
        assert '"User": "root"' in result.stdout.decode()

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

        check_installed(generic_debian_container, "mender-auth")
        check_installed(generic_debian_container, "mender-connect")
        check_installed(generic_debian_container, "mender-configure", installed=False)

    def test_configure(
        self, generic_debian_container,
    ):
        generic_debian_container.run(
            f"curl http://{SCRIPT_SERVER_ADDR}:{SCRIPT_SERVER_PORT}/install-mender.sh | bash -s -- mender-configure"
        )

        check_installed(generic_debian_container, "mender-auth")
        check_installed(generic_debian_container, "mender-update")
        check_installed(generic_debian_container, "mender-connect", installed=False)
        check_installed(generic_debian_container, "mender-configure")

    def test_upgrade_mender_v3_series(
        self, generic_debian_container,
    ):
        # Install latest stable software (client v3)
        generic_debian_container.run(
            f"curl http://{SCRIPT_SERVER_ADDR}:{SCRIPT_SERVER_PORT}/install-mender.sh | bash -s"
        )

        # Now upgrade to the freshly built packages
        local_apt_repo_from_built_packages(generic_debian_container)
        generic_debian_container.run("apt --assume-yes upgrade")

        # Only mender-client should be upgraded
        check_installed(generic_debian_container, "mender-client")
        check_installed(generic_debian_container, "mender-client4", installed=False)
        check_installed(generic_debian_container, "mender-update", installed=False)
        check_installed(generic_debian_container, "mender-auth", installed=False)
        check_installed(generic_debian_container, "mender-flash", installed=False)
        check_installed(generic_debian_container, "mender-setup", installed=False)
        check_installed(generic_debian_container, "mender-snapshot", installed=False)
        # The addons should not be removed
        check_installed(generic_debian_container, "mender-connect")
        check_installed(generic_debian_container, "mender-configure")

    def test_upgrade_mender_v4_series_meta_package_with_addons(
        self, generic_debian_container,
    ):
        # Install default stable software (legacy client v3 + addons)
        generic_debian_container.run(
            f"curl http://{SCRIPT_SERVER_ADDR}:{SCRIPT_SERVER_PORT}/install-mender.sh | bash -s"
        )

        # Now install freshly built mender-client4
        local_apt_repo_from_built_packages(generic_debian_container)
        generic_debian_container.run(
            "DEBIAN_FRONTEND=noninteractive apt install --assume-yes mender-client4"
        )

        # mender-client should be removed and mender-client4 + all packages should be installed
        check_installed(generic_debian_container, "mender-client", installed=False)
        check_installed(generic_debian_container, "mender-client4")
        check_installed(generic_debian_container, "mender-update")
        check_installed(generic_debian_container, "mender-auth")
        check_installed(generic_debian_container, "mender-flash")
        check_installed(generic_debian_container, "mender-setup")
        check_installed(generic_debian_container, "mender-snapshot")
        # The addons should not be removed
        check_installed(generic_debian_container, "mender-connect")
        check_installed(generic_debian_container, "mender-configure")

    def test_upgrade_mender_v4_series_meta_package_only_client(
        self, generic_debian_container,
    ):
        # Install only the legacy client v3)
        generic_debian_container.run(
            f"curl http://{SCRIPT_SERVER_ADDR}:{SCRIPT_SERVER_PORT}/install-mender.sh | bash -s -- mender-client"
        )

        # Now install freshly built mender-client4
        local_apt_repo_from_built_packages(generic_debian_container)
        generic_debian_container.run(
            "DEBIAN_FRONTEND=noninteractive apt install --assume-yes mender-client4"
        )

        # mender-client should be removed and mender-client4 + all packages should be installed
        check_installed(generic_debian_container, "mender-client", installed=False)
        check_installed(generic_debian_container, "mender-client4")
        check_installed(generic_debian_container, "mender-update")
        check_installed(generic_debian_container, "mender-auth")
        check_installed(generic_debian_container, "mender-flash")
        check_installed(generic_debian_container, "mender-setup")
        check_installed(generic_debian_container, "mender-snapshot")

    def test_upgrade_mender_v4_series_explicit_auth_update(
        self, generic_debian_container,
    ):
        # Install default stable software (legacy client v3 + addons)
        generic_debian_container.run(
            f"curl http://{SCRIPT_SERVER_ADDR}:{SCRIPT_SERVER_PORT}/install-mender.sh | bash -s"
        )

        # Now install freshly built packages
        local_apt_repo_from_built_packages(generic_debian_container)
        generic_debian_container.run(
            "DEBIAN_FRONTEND=noninteractive apt install --assume-yes mender-auth mender-update"
        )

        # mender-client should be removed and required packages should be installed
        check_installed(generic_debian_container, "mender-client", installed=False)
        check_installed(generic_debian_container, "mender-client4", installed=False)
        check_installed(generic_debian_container, "mender-update")
        check_installed(generic_debian_container, "mender-auth")
        check_installed(generic_debian_container, "mender-flash")
        # The addons should not be removed
        check_installed(generic_debian_container, "mender-connect")
        check_installed(generic_debian_container, "mender-configure")


@pytest.mark.usefixtures("script_server")
class TestUpgradeMenderV4:
    def test_upgrade_from_v3_to_v4_to_build(
        self, generic_debian_container,
    ):
        # Install mender-client 3.5.1 (epoch 0:)
        local_apt_repo_from_upstream_packages(
            generic_debian_container,
            [
                "m/mender-client/mender-client_3.5.1-1+debian+buster_amd64.deb",
                "m/mender-connect/mender-connect_2.1.1-1+debian+buster_amd64.deb",
                "m/mender-configure/mender-configure_1.1.1-1+debian+buster_all.deb",
            ],
            "/mender_3_5_1",
        )
        generic_debian_container.run(
            "DEBIAN_FRONTEND=noninteractive apt install --assume-yes mender-client mender-connect mender-configure"
        )

        check_installed(generic_debian_container, "mender-client")
        check_installed(generic_debian_container, "mender-connect")
        check_installed(generic_debian_container, "mender-configure")

        # Upgrade to mender-client 4.0.0
        local_apt_repo_from_test_packages(
            generic_debian_container,
            [
                "mender-client_4.0.0-1+debian+buster_amd64.deb",
                "mender-update_4.0.0-1+debian+buster_amd64.deb",
                "mender-auth_4.0.0-1+debian+buster_amd64.deb",
                "mender-flash_1.0.0-1+debian+buster_amd64.deb",
                "mender-setup_1.0.0-1+debian+buster_amd64.deb",
                "mender-snapshot_1.0.0-1+debian+buster_amd64.deb",
                "mender-connect_2.2.0-1+debian+buster_amd64.deb",
                "mender-configure_1.1.2-1+debian+buster_all.deb",
            ],
            "/mender_4_0_0",
        )
        # Note the use of apt instead of apt-get - the latter wouldn't install the new packages
        generic_debian_container.run("apt --assume-yes upgrade")
        check_installed(generic_debian_container, "mender-client")
        check_installed(generic_debian_container, "mender-update")
        check_installed(generic_debian_container, "mender-auth")
        check_installed(generic_debian_container, "mender-flash")
        check_installed(generic_debian_container, "mender-setup")
        check_installed(generic_debian_container, "mender-snapshot")
        check_installed(generic_debian_container, "mender-connect")
        check_installed(generic_debian_container, "mender-configure")

        # Upgrade to the freshly built packages
        local_apt_repo_from_built_packages(generic_debian_container)
        generic_debian_container.run("apt --assume-yes upgrade")
        check_installed(generic_debian_container, "mender-client")
        check_installed(generic_debian_container, "mender-update")
        check_installed(generic_debian_container, "mender-auth")
        check_installed(generic_debian_container, "mender-flash")
        check_installed(generic_debian_container, "mender-setup")
        check_installed(generic_debian_container, "mender-snapshot")
        check_installed(generic_debian_container, "mender-connect")
        check_installed(generic_debian_container, "mender-configure")

    def test_upgrade_from_v3_to_build(
        self, generic_debian_container,
    ):
        # Install mender-client 3.5.2 (epoch 1:)
        local_apt_repo_from_upstream_packages(
            generic_debian_container,
            [
                "m/mender-client/mender-client_3.5.2-1+debian+buster_amd64.deb",
                "m/mender-connect/mender-connect_2.2.0-1+debian+buster_amd64.deb",
                "m/mender-configure/mender-configure_1.1.1-1+debian+buster_all.deb",
            ],
            "/mender_3_5_2",
        )
        generic_debian_container.run(
            "DEBIAN_FRONTEND=noninteractive apt install --assume-yes mender-client mender-connect mender-configure"
        )
        check_installed(generic_debian_container, "mender-client")
        check_installed(generic_debian_container, "mender-connect")
        check_installed(generic_debian_container, "mender-configure")

        # Upgrade to the freshly built packages
        local_apt_repo_from_built_packages(generic_debian_container)
        generic_debian_container.run("apt --assume-yes upgrade")
        check_installed(generic_debian_container, "mender-client")
        check_installed(generic_debian_container, "mender-connect")
        check_installed(generic_debian_container, "mender-configure")

    def test_upgrade_from_v4_to_build(
        self, generic_debian_container,
    ):
        # Install mender-client 4.0.0
        local_apt_repo_from_test_packages(
            generic_debian_container,
            [
                "mender-client_4.0.0-1+debian+buster_amd64.deb",
                "mender-update_4.0.0-1+debian+buster_amd64.deb",
                "mender-auth_4.0.0-1+debian+buster_amd64.deb",
                "mender-flash_1.0.0-1+debian+buster_amd64.deb",
                "mender-setup_1.0.0-1+debian+buster_amd64.deb",
                "mender-snapshot_1.0.0-1+debian+buster_amd64.deb",
                "mender-connect_2.2.0-1+debian+buster_amd64.deb",
                "mender-configure_1.1.2-1+debian+buster_all.deb",
            ],
            "/mender_4_0_0",
        )
        generic_debian_container.run(
            "DEBIAN_FRONTEND=noninteractive apt install --assume-yes mender-client mender-connect mender-configure"
        )

        # Upgrade to the freshly built packages
        local_apt_repo_from_built_packages(generic_debian_container)
        generic_debian_container.run("apt --assume-yes upgrade")
        check_installed(generic_debian_container, "mender-client")
        check_installed(generic_debian_container, "mender-connect")
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
