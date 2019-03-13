FROM debian:stretch

#TODO: Verify Go version for mender 2.0.0 beta release
ARG MENDER_VERSION=2.0.0-beta
ARG GOLANG_VERSION=1.11.5

RUN dpkg --add-architecture armhf && \
    apt-get update && apt-get install -y \
    build-essential crossbuild-essential-armhf \
    git wget \
    debhelper devscripts \
    liblzma-dev:armhf

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
#TODO: replace this for the below command checkout after release
RUN git remote add kacf https://github.com/kacf/mender.git && git fetch kacf && git checkout kacf/update_modules
#RUN git checkout $MENDER_VERSION

ENV mender_version $MENDER_VERSION
COPY mender-deb-package /usr/local/bin/
ENTRYPOINT bash /usr/local/bin/mender-deb-package $mender_version
