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

import os.path

tests_path = os.path.dirname(os.path.realpath(__file__))

# Path were to find the packages under test
packages_path_default = os.path.normpath(os.path.join(tests_path, "..", "output"))


def package_filename(
    package_version, package_name="mender-client", package_arch="armhf"
):
    return "{name}_{version}_{arch}.deb".format(
        name=package_name, version=package_version, arch=package_arch
    )


def package_filename_path(
    package_version, package_name="mender-client", package_arch="armhf"
):
    return os.path.join(
        packages_path_default,
        package_filename(package_version, package_name, package_arch),
    )


def upload_deb_package(
    ssh_connection, package_version, package_name="mender-client", package_arch="armhf"
):
    ssh_connection.put(
        package_filename_path(package_version, package_name, package_arch)
    )
