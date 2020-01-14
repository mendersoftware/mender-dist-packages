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

from mender_test_containers.container_props import *
from mender_test_containers.conftest import *

TEST_CONTAINER_LIST = [MenderTestRaspbian]


@pytest.fixture(scope="session", params=TEST_CONTAINER_LIST)
def setup_test_container_props(request):
    return request.param


def pytest_addoption(parser):
    parser.addoption("--mender-client-version", required=True)
    parser.addoption("--mender-client-deb-version", required=True)


@pytest.fixture(scope="session")
def mender_version(request):
    return request.config.getoption("--mender-client-version")


@pytest.fixture(scope="session")
def mender_dist_packages_versions(request):
    """Returns dict matching package names and current versions"""

    return {"mender-client": request.config.getoption("--mender-client-deb-version")}
