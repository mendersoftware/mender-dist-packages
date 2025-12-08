[![Build Status](https://gitlab.com/Northern.tech/Mender/mender-dist-packages/badges/master/pipeline.svg)](https://gitlab.com/Northern.tech/Mender/mender-dist-packages/pipelines)

mender-dist-packages
====================

Mender is an open source over-the-air (OTA) software updater for embedded Linux devices. Mender comprises a client running at the embedded device, as well as a server that manages deployments across many devices.

This repository contains mender-dist-packages, which is used to create distribution packages of the mender client software

![Mender logo](https://mender.io/user/pages/resources/06.digital-assets/mender.io.png)

## Getting started

To start using Mender, we recommend that you begin with the Getting started
section in [the Mender documentation](https://docs.mender.io/).

## Requirements

You need to [install Docker Engine](https://docs.docker.com/install) to use this
environment. Then you need access to the registry.gitlab.com/northern.tech
container registry:

1. Create a new authentication token for the registry at
   https://gitlab.com/-/user_settings/personal_access_tokens

2. Log in to the registry:

```bash
docker login registry.gitlab.com/northern.tech
```

If you don't have access to the above registry and need to build the container
images required for builds locally, see the `build.sh` script and `Dockerfile`
in the [mender-test-containers
repository](https://github.com/mendersoftware/mender-test-containers/tree/master/mender-dist-packages-building).


### Instructions

To build the DEB packages, run the `docker-build-package` script as follows:

```bash
./docker-build-package build-type distro release arch package-name [version] [save-orig]
```

The only supported `build-type` is `crosscompile`. `distro`, `release` and
`arch` define the target OS. `distro` and `release` can currently be one of the
following combinations:

- `debian`: `bullseye`, `bookworm`, `trixie`
- `ubuntu`: `focal`, `jammy`, `noble`

These combinations change in time with new distribution releases and old
releases going out of support.

The `arch` argument specifies the architecture to build the package(s) for and
can be one of the following values:

- `armhf`
- `arm64`
- `amd64`

The `package-name` and `version` define what should be built. Possible package
names correspond to the Mender components:

- `mender-artifact`
- `mender-cli`
- `mender-client4`
- `mender-connect`
- `mender-configure`
- `mender-gateway`
- `mender-flash`
- `mender-monitor`
- `mender-setup`
- `mender-snapshot`
- `mender-orchestrator`
- `mender-orchestrator-support`

The version specified with `version` may be an exact version of the package
(usually a tag in the component's repository) or the name of the main branch.
The `version` also specifies the version of the recipes used. If there is a
recipe for the specific `version` in the respective `recipes/$package-name`
directory, it is used. Otherwise the `debian-master` recipe for the given
package is used.

*Note: Some recipes for past versions of various packages can be found in git
history.*


When building the `.orig` tarball (which is needed for building actual `.deb`
packages), `save-orig` must be set to `true`.

A full example can then be:

```bash
./docker-build-package crosscompile debian bookworm amd64 mender-flash 1.0.2 true
./docker-build-package crosscompile debian bookworm amd64 mender-flash 1.0.2
```

When finished, the packages should be ready in the `output/` directory.


## Contributing

We welcome and ask for your contribution. If you would like to contribute to Mender, please read our guide on how to best get started [contributing code or documentation](https://github.com/mendersoftware/mender/blob/master/CONTRIBUTING.md).

## License

Mender is licensed under the Apache License, Version 2.0. See [LICENSE](https://github.com/mendersoftware/mender-crossbuild/blob/master/LICENSE) for the full license text.

## Security disclosure

We take security very seriously. If you come across any issue regarding
security, please disclose the information by sending an email to
[security@mender.io](security@mender.io). Please do not create a new public
issue. We thank you in advance for your cooperation.

## Connect with us

* Join the [Mender Hub discussion forum](https://hub.mender.io)
* Follow us on [Twitter](https://twitter.com/mender_io). Please
  feel free to tweet us questions.
* Fork us on [Github](https://github.com/mendersoftware)
* Create an issue in the [bugtracker](https://northerntech.atlassian.net/projects/MEN)
* Email us at [contact@mender.io](mailto:contact@mender.io)
* Connect to the [#mender IRC channel on Libera](https://web.libera.chat/?#mender)


## Authors

Mender was created by the team at [Northern.tech AS](https://northern.tech), with many contributions from
the community. Thanks [everyone](https://github.com/mendersoftware/mender/graphs/contributors)!

[Mender](https://mender.io) is sponsored by [Northern.tech AS](https://northern.tech).
