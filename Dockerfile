ARG DEBIAN_VERSION=buster
FROM debian:$DEBIAN_VERSION
ARG DEBIAN_VERSION

RUN apt-get update && \
    apt-get install -y \
    build-essential \
    git wget curl \
    debhelper devscripts

ARG ARCH=amd64
RUN dpkg --add-architecture ${ARCH} && \
    apt-get update

RUN if [ "${ARCH}" != "armhf" ]; then \
        apt-get install -y \
        pkg-config \
        liblzma-dev:${ARCH} \
        libssl-dev:${ARCH} \
        libglib2.0-dev:${ARCH}; \
    fi

# To provide support for Raspberry Pi Zero W a toolchain tuned for ARMv6 architecture must be used.
# https://tracker.mender.io/browse/MEN-2399
ENV ARMV6_TOOLCHAIN_ROOT="/armv6-eabihf--glibc--stable-2020.08-1"
RUN if [ "${ARCH}" = "armhf" ]; then \
        wget -nc -q https://toolchains.bootlin.com/downloads/releases/toolchains/armv6-eabihf/tarballs/armv6-eabihf--glibc--stable-2020.08-1.tar.bz2 \
        && tar -xjf armv6-eabihf--glibc--stable-2020.08-1.tar.bz2 \
        && rm armv6-eabihf--glibc--stable-2020.08-1.tar.bz2; \
    fi

# Get depdendencies from upstream, manually donwloading deb packages, and fake pkg-config.
# NOTE: pkg-config is used from go build to obtain cflags and libs required to build C code; however
# for armhf we will explicitly pass these flags for go to use our custom sysroot instead of the system
# one. Alternatively pkg-config supports setting a prefix, but that would require patching the source code.
RUN if [ "${ARCH}" = "armhf" ]; then \
        set -e; \
        ln -s /bin/true /usr/bin/pkg-config; \
        curl -f http://raspbian.raspberrypi.org/raspbian/dists/${DEBIAN_VERSION}/main/binary-armhf/Packages.gz -o Packages.gz; \
        gunzip Packages.gz; \
        for pkg in \
            liblzma5 \
            liblzma-dev \
            libssl1.1 \
            libssl-dev \
            libglib2.0-0 \
            libglib2.0-dev \
            libpcre3 \
            libpcre3-dev \
            zlib1g \
            zlib1g-dev \
            libffi6 \
            libffi-dev \
            libmount1 \
            libmount-dev \
            libselinux1 \
            libselinux1-dev \
            libblkid1 \
            libblkid-dev \
            libuuid1 \
            uuid-runtime \
            uuid-dev \
        ; do \
            deb_package_url=$(grep Filename Packages | grep /${pkg}_ | grep armhf | tail -n1 | sed 's/Filename: //'); \
            echo "Downloading ${pkg}..."; \
            filename=$(basename $deb_package_url); \
            curl -L http://raspbian.raspberrypi.org/raspbian/${deb_package_url} -o $filename 2>/dev/null; \
            echo "Extracting ${pkg}..."; \
            ar -x ${pkg}_*_armhf.deb data.tar.xz; \
            for dir in ./lib ./usr/include ./usr/lib; do \
                ( tar -tf data.tar.xz ${dir} >/dev/null 2>/dev/null ) && \
                ( echo "   ${dir}..."; \
                  tar -C ${ARMV6_TOOLCHAIN_ROOT} \
                    -xf data.tar.xz  ${dir} ); \
            done; \
        done; \
        rm -f Packages data.tar.xz *.deb; \
    fi

RUN if [ "${ARCH}" = "arm64" ]; then \
        apt-get install -y gcc-aarch64-linux-gnu; \
    fi

# Golang environment, for cross-compiling the Mender client
ARG GOLANG_VERSION=1.14.7
RUN wget -q https://dl.google.com/go/go$GOLANG_VERSION.linux-amd64.tar.gz \
    && tar -C /usr/local -xzf go$GOLANG_VERSION.linux-amd64.tar.gz
ENV GOPATH "/root/go"
ENV PATH "$PATH:/usr/local/go/bin"
# Support building mender-client 2.3.x, since it does not have go modules support
# For newer clients with a go.mod file, this is a no-op however.
ENV GO111MODULE auto

# Import GPG key, if set
ARG GPG_KEY_BUILD=""
RUN if [ -n "$GPG_KEY_BUILD" ]; then \
        echo "$GPG_KEY_BUILD" | gpg --import; \
    fi

# TODO: Figure out why these packages are required
RUN if [ "${ARCH}" = "armhf" ]; then \
        apt-get install -y libmount1:armhf zlib1g:armhf; \
    fi

# Prepare the deb-package script
COPY mender-deb-package /usr/local/bin/
ENTRYPOINT  ["/usr/local/bin/mender-deb-package"]
