#!/usr/bin/python3
# Copyright 2025 Northern.tech AS
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

import os
import pytest

from helpers import package_filename, upload_deb_package, check_installed


# Copied from test_install_mender_sh
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


@pytest.mark.usefixtures("setup_mender_configured")
class TestPackageOrchestratorSplit:
    @pytest.mark.commercial
    def test_mender_orchestrator_split(
        self, setup_tester_ssh_connection, mender_dist_packages_versions
    ):
        try:
            # mender-orchestrator-core
            upload_deb_package(
                setup_tester_ssh_connection,
                mender_dist_packages_versions["mender-orchestrator"],
                "mender-orchestrator-core",
            )
            setup_tester_ssh_connection.run(
                "sudo dpkg --install "
                + package_filename(
                    mender_dist_packages_versions["mender-orchestrator"],
                    "mender-orchestrator-core",
                )
            )

            # mender-orchestrator-support
            upload_deb_package(
                setup_tester_ssh_connection,
                mender_dist_packages_versions["mender-orchestrator-support"],
                "mender-orchestrator-support",
                "all",
            )
            setup_tester_ssh_connection.run(
                "sudo dpkg --install "
                + package_filename(
                    mender_dist_packages_versions["mender-orchestrator-support"],
                    "mender-orchestrator-support",
                    "all",
                ),
            )

            check_installed(setup_tester_ssh_connection, "mender-orchestrator-support")
            setup_tester_ssh_connection.run(
                "test -x /usr/share/mender/inventory/mender-inventory-orchestrator-inventory"
            )
            setup_tester_ssh_connection.run(
                "test -x /usr/share/mender/modules/v3/mender-orchestrator-manifest"
            )
            setup_tester_ssh_connection.run(
                "test -x /usr/share/mender-orchestrator/interfaces/v1/rootfs-image"
            )

            # mender-orchestrator-demo
            upload_deb_package(
                setup_tester_ssh_connection,
                mender_dist_packages_versions["mender-orchestrator-support"],
                "mender-orchestrator-demo",
                "all",
            )
            setup_tester_ssh_connection.run(
                "sudo dpkg --install "
                + package_filename(
                    mender_dist_packages_versions["mender-orchestrator-support"],
                    "mender-orchestrator-demo",
                    "all",
                )
            )
            check_installed(setup_tester_ssh_connection, "mender-orchestrator-support")
            setup_tester_ssh_connection.run(
                "test -f /data/mender-orchestrator/topology.yaml"
            )
            setup_tester_ssh_connection.run(
                "test -d /data/mender-orchestrator/mock-instances/0"
            )
            setup_tester_ssh_connection.run(
                "test -d /data/mender-orchestrator/mock-instances/1"
            )
            setup_tester_ssh_connection.run(
                "test -d /data/mender-orchestrator/mock-instances/2"
            )

        finally:
            setup_tester_ssh_connection.run(
                f"sudo dpkg --purge remove mender-orchestrator-demo mender-orchestrator-support mender-orchestrator-core ",
            )


@pytest.mark.usefixtures("setup_mender_configured")
class TestPackageOrchestratorMeta:
    @pytest.mark.commercial
    def test_mender_orchestrator_meta_package(
        self, setup_tester_ssh_connection, mender_dist_packages_versions
    ):
        try:
            # Upload all the packages (including the demo one)
            for pkg in [
                "mender-orchestrator",
                "mender-orchestrator-core",
            ]:
                upload_deb_package(
                    setup_tester_ssh_connection,
                    mender_dist_packages_versions["mender-orchestrator"],
                    pkg,
                )
            for pkg in [
                "mender-orchestrator-support",
                "mender-orchestrator-demo",
            ]:
                upload_deb_package(
                    setup_tester_ssh_connection,
                    mender_dist_packages_versions["mender-orchestrator-support"],
                    pkg,
                    "all",
                )

            setup_tester_ssh_connection.run("mkdir -p /packages; mv *.deb /packages/")
            prepare_local_apt_repo(setup_tester_ssh_connection, "/packages")

            # Install the meta-package only
            setup_tester_ssh_connection.run(
                "sudo apt install --assume-yes mender-orchestrator",
            )

            check_installed(setup_tester_ssh_connection, "mender-orchestrator")
            check_installed(setup_tester_ssh_connection, "mender-orchestrator-core")
            check_installed(setup_tester_ssh_connection, "mender-orchestrator-support")
            check_installed(
                setup_tester_ssh_connection,
                "mender-orchestrator-demo",
                installed=False,
            )

        finally:
            setup_tester_ssh_connection.run(
                f"sudo dpkg --purge remove mender-orchestrator-support mender-orchestrator-core mender-orchestrator",
            )


# Keep this test at the end. Due to reusing the environment through the tests,
# after we remove a given version of mender-update (but keeping mender-auth)
# further tests will refuse downgrading.
@pytest.mark.usefixtures("setup_mender_configured")
class TestPackageOrchestratorCore:
    @pytest.mark.commercial
    def test_mender_orchestrator_standalone(
        self, setup_tester_ssh_connection, mender_dist_packages_versions
    ):
        try:
            # Remove mender-update (and add-ons that depend on it) to verify
            # that mender-orchestrator-core requires only mender-auth
            setup_tester_ssh_connection.run(
                f"sudo dpkg --purge remove mender-update mender-configure mender-connect"
            )

            upload_deb_package(
                setup_tester_ssh_connection,
                mender_dist_packages_versions["mender-orchestrator"],
                "mender-orchestrator-core",
            )
            setup_tester_ssh_connection.run(
                "apt install --assume-yes ./"
                + package_filename(
                    mender_dist_packages_versions["mender-orchestrator"],
                    "mender-orchestrator-core",
                )
            )
            check_installed(setup_tester_ssh_connection, "mender-orchestrator-core")
            setup_tester_ssh_connection.run("test -x /usr/bin/mender-orchestrator")

        finally:
            setup_tester_ssh_connection.run(
                f"sudo dpkg --purge remove mender-orchestrator-core"
            )
