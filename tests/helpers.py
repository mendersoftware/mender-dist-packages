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

import os.path

from fabric import Result as FabricResult

tests_path = os.path.dirname(os.path.realpath(__file__))
output_path = os.path.normpath(os.path.join(tests_path, "..", "output"))


COMMERCIAL_PACKAGES = [
    "mender-gateway",
    "mender-monitor",
]


# Returns path were to find the package to install
def packages_path(package, package_arch="armhf"):
    if package_arch == "all":
        package_arch = "amd64"
    subdir = "opensource/debian-buster-" + package_arch
    if package in COMMERCIAL_PACKAGES:
        subdir = "commercial/debian-buster-" + package_arch
    return os.path.join(output_path, subdir)


def package_filename(package_version, package_name, package_arch="armhf"):
    return "{name}_{version}_{arch}.deb".format(
        name=package_name, version=package_version, arch=package_arch
    )


def package_filename_path(package_version, package_name, package_arch="armhf"):
    return os.path.join(
        packages_path(package_name, package_arch),
        package_filename(package_version, package_name, package_arch),
    )


def upload_deb_package(
    ssh_connection, package_version, package_name, package_arch="armhf"
):
    ssh_connection.put(
        package_filename_path(package_version, package_name, package_arch)
    )


def check_installed(conn, pkg, installed=True):
    """Check whether the given package is installed on the device given by conn.
    Check the specific dpkg Status to differentiate between installed (install ok installed)
    and other status like removed but not purged (deinstall ok config-files)"""

    res = conn.run(f"dpkg --status {pkg}", warn=True)
    if isinstance(res, FabricResult):
        retcode = res.return_code
        output = res.stdout
    else:
        retcode = res.returncode
        output = res.stdout.decode()

    if installed:
        assert "Status: install ok installed" in output
    else:
        assert retcode != 0 or "Status: install ok installed" not in output
