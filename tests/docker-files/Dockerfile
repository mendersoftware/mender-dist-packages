FROM alpine:3.9

# Docker image to emulate Raspbian stock image with QEMU. See tutorial at:
# https://github.com/wimvanderbauwhede/limited-systems/wiki/Raspbian-%22stretch%22-for-Raspberry-Pi-3-on-QEMU

RUN apk update && apk upgrade
RUN apk add qemu-system-arm

RUN mkdir /testing
COPY 2019-04-08-raspbian-mender-testing.img /testing/
COPY kernel-qemu-4.14.79-stretch /testing/
COPY versatile-pb.dtb /testing/

EXPOSE 5555

ENTRYPOINT ["/usr/bin/qemu-system-arm", "-kernel", "/testing/kernel-qemu-4.14.79-stretch", \
            "-dtb", "/testing/versatile-pb.dtb", "-m", "256", "-M", "versatilepb", \
            "-cpu", "arm1176", "-serial", "stdio", "-append", \
            "rw console=ttyAMA0 root=/dev/sda2 rootfstype=ext4 loglevel=8 rootwait fsck.repair=yes memtest=1", \
            "-drive", "file=/testing/2019-04-08-raspbian-mender-testing.img,format=raw", \
            "-no-reboot", "-device", "virtio-net-pci,netdev=unet", \
            "-netdev", "user,id=unet,hostfwd=tcp::5555-:22"]
