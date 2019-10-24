FROM debian:stretch

RUN dpkg --add-architecture armhf && \
    dpkg --add-architecture arm64 && \
    apt-get update && apt-get install -y \
    build-essential \
    git wget \
    debhelper devscripts \
    liblzma-dev \
    liblzma-dev:armhf \
    liblzma-dev:arm64 \
    gcc-aarch64-linux-gnu

# To provide support for Raspberry Pi Zero W a toolchain tuned for ARMv6 architecture must be used.
# https://tracker.mender.io/browse/MEN-2399
RUN wget -nc -q https://toolchains.bootlin.com/downloads/releases/toolchains/armv6-eabihf/tarballs/armv6-eabihf--glibc--stable-2018.11-1.tar.bz2 \
    && tar -xjf armv6-eabihf--glibc--stable-2018.11-1.tar.bz2 \
    && rm armv6-eabihf--glibc--stable-2018.11-1.tar.bz2

# Golang environment, for cross-compiling the Mender client
ARG GOLANG_VERSION=1.11.5
RUN wget -q https://dl.google.com/go/go$GOLANG_VERSION.linux-amd64.tar.gz \
    && tar -C /usr/local -xzf go$GOLANG_VERSION.linux-amd64.tar.gz
ENV GOPATH "/root/go"
ENV PATH "$PATH:/usr/local/go/bin"

# Prepare the mender client source
ARG MENDER_VERSION=none
RUN if [ "$MENDER_VERSION" = none ]; then echo "MENDER_VERSION must be set!" 1>&2; exit 1; fi
RUN go get -d github.com/mendersoftware/mender
WORKDIR $GOPATH/src/github.com/mendersoftware/mender
RUN git checkout $MENDER_VERSION

# Prepare the deb-package script
ENV mender_version $MENDER_VERSION
COPY mender-deb-package /usr/local/bin/
COPY debian/* debian/
RUN cp support/mender.service debian/mender-client.service
ENTRYPOINT bash /usr/local/bin/mender-deb-package $mender_version
