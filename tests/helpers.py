#!/usr/bin/python3
# Copyright 2022 Northern.tech AS
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

from mender_test_containers.helpers import Result as SSHResult

tests_path = os.path.dirname(os.path.realpath(__file__))
output_path = os.path.normpath(os.path.join(tests_path, "..", "output"))


COMMERCIAL_PACKAGES = [
    "mender-gateway",
    "mender-monitor",
    "mender-orchestrator-core",
    "mender-orchestrator",
    "mender-orchestrator-support",
    "mender-orchestrator-demo",
]


DEFAULT_PACKAGE_ARCH = "armhf"

# Returns path were to find the package to install
def packages_path(package, package_arch=DEFAULT_PACKAGE_ARCH):
    if package_arch == "all":
        package_arch = "amd64"

    distro = "debian"
    # Inherit this from the CI calling the tests
    distro_version = os.getenv("DEBIAN_VERSION_NAME", "missing-debian-version")

    basedir = "opensource"
    if package in COMMERCIAL_PACKAGES:
        basedir = "commercial"

    return os.path.join(
        output_path, basedir, f"{distro}-{distro_version}-{package_arch}"
    )


def package_filename(package_version, package_name, package_arch=DEFAULT_PACKAGE_ARCH):
    return "{name}_{version}_{arch}.deb".format(
        name=package_name, version=package_version, arch=package_arch
    )


def package_filename_path(
    package_version, package_name, package_arch=DEFAULT_PACKAGE_ARCH
):
    return os.path.join(
        packages_path(package_name, package_arch),
        package_filename(package_version, package_name, package_arch),
    )


def upload_deb_package(
    ssh_connection, package_version, package_name, package_arch=DEFAULT_PACKAGE_ARCH
):
    ssh_connection.put(
        package_filename_path(package_version, package_name, package_arch)
    )


def check_installed(conn, pkg, installed=True):
    """Check whether the given package is installed on the device given by conn.
    Check the specific dpkg Status to differentiate between installed (install ok installed)
    and other status like removed but not purged (deinstall ok config-files)"""

    res = conn.run(f"dpkg --status {pkg}", warn=True)
    if isinstance(res, SSHResult):
        retcode = res.return_code
        output = res.stdout
    else:
        retcode = res.returncode
        output = res.stdout.decode()

    if installed:
        assert "Status: install ok installed" in output
    else:
        assert retcode != 0 or "Status: install ok installed" not in output
