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

from helpers import package_filename, upload_deb_package, check_installed


class TestPackageArtifact:
    def test_mender_artifact(
        self, setup_tester_ssh_connection, mender_dist_packages_versions
    ):
        # Upload
        upload_deb_package(
            setup_tester_ssh_connection,
            mender_dist_packages_versions["mender-artifact"],
            "mender-artifact",
        )

        # Install
        setup_tester_ssh_connection.run(
            "sudo dpkg --install "
            + package_filename(
                mender_dist_packages_versions["mender-artifact"], "mender-artifact",
            )
        )
        check_installed(setup_tester_ssh_connection, "mender-artifact")

        # Check mender-artifact files
        setup_tester_ssh_connection.run("test -x /usr/bin/mender-artifact")
        setup_tester_ssh_connection.run("mender-artifact --version")
