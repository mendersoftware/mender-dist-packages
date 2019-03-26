FROM debian:stretch

RUN dpkg --add-architecture armhf && \
    apt-get update && apt-get install -y \
    build-essential crossbuild-essential-armhf \
    git wget \
    debhelper devscripts \
    liblzma-dev:armhf

# Versions to use
ARG MENDER_VERSION=2.0.0b1
ARG GOLANG_VERSION=1.11.5

# Set cross-compiler
ENV CC "arm-linux-gnueabihf-gcc"

# Golang environment, for cross-compiling the Mender client
RUN wget -q https://dl.google.com/go/go$GOLANG_VERSION.linux-amd64.tar.gz \
    && tar -C /usr/local -xzf go$GOLANG_VERSION.linux-amd64.tar.gz
ENV GOPATH "/root/go"
ENV PATH "$PATH:/usr/local/go/bin"

# Prepare the mender client source
RUN go get -d github.com/mendersoftware/mender
WORKDIR $GOPATH/src/github.com/mendersoftware/mender
RUN git checkout $MENDER_VERSION

# Prepare the deb-package script
ENV mender_version $MENDER_VERSION
COPY mender-deb-package /usr/local/bin/
ENTRYPOINT bash /usr/local/bin/mender-deb-package $mender_version
