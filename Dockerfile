FROM debian:stretch

RUN apt-get update && apt-get install -y \
    build-essential \
    git wget \
    debhelper devscripts

# Versions to use
ARG MENDER_VERSION=2.0.0
ARG GOLANG_VERSION=1.11.5

# To provide support for Raspberry Pi Zero W a toolchain tuned for ARMv6 architecture must be used.
# https://tracker.mender.io/browse/MEN-2399
# Assumes $(pwd) is /
RUN wget -nc -q https://toolchains.bootlin.com/downloads/releases/toolchains/armv6-eabihf/tarballs/armv6-eabihf--glibc--stable-2018.11-1.tar.bz2 \
    && tar -xjf armv6-eabihf--glibc--stable-2018.11-1.tar.bz2 \
    && rm armv6-eabihf--glibc--stable-2018.11-1.tar.bz2
ENV CROSS_COMPILE "arm-buildroot-linux-gnueabihf"
ENV CC "$CROSS_COMPILE-gcc"
ENV PATH "$PATH:/armv6-eabihf--glibc--stable-2018.11-1/bin"

# Golang environment, for cross-compiling the Mender client
RUN wget -q https://dl.google.com/go/go$GOLANG_VERSION.linux-amd64.tar.gz \
    && tar -C /usr/local -xzf go$GOLANG_VERSION.linux-amd64.tar.gz
ENV GOPATH "/root/go"
ENV PATH "$PATH:/usr/local/go/bin"

# Build liblzma from source
RUN wget -q https://tukaani.org/xz/xz-5.2.4.tar.gz \
    && tar -C /root -xzf xz-5.2.4.tar.gz \
    && cd /root/xz-5.2.4 \
    && ./configure --host=$CROSS_COMPILE --prefix=/root/xz-5.2.4/install \
    && make \
    && make install
ENV LIBLZMA_INSTALL_PATH "/root/xz-5.2.4/install"

# Prepare the mender client source
RUN go get -d github.com/mendersoftware/mender
WORKDIR $GOPATH/src/github.com/mendersoftware/mender
RUN git checkout $MENDER_VERSION

# Prepare the deb-package script
ENV mender_version $MENDER_VERSION
COPY mender-deb-package /usr/local/bin/
ENTRYPOINT bash /usr/local/bin/mender-deb-package $mender_version
