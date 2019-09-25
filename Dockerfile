FROM debian:stretch


RUN dpkg --add-architecture armhf && \
    apt-get update && apt-get install -y \
    build-essential \
    git wget \
    debhelper devscripts \
    liblzma-dev:armhf

# To provide support for Raspberry Pi Zero W a toolchain tuned for ARMv6 architecture must be used.
# https://tracker.mender.io/browse/MEN-2399
RUN wget -nc -q https://toolchains.bootlin.com/downloads/releases/toolchains/armv6-eabihf/tarballs/armv6-eabihf--glibc--stable-2018.11-1.tar.bz2 \
    && tar -xjf armv6-eabihf--glibc--stable-2018.11-1.tar.bz2 \
    && rm armv6-eabihf--glibc--stable-2018.11-1.tar.bz2
ENV CROSS_COMPILE "arm-buildroot-linux-gnueabihf"
ENV CC "$CROSS_COMPILE-gcc"
ENV PATH "$PATH:/armv6-eabihf--glibc--stable-2018.11-1/bin"

# Golang environment, for cross-compiling the Mender client
ARG GOLANG_VERSION=1.11.5
RUN wget -q https://dl.google.com/go/go$GOLANG_VERSION.linux-amd64.tar.gz \
    && tar -C /usr/local -xzf go$GOLANG_VERSION.linux-amd64.tar.gz
ENV GOPATH "/root/go"
ENV PATH "$PATH:/usr/local/go/bin"

# Prepare the mender client source
ARG MENDER_VERSION=2.1.0
RUN go get -d github.com/mendersoftware/mender
WORKDIR $GOPATH/src/github.com/mendersoftware/mender
RUN git checkout $MENDER_VERSION

# Set the go CGO flags for the build
ENV CGO_CFLAGS="-idirafter /usr/include/"
ENV CGO_LDFLAGS="-L/usr/lib/arm-linux-gnueabihf/"

# Prepare the deb-package script
ENV mender_version $MENDER_VERSION
COPY mender-deb-package /usr/local/bin/
COPY debian/* debian/
ENTRYPOINT bash /usr/local/bin/mender-deb-package $mender_version
