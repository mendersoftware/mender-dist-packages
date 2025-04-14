%define mender_artifact_version 4.1.0
%define tag build1

# We don't want debuginfo packages
%global debug_package %{nil}

Name: mender-artifact
Summary: A CLI tool for working with Mender artifacts
Version: %{mender_artifact_version}
Release: 1%{?dist}
License: Apache-2.0
URL: https://github.com/mendersoftware/mender-artifact/

# Once we have releases at GitHub not just tags, we should use a URL like the
# one below, instead:
# Source0: https://github.com/mendersoftware/mender-artifact/releases/download/...
# The variant below, with the tarball name, results in a warning from rpmlint
# that it's not a valid URL. But the URL to get it from looks like this:
#   https://github.com/mendersoftware/mender-artifact/archive/refs/tags/4.1.0.tar.gz
# which has no package name in tarball file name. So we use a custom file name
# until we can use a release.
Source0: %{name}-%{version}-%{tag}.tar.gz

BuildRequires: git
BuildRequires: golang
BuildRequires: openssl-devel

# Fedora 41 deprecated the Engine API [1] and thus a separate package needs to
# be installed to get /usr/include/openssl/engine.h. Fedora 40 knows
# openssl-devel provides that file and would not install anything extra with the
# line below, but other RPM-based distros would have no clue.
# [1] https://fedoraproject.org/wiki/Changes/OpensslDeprecateEngine
%if %{?fedora}%{!?fedora:0} > 40
BuildRequires: openssl-devel-engine
%endif

%description
A CLI tool to work with a Mender artifact, which is a file that can be recognized
by its .mender suffix. Mender artifacts can contain binaries, metadata, checksums,
signatures and scripts that are used during a deployment.

%prep
%setup -q -n %{name}-%{version}

%build
make build

%install
install -m 0755 -vd %{buildroot}%{_bindir}
# Install the binary ourselves, instead of `GOBIN=... make install` because that
# does extra things we don't need/want.
install -m 0755 -vp ./mender-artifact %{buildroot}%{_bindir}/

%files
%{_bindir}/mender-artifact
%doc README.md
%license LICENSE
# TODO: Should we add artifact-format-v2.md artifact-format-v3.md?

%changelog
* Mon Apr 14 2025 Vratislav Podzimek <vratislav.podzimek@nothern.tech> - 4.1.0-1
- Initial release
